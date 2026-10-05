# -*- coding: utf-8 -*-
"""Easing / interpolation helpers for the motion-graphic renderer."""
import math


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else (hi if x > hi else x)


def lin(t):
    return t


def smooth(t):
    return t * t * (3.0 - 2.0 * t)


def in_cubic(t):
    return t ** 3


def out_cubic(t):
    return 1.0 - (1.0 - t) ** 3


def in_out_cubic(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def out_quart(t):
    return 1.0 - (1.0 - t) ** 4


def out_expo(t):
    return 1.0 if t >= 1 else 1.0 - 2 ** (-10 * t)


def out_back(t, s=1.70158):
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def out_elastic(t, amp=1.0, period=0.35):
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return amp * 2 ** (-10 * t) * math.sin((t - period / 4) * (2 * math.pi) / period) + 1


def out_bounce(t):
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def in_out_quint(t):
    return 16 * t ** 5 if t < 0.5 else 1 - (-2 * t + 2) ** 5 / 2


def segment(t, start, end):
    """Normalised 0..1 progress of `t` inside [start, end]."""
    if end <= start:
        return 1.0 if t >= end else 0.0
    return clamp((t - start) / (end - start))


def lerp(a, b, t):
    return a + (b - a) * t


def stepped(t, fps=8.0):
    """Quantise time to get a stop-motion / low-fps feel."""
    return math.floor(t * fps) / fps


EASINGS = {
    "linear": lin, "smooth": smooth, "in_cubic": in_cubic, "out_cubic": out_cubic,
    "in_out_cubic": in_out_cubic, "out_quart": out_quart, "out_expo": out_expo,
    "out_back": out_back, "out_elastic": out_elastic, "out_bounce": out_bounce,
    "in_out_quint": in_out_quint,
}
