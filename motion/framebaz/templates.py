# -*- coding: utf-8 -*-
"""Scene templates.  Each template draws one frame.

Signature: render(img, d, t, sc, B, S) -> PIL.Image (RGB, 1080x1920)
  t : local scene time in seconds
  sc: scene dict (from brand.py / brand.json)
  B : brand dict        S : style/animation settings dict

Layout contract: all content stays inside the safe box (100,300)-(930,1500);
the English subtitle pill sits at CAPTION_Y so nothing collides with it.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont

from . import fx
from .easings import (clamp, segment, lerp, smooth, out_back, out_elastic, out_expo,
                      out_cubic, in_out_cubic, in_out_quint, out_quart, stepped, EASINGS)
from .textkit import shape, font as F, draw_text, text_size, spaced

W, H = 1080, 1920
ANCH = (100, 300, 930, 1500)          # safe content box
ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
CAPTION_Y = 1372                      # burned-in English subtitle centre
WATERMARK_Y = 1520

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(n, sep="٬"):
    s = f"{int(round(n)):,}"
    if sep != ",":
        s = s.replace(",", sep)
    return s.translate(FA_DIGITS)


# --------------------------------------------------------------------------- #
# primitives
# --------------------------------------------------------------------------- #
def tracked(d, xy, text, f, fill, tracking=0.0, anchor="mm", stroke=0, stroke_fill=None, upper=True):
    """Draw text with letter tracking (Pillow has no tracking support)."""
    text = text.upper() if upper else text
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + tracking * max(len(text) - 1, 0)
    x, y = xy
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    for ch, cw in zip(text, widths):
        d.text((x, y), ch, font=f, fill=fill, anchor="l" + anchor[1],
               stroke_width=int(stroke), stroke_fill=stroke_fill)
        x += cw + tracking
    return total


def pill(d, cx, cy, text, f, bg, fg, padx=34, pady=16, radius=None, tracking=2.6, outline=None, ow=3):
    if isinstance(bg, str):
        bg = fx.hex2rgb(bg)
    if isinstance(fg, str):
        fg = fx.hex2rgb(fg)
    box = d.textbbox((0, 0), text, font=f, anchor="mm")
    tw = box[2] - box[0] + tracking * max(len(text) - 1, 0)
    th = box[3] - box[1]
    w, h = tw + padx * 2, th + pady * 2
    r = radius if radius is not None else h / 2
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=r,
                        fill=bg, outline=outline, width=ow)
    from .textkit import is_fa
    if is_fa(text):
        draw_text(d, (cx, cy), text, f, fg, anchor="mm")
    else:
        tracked(d, (cx, cy), text, f, fg, tracking, anchor="mm")
    return w, h


def card(d, box, radius, fill, shadow=18, shadow_alpha=110, outline=None, ow=4, offset=(0, 14)):
    x0, y0, x1, y1 = box
    if shadow:
        d.rounded_rectangle([x0 + offset[0], y0 + offset[1], x1 + offset[0], y1 + offset[1]],
                            radius=radius, fill=(0, 0, 0, shadow_alpha))
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                        outline=outline, width=ow)


def play_triangle(d, cx, cy, size, color, rot=0):
    pts = [(0, -1), (1.15, 0), (0, 1)]
    co, si = math.cos(rot), math.sin(rot)
    out = []
    for px, py in pts:
        x, y = px * size, py * size * 0.92
        out.append((cx + x * co - y * si, cy + x * si + y * co))
    d.polygon(out, fill=color)


def sparkle(d, cx, cy, r, color, rot=0.0, thin=0.24):
    pts = []
    for i in range(4):
        a = rot + i * math.pi / 2
        pts += [(cx + math.cos(a) * r, cy + math.sin(a) * r),
                (cx + math.cos(a + math.pi / 4) * r * thin, cy + math.sin(a + math.pi / 4) * r * thin)]
    d.polygon(pts, fill=color)


def arrow(d, x0, y0, x1, y1, color, width=14, head=30):
    d.line([x0, y0, x1, y1], fill=color, width=width)
    a = math.atan2(y1 - y0, x1 - x0)
    for s in (-1, 1):
        d.line([x1, y1, x1 - math.cos(a + s * 0.5) * head, y1 - math.sin(a + s * 0.5) * head],
               fill=color, width=width)


# --------------------------------------------------------------------------- #
# mascot assets (hand-drawn illustration uploaded by the client)
# --------------------------------------------------------------------------- #
_ASSETS = {}


def asset(name, height=None):
    """Loads assets/<name> (RGBA) scaled to `height`; cached across frames."""
    key = (name, height)
    if key not in _ASSETS:
        img = Image.open(os.path.join(ASSETS, name)).convert("RGBA")
        if height:
            img = img.resize((max(1, int(img.width * height / img.height)), int(height)),
                             Image.LANCZOS)
        _ASSETS[key] = img
    return _ASSETS[key]


def mascot_card(d, t, sc, B, S, x, y, height=700, delay=0.3, rot=-3.0, side="up"):
    """Pastes the hand-drawn mascot card with a spring-in + gentle bob."""
    img = asset("mascot_card.png", height)
    p = clamp(segment(t, delay, delay + 0.55))
    if p <= 0.01:
        return
    e = out_back(p)
    bob = math.sin(t * 1.6) * 6
    ang = rot * (1 - e)
    if side == "up":
        oy = (1 - e) * 140
        ox = 0.0
    else:
        ox = (1 - e) * 200 * (1 if side == "left" else -1)
        oy = 0.0
    layer = img.rotate(ang, resample=Image.BICUBIC, expand=True)
    x = int(x - layer.width / 2 + ox)
    y = int(y - layer.height / 2 + oy + bob)
    d._image.paste(layer, (x, y), layer)


def mascot_badge(d, t, sc, B, S, cx, cy, size=190, delay=0.2, ring=True, bob_amp=5):
    """Circular face badge with a pulsing 'speaking' ring."""
    img = asset("mascot_badge.png", size)
    p = out_back(clamp(segment(t, delay, delay + 0.5)))
    if p <= 0.01:
        return
    cy = cy + math.sin(t * 2.1) * bob_amp
    ln = img.width + int(36 + 26 * (0.5 + 0.5 * math.sin(t * 3.4)))
    if ring:
        d.ellipse([cx - ln / 2, cy - ln / 2, cx + ln / 2, cy + ln / 2],
                  outline=fx.hex2rgb(B["colors"][sc.get("accent", "yellow")]) + (150,), width=6)
    layer = img.resize((max(1, int(img.width * p)), max(1, int(img.height * p))), Image.LANCZOS)
    d._image.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)


# --------------------------------------------------------------------------- #
# background
# --------------------------------------------------------------------------- #
def bg_base(sc, B, t, S):
    """NOTE: cached gradients must be copied — drawing on the cached object would
    leak artwork between scenes that share the same background."""
    kind = sc.get("bg", "ink")
    C = B["colors"]
    if kind == "magenta":
        img = fx.linear_gradient(W, H, C["magenta"], "#C1125A", angle=115).copy()
    elif kind == "yellow":
        img = fx.linear_gradient(W, H, C["yellow"], "#FFC21F", angle=115).copy()
    elif kind == "lime":
        img = fx.linear_gradient(W, H, C["lime"], "#7FE03A", angle=115).copy()
    elif kind == "blue":
        img = fx.linear_gradient(W, H, "#16266F", "#070C2A", angle=120).copy()
    elif kind == "ink2":
        img = fx.linear_gradient(W, H, "#1A1533", "#08070F", angle=120).copy()
    else:
        img = fx.linear_gradient(W, H, C["ink"], "#050509", angle=120).copy()
    return img


def bg_motion(sc, d, B, t, S):
    light = sc.get("bg") in ("magenta", "yellow", "lime")
    tone = (0, 0, 0) if light else (255, 255, 255)
    alpha = 22 if light else 16
    kind = sc.get("bgfx", "stripes" if sc.get("bg") in ("ink", "ink2", "blue") else "dots")
    if kind == "stripes":
        lay = fx.stripe_field(W, H, spacing=96, width=30, color=tone + (alpha,),
                              angle=-32, offset=(t * 26) % 96)
        d._image.paste(lay, (0, 0), lay)
    else:
        for i in range(9):
            a = 0.10 - i * 0.008
            r = 150 + i * 96 + math.sin(t * 0.6 + i) * 6
            d.ellipse([540 - r, 1000 - r, 540 + r, 1000 + r],
                      outline=tone + (int(90 * max(a, 0.02)),), width=2)


def floating_particles(d, B, t, n=26, seed=3):
    rnd = random.Random(seed)
    for i in range(n):
        x = rnd.uniform(0, W)
        y0 = rnd.uniform(-200, H)
        sp, r = rnd.uniform(12, 46), rnd.uniform(2, 5.4)
        y = (y0 - t * sp) % (H + 300) - 150
        a = int(30 + 55 * (0.5 + 0.5 * math.sin(t * 1.7 + i)))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))


def base_frame(sc, B, t, S):
    img = bg_base(sc, B, t, S)
    d = ImageDraw.Draw(img, "RGBA")
    d._image = img
    bg_motion(sc, d, B, t, S)
    if sc.get("bg") in ("ink", "ink2", "blue"):
        floating_particles(d, B, t, seed=abs(hash(sc["id"])) % 99)
    return img, d


# --------------------------------------------------------------------------- #
# shared components
# --------------------------------------------------------------------------- #
def kicker(d, B, sc, t, y=336, color=None):
    C = B["colors"]
    col = color or (C["muted"] if sc.get("bg") in ("ink", "ink2", "blue") else (17, 17, 17))
    txt = sc.get("kicker_en", "")
    if not txt:
        return
    f = F("lat_heavy", 30)
    p = out_cubic(segment(t, 0.10, 0.55))
    if p <= 0:
        return
    x = ANCH[0]
    d.rounded_rectangle([x, y - 5, x + 42 * p, y + 5], radius=5, fill=fx.hex2rgb(C[sc.get("accent", "yellow")]))
    tracked(d, (x + 56 * p, y), txt, f, col, 3.4, anchor="lm")


def eng_caption(d, B, sc, t, y=CAPTION_Y, alpha_scale=1.0):
    txt = sc.get("caption_en")
    if not txt:
        return
    f = F("lat_heavy", 33)
    maxw = 880
    words, lines, cur = txt.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if d.textlength(trial, font=f) + 1.2 * len(trial) <= maxw - 62 or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    lh = 48
    bh = lh * len(lines) + 38
    a = out_cubic(segment(t, 0.35, 0.75)) * alpha_scale
    if a <= 0:
        return
    cx = W / 2
    yy = y + (1 - a) * 26
    d.rounded_rectangle([cx - maxw / 2, yy - bh / 2, cx + maxw / 2, yy + bh / 2],
                        radius=26, fill=(8, 8, 16, int(170 * a)))
    for i, ln in enumerate(lines):
        tracked(d, (cx, yy - bh / 2 + 30 + i * lh + 10), ln, f,
                (255, 255, 255, int(255 * a)), 1.2, anchor="mm")


def progress_bar(d, B, scene_idx, t_local, dur_local, n_scenes=8, y=152):
    m, gap = 40, 8
    seg_w = (W - m * 2 - gap * (n_scenes - 1)) / n_scenes
    for i in range(n_scenes):
        x0 = m + i * (seg_w + gap)
        d.rounded_rectangle([x0, y, x0 + seg_w, y + 9], radius=5, fill=(255, 255, 255, 70))
        f = 1.0 if i < scene_idx else (clamp(t_local / dur_local) if i == scene_idx else 0.0)
        if f > 0:
            d.rounded_rectangle([x0, y, x0 + seg_w * f, y + 9], radius=5, fill=B["colors"]["white"])


def watermark(d, B, sc, alpha=140, y=WATERMARK_Y):
    tracked(d, (W / 2, y), B["name_en"], F("lat_heavy", 25), (255, 255, 255, alpha), 6.0, anchor="mm")


def auto_persian_lines(d, B, sc, t, S, y, base_size=118, color=None, max_w=None, gap=0.09,
                       line_gap=1.14, stroke=0, stroke_fill=None, start=0.28, stagger=None,
                       style="pop", fit_pad=0):
    """Animate the hero Persian headline lines (auto-shrunk to fit the box)."""
    C = B["colors"]
    lines = [l for l in sc.get("fa_lines", []) if l]
    if not lines:
        return 0
    col = color or (C["white"] if sc.get("bg") in ("ink", "ink2", "blue", "magenta") else C["ink"])
    max_w = max_w or (ANCH[2] - ANCH[0])
    stag = stagger if stagger is not None else gap
    size = min(base_size, *[_fit_one(d, ln, "fa", max_w - fit_pad, base_size) for ln in lines])
    asc = F("fa", size).getmetrics()[0]
    lh = asc * line_gap
    total = lh * len(lines)
    y0 = y - total / 2 + lh / 2
    for i, ln in enumerate(lines):
        s = segment(t, start + i * stag, start + i * stag + 0.5)
        if s <= 0:
            continue
        if style == "pop":
            e = out_back(clamp(s))
        elif style == "stepped":
            e = out_back(stepped(clamp(s), S.get("stop_fps", 8)) / 1.0)
        else:
            e = out_cubic(clamp(s))
        yy = y0 + i * lh + (1 - e) * 60
        draw_text(d, (W / 2, yy), ln, F("fa", size), col, anchor="mm",
                  stroke=stroke, stroke_fill=stroke_fill)
    return total


def _fit_one(d, text, fname, max_w, start):
    size = start
    while size > 40:
        if text_size(d, text, F(fname, size))[0] <= max_w:
            return size
        size -= 2
    return 40


# --------------------------------------------------------------------------- #
# templates
# --------------------------------------------------------------------------- #
def tpl_hook(img, d, t, sc, B, S):
    C = B["colors"]
    kicker(d, B, sc, t, y=336)

    # ghost word behind the play button
    p = out_expo(segment(t, 0.12, 0.85))
    d.text((W / 2, 700), "VIDEO", font=F("lat_disp", int(400 * (1.0 + 0.22 * (1 - p)))),
           fill=(255, 255, 255, 38), anchor="mm")

    # play button
    s = out_elastic(segment(t, 0.18, 0.95))
    r = 140 * clamp(s)
    if r > 2:
        pulse = 1 + 0.05 * math.sin(t * 5.2)
        d.ellipse([W / 2 - r * pulse, 700 - r * pulse, W / 2 + r * pulse, 700 + r * pulse], fill=C["ink"])
        ring = 158 * clamp(out_back(segment(t, 0.3, 1.0)))
        if ring > 4:
            d.ellipse([W / 2 - ring, 700 - ring, W / 2 + ring, 700 + ring], outline=C["yellow"], width=8)
        play_triangle(d, W / 2 + 14, 700, r * 0.5, C["yellow"])

    auto_persian_lines(d, B, sc, t, S, y=1050, base_size=150, color=C["ink"], gap=0.12,
                       style="pop", start=0.42)
    ha = out_cubic(clamp(segment(t, 1.15, 1.7)))
    if ha > 0:
        tracked(d, (W / 2, 1225), B["handle"] + "  •  " + B["tagline_en"], F("lat_heavy", 26),
                (11, 11, 20, int(190 * ha)), 4.0, anchor="mm")
    return img


def tpl_services(img, d, t, sc, B, S):
    C = B["colors"]
    kicker(d, B, sc, t, y=336)
    auto_persian_lines(d, B, sc, t, S, y=520, base_size=88, color=C["white"], gap=0.1,
                       style="pop", start=0.10, max_w=880)
    cards = sc.get("cards", [])
    palette = [C["magenta"], C["cyan"], C["lime"], C["yellow"], C["pink"]]
    top, ch, cgap = 676, 182, 30
    for i, (en, fa) in enumerate(cards):
        st = 0.30 + i * 0.16
        s = out_back(clamp(segment(t, st, st + 0.55)))
        if s <= 0:
            continue
        x0, x1 = ANCH[0], ANCH[2]
        yy = top + i * (ch + cgap)
        shift = (1 - s) * 150
        col = palette[i % len(palette)]
        card(d, [x0 + shift, yy, x1 + shift, yy + ch], 40, (255, 255, 255, int(16 * s)),
             shadow=24, shadow_alpha=int(120 * s), outline=col, ow=5)
        d.text((x0 + 88 + shift, yy + ch / 2), f"0{i+1}", font=F("lat_disp", 78), fill=col, anchor="mm")
        draw_text(d, (x1 - 40 + shift, yy + ch / 2 - 26), fa, F("fa", 66), C["white"], anchor="rm")
        tracked(d, (x1 - 40 + shift, yy + ch / 2 + 40), en, F("lat_heavy", 24), C["muted"], 3.0, anchor="rm")
        d.ellipse([x0 + 142 + shift, yy + ch / 2 - 8, x0 + 158 + shift, yy + ch / 2 + 8], fill=C["white"])
    eng_caption(d, B, sc, t)
    return img


def tpl_education(img, d, t, sc, B, S):
    C = B["colors"]
    kicker(d, B, sc, t, y=336)

    # film-strip ribbon
    strip_y, sh = 400, 170
    d.rectangle([0, strip_y, W, strip_y + sh], fill=(11, 11, 20))
    off = (t * 90) % 120
    for i in range(-1, 12):
        x = i * 120 - off
        d.rounded_rectangle([x + 12, strip_y + 16, x + 100, strip_y + sh - 16], radius=10,
                            fill=(255, 255, 255, 26))
    for i in range(-1, 24):
        x = i * 60 - off
        d.rectangle([x + 12, strip_y + 5, x + 40, strip_y + 18], fill=(255, 255, 255, 60))
        d.rectangle([x + 12, strip_y + sh - 18, x + 40, strip_y + sh - 5], fill=(255, 255, 255, 60))

    # stop-motion 4-frame walk cycle
    px0, py0, px1, py1 = 170, 630, 910, 940
    card(d, [px0, py0, px1, py1], 40, C["ink"], shadow=26, shadow_alpha=130)
    phase = int(stepped(t, S.get("stop_fps", 8)) * 4) % 4
    steps = [(0, 0), (16, -12), (0, -20), (-16, -12)][phase]
    cx, cy = (px0 + px1) / 2, (py0 + py1) / 2 + 30
    d.line([px0 + 50, cy + 86, px1 - 50, cy + 86], fill=C["lime"], width=8)
    bx = cx - 60 + steps[0] * 2.2
    by = cy - 30 + steps[1] * 1.8
    d.rounded_rectangle([bx - 4, by - 96, bx + 76, by + 24], radius=18, fill=C["lime"])
    d.ellipse([bx + 6, by - 138, bx + 66, by - 78], fill=C["lime"])
    d.rectangle([bx + 8, by + 24, bx + 26, by + 66], fill=C["lime"])
    d.rectangle([bx + 48, by + 24, bx + 66, by + 66], fill=C["lime"])
    d.ellipse([bx + 40, by - 118, bx + 50, by - 108], fill=C["ink"])
    tracked(d, (px1 - 26, py0 + 36), f"FRAME {phase+1:02d}/04", F("lat_heavy", 22), C["muted"], 3.0, anchor="rm")
    d.rounded_rectangle([px0 + 26, py1 - 44, px1 - 26, py1 - 26], radius=9, fill=(255, 255, 255, 30))
    d.rounded_rectangle([px0 + 26, py1 - 44, px0 + 26 + (px1 - px0 - 52) * ((phase + 1) / 4), py1 - 26],
                        radius=9, fill=C["lime"])

    auto_persian_lines(d, B, sc, t, S, y=1080, base_size=118, color=C["ink"], gap=0.14,
                       style="stepped", start=0.45, max_w=900)
    s = out_back(clamp(segment(t, 1.05, 1.6)))
    if s > 0:
        pill(d, W / 2 - 110, 1250, "۲۴ فریم در ثانیه", F("fa", 40), (11, 11, 20), C["lime"], tracking=0.5)
    eng_caption(d, B, sc, t)
    return img


def tpl_process(img, d, t, sc, B, S):
    C = B["colors"]
    kicker(d, B, sc, t, y=336)
    items = [x for x in sc.get("fa_lines", []) if x]
    n = len(items)
    top, bot = 620, 1210
    line_x = 300
    p = out_cubic(segment(t, 0.10, 1.45))
    d.rounded_rectangle([line_x - 5, top, line_x + 5, bot], radius=6, fill=(255, 255, 255, 40))
    if p > 0:
        d.rounded_rectangle([line_x - 5, top, line_x + 5, top + (bot - top) * p], radius=6, fill=C["cyan"])
    for i, label in enumerate(items):
        cy = top + (bot - top) * (i / max(n - 1, 1))
        s = out_back(clamp(segment(t, 0.15 + i * 0.24, 0.65 + i * 0.24)))
        if s <= 0:
            continue
        active = clamp(p) >= (i / max(n - 1, 1)) - 0.001
        r = 32 * clamp(s)
        d.ellipse([line_x - r - 12, cy - r - 12, line_x + r + 12, cy + r + 12],
                  outline=C["cyan"] if active else (255, 255, 255, 70), width=6)
        d.ellipse([line_x - r, cy - r, line_x + r, cy + r], fill=C["cyan"] if active else C["ink2"])
        d.text((line_x, cy), f"{i+1}", font=F("lat_disp", 38), fill=C["ink"], anchor="mm")
        sh = (1 - s) * 80
        draw_text(d, (line_x + 92 + sh, cy - 14), label, F("fa", 70), C["white"], anchor="lm")
        tracked(d, (line_x + 92 + sh, cy + 48), f"STEP 0{i+1}", F("lat_heavy", 22), C["muted"], 3.0, anchor="lm")
    if p > 0.01:
        sparkle(d, line_x, top + (bot - top) * clamp(p), 24, C["yellow"], rot=t * 2.0)
    eng_caption(d, B, sc, t)
    return img


def tpl_results(img, d, t, sc, B, S):
    C = B["colors"]
    kicker(d, B, sc, t, y=336)
    auto_persian_lines(d, B, sc, t, S, y=470, base_size=84, color=C["white"], start=0.06, max_w=880)

    # giant Persian-number counter (Vazirmatn has Persian digits, Anton does not)
    s = clamp(segment(t, 0.15, 1.25))
    val = int(lerp(0, 300, in_out_quint(s)))
    draw_text(d, (W / 2, 620), f"+{fa_num(val)}%", F("fa", 196), C["white"], anchor="mm")
    tracked(d, (W / 2, 745), "MORE VIEWS", F("lat_heavy", 28), C["lime"], 5.0, anchor="mm")

    # bar chart
    base_y, maxh = 1060, 250
    bars = [0.34, 0.62, 1.0, 0.78]
    bx0, bw, bgap = 190, 130, 60
    d.line([bx0 - 40, base_y, bx0 + 4 * bw + 3 * bgap + 40, base_y], fill=(255, 255, 255, 80), width=6)
    for i, v in enumerate(bars):
        e = out_back(clamp(segment(t, 0.4 + i * 0.13, 1.0 + i * 0.13)))
        hgt = maxh * v * clamp(e)
        x = bx0 + i * (bw + bgap)
        col = C["lime"] if i == 2 else C["cyan"]
        d.rounded_rectangle([x, base_y - hgt, x + bw, base_y], radius=16, fill=col)
    # chips
    stats = sc.get("stats", [])
    y = 1200
    for i, (big, fa, en) in enumerate(stats):
        st = 1.15 + i * 0.16
        a = out_back(clamp(segment(t, st, st + 0.5)))
        if a <= 0:
            continue
        x = 233 + i * 307
        d.rounded_rectangle([x - 128, y - 66, x + 128, y + 66], radius=30,
                            fill=(255, 255, 255, int(24 * a)),
                            outline=(255, 255, 255, int(90 * a)), width=3)
        draw_text(d, (x, y - 24), big, F("fa", 44), C["white"], anchor="mm")
        tracked(d, (x, y + 28), en, F("lat_heavy", 20), C["muted"], 2.4, anchor="mm")
    eng_caption(d, B, sc, t)
    return img


def tpl_portfolio(img, d, t, sc, B, S):
    C = B["colors"]
    kicker(d, B, sc, t, y=336)
    auto_persian_lines(d, B, sc, t, S, y=440, base_size=84, color=C["white"], start=0.08, max_w=880)

    cols, rows = 2, 3
    gw, gh = 400, 196
    gx, gy = 140, 600
    gapx, gapy = 40, 20
    palettes = [(C["magenta"], C["yellow"]), (C["cyan"], C["ink"]), (C["lime"], C["ink"]),
                (C["yellow"], C["magenta"]), (C["pink"], C["ink"]), (C["white"], C["magenta"])]
    for i in range(cols * rows):
        st = 0.55 + i * 0.10
        s = out_back(clamp(segment(t, st, st + 0.5)))
        if s <= 0:
            continue
        c, r = i % cols, i // cols
        x0 = gx + c * (gw + gapx)
        y0 = gy + r * (gh + gapy)
        bob = math.sin(t * 1.1 + i) * 5
        off = (1 - s) * 120
        a, b = palettes[i % len(palettes)]
        lay = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle([0, 0, gw - 1, gh - 1], radius=24, fill=a)
        ld.ellipse([gw * 0.56, -70, gw * 1.35, gh * 0.75], fill=b)
        ld.rounded_rectangle([22, gh - 74, gw - 22, gh - 22], radius=12, fill=(0, 0, 0, 60))
        ld.text((40, gh - 48), f"0{i+1}", font=F("lat_disp", 34), fill=(255, 255, 255, 240), anchor="lm")
        ld.text((gw - 40, gh - 48), "REEL", font=F("lat_heavy", 20), fill=(255, 255, 255, 200), anchor="rm")
        play_triangle(ld, gw / 2, gh / 2 - 22, 38, (255, 255, 255, 235))
        lay = lay.rotate(-3 + (i % 3) * 3, resample=Image.BILINEAR, expand=False)
        img.paste(lay, (int(x0 + off), int(y0 + bob)), lay)

    a = out_cubic(clamp(segment(t, 1.5, 2.0)))
    if a > 0:
        tracked(d, (W / 2, 1290), "PORTFOLIO  •  " + B["handle"], F("lat_heavy", 30),
                (255, 255, 255, int(215 * a)), 4.0, anchor="mm")
        arrow(d, W / 2 + 120, 1290, W / 2 + 30, 1290, (255, 255, 255, int(200 * a)), width=9, head=22)
    eng_caption(d, B, sc, t)
    return img


def tpl_cta(img, d, t, sc, B, S):
    C = B["colors"]
    kicker(d, B, sc, t, y=336, color=(58, 16, 32))
    mrgb = fx.hex2rgb(C["magenta"])
    s = out_back(clamp(segment(t, 0.15, 0.9)))
    bw, bh = 800, 230
    cx, cy = W / 2, 780 + (1 - s) * 120
    if s > 0:
        d.rounded_rectangle([cx - bw / 2, cy - bh / 2 + 16, cx + bw / 2, cy + bh / 2 + 16],
                            radius=62, fill=(0, 0, 0, 90))
        d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=62, fill=C["magenta"])
        draw_text(d, (cx, cy), sc.get("fa_lines", ["دایرکت بده"])[0], F("fa", 92), C["white"], anchor="mm")
    for i in range(3):
        ph = (t * 0.55 + i * 0.33) % 1.0
        r = 290 + ph * 300
        d.ellipse([cx - r, cy - r * 0.97, cx + r, cy + r * 0.97],
                  outline=mrgb + (int(120 * (1 - ph)),), width=6)

    fa_ = out_expo(segment(t, 0.8, 1.6))
    if fa_ > 0:
        px = lerp(W + 200, cx + 400, fa_)
        py = lerp(-100, cy - 300, fa_)
        pl = [(0, 0), (-150, 60), (-56, 74), (-30, 140)]
        d.polygon([(px + x, py + y) for x, y in pl], fill=C["ink"])
        for k in range(5):
            tt = clamp(fa_ - k * 0.07)
            tx, ty = lerp(W + 200, cx + 400, tt), lerp(-100, cy - 300, tt)
            rr = max(3.0, 9 - k * 1.4)
            d.ellipse([tx - rr, ty + 34 + k * 10, tx + rr, ty + 34 + k * 10 + rr * 2],
                      fill=(11, 11, 20, int(110 * (1 - k / 5))))
    a = out_cubic(clamp(segment(t, 1.2, 1.8)))
    if a > 0:
        tracked(d, (W / 2, 1090), "DM  •  " + B["handle"], F("lat_heavy", 42), C["ink"], 5.0, anchor="mm")
        tracked(d, (W / 2, 1170), B["tagline_en"], F("lat_heavy", 26),
                (11, 11, 20, int(175 * a)), 5.0, anchor="mm")
    eng_caption(d, B, sc, t)
    return img


def tpl_outro(img, d, t, sc, B, S):
    C = B["colors"]
    mascot_badge(d, t, sc, B, S, cx=W / 2, cy=415, size=168, delay=0.15)
    s = out_elastic(clamp(segment(t, 0.1, 0.9)))
    cx, cy = W / 2, 600
    size = 200 * clamp(s)
    if size > 4:
        d.rounded_rectangle([cx - size / 2, cy - size / 2 + 14, cx + size / 2, cy + size / 2 + 14],
                            radius=58, fill=(0, 0, 0, 80))
        d.rounded_rectangle([cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2],
                            radius=58, fill=C["ink"])
        play_triangle(d, cx + 12, cy, size * 0.26, C["yellow"])
    a = out_cubic(clamp(segment(t, 0.45, 0.95)))
    if a > 0:
        tracked(d, (W / 2, cy + size / 2 + 112), B["name_en"], F("lat_disp", 82), C["white"], 9.0, anchor="mm")
        draw_text(d, (W / 2, cy + size / 2 + 205), sc.get("fa_lines", ["پیجت رو قاب کن"])[0],
                  F("fa", 72), C["ink"], anchor="mm")
    chips = [("FOLLOW", C["ink"]), ("SAVE", C["ink"]), ("SHARE", C["ink"])]
    for i, (txt, bg) in enumerate(chips):
        st = 0.95 + i * 0.15
        e = out_back(clamp(segment(t, st, st + 0.5)))
        if e <= 0:
            continue
        x = 233 + i * 307
        w = 240 * clamp(e)
        d.rounded_rectangle([x - w / 2, 1080 - 50, x + w / 2, 1080 + 50], radius=50, fill=bg)
        tracked(d, (x, 1080), txt, F("lat_heavy", 28), C["white"], 3.0, anchor="mm")
    ha = out_cubic(clamp(segment(t, 1.5, 2.0)))
    if ha > 0:
        tracked(d, (W / 2, 1200), B["gate_handle"] if False else B["handle"], F("lat_heavy", 40),
                (255, 255, 255, int(235 * ha)), 4.0, anchor="mm")
        tracked(d, (W / 2, 1275), B["tagline_en"], F("lat_heavy", 24),
                (255, 255, 255, int(170 * ha)), 5.0, anchor="mm")
    return img


def tpl_host(img, d, t, sc, B, S):
    """Introduces the maker: hand-drawn card + face badge + hero line."""
    C = B["colors"]
    kicker(d, B, sc, t, y=336, color=C["muted"])
    auto_persian_lines(d, B, sc, t, S, y=490, base_size=100, color=C["white"],
                       start=0.12, gap=0.14, max_w=880)
    mascot_badge(d, t, sc, B, S, cx=862, cy=716, size=170, delay=0.95)
    mascot_card(d, t, sc, B, S, x=W / 2 - 8, y=1010, height=620, delay=0.45, rot=-4)
    a = out_cubic(clamp(segment(t, 1.35, 1.9)))
    if a > 0:
        tracked(d, (W / 2, 1392), "IDEA  /  STORYBOARD  /  MOTION", F("lat_heavy", 25),
                (255, 255, 255, int(205 * a)), 4.0, anchor="mm")
    eng_caption(d, B, sc, t, y=248)
    return img


TEMPLATES = {
    "hook": tpl_hook, "services": tpl_services, "education": tpl_education,
    "process": tpl_process, "results": tpl_results, "portfolio": tpl_portfolio,
    "cta": tpl_cta, "outro": tpl_outro, "host": tpl_host,
}


def render_scene(sc, B, S, t, dur, idx, n_scenes):
    """Full pipeline for a single scene frame -> PIL.Image (RGB)."""
    img, d = base_frame(sc, B, t, S)
    TEMPLATES[sc["template"]](img, d, t, sc, B, S)
    progress_bar(d, B, idx, t, dur, n_scenes=n_scenes)
    watermark(d, B, sc)
    return img
