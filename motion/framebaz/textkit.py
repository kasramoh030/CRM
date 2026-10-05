# -*- coding: utf-8 -*-
"""Persian (RTL) text shaping + typography helpers built on Pillow."""
import os
import re
import functools

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import ImageFont, ImageDraw

TOOLS = os.environ.get("FRAMEBAZ_TOOLS", "/home/user/.local/share/framebaz")
FONT_DIR = os.path.join(TOOLS, "fonts")

FA_RE = re.compile(r"[\u0600-\u06FF]")

# logical name -> filename
FONT_FILES = {
    "fa": "Vazirmatn-Black.ttf",
    "fa_xb": "Vazirmatn-ExtraBold.ttf",
    "fa_bold": "Vazirmatn-Bold.ttf",
    "fa_semi": "Vazirmatn-SemiBold.ttf",
    "fa_med": "Vazirmatn-Medium.ttf",
    "fa_reg": "Vazirmatn-Regular.ttf",
    "lat_disp": "Anton.ttf",
    "lat_heavy": "ArchivoBlack.ttf",
}


def is_fa(text):
    return bool(FA_RE.search(text))


@functools.lru_cache(maxsize=4096)
def shape(text):
    """Reshape + bidi-reorder Persian text so Pillow renders it correctly."""
    if not FA_RE.search(text):
        return text
    return get_display(arabic_reshaper.reshape(text))


@functools.lru_cache(maxsize=512)
def font(name, size):
    path = os.path.join(FONT_DIR, FONT_FILES.get(name, name))
    return ImageFont.truetype(path, int(round(size)))


def text_size(draw, text, f):
    box = draw.textbbox((0, 0), shape(text), font=f)
    return box[2] - box[0], box[3] - box[1]


def draw_text(draw, xy, text, f, fill, anchor="mm", stroke=0, stroke_fill=None, spacing=0):
    draw.text(xy, shape(text), font=f, fill=fill, anchor=anchor,
              stroke_width=int(stroke), stroke_fill=stroke_fill,
              spacing=spacing, align="center" if anchor in ("mm", "ma", "ms") else "left")
    return draw


def wrap(text, f, max_width, draw=None):
    """Word-wrap honouring RTL; returns logical (unshaped) lines."""
    tmp = draw or ImageDraw.Draw(__import__("PIL.Image", fromlist=["Image"]).new("RGB", (8, 8)))
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_size(tmp, trial, f)[0] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_paragraph(draw, xy, text, f, fill, max_width, line_gap=1.28,
                   anchor="mm", stroke=0, stroke_fill=None, align="center"):
    lines = wrap(text, f, max_width, draw)
    asc = f.getmetrics()[0]
    line_h = asc * line_gap
    total = line_h * len(lines)
    x, y = xy
    if anchor in ("mm", "mt", "mb"):
        pass
    cy = y - total / 2 + line_h / 2 if anchor[1] == "m" else (
        y + line_h / 2 if anchor[1] == "t" else y - total + line_h / 2)
    cx = x if anchor[0] == "l" else (x if anchor[0] == "m" else x)
    for i, ln in enumerate(lines):
        a = {"c": "mm", "l": "lm", "r": "rm"}.get(align, "mm")
        draw_text(draw, (cx, cy + i * line_h), ln, f, fill, anchor=a,
                  stroke=stroke, stroke_fill=stroke_fill)
    return total


def fit_font(text, name, max_width, start, min_size=24, draw=None):
    """Shrink font size until the (single-line) text fits max_width."""
    size = start
    while size > min_size:
        f = font(name, size)
        if draw is None:
            from PIL import Image
            d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        else:
            d = draw
        if text_size(d, text, f)[0] <= max_width:
            return f
        size -= 2
    return font(name, min_size)


def spaced(text, gap="\u2009"):
    """Wide letter-spacing for small Latin labels (Pillow has no tracking)."""
    return gap.join(list(text))
