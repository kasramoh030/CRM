# -*- coding: utf-8 -*-
"""Turns the uploaded mascot illustration into transparent PNG assets.

The illustration sits on plain paper, so the paper is removed with a
*border-connected* flood fill: only the background that touches the image edge
becomes transparent, which keeps interior paper areas (e.g. the white inside the
film-strip frames or the clapperboard) solid.

Outputs (motion/assets/):
  mascot.png        full character, transparent background, trimmed
  mascot_head.png   square head crop (for the little "face-cam" avatar badge)
  mascot_thumb.png  small version for storyboards / docs
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

SRC_DEFAULT = "assets/mascot_source.png"


def estimate_bg(a):
    border = np.concatenate([a[0:10].reshape(-1, 3), a[-10:].reshape(-1, 3),
                             a[:, 0:10].reshape(-1, 3), a[:, -10:].reshape(-1, 3)])
    return np.median(border, axis=0)


def paper_mask(a, bg, lum_min=216, sat_max=34, dist_max=34):
    """Paper/background candidates: bright + low saturation + close to the paper tone.
    A flood fill from the border over this mask removes the sheet without eating
    enclosed artwork (film-strip cells, shirt, clapper stripes)."""
    lum = a.mean(2)
    sat = a.max(2) - a.min(2)
    d = np.sqrt(((a - bg) ** 2).sum(2))
    return ((lum > lum_min) & (sat < sat_max)) | (d < dist_max)


def cutout(src, out, thr_lo=18.0, thr_hi=60.0, feather=1.1, min_blob=500):
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    bg = estimate_bg(a)
    d = np.sqrt(((a - bg) ** 2).sum(2))

    # background = paper-ish pixels reachable from the image border
    from collections import deque
    h, w = d.shape
    paper = paper_mask(a, bg)
    bgmask = paper.astype(np.uint8)
    seen = np.zeros_like(bgmask)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bgmask[y, x] and not seen[y, x]:
                seen[y, x] = 1
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bgmask[y, x] and not seen[y, x]:
                seen[y, x] = 1
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and bgmask[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = 1
                q.append((ny, nx))

    outer = seen.astype(bool)
    # soft edge: ramp on the paper-distance, only in the outer region
    ramp = np.clip((d - thr_lo) / (thr_hi - thr_lo), 0, 1)
    alpha = np.where(outer, ramp * 255.0, 255.0)

    am = Image.fromarray(alpha.astype(np.uint8), "L")
    # kill specks: erode hard first so paper halos and stray dots disappear
    am = am.filter(ImageFilter.MinFilter(3))
    am = am.point(lambda v: 0 if v < 120 else (255 if v > 235 else int((v - 120) * 2.22)))
    am = am.filter(ImageFilter.MaxFilter(3))
    if feather:
        am = am.filter(ImageFilter.GaussianBlur(feather))
    # drop tiny isolated islands (paper specks) but keep the character + his props
    from PIL import ImageOps
    lab = np.zeros((h, w), np.uint8)
    am_np = np.asarray(am) > 90
    # simple 4-neighbour labelling by BFS on the binary mask
    cur = 0
    keep = np.zeros_like(am_np)
    for y0 in range(h):
        for x0 in range(w):
            if am_np[y0, x0] and not lab[y0, x0]:
                cur += 1
                qq = deque([(y0, x0)])
                lab[y0, x0] = cur
                cells = []
                while qq:
                    y, x = qq.popleft()
                    cells.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and am_np[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = cur
                            qq.append((ny, nx))
                if len(cells) >= min_blob:
                    for y, x in cells:
                        keep[y, x] = True
    am = Image.fromarray(np.where(keep, np.asarray(am), 0).astype(np.uint8), "L")

    rgb = Image.fromarray(a.astype(np.uint8), "RGB")
    out_img = rgb.convert("RGBA")
    out_img.putalpha(am)
    # colour decontamination: un-blend the paper tint from soft edge pixels
    arr = np.asarray(out_img).astype(np.float32)
    al = arr[..., 3:4] / 255.0
    soft = (al > 0.02) & (al < 0.98)
    if soft.any():
        c = arr[..., :3]
        un = (c - (1 - al) * bg) / np.maximum(al, 0.06)
        arr[..., :3] = np.where(soft, np.clip(un, 0, 255), c)
    out_img = Image.fromarray(arr.astype(np.uint8), "RGBA")

    bbox = out_img.getbbox()
    out_img = out_img.crop(bbox)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    out_img.save(out)
    print("wrote", out, out_img.size)

    # head crop for the avatar badge (top ~34% of the character, centred)
    ww, hh = out_img.size
    side = int(ww * 0.86)
    head = out_img.crop((int(ww * 0.07), 0, int(ww * 0.07) + side, side))
    head = head.resize((512, 512), Image.LANCZOS)
    head.save("assets/mascot_head.png")
    print("wrote assets/mascot_head.png", head.size)

    thumb = out_img.copy()
    thumb.thumbnail((420, 620), Image.LANCZOS)
    thumb.save("assets/mascot_thumb.png")
    print("wrote assets/mascot_thumb.png", thumb.size)
    return out


def _hsv(rgb):
    import colorsys
    mx = rgb.max(2); mn = rgb.min(2)
    d = np.maximum(mx - mn, 1e-6)
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    hue = np.zeros_like(mx)
    m1 = mx == R
    m2 = (mx == G) & ~m1
    m3 = ~m1 & ~m2
    hue[m1] = ((G - B) / d)[m1] % 6
    hue[m2] = ((B - R) / d)[m2] + 2
    hue[m3] = ((R - G) / d)[m3] + 4
    hue *= 60
    sat = (mx - mn) / np.maximum(mx, 1)
    return hue, sat, mx / 255.0


def _bfs(mask, seeds):
    from collections import deque
    h, w = mask.shape
    out = np.zeros_like(mask)
    qq = deque(map(tuple, np.argwhere(seeds)))
    for y, x in qq:
        out[y, x] = True
    while qq:
        y, x = qq.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not out[ny, nx]:
                    out[ny, nx] = True
                    qq.append((ny, nx))
    return out


def _largest_component(binary, min_size=400):
    from collections import deque
    h, w = binary.shape
    lab = np.zeros((h, w), np.int32)
    best, best_size, cur = None, 0, 0
    for y0 in range(h):
        for x0 in range(w):
            if binary[y0, x0] and not lab[y0, x0]:
                cur += 1
                qq = deque([(y0, x0)])
                lab[y0, x0] = cur
                cells = []
                while qq:
                    y, x = qq.popleft()
                    cells.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and binary[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = cur
                            qq.append((ny, nx))
                if len(cells) > best_size:
                    best, best_size = cells, len(cells)
    out = np.zeros_like(binary)
    if best and best_size >= min_size:
        for y, x in best:
            out[y, x] = True
    return out


def _fill_holes(binary):
    """Fill transparent regions fully enclosed by the shape (shirt, clapper fields)."""
    from collections import deque
    h, w = binary.shape
    holes = ~binary
    seen = np.zeros_like(binary)
    qq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if holes[y, x] and not seen[y, x]:
                seen[y, x] = True
                qq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if holes[y, x] and not seen[y, x]:
                seen[y, x] = True
                qq.append((y, x))
    while qq:
        y, x = qq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and holes[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                qq.append((ny, nx))
    return binary | (holes & ~seen)


def _components(binary, min_size=0):
    """All connected components (8-neighbour) as a list of boolean masks."""
    from collections import deque
    h, w = binary.shape
    lab = np.zeros((h, w), np.int32)
    out, cur = [], 0
    for y0 in range(h):
        for x0 in range(w):
            if binary[y0, x0] and not lab[y0, x0]:
                cur += 1
                qq = deque([(y0, x0)])
                lab[y0, x0] = cur
                cells = []
                while qq:
                    y, x = qq.popleft()
                    cells.append((y, x))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h and 0 <= nx < w and binary[ny, nx] and not lab[ny, nx]:
                                lab[ny, nx] = cur
                                qq.append((ny, nx))
                if len(cells) >= min_size:
                    mm = np.zeros_like(binary)
                    ys, xs = zip(*cells)
                    mm[list(ys), list(xs)] = True
                    out.append(mm)
    return out


def character_only(src, out, keep_height=1180, open_k=15, grow_k=7, min_blob=1400):
    """Drops the crayon backdrop.

    The crayon block and warm skin tones share a hue, so colour alone is not
    enough: the orange mask is *opened* with a big kernel which keeps only the
    large backdrop slabs (skin patches, film strips and the suit disappear) and
    those slabs are then grown back slightly and subtracted from the artwork.
    """
    full = Image.open("assets/mascot.png").convert("RGBA")
    a = np.asarray(full).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3]
    hue, sat, val = _hsv(rgb)
    art = al > 40

    orange = (hue < 45) & (sat > 0.22) & (val > 0.40) & art
    om = Image.fromarray((orange * 255).astype(np.uint8))
    opened = np.asarray(om.filter(ImageFilter.MinFilter(open_k)).filter(ImageFilter.MaxFilter(open_k))) > 127
    slabs = [c for c in _components(opened, min_size=min_blob)]
    crayon = np.zeros_like(art)
    for c in slabs:
        crayon |= np.asarray(Image.fromarray((c * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(grow_k))) > 127

    keep = art & (~crayon)
    km = Image.fromarray((keep * 255).astype(np.uint8))
    keep = np.asarray(km.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))) > 127

    comps = _components(keep, min_size=200)
    comps.sort(key=lambda m: -m.sum())
    main = comps[0] if comps else keep
    ys0, xs0 = np.where(main)
    cy, cx = ys0.mean(), xs0.mean()
    keep = main.copy()
    for c in comps[1:]:
        ys, xs = np.where(c)
        size = int(c.sum())
        dist = np.sqrt((ys.mean() - cy) ** 2 + (xs.mean() - cx) ** 2)
        warm = float(orange[ys, xs].mean())            # crayon residues are warm & small
        if size < 900:
            continue
        if warm > 0.5 and size < 12000:                # crayon streak -> drop
            continue
        if dist < 340 or not warm:                     # body fragment / clean doodle -> keep
            keep |= c
    # final polish: crayon streaks are warm AND thin -> drop them wherever they are
    warm_only = orange & keep
    for c in _components(warm_only, min_size=120):
        size = int(c.sum())
        if size > 9000:
            continue
        ys, xs = np.where(c)
        bw, bh = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        thin = size / float(bw * bh)
        dist = np.sqrt((ys.mean() - cy) ** 2 + (xs.mean() - cx) ** 2)
        if thin < 0.34 and (dist > 150 or size < 2500):
            keep &= ~c
    keep = _fill_holes(keep)

    arr = np.asarray(full).copy()
    arr[..., 3] = np.where(keep, arr[..., 3], 0)
    out_img = Image.fromarray(arr, "RGBA")
    out_img = out_img.crop(out_img.getbbox())
    if out_img.height > keep_height:
        out_img = out_img.resize((int(out_img.width * keep_height / out_img.height), keep_height),
                                 Image.LANCZOS)
    out_img.save(out)
    print("wrote", out, out_img.size)
    return out


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else SRC_DEFAULT
    cutout(src, "assets/mascot.png")
    character_only(src, "assets/mascot_char.png")
