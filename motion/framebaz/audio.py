# -*- coding: utf-8 -*-
"""Audio timeline builder.

* decodes each Persian voice-over clip (no ffprobe needed — we decode to raw PCM),
* lays the narration out scene by scene with lead-in / tail gaps,
* adds an optional subtle rhythmic music bed,
* writes out/audio.m4a + out/timeline.json (scene start/duration/frames).
"""
import json
import math
import os
import subprocess
import wave

import numpy as np

from . import brand as BR

TOOLS = os.environ.get("FRAMEBAZ_TOOLS", "/home/user/.local/share/framebaz")
FFMPEG = os.path.join(TOOLS, "bin", "ffmpeg")
SR = 44100


def ffmpeg(*args):
    return subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *args],
                          check=True, capture_output=True)


def decode(path):
    """-> float32 mono numpy array at SR."""
    out = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", path,
                          "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def _env(n, atk, rel):
    e = np.ones(n, np.float32)
    a = min(int(atk * SR), n // 2)
    r = min(int(rel * SR), n // 2)
    if a:
        e[:a] = np.linspace(0, 1, a) ** 1.5
    if r:
        e[-r:] = np.linspace(1, 0, r) ** 1.5
    return e


def _kick(dur=0.32, f0=118.0, f1=44.0):
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 22)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 9.5)
    click = np.random.default_rng(3).normal(0, 0.25, t.size) * np.exp(-t * 90)
    return (body + click).astype(np.float32)


def _hat(dur=0.06, bright=0.6):
    t = np.arange(int(dur * SR)) / SR
    n = np.random.default_rng(11).normal(0, 1, t.size)
    # crude high-pass: difference of noise
    hp = np.diff(np.concatenate([[0.0], n]))
    return (hp * np.exp(-t * 55) * bright).astype(np.float32)


def music_bed(total_s, bpm=104.0, level=0.085, seed=5):
    """Soft rhythmic bed: kick on the beat, hats off-beat, low drone. Deliberately
    quiet so it never fights the narration."""
    n = int(total_s * SR) + SR
    out = np.zeros(n, np.float32)
    beat = 60.0 / bpm
    k, h = _kick(), _hat()
    i = 0
    while i * beat / 2 < total_s:
        pos = int(i * beat / 2 * SR)
        if i % 2 == 0:                                     # kick on the beat
            out[pos:pos + k.size] += k * (1.0 if i % 4 == 0 else 0.72)
        else:                                              # hat on the off-beat
            out[pos:pos + h.size] += h * (0.55 if i % 4 == 3 else 0.35)
        i += 1
    # low drone with slow tremolo
    t = np.arange(n) / SR
    out += (np.sin(2 * np.pi * 55 * t) * 0.5 + np.sin(2 * np.pi * 82.4 * t) * 0.25) * \
        (0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t)) * 0.09
    # duck the very start/end
    out *= _env(n, 0.4, 1.4)
    return out * level


def normalize(x, peak=0.89):
    m = float(np.max(np.abs(x))) or 1.0
    return (x * (peak / m)).astype(np.float32)


def build(vo_dir="audio", out_dir="out", bed=True, fps=None, brand_json=None,
          lead_default=0.5, tail_default=0.5, only=None,
          audio_name="audio.m4a", timeline_name="timeline.json"):
    os.makedirs(out_dir, exist_ok=True)
    brand, scenes = BR.load(brand_json)
    if only:
        keep = [s.strip() for s in only.split(",") if s.strip()]
        order = {sid: k for k, sid in enumerate(keep)}
        scenes = sorted([s for s in scenes if s["id"] in order], key=lambda s: order[s["id"]])
        brand = dict(brand, scenes=scenes)
    fps = fps or brand.get("fps", 30)

    BR_INDEX = {s["id"]: i for i, s in enumerate(BR.SCENES)}
    clips, vdur = [], []
    for i, sc in enumerate(scenes):
        path = os.path.join(vo_dir, f"vo_{BR_INDEX.get(sc['id'], i):02d}.mp3")
        if not os.path.exists(path):
            print(f"[audio] MISSING {path} — scene {sc['id']} will be silent")
            clips.append(np.zeros(0, np.float32))
            vdur.append(0.0)
            continue
        a = decode(path)
        clips.append(a)
        vdur.append(len(a) / SR)

    # scene durations
    timeline, t0 = [], 0.0
    for i, sc in enumerate(scenes):
        lead = float(sc.get("lead", lead_default))
        tail = float(sc.get("tail", tail_default))
        dur = max(float(sc.get("min_dur", 3.0)), lead + vdur[i] + tail)
        dur = math.ceil(dur * fps) / fps                      # whole frames
        timeline.append(dict(id=sc["id"], start=t0, dur=dur, vo_dur=vdur[i],
                             lead=lead, vo_start=t0 + lead, frames=int(round(dur * fps))))
        t0 += dur
    total = t0

    # lay out the mix
    n = int(total * SR) + SR // 2
    mix = np.zeros(n, np.float32)
    for i, sc in enumerate(scenes):
        if clips[i].size == 0:
            continue
        c = clips[i] * _env(clips[i].size, 0.02, 0.05)
        pos = int((timeline[i]["vo_start"]) * SR)
        end = min(pos + c.size, n)
        mix[pos:end] += c[:end - pos]
    if bed:
        mix[:n] += music_bed(total, level=0.085)[:n]
    mix = normalize(mix, 0.9)
    # gentle limiter
    mix = np.tanh(mix * 1.12) * 0.94

    wav = os.path.join(out_dir, "_mix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    m4a = os.path.join(out_dir, audio_name)
    ffmpeg("-i", wav, "-c:a", "aac", "-b:a", "192k", "-ac", "2", m4a)
    os.remove(wav)

    with open(os.path.join(out_dir, timeline_name), "w", encoding="utf-8") as fh:
        json.dump(dict(fps=fps, total=total, scenes=timeline), fh, ensure_ascii=False, indent=2)
    print(f"[audio] {audio_name} {total:.2f}s | " + " ".join(f"{s['id']}:{s['dur']:.2f}s" for s in timeline))
    return dict(fps=fps, total=total, scenes=timeline)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-bed", action="store_true")
    ap.add_argument("--vo-dir", default="audio")
    ap.add_argument("--out", default="out")
    ap.add_argument("--only", default="")
    ap.add_argument("--cut", default="")
    ap.add_argument("--audio-name", default="")
    a = ap.parse_args()
    only = a.only or None
    name = a.audio_name or "audio.m4a"
    tl_name = "timeline.json"
    if a.cut:
        with open("brand.json", encoding="utf-8") as fh:
            cuts = json.load(fh).get("cuts", {})
        only = ",".join(cuts[a.cut])
        suffix = f"{a.cut}s" if a.cut.isdigit() else a.cut
        name = a.audio_name or f"audio_{suffix}.m4a"
        tl_name = f"timeline_{suffix}.json"
    build(a.vo_dir, a.out, bed=not a.no_bed, only=only, audio_name=name, timeline_name=tl_name)
