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
$PY -m framebaz.audio --out out --cut 30               # out/audio_30s.m4a    (30s cut-down)
$PY -m framebaz.audio --out out --cut 15 --no-bed --audio-name audio_15s_clean.m4a

echo "── 2/5 master video (silent, high quality) ──────────────────"
$PY -m framebaz.render --out out/_video_master.mp4 --timeline out/timeline.json \
    --audio "" --crf 22 --sheet build/contact_sheet_master.png

echo "── 3/5 30s cut-down video ───────────────────────────────────"
$PY -m framebaz.render --out out/_video_30s.mp4 --timeline out/timeline_30s.json \
    --audio "" --crf 22 --sheet build/contact_sheet_30s.png

echo "── 4/5 mux audio variants ───────────────────────────────────"
$PY - <<'PYEOF'
import json
from framebaz.render import mux, poster
mux("out/_video_master.mp4", "out/audio.m4a",       "out/framebaz_reel_44s_music.mp4")
mux("out/_video_master.mp4", "out/audio_clean.m4a", "out/framebaz_reel_44s_vonoly.mp4")
mux("out/_video_30s.mp4",    "out/audio_30s.m4a",   "out/framebaz_reel_30s_music.mp4")
poster("out/framebaz_reel_44s_music.mp4", "out/cover_frame.png", 2.4)
PYEOF

echo "── 5/5 cover, storyboard docs, verification ─────────────────"
$PY tools/make_cover.py
$PY tools/make_docs.py
for f in out/framebaz_reel_44s_music.mp4 out/framebaz_reel_30s_music.mp4; do
  echo "── $f"
  "$TOOLS/bin/ffmpeg" -hide_banner -i "$f" 2>&1 | grep -E "Duration|Stream #"
done
ls -sh out/*.mp4 out/*.m4a out/*.png 2>/dev/null || true
