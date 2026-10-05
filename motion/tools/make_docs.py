# -*- coding: utf-8 -*-
"""Generates the storyboard documents (out/storyboard.md + out/storyboard.html)
straight from brand.json + out/timeline*.json + the rendered video, so the docs
can never drift away from the actual video."""
import base64
import json
import os
import subprocess

TOOLS = os.environ.get("FRAMEBAZ_TOOLS", "/home/user/.local/share/framebaz")
FFMPEG = os.path.join(TOOLS, "bin", "ffmpeg")

MOTION_NOTES = {
    "hook": "کلمهٔ «VIDEO» بزرگ پشت صحنه + دکمهٔ پلی با انیمیشن الاستیک و حلقهٔ زرد ضربان‌دار؛ تیتر فارسی با فرود پاپ (out-back) وارد می‌شود. punch-in دوربین در ابتدای صحنه.",
    "services": "سه کارت خدمات نوبتی از راست سُر می‌خورند و شمارهٔ لاتین + برچسب فارسی + برچسب لاتین را نشان می‌دهند.",
    "education": "نوار فیلم متحرک در بالا + پنل استاپ‌موشن با انیمیشن ۴ فریمی (۸ فریم در ثانیه) و نوار پیشرفت؛ تیتر فارسی با حس پله‌ای/قطع وارد می‌شود.",
    "process": "ریل عمودی مرحله‌به‌مرحله کشیده می‌شود، دایره‌های شماره‌دار روشن می‌شوند و یک جرقهٔ زرد روی ریل حرکت می‌کند.",
    "results": "شمارندهٔ بزرگ «+۳۰۰٪» با اعداد فارسی بالا می‌رود، نمودار میله‌ای از پایین رشد می‌کند و سه چیپ آماری وارد می‌شوند.",
    "portfolio": "گرید ۲×۳ نمونه‌کارها با کجی ملایم و حرکت شناور؛ اشارهٔ «PORTFOLIO • @framebaz» و فلش.",
    "cta": "دکمهٔ بزرگ «فریم‌باز» با حلقه‌های ضربان‌دار و هواپیمای کاغذی که با رد دنباله وارد می‌شود؛ آیدی و شعار لاتین.",
    "outro": "لوگوتایپ تیره با دکمهٔ پلی، نام FRAMEBAZ + تگ‌لاین، سه چیپ FOLLOW/SAVE/SHARE و آیدی پیج.",
}

GRADE_NOTES = "ترنزیشن whip-pan با smear و اعوجاج رنگی بین صحنه‌ها، دانهٔ فیلم (grain)، وینیت، نوار پیشرفت استوری (۸ بخش) و واترمارک FRAMEBAZ در همهٔ صحنه‌ها."


def frame(video, t, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(t),
                    "-i", video, "-frames:v", "1", "-vf", "scale=540:-1", out], check=True)
    return out


def b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def tc(sec):
    return f"{int(sec // 60):01d}:{sec % 60:04.1f}"


