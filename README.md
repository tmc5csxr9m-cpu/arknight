# Arknights Home Voice Overlay

Private PySide6 overlay for showing an Arknights-style home assistant voice bubble over the existing character images.

## Run

Use the default matched voice config:

```bash
python main.py config.py
```

Use the short greeting-only config:

```bash
python main.py start.py
```

Render a preview PNG without opening the overlay:

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py --preview previews/home_voice_bubble.png --line "你们在最危急的时候带领罗德岛找到了航向，阿米娅无疑已经是成熟的领袖，我也从未怀疑过可露希尔的才能与你的决策。罗德岛不会因为离开谁就无法前行，失去的一切同样造就了现在的罗德岛。"
```

## Config

Each `voices` item binds one audio file to its matching subtitle:

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

Useful flags:

```bash
python main.py config.py --speaker 凯尔希·思衡托 --line "Dr.，我在。" --side left
python main.py config.py --no-dialog
python main.py config.py --typing-cps 0 --hold-ms 1600
```

PRTS-downloaded voice files are documented in `assets/voices/char_1052_kalts2/SOURCES.md`. Keep this project private while it contains game assets.
