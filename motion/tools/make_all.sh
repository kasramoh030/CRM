#!/usr/bin/env bash
# make_all.sh — full Framebaz motion-story pipeline (edit brand.json / voice files, then run this)
set -euo pipefail
TOOLS="${FRAMEBAZ_TOOLS:-/home/user/.local/share/framebaz}"
cd "$(dirname "$0")/.."                       # motion/
export PYTHONPATH="$TOOLS/pylibs:$(pwd)"
PY=python3

echo "── 1/5 narration + music mixes ──────────────────────────────"
$PY -m framebaz.audio --out out                        # out/audio.m4a        (VO + music bed)
$PY -m framebaz.audio --out out --no-bed --audio-name audio_clean.m4a   # VO only
$PY -m framebaz.audio --out out --cut short --audio-name audio_short.m4a  # cut-down mix

echo "── 2/5 master video (silent, high quality) ──────────────────"
$PY -m framebaz.render --out out/_video_master.mp4 --timeline out/timeline.json \
    --audio "" --crf 22 --sheet build/contact_sheet_master.png

echo "── 3/5 short cut-down video ─────────────────────────────────"
$PY -m framebaz.render --out out/_video_short.mp4 --timeline out/timeline_short.json \
    --audio "" --crf 22 --sheet build/contact_sheet_short.png

echo "── 4/5 mux audio variants ───────────────────────────────────"
$PY - <<'PYEOF'
import json
from framebaz.render import mux, poster
mux("out/_video_master.mp4", "out/audio.m4a",       "out/framebaz_reel_full_music.mp4")
mux("out/_video_master.mp4", "out/audio_clean.m4a", "out/framebaz_reel_full_vonoly.mp4")
mux("out/_video_short.mp4",  "out/audio_short.m4a", "out/framebaz_reel_short_music.mp4")
poster("out/framebaz_reel_full_music.mp4", "out/cover_frame.png", 2.4)
PYEOF

echo "── 5/5 cover, storyboard docs, verification ─────────────────"
$PY tools/make_cover.py
$PY tools/make_docs.py
$PY tools/make_srt.py
for f in out/framebaz_reel_full_music.mp4 out/framebaz_reel_short_music.mp4; do
  echo "── $f"
  "$TOOLS/bin/ffmpeg" -hide_banner -i "$f" 2>&1 | grep -E "Duration|Stream #"
done
ls -sh out/*.mp4 out/*.m4a out/*.png 2>/dev/null || true
