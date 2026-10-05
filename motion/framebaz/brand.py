# -*- coding: utf-8 -*-
"""Brand identity + copy deck for the Framebaz motion stories.

Everything a non-programmer may want to change lives here (and in brand.json,
which overrides these values when present).
"""
import json
import os

BRAND = {
    "name_fa": "فریم\u200cباز",
    "name_en": "FRAMEBAZ",
    "handle": "@framebaz",
    "tagline_fa": "پیجت رو قاب کن",
    "tagline_en": "CINEMATIC CONTENT FOR YOUR PAGE",
    "colors": {
        "ink": "#0B0B14",
        "ink2": "#161327",
        "magenta": "#FF2D6F",
        "pink": "#FF7FB0",
        "yellow": "#FFE24B",
        "lime": "#C6FF3D",
        "cyan": "#3EE0FF",
        "purple": "#3A1D6E",
        "blue": "#1B2A6B",
        "white": "#FFFFFF",
        "muted": "#9C9CB4",
    },
    "fps": 30,
    "size": [1080, 1920],
}

# One entry per scene.  `vo` is the Persian voice-over line, `caption_en` is the
# burned-in English subtitle for that same line.
SCENES = [
    dict(
        id="hook", template="hook", bg="magenta", accent="yellow",
        kicker_en="FRAMEBAZ / MOTION STUDIO",
        fa_lines=["با ویدیو", "دیده شو"],
        lat_big="VIDEO",
        caption_en="Photos not growing your page? Try video.",
        vo="اگه پیجت با عکس دیده نمی\u200cشه، وقتشه ویدیو رو امتحان کنی.",
        min_dur=3.2, weight=1.0, lead=0.55, tail=0.55,
    ),
    dict(
        id="services", template="services", bg="ink", accent="yellow",
        kicker_en="WHAT WE DO",
        fa_lines=["موشن گرافیک", "موشن استوری", "ریلز"],
        cards=[("MOTION GRAPHICS", "موشن گرافیک"), ("MOTION STORY", "موشن استوری"), ("REELS & ADS", "ریلز و تیزر")],
        caption_en="Motion graphics, motion stories and pro reels for your page.",
        vo="فریم\u200cباز موشن\u200cگرافیک، موشن استوری و ریلز حرفه\u200cای برای پیجت می\u200cسازه.",
        min_dur=4.2, weight=1.0, lead=0.5, tail=0.5,
    ),
    dict(
        id="education", template="education", bg="lime", accent="ink",
        kicker_en="ANIMATED TUTORIALS + STOP MOTION",
        fa_lines=["آموزش انیمیشنی", "استاپ موشن"],
        badge_fa="۲۴ فریم در ثانیه",
        caption_en="Animated tutorials and stop-motion — idea to delivery.",
        vo="از آموزش انیمیشنی و استاپ\u200cموشن تا تیزر تبلیغاتی؛ ایده تا اجرا، همه\u200cچیز دست ما.",
        min_dur=4.4, weight=1.0, lead=0.5, tail=0.5,
    ),
    dict(
        id="process", template="process", bg="ink2", accent="cyan",
        kicker_en="HOW IT WORKS",
        fa_lines=["ایده", "استوری\u200cبورد", "انیمیشن", "تحویل"],
        lat_big="PROCESS",
        caption_en="Idea, storyboard, animation, delivery — step by step.",
        vo="فرایندش ساده\u200cست: ایده، استوری\u200cبورد، انیمیشن و تحویل؛ مرحله\u200cبه\u200cمرحله با خودت هماهنگیم.",
        min_dur=4.6, weight=1.0, lead=0.5, tail=0.5,
    ),
    dict(
        id="results", template="results", bg="blue", accent="lime",
        kicker_en="THE DIFFERENCE",
        stats=[("+۳۰۰٪", "بازدید بیشتر", "MORE VIEWS"),
               ("×۲", "موندگاری", "RETENTION"),
               ("۲۴س", "زمان تحویل", "DELIVERY")],
        fa_lines=["نتیجه\u200cاش رو می\u200cبینی"],
        caption_en="More views, higher retention, real sales.",
        vo="بازدید بیشتر، موندگاری بالاتر، فروش واقعی؛ فرقش رو توی تعامل می\u200cبینی.",
        min_dur=4.4, weight=1.0, lead=0.5, tail=0.5,
    ),
    dict(
        id="portfolio", template="portfolio", bg="ink", accent="magenta",
        kicker_en="PORTFOLIO",
        fa_lines=["نمونه\u200cکارها"],
        caption_en="See our portfolio, then DM us to start.",
        vo="نمونه\u200cکارها رو ببین و با یه دایرکت شروع کن.",
        min_dur=3.6, weight=1.0, lead=0.45, tail=0.45,
    ),
    dict(
        id="cta", template="cta", bg="yellow", accent="magenta",
        kicker_en="FRAMEBAZ",
        fa_lines=["فریم\u200cباز", "پیجت رو قاب کن"],
        caption_en="Framebaz — frame your page.",
        vo="فریم\u200cباز؛ پیجت رو قاب کن.",
        min_dur=3.4, weight=1.0, lead=0.5, tail=0.5,
    ),
    dict(
        id="outro", template="outro", bg="magenta", accent="yellow",
        kicker_en="LET'S TALK",
        fa_lines=["دایرکت بده"],
        handle="@framebaz",
        caption_en="DM us to start • Follow for more.",
        vo="برای شروع، دایرکت بده و ما رو دنبال کن.",
        min_dur=3.4, weight=1.0, lead=0.5, tail=0.6,
    ),
]


def load(brand_json=None):
    """Return (brand, scenes) with optional JSON overrides."""
    brand, scenes = dict(BRAND), [dict(s) for s in SCENES]
    brand["colors"] = dict(BRAND["colors"])
    path = brand_json or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brand.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            brand.update({k: v for k, v in data.get("brand", {}).items() if k != "colors"})
            brand["colors"].update(data.get("brand", {}).get("colors", {}))
            overrides = {s["id"]: s for s in data.get("scenes", []) if "id" in s}
            for sc in scenes:
                if sc["id"] in overrides:
                    sc.update(overrides[sc["id"]])
        except Exception as exc:              # keep rendering even with a broken json
            print(f"[brand] ignoring {path}: {exc}")
    return brand, scenes