def write_md(brand, tl, css, path):
    rows = ["| # | صحنه | زمان | طول | تیتر فارسی (روی تصویر) | زیرنویس انگلیسی | گویندگی فارسی | حرکت |",
            "|---|---|---|---|---|---|---|---|"]
    for i, (sc, info) in enumerate(zip(brand["scenes"], tl["scenes"]), 1):
        hero = " / ".join(css.get(sc["id"], {}).get("fa_lines", [])) or "—"
        rows.append(f"| {i} | {sc['id']} | {tc(info['start'])}–{tc(info['start']+info['dur'])} "
                    f"| {info['dur']:.1f}s | {hero} | {sc.get('caption_en','')} "
                    f"| {sc.get('vo','')} | {MOTION_NOTES.get(sc['id'],'')} |")
    doc = f"""# استوری‌بورد موشن‌گرافیک فریم‌باز — Framebaz motion story

نسخه‌ها: **44s** (کامل، ۸ صحنه) و **30s** (کوتاه‌شده، ۶ صحنه) — ۱۰۸۰×۱۹۲۰، ۳۰fps، گویندگی فارسی + زیرنویس انگلیسی سوخته.

{GRADE_NOTES}

## نسخه اصلی (۴۳.۹ ثانیه)

{chr(10).join(rows)}

## نسخه ۳۰ ثانیه‌ای

صحنه‌های `hook → services → results → portfolio → cta → outro` (۲۹.۴ ثانیه).

## فایل‌های مرتبط

* `framebaz_reel_44s_music.mp4` — نسخه نهایی با موسیقی
* `framebaz_reel_44s_vonoly.mp4` — فقط گویندگی (برای گذاشتن آهنگ ترند)
* `framebaz_reel_30s_music.mp4` — نسخه کوتاه
* `cover_frame.png` — کاور
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return path


def write_html(brand, tl, css, video, path, frames_dir):
    cards = []
    for i, (sc, info) in enumerate(zip(brand["scenes"], tl["scenes"]), 1):
        t = info["start"] + min(1.6, info["dur"] * 0.55)
        img = frame(video, t, os.path.join(frames_dir, f"{i:02d}_{sc['id']}.png"))
        hero = " / ".join(css.get(sc["id"], {}).get("fa_lines", []))
        cards.append(f"""
    <article class="scene">
      <img src="{os.path.relpath(img, os.path.dirname(path))}" alt="{sc['id']}">
      <div class="meta">
        <div class="row"><span class="num">{i}</span><h3>{sc['id'].upper()}</h3>
          <span class="time">{tc(info['start'])} → {tc(info['start']+info['dur'])} · {info['dur']:.1f}s</span></div>
        <p class="hero">{hero}</p>
        <p class="sub">EN SUB — {sc.get('caption_en','')}</p>
        <p class="vo">🎙 {sc.get('vo','')}</p>
        <p class="note">{MOTION_NOTES.get(sc['id'],'')}</p>
      </div>
    </article>""")
    html = f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>استوری‌بورد فریم‌باز — Framebaz storyboard</title>
<style>
 :root {{ --ink:#0B0B14; --mag:#FF2D6F; --yel:#FFE24B; --lim:#C6FF3D; }}
 * {{ box-sizing:border-box }}
 body {{ margin:0; background:var(--ink); color:#fff; font-family:"Vazirmatn",Tahoma,system-ui,sans-serif }}
 header {{ padding:48px 32px 24px; background:linear-gradient(120deg,var(--mag),#C1125A) }}
 header h1 {{ margin:0 0 8px; font-size:34px }}
 header p {{ margin:4px 0; opacity:.9; font-size:16px }}
 .pill {{ display:inline-block; background:var(--yel); color:#111; border-radius:999px; padding:6px 14px; font-size:13px; font-weight:700; margin-inline-end:8px }}
 .wrap {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:22px; padding:28px 24px 64px }}
 .scene {{ background:#14121f; border:1px solid #262338; border-radius:22px; overflow:hidden }}
 .scene img {{ width:100%; display:block }}
 .meta {{ padding:16px 18px 20px; text-align:right }}
 .row {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap }}
 .num {{ background:var(--mag); width:30px; height:30px; border-radius:9px; display:grid; place-items:center; font-weight:800 }}
 h3 {{ margin:0; font-size:18px; letter-spacing:.14em; color:#cfcbe4 }}
 .time {{ margin-inline-start:auto; font-size:13px; color:#8f8aa8; direction:ltr }}
 .hero {{ font-weight:800; font-size:20px; margin:12px 0 4px; color:#fff }}
 .sub {{ margin:4px 0; font-size:13px; color:var(--lim); direction:ltr; text-align:left }}
 .vo {{ margin:8px 0; font-size:14px; color:#ffd9e6 }}
 .note {{ margin:8px 0 0; font-size:13px; color:#a49fbe; line-height:1.9 }}
 footer {{ padding:0 32px 48px; color:#8f8aa8; font-size:13px }}
</style></head><body>
<header>
  <h1>استوری‌بورد موشن‌گرافیک — FRAMEBAZ</h1>
  <p><span class="pill">1080×1920</span><span class="pill">30fps</span><span class="pill">۸ صحنه / ۴۳.۹ ثانیه</span></p>
  <p>{GRADE_NOTES}</p>
</header>
<div class="wrap">{''.join(cards)}</div>
<footer>گویندگی فارسی + زیرنویس انگلیسی سوخته · نسخه‌ها: 44s (کامل) و 30s (کوتاه) · @framebaz</footer>
</body></html>"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path


def main():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from framebaz import brand as BR
    brand, scenes = BR.load()
    with open("out/timeline.json", encoding="utf-8") as fh:
        tl = json.load(fh)
    css = {s["id"]: s for s in scenes}
    video = "out/framebaz_reel_44s_music.mp4"
    print(write_md(brand, tl, css, "out/storyboard.md"))
    print(write_html(brand, tl, css, video, "out/storyboard.html", "out/frames"))


if __name__ == "__main__":
    main()
