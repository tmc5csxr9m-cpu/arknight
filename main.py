#!/usr/bin/env python3
import os
import sys
import random
import argparse
import importlib.util
import fcntl
from pathlib import Path
from typing import Any

# 必须在 QApplication 创建前设置。
os.environ.setdefault("QT_QPA_PLATFORM", "wayland")
os.environ.setdefault("QT_WAYLAND_SHELL_INTEGRATION", "layer-shell")
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg=false")

from PySide6.QtCore import (
    Qt,
    QUrl,
    QRect,
    QPoint,
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
)
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


APP_ID = "alpha-floating-widget"
DEFAULT_ANIM_MS = 500


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        nargs="?",
        default="config.py",
        help="Path to config.py / processed_config.py",
    )
    parser.add_argument(
        "--anim-ms",
        type=int,
        default=DEFAULT_ANIM_MS,
        help="Animation duration in milliseconds",
    )
    parser.add_argument(
        "--volume",
        type=float,
        default=1.0,
        help="Audio volume, 0.0 - 1.0",
    )
    return parser.parse_args()


def single_instance_lock():
    f = open(f"/tmp/{APP_ID}.lock", "w", encoding="utf-8")

    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        f.write(str(os.getpid()))
        f.flush()
        return f
    except BlockingIOError:
        return None


def load_config(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"config not found: {config_path}")

    spec = importlib.util.spec_from_file_location("user_config", config_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load config: {config_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    data = getattr(module, "myconfig", None)

    if not isinstance(data, dict) or not data:
        raise RuntimeError(
            "config must contain: myconfig = {image_path: [audio_path, ...], ...}"
        )

    # 注意：这里故意不转换 value。
    # 新配置格式中 value 是 list[str]，如果 str(value)，会变成
    # "['1.wav', '2.wav']" 这种错误路径。
    return data


def choose_pair(config: dict[str, Any]) -> tuple[Path, Path] | None:
    pairs: list[tuple[Path, list[Path]]] = []

    for img, audio_items in config.items():
        img_path = Path(str(img)).expanduser()

        if not img_path.is_absolute():
            continue

        if not img_path.exists():
            continue

        if isinstance(audio_items, str):
            audio_list = [audio_items]
        elif isinstance(audio_items, list | tuple):
            audio_list = audio_items
        else:
            continue

        valid_audios: list[Path] = []

        for audio in audio_list:
            audio_path = Path(str(audio)).expanduser()

            if not audio_path.is_absolute():
                continue

            if audio_path.exists():
                valid_audios.append(audio_path)

        if valid_audios:
            pairs.append((img_path, valid_audios))

    if not pairs:
        return None

    image_path, audio_list = random.choice(pairs)
    audio_path = random.choice(audio_list)

    return image_path, audio_path


def calc_size(img_w: int, img_h: int, screen_w: int, screen_h: int) -> tuple[int, int]:
    max_w = screen_w // 2
    max_h = screen_h

    scale = min(max_w / img_w, max_h / img_h)

    return max(1, int(img_w * scale)), max(1, int(img_h * scale))


class Overlay(QWidget):
    def __init__(self, image_path: Path, audio_path: Path, anim_ms: int, volume: float):
        super().__init__()

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("no screen found")

        self.geo: QRect = screen.geometry()
        self.sw = self.geo.width()
        self.sh = self.geo.height()

        pix_probe = QPixmap(str(image_path))
        if pix_probe.isNull():
            raise RuntimeError(f"cannot load image: {image_path}")

        self.pic_w, self.pic_h = calc_size(
            pix_probe.width(),
            pix_probe.height(),
            self.sw,
            self.sh,
        )

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
        )

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # Wayland / Niri 下不要移动真实顶层窗口。
        # 使用全屏透明 Layer Shell 窗口，只移动里面的 QLabel，动画稳定很多。
        self.setGeometry(self.geo)

        self.label = QLabel(self)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.label.setFixedSize(self.pic_w, self.pic_h)

        pix = pix_probe.scaled(
            self.pic_w,
            self.pic_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.label.setPixmap(pix)

        y = (self.sh - self.pic_h) // 2

        from_left = random.choice([True, False])

        if from_left:
            self.start_pos = QPoint(-self.pic_w, y)
            self.visible_pos = QPoint(0, y)
            self.end_pos = QPoint(-self.pic_w, y)
        else:
            self.start_pos = QPoint(self.sw, y)
            self.visible_pos = QPoint(self.sw - self.pic_w, y)
            self.end_pos = QPoint(self.sw, y)

        self.label.move(self.start_pos)

        self.enter_anim = QPropertyAnimation(self.label, b"pos", self)
        self.enter_anim.setDuration(max(1, anim_ms))
        self.enter_anim.setStartValue(self.start_pos)
        self.enter_anim.setEndValue(self.visible_pos)
        self.enter_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.enter_anim.finished.connect(self.play_audio)

        self.exit_anim = QPropertyAnimation(self.label, b"pos", self)
        self.exit_anim.setDuration(max(1, anim_ms))
        self.exit_anim.setStartValue(self.visible_pos)
        self.exit_anim.setEndValue(self.end_pos)
        self.exit_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.exit_anim.finished.connect(QApplication.instance().quit)

        self.audio = QAudioOutput(self)
        self.audio.setVolume(max(0.0, min(1.0, volume)))

        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)
        self.player.setSource(QUrl.fromLocalFile(str(audio_path)))

        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.errorOccurred.connect(lambda *_: self.start_exit())

    def start(self):
        self.showFullScreen()
        self.raise_()
        QTimer.singleShot(50, self.enter_anim.start)

    def play_audio(self):
        self.player.play()

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.start_exit()

    def start_exit(self):
        if self.exit_anim.state() != QPropertyAnimation.State.Running:
            self.exit_anim.start()


def main() -> int:
    args = parse_args()

    lock = single_instance_lock()
    if lock is None:
        return 0

    config = load_config(Path(args.config))

    chosen = choose_pair(config)
    if chosen is None:
        return 0

    image, audio = chosen

    app = QApplication(sys.argv)
    app.setApplicationName(APP_ID)
    app.setDesktopFileName(APP_ID)

    w = Overlay(
        image_path=image,
        audio_path=audio,
        anim_ms=args.anim_ms,
        volume=args.volume,
    )
    w.start()

    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)