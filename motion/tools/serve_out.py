# -*- coding: utf-8 -*-
"""Serves motion/out as a small Persian download page (with ZIP bundles).

Usage:  python3 tools/serve_out.py [port] [--root out]
Endpoints:
  /                 download page (RTL, file sizes, play + download buttons)
  /file/<name>      inline view / playback
  /file/<name>?dl=1 download (Content-Disposition: attachment)
  /bundle/<id>.zip  ready-made ZIP bundles
Range requests are supported so video players can seek.
"""
import html
import io
import os
import re
import sys
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

ROOT = "out"
BUNDLES = {
    "all": ("همهٔ فایل‌ها (ویدیو + تصویر + مستندات)", None),
    "videos": ("فقط ویدیوها", ("framebaz_reel_full_music.mp4", "framebaz_reel_full_vonoly.mp4",
                               "framebaz_reel_short_music.mp4")),
    "docs": ("تصاویر، زیرنویس و استوری‌بورد", ("cover.png", "cover_frame.png", "storyboard.md",
                                             "storyboard.html", "subtitles_fa.srt",
                                             "subtitles_en.srt", "timeline.json")),
}
SKIP_PREFIX = ("_mix",)
VIDEO_EXT = (".mp4", ".mov")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
DOC_EXT = (".md", ".html", ".srt", ".json", ".txt")

LABELS = {
    "framebaz_reel_full_music.mp4": ("ویدیوی اصلی — ۴۹ ثانیه، ۹ صحنه، گویندگی + موسیقی", "video"),
    "framebaz_reel_full_vonoly.mp4": ("همان ویدیو، فقط گویندگی (برای گذاشتن آهنگ ترند)", "video"),
    "framebaz_reel_short_music.mp4": ("نسخهٔ کوتاه — ۳۱ ثانیه", "video"),
    "cover.png": ("کاور طراحى‌شدهٔ ریلز/استوری", "image"),
    "cover_frame.png": ("فریم کاور از داخل ویدیو", "image"),
    "storyboard.md": ("استوری‌بورد (متن)", "doc"),
    "storyboard.html": ("استوری‌بورد (صفحهٔ گرافیکی)", "doc"),
    "subtitles_fa.srt": ("زیرنویس فارسی", "doc"),
    "subtitles_en.srt": ("زیرنویس انگلیسی", "doc"),
    "timeline.json": ("زمان‌بندی صحنه‌ها (JSON)", "doc"),
    "audio.m4a": ("صدای کامل (گویندگی + موسیقی)", "doc"),
    "audio_clean.m4a": ("فقط گویندگی", "doc"),
    "audio_short.m4a": ("صدای نسخهٔ کوتاه", "doc"),
    "_video_master.mp4": ("ویدیوی بی‌صدا (برای تدوین مجدد)", "video"),
}
ORDER = ["framebaz_reel_full_music.mp4", "framebaz_reel_full_vonoly.mp4",
         "framebaz_reel_short_music.mp4", "cover.png", "cover_frame.png",
         "storyboard.html", "storyboard.md", "subtitles_fa.srt", "subtitles_en.srt",
         "timeline.json", "audio.m4a", "audio_clean.m4a", "audio_short.m4a",
         "_video_master.mp4"]


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0


def listing(root):
    files = []
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        path = os.path.join(root, name)
        if not os.path.isfile(path) or name.startswith(SKIP_PREFIX):
            continue
        files.append((name, os.path.getsize(path), datetime.fromtimestamp(os.path.getmtime(path))))
    files.sort(key=lambda f: (ORDER.index(f[0]) if f[0] in ORDER else 99, f[0]))
    return files


