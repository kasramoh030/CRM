#!/usr/bin/env bash
# bootstrap.sh — نصب ابزارهای رندر موشن‌گرافیک (ffmpeg + Pillow/reshaping + فونت‌های فارسی)
set -u
TOOLS="${TOOLS:-/home/user/.local/share/framebaz}"
mkdir -p "$TOOLS/bin" "$TOOLS/fonts" "$TOOLS/pylibs" "$TOOLS/tmp"
log(){ printf '\n== %s ==\n' "$*"; }

log "system"
whoami; df -h /home/user | tail -1
command -v curl >/dev/null || { echo "NO_CURL"; exit 1; }

log "network"
for u in https://pypi.org/simple/ https://raw.githubusercontent.com https://cdn.jsdelivr.net; do
  printf '%s -> ' "$u"; curl -sS -o /dev/null -w '%{http_code}\n' --max-time 20 "$u" || echo FAIL
done

log "ffmpeg"
export PATH="$TOOLS/bin:$PATH"
if ! command -v ffmpeg >/dev/null 2>&1; then
  got=0
  if sudo -n true 2>/dev/null; then
    (sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg) >/dev/null 2>&1 && got=1
  fi
  if [ "$got" != 1 ]; then
    cd "$TOOLS/tmp" || exit 1
    for u in \
      "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz" \
      "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" ; do
      echo "try: $u"
      if curl -fL --retry 2 --max-time 900 -o ff.tar.xz "$u"; then
        tar -xf ff.tar.xz || continue
        f=$(find . -maxdepth 4 -type f -name ffmpeg | head -1)
        [ -n "$f" ] && cp "$f" "$TOOLS/bin/ffmpeg" && chmod +x "$TOOLS/bin/ffmpeg" && break
      fi
    done
    rm -f "$TOOLS/tmp/ff.tar.xz"
  fi
fi
if command -v ffmpeg >/dev/null 2>&1; then ffmpeg -version | head -1; echo "FFMPEG_OK=$(command -v ffmpeg)"; else echo "FFMPEG_FAIL"; fi

log "python libs"
if python3 -m pip -V >/dev/null 2>&1; then
  python3 -m pip install -q --target "$TOOLS/pylibs" --upgrade pillow arabic-reshaper python-bidi \
    || python3 -m pip install -q --break-system-packages --target "$TOOLS/pylibs" --upgrade pillow arabic-reshaper python-bidi
else
  echo "NO_PIP"
fi
PYTHONPATH="$TOOLS/pylibs" python3 -c "import PIL,arabic_reshaper,bidi;print('PYLIBS_OK pillow',PIL.__version__)" || echo "PYLIBS_FAIL"

log "fonts"
cd "$TOOLS/fonts" || exit 1
dl(){ curl -fL --retry 2 --max-time 120 -o "$2" "$1" >/dev/null 2>&1 && echo "ok  $2" || echo "MISS $2"; }
dl "https://raw.githubusercontent.com/google/fonts/main/ofl/vazirmatn/Vazirmatn%5Bwght%5D.ttf" "Vazirmatn-var.ttf"
for w in Regular Medium SemiBold Bold ExtraBold Black; do
  dl "https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/fonts/ttf/Vazirmatn-$w.ttf" "Vazirmatn-$w.ttf"
done
dl "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf" "Anton.ttf"
dl "https://raw.githubusercontent.com/google/fonts/main/ofl/archivoblack/ArchivoBlack-Regular.ttf" "ArchivoBlack.ttf"
dl "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf" "Inter-var.ttf"
ls -1sh "$TOOLS/fonts" | head -20
PYTHONPATH="$TOOLS/pylibs" python3 - <<'PY'
import glob
from PIL import ImageFont
for p in sorted(glob.glob("/home/user/.local/share/framebaz/fonts/*.ttf")):
    try:
        ImageFont.truetype(p, 40); print("font ok:", p.split("/")[-1])
    except Exception as e:
        print("font bad:", p, e)
PY
echo "DONE tools at $TOOLS"
