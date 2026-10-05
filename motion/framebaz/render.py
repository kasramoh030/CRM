# -*- coding: utf-8 -*-
"""Video renderer: draws every frame and pipes raw RGB into ffmpeg.

Features
  * per-scene timing driven by deliverables/timeline.json (narration aware)
  * whip-pan transitions with motion smear
  * zoom punch-in at every scene entry
  * film grain + vignette + subtle chromatic aberration
  * 1080x1920 @ 30fps H.264 + AAC, Reels/Story friendly
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

from . import brand as BR
from . import fx, templates as T
from .easings import clamp, smooth, out_cubic

DEFAULT_STYLE = dict(grain=0.012, grain_block=2, chroma=2.0, maxrate="6M", bufsize="12M")

TOOLS = os.environ.get("FRAMEBAZ_TOOLS", "/opt/framebaz-tools")
FFMPEG = os.path.join(TOOLS, "bin", "ffmpeg")
W, H = 1080, 1920


# --------------------------------------------------------------------------- #
# frame styling
# --------------------------------------------------------------------------- #
def style_frame(img, sc, t, S, punch):
    """zoom punch + film grain + vignette (+ gate weave on 'film' scenes)."""
    if punch > 0.001:
        k = 1.0 + 0.075 * punch
        w, h = int(W / k), int(H / k)
        x0, y0 = (W - w) // 2, (H - h) // 2
        img = img.crop((x0, y0, x0 + w, y0 + h)).resize((W, H), Image.BILINEAR)
    arr = fx.to_np(img)
    if sc.get("weave"):
        arr = fx.chromatic(arr, S.get("chroma", 2.0))
    arr = fx.vignette(arr, 0.30, 1.35)
    arr = fx.add_grain(arr, S.get("grain", 0.012), frame=int(t * S.get("fps", 30)),
                       block=int(S.get("grain_block", 2)))
    return fx.to_img(arr)


def mux(video, audio, out, fade_out=0.6):
    """Attach a narration/music mix to a rendered video (stream copy for video)."""
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-i", audio,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    print(f"[mux] {out}")
    return out


def poster(video, out, t=1.2):
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(t),
                    "-i", video, "-frames:v", "1", out], check=True)
    return out


def render_frames(tl, out_path, brand_json=None, style=None, limit=None, sheet=None,
                  progress_every=30, only=None, audio="deliverables/audio.m4a", crf="20"):
    brand, scenes = BR.load(brand_json)
    if only:
        keep = [s.strip() for s in only.split(",") if s.strip()]
        scenes = [s for s in scenes if s["id"] in keep]
    S = dict(DEFAULT_STYLE)
    S.update(style or {})
    S.setdefault("fps", tl["fps"])
    S.setdefault("stop_fps", 8)
    fps = tl["fps"]
    # scene boundaries in frames
    bounds, acc = [], 0
    for sc, info in zip(scenes, tl["scenes"]):
        bounds.append((acc, acc + info["frames"], sc, info))
        acc += info["frames"]
    total_frames = acc
    if limit:
        total_frames = min(total_frames, limit)

    TR = int(round(0.30 * fps))            # transition length in frames
    PUNCH = int(round(0.28 * fps))
    entry_cache = {}
    if sheet:
        os.makedirs(os.path.dirname(sheet) or ".", exist_ok=True)

    audio_args = ["-i", audio] if audio else []
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"] + \
          audio_args + [
           "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
           "-maxrate", str(S.get("maxrate", "6M")), "-bufsize", str(S.get("bufsize", "12M")),
           "-profile:v", "high", "-level", "4.1", "-g", str(fps * 2), "-bf", "2",
           "-movflags", "+faststart", "-an" if not audio else "-c:a", "-b:a", "192k", "-shortest",
           out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t_start = time.time()
    thumbs = []
    for f in range(total_frames):
        idx, sc, info = 0, scenes[0], tl["scenes"][0]
        for i, (a, b, s, n) in enumerate(bounds):
            if a <= f < b:
                idx, sc, info = i, s, n
                break
        t_local = (f - bounds[idx][0]) / fps
        dur = info["dur"]
        punch = 1.0 - out_cubic(clamp(t_local / (PUNCH / fps))) if t_local < PUNCH / fps else 0.0

        img = T.render_scene(sc, brand, S, t_local, dur, idx, len(scenes))

        # --- transition: whip-pan into the next scene -------------------------
        rem = (bounds[idx][1] - f)
        if idx + 1 < len(bounds) and rem <= TR:
            p = smooth(clamp(1.0 - rem / TR))
            nxt = bounds[idx + 1]
            if idx not in entry_cache:
                entry_cache[idx] = T.render_scene(nxt[2], brand, S, 0.0, nxt[3]["dur"],
                                                  idx + 1, len(scenes))
            nxt_img = entry_cache[idx]
            layer = Image.new("RGB", (W, H), (0, 0, 0))
            dx = int(W * p)
            layer.paste(img, (-dx, 0))
            layer.paste(nxt_img, (W - dx, 0))
            smear = math.sin(math.pi * p) ** 1.4
            layer = fx.step_blur(layer, min(1.0, smear * 0.9))
            arr = fx.to_np(layer)
            arr = fx.chromatic(arr, 2 + 8 * smear)
            img = fx.to_img(arr)
        elif idx > 0 and (f - bounds[idx][0]) < TR * 0.35:
            pass  # entry side is already covered by the previous scene's exit blend

        img = style_frame(img, sc, t_local, S, punch)
        proc.stdin.write(np.asarray(img, np.uint8).tobytes())

        if sheet and f % max(1, int(fps / 4)) == 0:
            thumbs.append(img.resize((135, 240), Image.BILINEAR))
        if progress_every and f % progress_every == 0 and f:
            el = time.time() - t_start
            print(f"  frame {f}/{total_frames}  ({f/el:.1f} fps, eta {max(0,(total_frames-f)/max(f/el,.01)):.0f}s)",
                  flush=True)
    proc.stdin.close()
    rc = proc.wait()
    if rc != 0:
        raise SystemExit(f"ffmpeg failed with code {rc}")
    if sheet and thumbs:
        cols = 8
        rows = (len(thumbs) + cols - 1) // cols
        sh = Image.new("RGB", (cols * 135, rows * 240), (12, 12, 16))
        for k, th in enumerate(thumbs):
            sh.paste(th, ((k % cols) * 135, (k // cols) * 240))
        sh.save(sheet)
    print(f"[render] {out_path}  {total_frames} frames in {time.time()-t_start:.0f}s")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="deliverables/framebaz_reel_full.mp4")
    ap.add_argument("--timeline", default="deliverables/timeline.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--audio", default="deliverables/audio.m4a")   # empty string => video only
    ap.add_argument("--crf", default="22")
    a = ap.parse_args()
    with open(a.timeline, encoding="utf-8") as fh:
        tl = json.load(fh)
    render_frames(tl, a.out, limit=a.limit or None, sheet=a.sheet or None,
                  only=a.only or None, audio=a.audio, crf=a.crf)
