#!/usr/bin/env bash
# bootstrap.sh — installs the render toolchain (ffmpeg + Pillow/Arabic reshaping + Persian fonts).
#
#   TOOLS=/opt/framebaz-tools bash tools/bootstrap.sh
#
# The toolchain is deliberately kept OUTSIDE the workspace: it is ~150 MB and the
# workspace snapshot only keeps small files. Re-run this script whenever the sandbox
# has been recycled (it is idempotent and takes ~1–2 min).
set -u
TOOLS="${TOOLS:-/opt/framebaz-tools}"
log(){ printf '\n== %s ==\n' "$*"; }

log "prepare $TOOLS"
if [ ! -w "$(dirname "$TOOLS")" ] 2>/dev/null; then
  sudo mkdir -p "$TOOLS" && sudo chown -R "$(id -u):$(id -g)" "$TOOLS" || true
fi
mkdir -p "$TOOLS/bin" "$TOOLS/fonts" "$TOOLS/pylibs" "$TOOLS/tmp" || { echo "CANNOT_WRITE $TOOLS"; exit 1; }
whoami; date

log "network check"
for u in https://pypi.org/simple/ https://registry.npmjs.org/; do
  printf '%s -> ' "$u"; curl -sS -o /dev/null -w '%{http_code}\n' --max-time 20 "$u" || echo FAIL
done

log "python tools (Pillow, reshaping, numpy, fonttools)"
python3 -m pip install -q --target "$TOOLS/pylibs" --upgrade \
  pillow numpy arabic-reshaper python-bidi fonttools brotli imageio-ffmpeg 2>&1 | tail -2
PYTHONPATH="$TOOLS/pylibs" python3 - <<'PY'
import PIL, numpy, arabic_reshaper, bidi, fontTools, imageio_ffmpeg
print("libs ok — pillow", PIL.__version__, "| numpy", numpy.__version__)
PY

log "ffmpeg (static binary bundled with the imageio-ffmpeg wheel)"
PYTHONPATH="$TOOLS/pylibs" python3 - <<'PY'
import os, shutil, imageio_ffmpeg
exe = imageio_ffmpeg.get_ffmpeg_exe()
dst = "/opt/framebaz-tools/bin/ffmpeg" if os.environ.get("TOOLS") in (None, "") else os.path.join(os.environ["TOOLS"], "bin/ffmpeg")
shutil.copy(exe, dst); os.chmod(dst, 0o755); print("ffmpeg ->", dst)
PY
"$TOOLS/bin/ffmpeg" -hide_banner -version 2>&1 | head -1

log "fonts (npm registry: Vazirmatn + Anton + Archivo Black)"
cd "$TOOLS/tmp" || exit 1
rm -rf vazirmatn anton archivo
fetch(){ curl -sS -o "$1.tgz" "$2" && mkdir -p "$1" && tar -xzf "$1.tgz" -C "$1"; }
fetch vazirmatn "https://registry.npmjs.org/vazirmatn/-/vazirmatn-33.0.3.tgz"
fetch anton    "https://registry.npmjs.org/@fontsource/anton/-/anton-5.3.0.tgz"
fetch archivo  "https://registry.npmjs.org/@fontsource/archivo-black/-/archivo-black-5.3.0.tgz"
# Vazirmatn: main build (Latin + Persian, both digit sets)
find vazirmatn -path '*fonts/ttf/*.ttf' ! -path '*misc/*' ! -name '*RD*' ! -name '*UI*' \
     ! -name '*NL*' ! -name '*FD*' -exec cp -n {} "$TOOLS/fonts/" \;
PYTHONPATH="$TOOLS/pylibs" python3 - <<'PY'
# Anton / Archivo Black ship as woff2 in @fontsource — convert to ttf
import os
from fontTools.ttLib import TTFont
TOOLS = "/opt/framebaz-tools"
for src, dst in (("/opt/framebaz-tools/tmp/anton/package/files/anton-latin-400-normal.woff2", "Anton.ttf"),
                 ("/opt/framebaz-tools/tmp/archivo/package/files/archivo-black-latin-400-normal.woff2", "ArchivoBlack.ttf")):
    try:
        f = TTFont(src); f.flavor = None
        f.save(os.path.join(TOOLS, "fonts", dst)); print("converted", dst)
    except Exception as e:
        print("convert failed", src, e)
PY

log "verify"
PYTHONPATH="$TOOLS/pylibs" python3 - <<'PY'
import glob
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
TOOLS = "/opt/framebaz-tools"
ok = []
for p in sorted(glob.glob(TOOLS + "/fonts/*.ttf")):
    try:
        ImageFont.truetype(p, 40); ok.append(p.split("/")[-1])
    except Exception as e:
        print("BAD", p, e)
print("fonts ok:", len(ok), "->", ", ".join(ok[:8]), "...")
txt = get_display(arabic_reshaper.reshape("موشن استوری فریم‌باز ۰۱۲۳"))
img = Image.new("RGB", (900, 160), (255, 45, 111))
ImageDraw.Draw(img).text((450, 80), txt, font=ImageFont.truetype(TOOLS + "/fonts/Vazirmatn-Black.ttf", 70),
                         fill="white", anchor="mm")
img.save(TOOLS + "/tmp/verify.png"); print("persian shaping ok")
PY
du -sh "$TOOLS"; echo "DONE"