def page(root):
    files = listing(root)
    vids = [f for f in files if f[0].lower().endswith(VIDEO_EXT)]
    total = sum(f[1] for f in files)
    rows = []
    for name, size, mtime in files:
        label, kind = LABELS.get(name, (name, "doc"))
        icon = {"video": "🎬", "image": "🖼", "doc": "📄"}.get(kind, "📄")
        rows.append(f"""
        <li class="card {kind}">
          <span class="ico">{icon}</span>
          <div class="meta">
            <a class="name" href="/file/{name}">{html.escape(label)}</a>
            <code>{html.escape(name)}</code>
            <span class="size">{human(size)}</span>
          </div>
          <div class="acts">
            <a class="btn" href="/file/{name}">نمایش / پخش</a>
            <a class="btn primary" href="/file/{name}?dl=1">دانلود ⬇</a>
          </div>
        </li>""")
    bundles = "".join(
        f'<a class="bundle" href="/bundle/{bid}.zip">📦 {html.escape(title)}</a>'
        for bid, (title, _) in BUNDLES.items())
    preview = ""
    if vids:
        preview = (f'<video controls playsinline preload="metadata" '
                   f'src="/file/{vids[0][0]}"></video>')
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>دانلود فایل‌های فریم‌باز</title>
<style>
 * {{ box-sizing:border-box }}
 body {{ margin:0; background:#0B0B14; color:#fff; font-family:"Vazirmatn",Tahoma,system-ui,sans-serif }}
 header {{ padding:34px 26px 22px; background:linear-gradient(120deg,#FF2D6F,#C1125A) }}
 header h1 {{ margin:0 0 6px; font-size:26px }}
 header p {{ margin:2px 0; opacity:.92; font-size:14px }}
 .wrap {{ max-width:1000px; margin:0 auto; padding:22px 18px 60px }}
 .bundles {{ display:flex; gap:10px; flex-wrap:wrap; margin:0 0 22px }}
 .bundle {{ background:#FFE24B; color:#111; text-decoration:none; font-weight:700; padding:12px 18px; border-radius:14px; font-size:15px }}
 .bundle:hover {{ filter:brightness(1.06) }}
 video {{ width:100%; max-width:330px; border-radius:16px; display:block; margin:0 0 22px; background:#000 }}
 ul {{ list-style:none; padding:0; margin:0; display:grid; gap:12px }}
 .card {{ display:flex; align-items:center; gap:14px; background:#14121f; border:1px solid #262338; border-radius:16px; padding:14px 16px }}
 .ico {{ font-size:24px }}
 .meta {{ display:flex; flex-direction:column; gap:2px; min-width:0; flex:1 }}
 .name {{ color:#fff; text-decoration:none; font-weight:700; font-size:15px }}
 .name:hover {{ text-decoration:underline }}
 code {{ color:#8f8aa8; font-size:12px; direction:ltr; text-align:left }}
 .size {{ color:#C6FF3D; font-size:12px }}
 .acts {{ display:flex; gap:8px; flex-wrap:wrap }}
 .btn {{ text-decoration:none; font-size:13px; padding:9px 14px; border-radius:11px; background:#262338; color:#fff }}
 .btn.primary {{ background:#FF2D6F; font-weight:700 }}
 footer {{ color:#8f8aa8; font-size:12px; padding:0 26px 40px; text-align:center }}
</style></head><body>
<header>
  <h1>دانلود فایل‌های موشن‌گرافیک فریم‌باز</h1>
  <p>{len(files)} فایل · مجموع {human(total)} · ۱۰۸۰×۱۹۲۰ · ۳۰fps</p>
  <p>روی «دانلود ⬇» بزن؛ برای دیدن سریع ویدیو، پلیر زیر یا دکمهٔ «نمایش/پخش».</p>
</header>
<div class="wrap">
  <div class="bundles">{bundles}</div>
  {preview}
  <ul>{''.join(rows)}</ul>
</div>
<footer>@framebaz · همهٔ فایل‌ها از پوشهٔ motion/out سرو می‌شوند</footer>
</body></html>"""


def zip_bytes(root, names=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, _, _ in listing(root):
            if name.startswith(SKIP_PREFIX):
                continue
            if names is not None and name not in names:
                continue
            z.write(os.path.join(root, name), name)
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "FramebazDownload/1.0"

    def log_message(self, fmt, *a):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % a))

    # ---- helpers -----------------------------------------------------------
    def _send(self, code, body=b"", ctype="application/octet-stream", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Accept-Ranges", "bytes")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _safe(self, name):
        name = unquote(name).lstrip("/")
        path = os.path.abspath(os.path.join(ROOT, name))
        base = os.path.abspath(ROOT) + os.sep
        if not path.startswith(base):          # no path traversal outside the folder
            return None
        return path if os.path.isfile(path) else None

    def _file(self, name, download=False):
        path = self._safe(name)
        if not path:
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        size = os.path.getsize(path)
        ctype = ("video/mp4" if name.endswith(".mp4") else
                 "image/png" if name.endswith(".png") else
                 "audio/mp4" if name.endswith(".m4a") else
                 "text/html; charset=utf-8" if name.endswith(".html") else
                 "text/plain; charset=utf-8")
        extra = {}
        if download:
            extra["Content-Disposition"] = f'attachment; filename="{os.path.basename(name)}"'
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        code = 200
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), size - 1)
                if end < start:
                    end = size - 1
                code, extra["Content-Range"] = 206, f"bytes {start}-{end}/{size}"
        length = end - start + 1
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(path, "rb") as fh:
            fh.seek(start)
            left = length
            while left > 0:
                chunk = fh.read(min(262144, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    # ---- routes ------------------------------------------------------------
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            body = page(ROOT).encode("utf-8")
            return self._send(200, body, "text/html; charset=utf-8")
        m = re.match(r"^/file/(.+)$", u.path)
        if m:
            return self._file(m.group(1), download="dl" in q)
        m = re.match(r"^/bundle/([a-z0-9_]+)\.zip$", u.path)
        if m and m.group(1) in BUNDLES:
            names = BUNDLES[m.group(1)][1]
            data = zip_bytes(ROOT, set(names) if names else None)
            return self._send(200, data, "application/zip",
                              {"Content-Disposition": f'attachment; filename="framebaz_{m.group(1)}.zip"'})
        return self._send(404, b"not found", "text/plain; charset=utf-8")


def main():
    global ROOT
    port = 8080
    args = [a for a in sys.argv[1:]]
    if "--root" in args:
        i = args.index("--root")
        ROOT = args[i + 1]
        del args[i:i + 2]
    if args:
        port = int(args[0])
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"serving {os.path.abspath(ROOT)} on http://0.0.0.0:{port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
