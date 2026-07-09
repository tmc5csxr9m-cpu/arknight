# Arknights Home Voice Overlay

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?style=flat-square)
![Wayland](https://img.shields.io/badge/Target-Linux%20Wayland-555?style=flat-square)
![Code License](https://img.shields.io/badge/Code%20License-AGPL--3.0--only-blue?style=flat-square)
![Fan Tool](https://img.shields.io/badge/Project-Non--Commercial%20Fan%20Tool-2E8B57?style=flat-square)

A PySide6 desktop overlay that simulates the Arknights home assistant `VOICE` bubble. It displays the existing character portrait, plays a matched voice clip, and renders a translucent subtitle bubble near the lower-left corner.

> Copyright notice: This is a non-commercial fan project. Game portraits, voices, dialogue text, and related assets remain the property of Hypergryph and its affiliates. PRTS is documented only as the asset source. This repository does not re-license the original game assets and is not legal advice. Public repository availability does not mean the assets are open-licensed, and non-commercial use does not automatically remove copyright risk.

## Table of Contents

- [Result](#result)
- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [CLI Options](#cli-options)
- [Preview Rendering](#preview-rendering)
- [License and Asset Boundary](#license-and-asset-boundary)
- [Asset Sources](#asset-sources)
- [Troubleshooting](#troubleshooting)
- [Developer Documentation](#developer-documentation)

<a id="result"></a>
## Result

The app displays the processed existing portrait and renders a `VOICE` bubble similar to the Arknights home assistant interaction. The bubble supports:

- Automatic exit after audio playback
- Portrait slide-in and slide-out
- Bubble fade-in and fade-out
- Typewriter text
- Automatic long-text font fitting
- Text clipping inside the bubble

Preview:

![Home voice bubble preview](previews/home_voice_bubble.png)

Small-window validation:

![Small preview](previews/home_voice_bubble_small.png)

<a id="features"></a>
## Features

| Feature | Description |
| --- | --- |
| Transparent top-level overlay | A frameless, always-on-top PySide6 window with transparent background. |
| Existing character art | Keeps the repository's existing `1.png`, `2.png`, and processed portraits. |
| Random voice mode | `config.py` randomly selects a home-related voice clip. |
| Greeting-only mode | `start.py` only plays the greeting clip. |
| Matched subtitles | Each `voices` item contains both `audio` and `text`, avoiding mismatches. |
| Long-text fitting | Uses `QTextDocument` measurement to fit text into the bubble. |
| Offline preview | `--preview` renders a PNG without opening the live overlay. |

<a id="requirements"></a>
## Requirements

Recommended environment:

- Linux desktop
- Wayland session
- Python 3.11 or newer
- PySide6
- Pillow

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install PySide6 Pillow
```

> Note: The script sets `QT_QPA_PLATFORM=wayland` and `QT_WAYLAND_SHELL_INTEGRATION=layer-shell` by default. If you use X11 or another desktop setup, adjust Qt platform variables for your environment.

<a id="quick-start"></a>
## Quick Start

### Run Random Voice Mode

`config.py` randomly selects one processed portrait and one of eight home-related voice clips.

```bash
python main.py config.py
```

### Run Greeting Mode

`start.py` only plays the greeting clip. It is suitable for startup scripts, key bindings, or desktop events.

```bash
python main.py start.py
```

### Override Subtitle Temporarily

```bash
python main.py config.py \
  --speaker "Kal'tsit the Shimmering Vow" \
  --line "Dr., I am here." \
  --side left
```

### Hide the Bubble

```bash
python main.py config.py --no-dialog
```

<a id="configuration"></a>
## Configuration

### `config.py`

Random mode. Each portrait currently has eight Chinese Kal'tsit the Shimmering Vow home clips:

- Assistant assignment
- Talk 1
- Talk 2
- Talk 3
- Idle
- Tap
- Trust tap
- Greeting

### `start.py`

Greeting-only mode. Each portrait only has one clip:

- Greeting

### Recommended Config Shape

```python
myconfig = {
    "processed_png/2_3_cropped.png": {
        "speaker": "凯尔希·思衡托",
        "side": "left",
        "voices": [
            {
                "title": "交谈2",
                "audio": "assets/voices/char_1052_kalts2/cn_003.mp3",
                "text": "你们在最危急的时候带领罗德岛找到了航向...",
            },
        ],
    },
}
```

### Field Reference

| Field | Type | Description |
| --- | --- | --- |
| `myconfig` | `dict` | Required top-level config. Keys are image paths; values are image-specific settings. |
| `speaker` | `str` | Speaker metadata. The current UI does not display it, but it is kept for future use. |
| `side` | `"left"` / `"right"` | Portrait entrance and resting side. |
| `voices` | `list[dict]` | Candidate voice clips. |
| `title` | `str` | Voice title, such as `交谈2`. |
| `audio` | `str` | Local audio path. Relative paths are supported. |
| `text` | `str` | Subtitle text shown in the bubble. |

Path rules:

- Absolute paths are used as-is.
- Relative paths are resolved from the config file directory.
- Missing audio files are skipped.
- Missing image files are skipped.

<a id="cli-options"></a>
## CLI Options

Base command:

```bash
python main.py [config] [options]
```

Common options:

| Option | Example | Description |
| --- | --- | --- |
| `config` | `config.py` | Config file path. Defaults to `config.py`. |
| `--volume` | `--volume 0.8` | Audio volume from `0.0` to `1.0`. |
| `--anim-ms` | `--anim-ms 450` | Portrait slide duration in milliseconds. |
| `--typing-cps` | `--typing-cps 36` | Typewriter speed in characters per second. `0` shows full text immediately. |
| `--hold-ms` | `--hold-ms 1600` | Extra hold time after audio ends, in milliseconds. |
| `--side` | `--side left` | Force the portrait side. |
| `--line` | `--line "Dr., I am here."` | Temporarily override subtitle text. Can be repeated; one line is chosen randomly. |
| `--speaker` | `--speaker "Kal'tsit"` | Override speaker metadata. |
| `--no-dialog` | `--no-dialog` | Hide the voice bubble. |
| `--background` | `--background bg.png` | Optional background image. |
| `--preview` | `--preview out.png` | Render a preview image instead of opening the live overlay. |
| `--preview-size` | `--preview-size 1600x900` | Preview image size. |

<a id="preview-rendering"></a>
## Preview Rendering

Use preview mode while tuning the UI to avoid repeatedly opening the live desktop overlay.

Standard 16:9 preview:

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble.png \
  --preview-size 1600x900 \
  --typing-cps 0
```

Small-window long-text validation:

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble_small.png \
  --preview-size 1055x965 \
  --typing-cps 0 \
  --line "你们在最危急的时候带领罗德岛找到了航向，阿米娅无疑已经是成熟的领袖，我也从未怀疑过可露希尔的才能与你的决策。罗德岛不会因为离开谁就无法前行，失去的一切同样造就了现在的罗德岛。"
```

<a id="license-and-asset-boundary"></a>
## License and Asset Boundary

This repository uses split licensing:

- Project-owned Python code is licensed under `AGPL-3.0-only`.
- Full license text: [LICENSES/AGPL-3.0-only.txt](LICENSES/AGPL-3.0-only.txt).
- Scope summary: [LICENSE.md](LICENSE.md).
- Game assets and game content are excluded from AGPL: [ASSETS-NOTICE.md](ASSETS-NOTICE.md).

Materials not covered by AGPL-3.0-only include:

- `1.png`, `2.png`
- `processed_png/`
- `previews/`
- `assets/voices/`
- Arknights character names, dialogue text, voice audio, portraits, and other
  game-derived content appearing in configuration files and documentation

<a id="asset-sources"></a>
## Asset Sources

Voice files are sourced from the PRTS `凯尔希·思衡托/语音记录` page. Download paths and voice IDs are documented in:

- [assets/voices/char_1052_kalts2/SOURCES.md](assets/voices/char_1052_kalts2/SOURCES.md)

Current voice directory:

```text
assets/voices/char_1052_kalts2/
├── cn_001.mp3
├── cn_002.mp3
├── cn_003.mp3
├── cn_004.mp3
├── cn_010.mp3
├── cn_034.mp3
├── cn_036.mp3
├── cn_042.mp3
└── SOURCES.md
```

Public maintenance notes:

- Do not claim that game assets are open-source assets.
- Do not re-license the assets to others.
- Remove assets promptly if requested by rights holders.
- For commercial use, replace all game assets with assets you are licensed to use.

<a id="troubleshooting"></a>
## Troubleshooting

### No Window Appears

The app uses `/tmp/alpha-floating-widget.lock` to prevent duplicate instances. If another instance is running, the new process exits immediately.

### No Audio

Check:

- The audio file exists.
- System audio output works.
- You did not pass `--volume 0`.
- Qt Multimedia can play mp3 files in your environment.

### Does Not Show on Wayland

Default environment variables:

```python
QT_QPA_PLATFORM=wayland
QT_WAYLAND_SHELL_INTEGRATION=layer-shell
```

Different desktop environments vary in support. If the overlay does not appear, try adjusting Qt platform settings for your desktop.

### Preview Fails

Use the offscreen platform:

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py --preview out.png
```

### Subtitle Is Still Too Long

The implementation auto-fits font size and clips text inside the bubble. If you want a result closer to the game, shorten `text`, because the real home bubble is not designed for very long paragraphs either.

<a id="developer-documentation"></a>
## Developer Documentation

- [English Development Guide](docs/DEVELOPMENT.en.md)
- [中文开发文档](docs/DEVELOPMENT.zh-CN.md)

Language links:

- [中文说明](README.zh-CN.md)
- [Root README](README.md)
