# -*- coding: utf-8 -*-
"""Static cover image (1080x1920) for the Reel / Story — same art direction as the video."""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framebaz import brand as BR, fx
from framebaz.textkit import font as F, draw_text
from framebaz.templates import tracked, play_triangle, ANCH, W, H


def main(out="out/cover.png", brand_json=None):
    brand, scenes = BR.load(brand_json)
    C = brand["colors"]
    img = fx.linear_gradient(W, H, C["magenta"], "#C1125A", angle=115).copy()
    d = ImageDraw.Draw(img, "RGBA")
    lay = fx.stripe_field(W, H, spacing=96, width=30, color=(0, 0, 0, 22), angle=-32, offset=0)
    img.paste(lay, (0, 0), lay)

    # logo lockup
    size = 250
    cx, cy = W / 2, 640
    d.rounded_rectangle([cx - size / 2, cy - size / 2 + 16, cx + size / 2, cy + size / 2 + 16],
                        radius=60, fill=(0, 0, 0, 90))
    d.rounded_rectangle([cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2],
                        radius=60, fill=C["ink"])
    play_triangle(d, cx + 14, cy, size * 0.26, C["yellow"])

    tracked(d, (W / 2, cy + size / 2 + 118), brand["name_en"], F("lat_disp", 96), C["white"], 9.0, anchor="mm")
    draw_text(d, (W / 2, cy + size / 2 + 225), "موشن استوری · ریلز · تیزر", F("fa", 66), C["ink"], anchor="mm")

    # headline
    draw_text(d, (W / 2, 1090), "پیجت رو قاب کن", F("fa", 132), C["white"], anchor="mm")

    # CTA button
    d.rounded_rectangle([W / 2 - 330, 1250, W / 2 + 330, 1370], radius=60, fill=C["ink"])
    draw_text(d, (W / 2, 1310), "دایرکت بده", F("fa", 68), C["yellow"], anchor="mm")
    tracked(d, (W / 2, 1450), "MOTION GRAPHICS  •  MOTION STORY  •  REELS", F("lat_heavy", 26),
            (255, 255, 255, 215), 3.4, anchor="mm")
    tracked(d, (W / 2, 1540), brand["handle"], F("lat_heavy", 40), C["yellow"], 6.0, anchor="mm")

    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print("wrote", out)
    return out


if __name__ == "__main__":
    main()
