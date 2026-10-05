# -*- coding: utf-8 -*-
"""Builds deliverables/index.html — a download page for the deliverables — plus a single
zip pack, so the client can grab everything (or individual files) in one click."""
import argparse
import html
import os
import re
import subprocess
import zipfile

TOOLS = os.environ.get("FRAMEBAZ_TOOLS", "/opt/framebaz-tools")
FFMPEG = os.path.join(TOOLS, "bin", "ffmpeg")
OUT = "deliverables"
ZIP_NAME = "framebaz_motion_pack.zip"

# (filename, Persian title, description)
ITEMS = [
    ("framebaz_reel_full_music.mp4", "ویدیوی اصلی — نسخه کامل با موسیقی",
     "۹ صحنه، ۱۰۸۰×۱۹۲۰، ۳۰fps، گویندگی فارسی + زیرنویس انگلیسی. همین را برای ریلز/استوری آپلود کن."),
    ("framebaz_reel_full_vonoly.mp4", "نسخه کامل — فقط گویندگی (بدون موسیقی)",
     "اگر می‌خواهی در اینستاگرام یک آهنگ ترند روی ویدیو بگذاری، این نسخه را انتخاب کن."),
    ("framebaz_reel_short_music.mp4", "نسخه کوتاه ۳۱ ثانیه‌ای",
     "فقط ۶ صحنه اصلی؛ مناسب تبلیغ، تیزر کوتاه یا تست سریع."),
    ("cover.png", "کاور طراحی‌شده", "برای کاور ریلز یا پست معرفی."),
    ("cover_frame.png", "فریم کاور (از خود ویدیو)", "یک فریم واقعی ویدیو، مناسب کاور."),
    ("storyboard.html", "استوری‌بورد تعاملی", "صحنه‌به‌صحنه با فریم، متن فارسی، زیرنویس و توضیح حرکت."),
    ("storyboard.md", "استوری‌بورد متنی", "همان استوری‌بورد در قالب متن (برای ویرایش سریع)."),
    ("subtitles_fa.srt", "زیرنویس فارسی", "برای آپلود به‌عنوان کپشن یا زیرنویس."),
    ("subtitles_en.srt", "زیرنویس انگلیسی", "برای کپشن/دسترس‌پذیری."),
    ("audio.m4a", "صدای نهایی (گویندگی + موسیقی)", "برای ویرایش در پریمیر/کپ‌کات."),
    ("audio_clean.m4a", "صدای فقط گویندگی", "برای میکس با موسیقی دلخواه."),
]


def probe(path):
    """-> (duration seconds or None) using the bundled static ffmpeg."""
    try:
        out = subprocess.run([FFMPEG, "-hide_banner", "-i", path],
                             capture_output=True, text=True).stderr
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
        if m:
            h, mnt, s = m.groups()
            return int(h) * 3600 + int(mnt) * 60 + float(s)
        m = re.search(r"1080x1920", out)
        return None
    except Exception:
        return None


def human(nbytes):
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024 or unit == "GB":
            return f"{nbytes:.0f} {unit}" if unit == "B" else f"{nbytes/1:.1f} {unit}"
        nbytes /= 1024


def main(make_zip=False):
    rows, existing, total = [], [], 0
    for name, title, desc in ITEMS:
        path = os.path.join(OUT, name)
        if not os.path.exists(path):
            continue
        size = os.path.getsize(path)
        total += size
        dur = probe(path) if name.endswith((".mp4", ".m4a")) else None
        meta = human(size) + (f" · {int(dur//60)}:{dur%60:04.1f} دقیقه" if dur else "")
        existing.append(name)
        rows.append(f"""
      <article class="card">
        <div class="txt">
          <h3>{html.escape(title)}</h3>
          <p>{html.escape(desc)}</p>
          <span class="meta">{name} — {meta}</span>
        </div>
        <a class="btn" href="{html.escape(name)}" download>دانلود</a>
      </article>""")

    # optional single zip with everything (off by default: it doubles the disk/snapshot size)
    zip_path = os.path.join(OUT, ZIP_NAME)
    if make_zip:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for name in existing:
                z.write(os.path.join(OUT, name), name)
    has_zip = os.path.exists(zip_path)
    zsize = os.path.getsize(zip_path) if has_zip else 0

    page = f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>دانلود موشن‌استوری فریم‌باز</title>
