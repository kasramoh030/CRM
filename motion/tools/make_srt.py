# -*- coding: utf-8 -*-
"""Exports .srt subtitle files (Persian narration + English captions) from the timeline.

Useful for platform captions, accessibility, or re-editing in Premiere/CapCut.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framebaz import brand as BR


def tc(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(tl, scenes, key, out, lead=0.55, tail=0.35):
    blocks = []
    for i, (sc, info) in enumerate(zip(scenes, tl["scenes"]), 1):
        txt = sc.get(key)
        if not txt:
            continue
        start = info["start"] + (info["lead"] if key == "vo" else 0.15)
        end = start + (info["vo_dur"] if key == "vo" and info.get("vo_dur") else info["dur"] - 0.4)
        end = min(end + tail if key == "vo" else end, info["start"] + info["dur"] - 0.05)
        blocks.append(f"{i}\n{tc(start)} --> {tc(end)}\n{txt}\n")
    with open(out, "w", encoding="utf-8-sig") as fh:
        fh.write("\n".join(blocks))
    print("wrote", out)
    return out


def main():
    brand, scenes = BR.load()
    with open("deliverables/timeline.json", encoding="utf-8") as fh:
        tl = json.load(fh)
    write_srt(tl, scenes, "vo", "deliverables/subtitles_fa.srt")
    write_srt(tl, scenes, "caption_en", "deliverables/subtitles_en.srt")


if __name__ == "__main__":
    main()
