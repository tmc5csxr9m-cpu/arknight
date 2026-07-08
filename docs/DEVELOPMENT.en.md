# Development Guide

This document is for maintainers. It covers architecture, data flow, rendering, animation, asset maintenance, validation, and release checks.

## Table of Contents

- [Project Scope](#project-scope)
- [Repository Layout](#repository-layout)
- [Entry Flow](#entry-flow)
- [Core Data Model](#core-data-model)
- [Config Loading](#config-loading)
- [Random Selection](#random-selection)
- [Window and Layer Structure](#window-and-layer-structure)
- [Bubble Rendering](#bubble-rendering)
- [Animation and Lifecycle](#animation-and-lifecycle)
- [Audio Playback](#audio-playback)
- [Preview Rendering](#preview-rendering)
- [PNG Preprocessing](#png-preprocessing)
- [Adding Voice Clips](#adding-voice-clips)
- [Adding Portraits](#adding-portraits)
- [Quality Checks](#quality-checks)
- [Public Release Checks](#public-release-checks)
- [Common Maintenance Tasks](#common-maintenance-tasks)
- [Future Improvements](#future-improvements)

<a id="project-scope"></a>
## Project Scope

This project is only a local desktop overlay:

- It does not read game process memory.
- It does not modify game files.
- It does not automate the game client.
- It does not call official game APIs.
- It does not upload user data.

The current target is the Arknights home assistant `VOICE` bubble, not the visual-novel story dialogue UI. The earlier story-style bottom subtitle bar has been replaced; future UI work should continue to reference the home-screen voice bubble.

Asset maintenance principles:

- The code may be public, but game assets should not be described as open-source assets.
- Voice, portrait, and dialogue sources must be documented.
- Non-commercial use does not automatically remove copyright risk.
- Remove assets promptly if requested by rights holders.

<a id="repository-layout"></a>
## Repository Layout

```text
.
├── main.py
├── config.py
├── start.py
├── process.py
├── 1.png
├── 2.png
├── processed_png/
├── assets/
│   └── voices/
│       └── char_1052_kalts2/
│           ├── cn_001.mp3
│           ├── cn_002.mp3
│           ├── cn_003.mp3
│           ├── cn_004.mp3
│           ├── cn_010.mp3
│           ├── cn_034.mp3
│           ├── cn_036.mp3
│           ├── cn_042.mp3
│           └── SOURCES.md
├── previews/
├── docs/
│   ├── DEVELOPMENT.md
│   ├── DEVELOPMENT.zh-CN.md
│   └── DEVELOPMENT.en.md
├── README.md
├── README.zh-CN.md
└── README.en.md
```

Key files:

| File | Purpose |
| --- | --- |
| `main.py` | Runtime entry point: config loading, scene selection, Qt overlay, rendering, and playback. |
| `config.py` | Random voice config. |
| `start.py` | Greeting-only config. |
| `process.py` | PNG transparent-border cropping helper. |
| `processed_png/` | Cropped portrait assets. |
| `assets/voices/.../SOURCES.md` | Voice source notes. |
| `previews/` | Rendered UI previews. |

`main.py.bak` and `process.py.bak` are historical backup files and are still tracked. If you remove them, do it in a dedicated cleanup commit.

<a id="entry-flow"></a>
## Entry Flow

Run command:

```bash
python main.py config.py
```

Execution flow:

1. Set Qt environment variables.
2. Import PySide6.
3. `parse_args()` reads CLI options.
4. `load_config()` loads the config file.
5. `choose_scene()` selects one valid `Scene`.
6. Create `QApplication`.
7. If `--preview` is provided, call `render_preview()` and exit.
8. For live overlay mode, acquire the single-instance lock.
9. Create `Overlay`.
10. `Overlay.start()` shows the full-screen transparent window.
11. The portrait slides in.
12. The bubble fades in, typewriter text begins, and audio starts.
13. After audio ends, wait for `hold_ms`.
14. The bubble fades out and the portrait slides out.
15. The app exits.

<a id="core-data-model"></a>
## Core Data Model

### `DialogueClip`

Represents one voice clip and its matching subtitle.

```python
@dataclass(frozen=True)
class DialogueClip:
    audio_path: Path
    title: str
    line: str
```

Maintenance rules:

- `audio_path` must point to a local playable file.
- `line` should match the audio.
- `title` is used for debugging, config readability, and future extensions.

### `SceneEntry`

Represents one portrait and its candidate clips.

```python
@dataclass(frozen=True)
class SceneEntry:
    image_path: Path
    clips: list[DialogueClip]
    speaker: str
    side: str | None
```

### `ConfigBundle`

Loaded config collection.

```python
@dataclass(frozen=True)
class ConfigBundle:
    entries: list[SceneEntry]
    background_path: Path | None
```

### `Scene`

The selected scene for one run.

```python
@dataclass(frozen=True)
class Scene:
    image_path: Path
    audio_path: Path
    speaker: str
    line: str
    side: str
    title: str
```

<a id="config-loading"></a>
## Config Loading

`load_config(config_path)` dynamically loads a Python config file with `importlib.util.spec_from_file_location()`.

Requirements:

- The config file must define `myconfig`.
- `myconfig` must be a non-empty `dict`.
- Keys are image paths.
- Values may use the older format or the recommended new format.

Recommended format:

```python
myconfig = {
    "processed_png/1_3_cropped.png": {
        "speaker": "凯尔希·思衡托",
        "side": "left",
        "voices": [
            {
                "title": "问候",
                "audio": "assets/voices/char_1052_kalts2/cn_042.mp3",
                "text": "Dr.，我在。",
            },
        ],
    },
}
```

Compatible older format:

```python
myconfig = {
    "processed_png/1_3_cropped.png": ["voice1.mp3", "voice2.mp3"],
}
```

The older format has no subtitle binding and is only suitable for simple playback. New maintenance should prefer `voices`.

Path resolution is handled by `resolve_path()`:

- `~/...` is expanded.
- Relative paths are resolved from the config file directory.
- The final value is an absolute path.

<a id="random-selection"></a>
## Random Selection

`choose_scene()` filters invalid candidates first:

- Missing image: skip the `SceneEntry`.
- Missing audio: skip the `DialogueClip`.
- No valid clips for an image: skip that image.

Then it randomly selects:

1. One valid `SceneEntry`.
2. One valid `DialogueClip` from that entry.
3. CLI `--line` text if provided.
4. Otherwise, the clip's own subtitle.
5. If the clip has no subtitle, fallback `DEFAULT_LINES`.
6. Portrait side from CLI `--side`, config `side`, or random choice.

The audio and subtitle must be bound in the same `DialogueClip` to avoid mismatches.

<a id="window-and-layer-structure"></a>
## Window and Layer Structure

`Overlay` is the top-level window:

- `FramelessWindowHint`
- `Tool`
- `WindowStaysOnTopHint`
- `WindowTransparentForInput`
- `WA_TranslucentBackground`
- `WA_NoSystemBackground`
- `WA_TransparentForMouseEvents`

Layers from bottom to top:

1. Optional background image: `background_label`
2. Portrait: `label`
3. Bubble layer: `dialog_layer`

On Wayland / Niri, the top-level window stays fixed and only the inner `QLabel` moves. This reduces flicker and layer instability.

<a id="bubble-rendering"></a>
## Bubble Rendering

Core function: `draw_dialogue_hud()`

Main steps:

1. Compute bubble size and position.
2. Create a clipped-corner `QPainterPath`.
3. Paint panel shadow.
4. Paint translucent gradient panel.
5. Paint top highlight and subtle bottom line.
6. Paint the `VOICE` label.
7. Compute text bounds.
8. Use `fit_font_to_rect()` to choose font size.
9. Set clip path so text stays inside the panel.
10. Paint low-shadow text.
11. If typing is complete, paint the small completion arrow.

### Text Fitting

`fit_font_to_rect()` uses `QTextDocument` for measurement:

```python
doc = QTextDocument()
doc.setDocumentMargin(0)
doc.setDefaultFont(font)
doc.setPlainText(text)
doc.setTextWidth(rect.width())
doc.size().height()
```

It walks from max font size down to min font size and returns the largest font that fits inside the text rectangle.

### Visual Rules

The home bubble is not a story subtitle box. Avoid:

- Large bottom black bars
- Over-bright white text
- Heavy outlines
- Card-like rounded rectangles
- Strong drop shadows

Current direction:

- Dark translucent panel
- Light glass-like layering
- Subtle borders
- Low-outline text
- Clear `VOICE` label

<a id="animation-and-lifecycle"></a>
## Animation and Lifecycle

### Portrait Motion

The portrait uses `QPropertyAnimation(self.label, b"pos")`:

- Enter: `OutCubic`
- Exit: `InCubic`
- Default duration: `DEFAULT_ANIM_MS = 500`

Side behavior:

- `left`: enters from outside the left edge.
- `right`: enters from outside the right edge.

### Bubble Motion

The bubble uses `QGraphicsOpacityEffect`:

- Fade in: 180ms, `OutCubic`
- Fade out: 220ms, `OutCubic`

Why:

- The UI no longer disappears abruptly.
- The bubble does not move, reducing visual separation from the home-screen style.
- Only opacity is animated, keeping overhead low.

### Exit Order

1. Audio reaches `EndOfMedia`.
2. Wait `hold_ms`.
3. If typewriter text is still running, wait for it to finish.
4. `dialog_layer.fade_out()`.
5. Portrait slides out.
6. `QApplication.quit()`.

<a id="audio-playback"></a>
## Audio Playback

Uses:

- `QMediaPlayer`
- `QAudioOutput`
- `QUrl.fromLocalFile()`

End detection:

```python
if status == QMediaPlayer.MediaStatus.EndOfMedia:
    self.request_exit()
```

Error handling:

```python
self.player.errorOccurred.connect(lambda *_: self.request_exit())
```

If playback fails, the app still exits cleanly instead of hanging.

<a id="preview-rendering"></a>
## Preview Rendering

`render_preview()` does not create the live overlay. It paints directly into a `QImage`:

1. Create a `QImage` with the requested size.
2. Fill a dark background.
3. Optionally paint the background image.
4. Paint the scaled portrait.
5. Call `draw_dialogue_hud()`.
6. Save PNG.

Standard preview:

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble.png \
  --preview-size 1600x900 \
  --typing-cps 0
```

Small-window validation:

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble_small.png \
  --preview-size 1055x965 \
  --typing-cps 0
```

Before committing UI changes, check:

- Text does not overflow.
- Long text is not clipped into unreadability.
- The bubble does not cover the face.
- The layout remains acceptable in a smaller window.

<a id="png-preprocessing"></a>
## PNG Preprocessing

`process.py` uses Pillow to crop fully transparent PNG borders.

Command:

```bash
python process.py config.py --out-dir processed_png --out-config processed_config.py
```

Core logic:

```python
img = Image.open(src).convert("RGBA")
bbox = img.getchannel("A").getbbox()
cropped = img.crop(bbox)
cropped.save(dst, format="PNG")
```

Notes:

- No recoloring.
- No alpha premultiplication.
- No opacity changes.
- Only fully transparent outer borders are cropped.

<a id="adding-voice-clips"></a>
## Adding Voice Clips

1. Confirm the operator voice key from the PRTS voice record page.
2. Confirm the Chinese resource path, for example `voice_cn/char_1052_kalts2`.
3. Download audio into `assets/voices/<voice-key>/`.
4. Update `SOURCES.md` with page URL, resource path, filenames, and titles.
5. Add `voices` entries to `config.py`.
6. Ensure `audio` and `text` match.
7. Run compile checks.
8. Render previews.

Download example:

```bash
curl -L --fail -o assets/voices/char_1052_kalts2/cn_003.mp3 \
  https://torappu.prts.wiki/assets/audio/voice_cn/char_1052_kalts2/cn_003.mp3
```

<a id="adding-portraits"></a>
## Adding Portraits

1. Add the original PNG.
2. Write a temporary config so `process.py` can see the image.
3. Run `process.py` to crop transparent borders.
4. Inspect the cropped output.
5. Reference `processed_png/...` in the real config.
6. Render a preview to check portrait placement.

Portrait scale is controlled by `calc_size()`:

```python
max_w = int(screen_w * 0.56)
max_h = int(screen_h * 0.96)
scale = min(max_w / img_w, max_h / img_h)
```

If a portrait is too large or too small, adjust this logic before editing source images.

<a id="quality-checks"></a>
## Quality Checks

Compile check:

```bash
python -m py_compile main.py process.py config.py start.py
```

Config check:

```bash
python - <<'PY'
from pathlib import Path
from main import load_config

for cfg in ["config.py", "start.py"]:
    bundle = load_config(Path(cfg))
    print(cfg)
    for entry in bundle.entries:
        print(entry.image_path.name, len(entry.clips), [clip.title for clip in entry.clips])
PY
```

Preview check:

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble.png \
  --preview-size 1600x900 \
  --typing-cps 0
```

High-confidence secret scan:

```bash
git grep -I -n -E '(gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |OPENSSH |DSA |EC |PGP )?PRIVATE KEY-----|Bearer [A-Za-z0-9._-]{30,})' -- . ':!*.png' ':!*.mp3'
```

<a id="public-release-checks"></a>
## Public Release Checks

Before public release:

- `git status --short --branch` is clean.
- No `.env` files.
- No token, key, pem, p12, or secret files.
- Local reference screenshots are ignored.
- README copyright wording is not overconfident.
- Voice and portrait sources are documented.
- Preview images render correctly.
- Compile checks pass.

Make public:

```bash
gh repo edit --visibility public --accept-visibility-change-consequences
```

Make private again:

```bash
gh repo edit --visibility private --accept-visibility-change-consequences
```

<a id="common-maintenance-tasks"></a>
## Common Maintenance Tasks

### Update README Preview

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble.png \
  --preview-size 1600x900 \
  --typing-cps 0
```

### Verify `config.py` Is Random Mode

```bash
python - <<'PY'
from pathlib import Path
from main import load_config
bundle = load_config(Path("config.py"))
print([len(entry.clips) for entry in bundle.entries])
PY
```

Each portrait should have eight candidates.

### Verify `start.py` Is Greeting-Only

```bash
python - <<'PY'
from pathlib import Path
from main import load_config
bundle = load_config(Path("start.py"))
print([[clip.title for clip in entry.clips] for entry in bundle.entries])
PY
```

Only `问候` should appear.

### Debug Audio Playback

Check files:

```bash
file assets/voices/char_1052_kalts2/*.mp3
```

If Qt cannot play mp3, check your system GStreamer / FFmpeg backend.

<a id="future-improvements"></a>
## Future Improvements

Possible improvements:

- Split `main.py` into `config_loader.py`, `rendering.py`, and `overlay.py`.
- Add unit tests for config parsing.
- Add more preview samples for different aspect ratios.
- Improve font baseline tuning to better match screenshots.
- Support theme parameters instead of editing drawing code directly.
- Remove historical `.bak` files.
- Add `requirements.txt` or `pyproject.toml`.

Back:

- [English README](../README.en.md)
- [Development documentation index](DEVELOPMENT.md)