<style>
  :root {{ --ink:#0B0B14; --mag:#FF2D6F; --yel:#FFE24B; --lim:#C6FF3D; --muted:#9C9CB4 }}
  * {{ box-sizing:border-box }}
  body {{ margin:0; background:var(--ink); color:#fff;
         font-family:"Vazirmatn",Tahoma,system-ui,sans-serif; line-height:1.9 }}
  header {{ padding:44px 28px 30px; background:linear-gradient(120deg,var(--mag),#C1125A) }}
  header h1 {{ margin:0 0 6px; font-size:30px }}
  header p {{ margin:6px 0 0; opacity:.92; font-size:15px; max-width:760px }}
  .chips {{ margin-top:14px }}
  .chip {{ display:inline-block; background:rgba(0,0,0,.28); border-radius:999px;
          padding:5px 14px; font-size:13px; margin-inline-end:8px }}
  main {{ max-width:900px; margin:0 auto; padding:26px 20px 70px }}
  .all {{ display:flex; align-items:center; gap:14px; background:#161327; border:1px solid #2A2440;
          border-radius:20px; padding:18px 20px; margin-bottom:22px }}
  .all h2 {{ margin:0 0 4px; font-size:19px }}
  .all p {{ margin:0; color:var(--muted); font-size:13.5px }}
  .all .btn {{ margin-inline-start:auto; background:var(--yel); color:#111 }}
  .card {{ display:flex; align-items:center; gap:16px; background:#14121f; border:1px solid #262338;
          border-radius:18px; padding:16px 18px; margin-bottom:12px }}
  .txt {{ flex:1 }}
  .card h3 {{ margin:0 0 4px; font-size:17px }}
  .card p {{ margin:0 0 6px; font-size:13.5px; color:#b9b4d0 }}
  .meta {{ font-size:12.5px; color:#8f8aa8; direction:ltr; display:inline-block }}
  .btn {{ background:var(--mag); color:#fff; text-decoration:none; font-weight:700;
         border-radius:999px; padding:11px 26px; white-space:nowrap; font-size:14.5px }}
  .btn:hover {{ filter:brightness(1.1) }}
  footer {{ color:var(--muted); font-size:12.5px; text-align:center; padding-bottom:40px }}
  @media (max-width:560px) {{ .card {{ flex-direction:column; align-items:stretch }}
    .btn {{ text-align:center }} .all {{ flex-wrap:wrap }} }}
</style></head><body>
<header>
  <h1>موشن‌استوری فریم‌باز — فایل‌های آماده</h1>
  <p>همه فایل‌ها ۱۰۸۰×۱۹۲۰ (۹:۱۶)، ۳۰ فریم بر ثانیه، با گویندگی فارسی و زیرنویس انگلیسی سوخته. کافی است فایل را دانلود و در اینستاگرام آپلود کنی.</p>
  <div class="chips"><span class="chip">۳ ویدیو</span><span class="chip">۲ کاور</span>
    <span class="chip">۲ زیرنویس</span><span class="chip">استوری‌بورد</span>
    <span class="chip">مجموع {human(total)}</span></div>
</header>
<main>
  <div class="all">
    <div>
      <h2>{'دانلود همه فایل‌ها با هم' if has_zip else 'شروع کن از ویدیوی اصلی'}</h2>
      <p>{'یک فایل زیپ شامل ویدیوها، کاورها، زیرنویس‌ها و استوری‌بورد — ' + human(zsize) if has_zip
          else 'روی «دانلود» هر کارت بزن؛ همه فایل‌ها جداگانه قابل دانلودند. برای آپلود، فایل اول کافیه.'}</p>
    </div>
    <a class="btn" href="{ZIP_NAME if has_zip else 'framebaz_reel_full_music.mp4'}" download>{'دانلود زیپ' if has_zip else 'دانلود ویدیوی اصلی'}</a>
  </div>
  {''.join(rows)}
  <footer>فریم‌باز · @framebaz — برای تغییر متن‌ها، رنگ‌ها یا گویندگی، فایل راهنمای ویرایش را ببین.</footer>
</main></body></html>"""
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"wrote {OUT}/index.html ({len(existing)} files, pack {human(zsize)})")
    return zip_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", action="store_true", help="also build a zip pack")
    a = ap.parse_args()
    main(make_zip=a.zip)
