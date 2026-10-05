# Framebaz Motion — قالب موشن‌گرافیک / Motion‑graphic template engine

A small, dependency‑light **motion‑graphic video engine** that renders vertical
(1080×1920, 9:16) Instagram **Stories / Reels** for the `@framebaz` page:

* Persian **voice‑over** (narration) + **English burned‑in subtitles**
* bold "energetic" art‑direction: hot magenta / lime / yellow / cyan on ink
* 8 designed scenes, whip‑pan transitions, zoom punch‑ins, film grain, chromatic aberration
* renders to H.264 MP4 with AAC audio at 30 fps — ready to upload to Instagram

Everything is **data‑driven**: copy, colours, scene order and timing live in
[`brand.json`](brand.json) and [`framebaz/brand.py`](framebaz/brand.py); the visuals are
code in [`framebaz/templates.py`](framebaz/templates.py).

---

## Deliverables (`out/`)

| file | what it is |
|---|---|
| `framebaz_reel_full_music.mp4` | **main video** — 9 scenes, narration + subtle rhythmic music bed (~49 s) |
| `framebaz_reel_full_vonoly.mp4` | same picture, **voice‑over only** — drop a trending track on it in the Instagram editor |
| `framebaz_reel_short_music.mp4` | cut‑down version (~31 s) for ads / shorter attention |
| `cover_frame.png` / `cover.png` | still from the video / designed cover, usable as the Reel cover |
| `storyboard.md` | scene‑by‑scene script: timings, Persian on‑screen text, English subtitle, narration, motion notes |
| `timeline.json` / `timeline_30s.json` | machine‑readable timing (used by the renderer) |
| `audio.m4a`, `audio_clean.m4a`, `audio_30s.m4a` | audio mixes |

## How it is built

```
motion/
├── brand.json              ← EDIT ME: copy, colours, handle, cut definitions
├── assets/                 ← mascot artwork (mascot_source.png → transparent PNGs)
│   ├── mascot_card.png     hand-drawn card with paper edge + shadow (used in the "host" scene)
│   ├── mascot_badge.png    circular face badge (used in "host" + "outro")
│   └── mascot_head.png     head crop
├── audio/vo_0*.mp3         ← EDIT ME: Persian narration, one file per scene, in order
├── framebaz/
│   ├── brand.py            brand + scene deck (Persian on‑screen lines & English subs)
│   ├── textkit.py          Persian reshaping/bidi + typography (Pillow)
│   ├── easings.py          easing curves (out‑back, elastic, expo, stepped/stop‑motion …)
│   ├── fx.py               gradients, grain, vignette, glow, whip‑pan smear, halftone, chromatic aberration
│   ├── templates.py        the 9 scene templates (hook, services, education, process, results,
│   │                       portfolio, host, cta, outro) + mascot card/badge helpers
│   ├── audio.py            decodes the voice‑overs, lays them out scene‑by‑scene, adds the music bed, writes timeline.json
│   └── render.py           draws every frame → pipes raw RGB into ffmpeg; transitions + grade; mux helpers
└── tools/make_all.sh       one command that rebuilds everything
```

Rendering: 1317 frames of 1080×1920 in ~2.5 min (~10 fps) on a 2‑core box, single process,
no GPU — pure Pillow + numpy + ffmpeg. Video is rendered **silent** once, then muxed with
several audio mixes (stream copy), so adding an audio variant costs seconds.

### The drawn character (mascot)

The client illustration lives in `assets/mascot_source.png`. `tools/make_mascot.py`
removes the paper background (border flood-fill, keeps enclosed artwork solid) and
produces `mascot.png` (character + crayon backdrop), `mascot_card.png` (the sticker
card used in the video), `mascot_badge.png` and `mascot_head.png`:

```bash
python3 tools/make_mascot.py                       # uses assets/mascot_source.png
python3 tools/make_mascot.py path/to/new_art.png    # swap in new artwork
```

> Note: the crayon backdrop shares its hue with the skin tones, so a fully automated
> "character only" cut-out is not reliable — the card treatment (character + his own
> crayon backdrop inside a paper-edged card) is both artifact-free and on-brand.
> `make_mascot.py` still writes `assets/mascot_char.png` as a best-effort cut-out.

### Requirements (already provisioned by `tools/bootstrap.sh` in this sandbox)

```bash
# ffmpeg (no apt/network for Debian repos → pip wheel with a static ffmpeg binary)
python3 -m pip install --target ~/.local/share/framebaz/pylibs imageio-ffmpeg
# python libs
python3 -m pip install --target ~/.local/share/framebaz/pylibs pillow numpy arabic-reshaper python-bidi fonttools brotli
# Persian font Vazirmatn + Latin display fonts (Anton, Archivo Black) — npm registry has them
npm pack vazirmatn @fontsource/anton @fontsource/archivo-black
```

Fonts live in `~/.local/share/framebaz/fonts/` and are resolved by
`framebaz/textkit.py` (`FRAMEBAZ_TOOLS` env var overrides the folder).

### Rebuild

```bash
export PYTHONPATH=~/.local/share/framebaz/pylibs:$(pwd)
bash tools/make_all.sh                 # audio → master render → 30s render → mux → poster
# or one step at a time:
python3 -m framebaz.audio  --out out
python3 -m framebaz.render --out out/master.mp4 --timeline out/timeline.json --audio "" --crf 20
```

## How to customise

1. **Text & subtitles** — edit `brand.json` (`scenes[].caption_en`, `scenes[].vo`) and the
   hero Persian headline / card labels in `framebaz/brand.py` (`fa_lines`, `cards`, `stats`).
2. **Colours / logo / handle** — `brand.json → brand.colors`, `name_en`, `handle`, `tagline_en`.
3. **Narration** — replace `audio/vo_XX.mp3` (any TTS or a human recording; mp3/wav both work,
   duration is measured automatically and scene length adapts).
4. **Timing** — per scene `min_dur`, `lead`, `tail` in `brand.py`; total duration is derived
   from the narration.
5. **A new scene** — add an entry to `SCENES` in `brand.py`, a matching block in `brand.json`
   and (optionally) a new template function in `templates.py`, then register it in `TEMPLATES`.

Persian notes: the engine reshapes/bidi‑reorders Persian per frame (`textkit.shape`), and
**Anton/Archivo Black have no Persian glyphs** — Persian numerals/text always use Vazirmatn
(Black/ExtraBold), Latin use the display faces.
