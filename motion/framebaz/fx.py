# -*- coding: utf-8 -*-
"""Post-processing / compositing effects (numpy backed)."""
import functools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1080, 1920


def to_np(img):
    return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0


def to_img(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255.0 + 0.5).astype(np.uint8), "RGB")


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, t):
    a, b = hex2rgb(c1) if isinstance(c1, str) else c1, hex2rgb(c2) if isinstance(c2, str) else c2
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


@functools.lru_cache(maxsize=64)
def linear_gradient(w, h, c1, c2, angle=90):
    """Cached linear gradient as PIL image."""
    a, b = np.array(hex2rgb(c1), np.float32), np.array(hex2rgb(c2), np.float32)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    th = math.radians(angle)
    p = (xs * math.cos(th) + ys * math.sin(th))
    p = (p - p.min()) / max(p.max() - p.min(), 1e-6)
    arr = (a[None, None, :] * (1 - p[..., None]) + b[None, None, :] * p[..., None]) / 255.0
    return to_img(arr.astype(np.float32))


@functools.lru_cache(maxsize=64)
def radial_gradient(w, h, c_in, c_out, cx=0.5, cy=0.5, power=1.0):
    a, b = np.array(hex2rgb(c_in), np.float32), np.array(hex2rgb(c_out), np.float32)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xs / w) - cx) ** 2 + ((ys / h) - cy) ** 2)
    d = np.clip(d / max(d.max(), 1e-6), 0, 1) ** power
    arr = (a[None, None, :] * (1 - d[..., None]) + b[None, None, :] * d[..., None]) / 255.0
    return to_img(arr.astype(np.float32))


_NOISE_TILES = None


def _noise_tiles():
    global _NOISE_TILES
    if _NOISE_TILES is None:
        rng = np.random.default_rng(7)
        _NOISE_TILES = [rng.normal(0, 1, (256, 256, 1)).astype(np.float32) for _ in range(6)]
    return _NOISE_TILES


def add_grain(arr, amount=0.045, frame=0, seed=0, block=2):
    """Film grain. `block`>1 makes the noise coarser (2x2 px), which reads the same
    on screen but costs the H.264 encoder far fewer bits than per-pixel noise."""
    tile = _noise_tiles()[(frame + seed) % 6]
    h, w = arr.shape[:2]
    reps = (h // tile.shape[0] + 1, w // tile.shape[1] + 1, 1)
    n = np.tile(tile, reps)[:h, :w]
    if block > 1:
        hh, ww = (h // block) * block, (w // block) * block
        ng = n[:hh, :ww, 0].reshape(hh // block, block, ww // block, block).mean(axis=(1, 3))
        ng = np.kron(ng, np.ones((block, block), np.float32))
        n = np.pad(ng, ((0, h - ng.shape[0]), (0, w - ng.shape[1])), mode="edge")[..., None]
    return arr + n * amount


_VIGNETTE = {}


def vignette(arr, strength=0.35, power=1.35):
    key = (arr.shape[1], arr.shape[0], round(strength, 3), power)
    m = _VIGNETTE.get(key)
    if m is None:
        h, w = arr.shape[:2]
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((xs - w / 2) / (w / 2)) ** 2 + ((ys - h / 2) / (h / 2)) ** 2 * 0.55)
        d = np.clip(d, 0, 1.6) ** power
        m = np.clip(1.0 - strength * d, 0.0, 1.0)[..., None].astype(np.float32)
        _VIGNETTE[key] = m
    return arr * m


def glow(img, radius=26, amount=0.55, threshold=0.62):
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    lum = a.max(axis=2, keepdims=True)
    mask = np.clip((lum - threshold) / (1 - threshold), 0, 1)
    bright = to_img(a * mask)
    blurred = np.asarray(bright.filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255.0
    out = 1 - (1 - a) * (1 - blurred * amount)          # screen blend
    return to_img(out.astype(np.float32))


def chromatic(arr, px=6):
    if px <= 0:
        return arr
    out = arr.copy()
    out[..., 0] = np.roll(arr[..., 0], int(round(px)), axis=1)
    out[..., 2] = np.roll(arr[..., 2], -int(round(px)), axis=1)
    return out


def zoom_blur(img, amount=0.0):
    """Cheap radial blur approximated by a few scaled copies."""
    if amount <= 0.001:
        return img
    base = np.asarray(img.convert("RGB"), np.float32) / 255.0
    acc = base.copy()
    n = 4
    for i in range(1, n + 1):
        s = 1.0 + amount * (i / n) * 0.02
        w, h = img.size
        sc = img.resize((int(w * s), int(h * s)), Image.BILINEAR)
        ox, oy = (sc.width - w) // 2, (sc.height - h) // 2
        sc = sc.crop((ox, oy, ox + w, oy + h))
        acc += np.asarray(sc, np.float32) / 255.0
    return to_img(acc / (n + 1))


def step_blur(img, amount=0.0):
    """Directional smear used for transition whip-pans."""
    if amount <= 0.001:
        return img
    sm = img.filter(ImageFilter.GaussianBlur(2 + 26 * amount))
    band = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(band)
    # horizontal smear mask (centre band strongest)
    for i in range(0, img.size[1], 4):
        v = int(255 * (1 - abs((i - img.size[1] / 2) / (img.size[1] / 2))) ** 0.6)
        d.rectangle([0, i, img.size[0], i + 3], fill=v)
    return Image.composite(sm, img, band)


def halftone_dots(w, h, spacing=34, radius=6, color=(255, 255, 255), alpha=255, offset=0):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = color if len(color) == 4 else color + (alpha,)
    for y in range(-spacing, h + spacing, spacing):
        for x in range(-spacing + ((y // spacing) % 2) * (spacing // 2) - offset, w + spacing, spacing):
            d.ellipse([x - radius, y - radius, x + radius, y + radius], fill=c)
    return layer


def stripe_field(w, h, spacing=64, width=22, color=(255, 255, 255, 26), angle=-32, offset=0):
    big = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    for x in range(-big.width, big.width, spacing):
        d.line([(x + offset, -big.height), (x + offset + big.height * 2, big.height * 3)],
               fill=color, width=width)
    big = big.rotate(angle, resample=Image.BILINEAR, expand=False)
    return big.crop(((big.width - w) // 2, (big.height - h) // 2,
                     (big.width - w) // 2 + w, (big.height - h) // 2 + h))


def rounded_mask(size, radius, supersample=2):
    m = Image.new("L", (size[0] * supersample, size[1] * supersample), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, m.width - 1, m.height - 1],
                                        radius=radius * supersample, fill=255)
    return m.resize(size, Image.LANCZOS)


def paste_rounded(base_img, img, xy, radius):
    img = img.convert("RGBA")
    mask = rounded_mask(img.size, radius)
    base_img.paste(img, xy, ImageChops.multiply(mask, img.getchannel("A")))


def shake_offset(frame, amp=1.0, seed=0):
    """Deterministic camera shake (decaying) for impact frames."""
    rng = np.random.default_rng(seed * 977 + frame)
    return (rng.uniform(-1, 1) * amp, rng.uniform(-1, 1) * amp)
