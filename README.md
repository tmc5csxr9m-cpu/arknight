# Arknights Dialogue Overlay

Private PySide6 overlay for showing an Arknights-like story dialogue HUD over a character image and voice line.

## Run

Use the existing processed config:

```bash
python main.py config.py
```

Use the PRTS sample assets:

```bash
python main.py prts_sample_config.py
```

Render a preview PNG without opening the overlay:

```bash
QT_QPA_PLATFORM=offscreen python main.py prts_sample_config.py --preview previews/prts_story_dialog.png
```

## Config

The old format still works:

```python
myconfig = {
    "processed_png/1_3_cropped.png": ["1.wav", "2.wav"],
}
```

The richer dialogue format supports speaker, lines, side, and optional background:

```python
myconfig = {
    "assets/prts/Avg_avg_2026_yu_1-1$1.png": {
        "audios": ["start.wav"],
        "speaker": "余",
        "lines": ["这里不是终点，只是另一个需要做出选择的路口。"],
        "side": "right",
    },
}

background = "assets/prts/Avg_23_I01.png"
```

Useful flags:

```bash
python main.py config.py --speaker 阿米娅 --line "博士，请下达指令。" --side left
python main.py config.py --no-dialog
python main.py config.py --typing-cps 0 --hold-ms 1600 --speed-label 3X
```

PRTS-downloaded files are documented in `assets/prts/SOURCES.md`. Keep this project private while it contains game assets.
