#!/usr/bin/env python3
import argparse
import fcntl
import importlib.util
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Must be set before QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "wayland")
os.environ.setdefault("QT_WAYLAND_SHELL_INTEGRATION", "layer-shell")
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg=false")

from PySide6.QtCore import (  # noqa: E402
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import (  # noqa: E402
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QTextOption,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QWidget  # noqa: E402


APP_ID = "alpha-floating-widget"
DEFAULT_ANIM_MS = 500
DEFAULT_TYPING_CPS = 36.0
DEFAULT_HOLD_MS = 900
DEFAULT_PREVIEW_SIZE = "1600x900"
DEFAULT_LINES = [
    "博士，通讯链路已经接入。接下来的行动，请交给我。",
    "这里是罗德岛。目标区域状态稳定，可以开始下一步确认。",
    "作战记录已同步。请在信号消失前完成必要判断。",
]
FONT_CANDIDATES = [
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "Microsoft YaHei",
    "PingFang SC",
    "WenQuanYi Micro Hei",
    "Sans Serif",
]


@dataclass(frozen=True)
class DialogueClip:
    audio_path: Path
    title: str
    line: str


@dataclass(frozen=True)
class SceneEntry:
    image_path: Path
    clips: list[DialogueClip]
    speaker: str
    side: str | None


@dataclass(frozen=True)
class ConfigBundle:
    entries: list[SceneEntry]
    background_path: Path | None


@dataclass(frozen=True)
class Scene:
    image_path: Path
    audio_path: Path
    speaker: str
    line: str
    side: str
    title: str


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
    parser.add_argument(
        "--speaker",
        default=None,
        help="Override the speaker name shown in the dialogue HUD",
    )
    parser.add_argument(
        "--line",
        action="append",
        default=None,
        help="Override dialogue text. Repeat to choose one line randomly.",
    )
    parser.add_argument(
        "--side",
        choices=("left", "right", "random"),
        default="random",
        help="Visible side for the character portrait",
    )
    parser.add_argument(
        "--typing-cps",
        type=float,
        default=DEFAULT_TYPING_CPS,
        help="Dialogue typing speed in characters per second; use 0 for instant text",
    )
    parser.add_argument(
        "--hold-ms",
        type=int,
        default=DEFAULT_HOLD_MS,
        help="Milliseconds to keep the dialogue visible after audio and typing finish",
    )
    parser.add_argument(
        "--no-dialog",
        action="store_true",
        help="Keep the old character/audio overlay without the dialogue HUD",
    )
    parser.add_argument(
        "--background",
        default=None,
        help="Optional background image. Relative paths resolve from the config directory.",
    )
    parser.add_argument(
        "--preview",
        default=None,
        help="Render one frame to a PNG instead of showing the overlay",
    )
    parser.add_argument(
        "--preview-size",
        default=DEFAULT_PREVIEW_SIZE,
        help="Preview size as WIDTHxHEIGHT",
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


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return list(value)
    return [value]


def resolve_path(path: str, base_dir: Path) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = base_dir / p
    return p.resolve()


def parse_clip(value: Any, base_dir: Path, fallback_line: str = "") -> DialogueClip | None:
    if isinstance(value, dict):
        audio_value = (
            value.get("audio")
            or value.get("path")
            or value.get("voice")
            or value.get("file")
        )
        title = str(value.get("title") or value.get("name") or "").strip()
        line = str(
            value.get("line")
            or value.get("text")
            or value.get("dialogue")
            or fallback_line
        ).strip()
    else:
        audio_value = value
        title = ""
        line = fallback_line

    if not audio_value or not str(audio_value).strip():
        return None

    return DialogueClip(
        audio_path=resolve_path(str(audio_value), base_dir),
        title=title,
        line=line,
    )


def parse_clips(value: Any, base_dir: Path) -> list[DialogueClip]:
    if isinstance(value, dict):
        voice_items = value.get("voices") or value.get("clips") or value.get("dialogues")
        if voice_items:
            return [
                clip
                for clip in (
                    parse_clip(item, base_dir) for item in as_list(voice_items)
                )
                if clip is not None
            ]

        audio_value = (
            value.get("audios")
            or value.get("audio")
            or value.get("voices")
            or value.get("voice")
        )
        lines = [
            str(item).strip()
            for item in as_list(
                value.get("lines")
                or value.get("line")
                or value.get("text")
                or value.get("dialogue")
            )
            if str(item).strip()
        ]
    else:
        audio_value = value
        lines = []

    clips: list[DialogueClip] = []
    for index, audio in enumerate(as_list(audio_value)):
        fallback_line = lines[index] if index < len(lines) else (lines[0] if lines else "")
        clip = parse_clip(audio, base_dir, fallback_line=fallback_line)
        if clip is not None:
            clips.append(clip)

    return clips


def load_config(config_path: Path) -> ConfigBundle:
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

    base_dir = config_path.parent
    entries: list[SceneEntry] = []

    for img, value in data.items():
        image_path = resolve_path(str(img), base_dir)
        speaker = ""
        side: str | None = None

        if isinstance(value, dict):
            speaker = str(value.get("speaker") or value.get("name") or "").strip()
            side_value = str(value.get("side") or "").strip().lower()
            if side_value in {"left", "right"}:
                side = side_value

        entries.append(
            SceneEntry(
                image_path=image_path,
                clips=parse_clips(value, base_dir),
                speaker=speaker,
                side=side,
            )
        )

    background_value = getattr(module, "background", None) or getattr(
        module, "mybackground", None
    )
    background_path = (
        resolve_path(str(background_value), base_dir) if background_value else None
    )

    return ConfigBundle(entries=entries, background_path=background_path)


def choose_scene(
    config: ConfigBundle,
    cli_lines: list[str] | None,
    cli_speaker: str | None,
    cli_side: str,
) -> Scene | None:
    candidates: list[SceneEntry] = []

    for entry in config.entries:
        if not entry.image_path.exists():
            continue

        valid_clips = [clip for clip in entry.clips if clip.audio_path.exists()]
        if not valid_clips:
            continue

        candidates.append(
            SceneEntry(
                image_path=entry.image_path,
                clips=valid_clips,
                speaker=entry.speaker,
                side=entry.side,
            )
        )

    if not candidates:
        return None

    entry = random.choice(candidates)
    clip = random.choice(entry.clips)
    lines = [line.strip() for line in (cli_lines or []) if line.strip()]
    if not lines:
        lines = [clip.line] if clip.line else DEFAULT_LINES

    speaker = (cli_speaker or entry.speaker or "罗德岛").strip()

    if cli_side in {"left", "right"}:
        side = cli_side
    elif entry.side in {"left", "right"}:
        side = entry.side
    else:
        side = random.choice(["left", "right"])

    return Scene(
        image_path=entry.image_path,
        audio_path=clip.audio_path,
        speaker=speaker,
        line=random.choice(lines),
        side=side,
        title=clip.title,
    )


def calc_size(img_w: int, img_h: int, screen_w: int, screen_h: int) -> tuple[int, int]:
    max_w = int(screen_w * 0.56)
    max_h = int(screen_h * 0.96)
    scale = min(max_w / img_w, max_h / img_h)
    return max(1, int(img_w * scale)), max(1, int(img_h * scale))


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def pick_font_family() -> str:
    try:
        families = set(QFontDatabase.families())
    except TypeError:
        families = set(QFontDatabase().families())

    for family in FONT_CANDIDATES:
        if family in families:
            return family

    return "Sans Serif"


def draw_text_shadow(
    painter: QPainter,
    rect: QRectF,
    text: str,
    font: QFont,
    color: QColor,
    option: QTextOption,
    shadow_alpha: int = 220,
) -> None:
    painter.setFont(font)
    painter.setPen(QColor(0, 0, 0, shadow_alpha))
    for dx, dy in ((0, 2), (2, 0), (-2, 0), (0, -2)):
        painter.drawText(rect.translated(dx, dy), text, option)

    painter.setPen(color)
    painter.drawText(rect, text, option)


def draw_dialogue_hud(
    painter: QPainter,
    bounds: QRect,
    speaker: str,
    text: str,
    *,
    visible_chars: int | None = None,
    show_controls: bool = True,
    now_ms: int = 0,
    font_family: str = "Sans Serif",
) -> None:
    w = bounds.width()
    h = bounds.height()
    if w <= 0 or h <= 0:
        return

    shown_text = text if visible_chars is None else text[:visible_chars]
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    panel_w = clamp(int(w * 0.39), 520, 850)
    panel_h = clamp(int(h * 0.24), 178, 260)
    panel_x = clamp(int(w * 0.022), 22, 54)
    panel_y = min(
        h - panel_h - clamp(int(h * 0.12), 70, 160),
        clamp(int(h * 0.62), 300, h - panel_h - 16),
    )
    panel = QRectF(panel_x, panel_y, panel_w, panel_h)

    body = QPainterPath()
    cut = clamp(int(panel_h * 0.10), 10, 22)
    body.moveTo(panel.left() + cut, panel.top())
    body.lineTo(panel.right(), panel.top())
    body.lineTo(panel.right(), panel.bottom() - cut)
    body.lineTo(panel.right() - cut, panel.bottom())
    body.lineTo(panel.left(), panel.bottom())
    body.lineTo(panel.left(), panel.top() + cut)
    body.closeSubpath()

    fill = QLinearGradient(panel.left(), panel.top(), panel.right(), panel.bottom())
    fill.setColorAt(0.0, QColor(18, 22, 24, 214))
    fill.setColorAt(1.0, QColor(18, 20, 22, 174))
    painter.setPen(QPen(QColor(255, 255, 255, 38), 1))
    painter.setBrush(QBrush(fill))
    painter.drawPath(body)

    painter.setPen(QPen(QColor(255, 255, 255, 46), 1))
    painter.drawLine(
        QPointF(panel.left() + 16, panel.top() + 1),
        QPointF(panel.right() - 16, panel.top() + 1),
    )

    label_w = clamp(int(panel_w * 0.29), 116, 168)
    label_h = clamp(int(panel_h * 0.18), 22, 31)
    label_rect = QRectF(panel.left() + 16, panel.top() - label_h + 5, label_w, label_h)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(224, 230, 232, 88))
    painter.drawRect(label_rect)

    label_font = QFont(font_family, clamp(int(h * 0.012), 9, 14), QFont.Weight.Bold)
    label_option = QTextOption(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    label_option.setWrapMode(QTextOption.WrapMode.NoWrap)
    painter.setFont(label_font)
    painter.setPen(QColor(44, 48, 50, 220))
    painter.drawText(label_rect.adjusted(10, 0, 0, 0), "VOICE", label_option)

    text_font_size = clamp(int(h * 0.022), 17, 28)
    text_font = QFont(font_family, text_font_size, QFont.Weight.Medium)
    text_option = QTextOption(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    text_option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    text_rect = QRectF(
        panel.left() + clamp(int(panel_w * 0.055), 24, 42),
        panel.top() + clamp(int(panel_h * 0.17), 24, 38),
        panel.width() - clamp(int(panel_w * 0.12), 56, 94),
        panel.height() - clamp(int(panel_h * 0.24), 40, 62),
    )
    draw_text_shadow(
        painter,
        text_rect,
        shown_text,
        text_font,
        QColor(246, 247, 248),
        text_option,
    )

    if visible_chars is not None and visible_chars >= len(text):
        blink_on = (now_ms // 420) % 2 == 0
        arrow_alpha = 230 if blink_on else 88
        arrow_size = clamp(int(h * 0.014), 10, 18)
        ax = panel.right() - arrow_size * 2.0
        ay = panel.bottom() - arrow_size * 1.45
        arrow = QPolygonF(
            [
                QPointF(ax, ay + arrow_size * 0.2),
                QPointF(ax + arrow_size, ay + arrow_size * 0.2),
                QPointF(ax + arrow_size * 0.5, ay + arrow_size),
            ]
        )
        painter.setBrush(QColor(255, 255, 255, arrow_alpha))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(arrow)

    painter.restore()


def cover_pixmap(pix: QPixmap, width: int, height: int) -> QPixmap:
    scaled = pix.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - width) // 2)
    y = max(0, (scaled.height() - height) // 2)
    return scaled.copy(x, y, width, height)


def parse_size(value: str) -> tuple[int, int]:
    try:
        width_str, height_str = value.lower().split("x", 1)
        width = int(width_str)
        height = int(height_str)
    except ValueError as exc:
        raise ValueError("preview size must be WIDTHxHEIGHT") from exc

    if width < 320 or height < 180:
        raise ValueError("preview size is too small")

    return width, height


class DialogueLayer(QWidget):
    def __init__(
        self,
        parent: QWidget,
        speaker: str,
        line: str,
        typing_cps: float,
        show_controls: bool,
    ):
        super().__init__(parent)
        self.speaker = speaker
        self.line = line
        self.typing_cps = max(0.0, typing_cps)
        self.show_controls = show_controls
        self.font_family = pick_font_family()
        self.visible_chars = len(line) if self.typing_cps <= 0 else 0
        self.typing_started = 0.0

        self.setGeometry(0, 0, parent.width(), parent.height())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self.advance_text)

        self.repaint_timer = QTimer(self)
        self.repaint_timer.timeout.connect(self.update)

    def start(self):
        self.show()
        self.raise_()
        self.typing_started = time.monotonic()
        if self.typing_cps > 0 and self.visible_chars < len(self.line):
            self.typing_timer.start(16)
        self.repaint_timer.start(420)
        self.update()

    def advance_text(self):
        elapsed = time.monotonic() - self.typing_started
        self.visible_chars = min(len(self.line), int(elapsed * self.typing_cps))
        if self.visible_chars >= len(self.line):
            self.typing_timer.stop()
        self.update()

    def ms_until_finished(self) -> int:
        if self.typing_cps <= 0:
            return 0
        remaining = max(0, len(self.line) - self.visible_chars)
        return int((remaining / self.typing_cps) * 1000)

    def paintEvent(self, _event):
        painter = QPainter(self)
        draw_dialogue_hud(
            painter,
            self.rect(),
            self.speaker,
            self.line,
            visible_chars=self.visible_chars,
            show_controls=self.show_controls,
            now_ms=int(time.monotonic() * 1000),
            font_family=self.font_family,
        )


class Overlay(QWidget):
    def __init__(
        self,
        scene: Scene,
        background_path: Path | None,
        anim_ms: int,
        volume: float,
        typing_cps: float,
        hold_ms: int,
        show_dialog: bool,
    ):
        super().__init__()

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            raise RuntimeError("no screen found")

        self.geo: QRect = screen.geometry()
        self.sw = self.geo.width()
        self.sh = self.geo.height()
        self.hold_ms = max(0, hold_ms)
        self.exit_requested = False

        pix_probe = QPixmap(str(scene.image_path))
        if pix_probe.isNull():
            raise RuntimeError(f"cannot load image: {scene.image_path}")

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

        # Wayland / Niri is more stable when the real top-level window stays put.
        self.setGeometry(self.geo)

        self.background_label: QLabel | None = None
        if background_path is not None:
            bg = QPixmap(str(background_path))
            if not bg.isNull():
                self.background_label = QLabel(self)
                self.background_label.setGeometry(0, 0, self.sw, self.sh)
                self.background_label.setPixmap(cover_pixmap(bg, self.sw, self.sh))

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

        y = max(0, self.sh - self.pic_h + int(self.sh * 0.025))
        edge_margin = max(16, int(self.sw * 0.03))

        if scene.side == "left":
            self.start_pos = QPoint(-self.pic_w, y)
            self.visible_pos = QPoint(edge_margin, y)
            self.end_pos = QPoint(-self.pic_w, y)
        else:
            self.start_pos = QPoint(self.sw, y)
            self.visible_pos = QPoint(self.sw - self.pic_w - edge_margin, y)
            self.end_pos = QPoint(self.sw, y)

        self.label.move(self.start_pos)

        self.dialog_layer = (
            DialogueLayer(
                self,
                speaker=scene.speaker,
                line=scene.line,
                typing_cps=typing_cps,
                show_controls=True,
            )
            if show_dialog
            else None
        )

        self.enter_anim = QPropertyAnimation(self.label, b"pos", self)
        self.enter_anim.setDuration(max(1, anim_ms))
        self.enter_anim.setStartValue(self.start_pos)
        self.enter_anim.setEndValue(self.visible_pos)
        self.enter_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.enter_anim.finished.connect(self.on_enter_finished)

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
        self.player.setSource(QUrl.fromLocalFile(str(scene.audio_path)))

        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.errorOccurred.connect(lambda *_: self.request_exit())

    def start(self):
        self.showFullScreen()
        self.raise_()
        if self.dialog_layer is not None:
            self.dialog_layer.raise_()
        QTimer.singleShot(50, self.enter_anim.start)

    def on_enter_finished(self):
        if self.dialog_layer is not None:
            self.dialog_layer.start()
        self.player.play()

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.request_exit()

    def request_exit(self):
        if self.exit_requested:
            return

        self.exit_requested = True
        delay = self.hold_ms
        if self.dialog_layer is not None:
            delay += self.dialog_layer.ms_until_finished()

        QTimer.singleShot(max(0, delay), self.start_exit)

    def start_exit(self):
        if self.exit_anim.state() != QPropertyAnimation.State.Running:
            self.exit_anim.start()


def render_preview(
    scene: Scene,
    background_path: Path | None,
    output_path: Path,
    size: tuple[int, int],
    show_dialog: bool,
) -> None:
    width, height = size
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(12, 14, 18, 255))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    if background_path is not None:
        bg = QPixmap(str(background_path))
        if not bg.isNull():
            painter.drawPixmap(0, 0, cover_pixmap(bg, width, height))

    char_pix = QPixmap(str(scene.image_path))
    if char_pix.isNull():
        raise RuntimeError(f"cannot load image: {scene.image_path}")

    pic_w, pic_h = calc_size(char_pix.width(), char_pix.height(), width, height)
    char_pix = char_pix.scaled(
        pic_w,
        pic_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    edge_margin = max(16, int(width * 0.03))
    x = edge_margin if scene.side == "left" else width - pic_w - edge_margin
    y = max(0, height - pic_h + int(height * 0.025))
    painter.drawPixmap(x, y, char_pix)

    if show_dialog:
        draw_dialogue_hud(
            painter,
            QRect(0, 0, width, height),
            scene.speaker,
            scene.line,
            visible_chars=len(scene.line),
            show_controls=True,
            now_ms=int(time.monotonic() * 1000),
            font_family=pick_font_family(),
        )

    painter.end()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(output_path)):
        raise RuntimeError(f"failed to save preview: {output_path}")


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    config = load_config(config_path)
    scene = choose_scene(
        config=config,
        cli_lines=args.line,
        cli_speaker=args.speaker,
        cli_side=args.side,
    )
    if scene is None:
        return 0

    background_path = (
        resolve_path(args.background, config_path.parent)
        if args.background
        else config.background_path
    )
    if background_path is not None and not background_path.exists():
        background_path = None

    app = QApplication(sys.argv)
    app.setApplicationName(APP_ID)
    app.setDesktopFileName(APP_ID)

    if args.preview:
        render_preview(
            scene=scene,
            background_path=background_path,
            output_path=Path(args.preview).expanduser().resolve(),
            size=parse_size(args.preview_size),
            show_dialog=not args.no_dialog,
        )
        return 0

    lock = single_instance_lock()
    if lock is None:
        return 0

    w = Overlay(
        scene=scene,
        background_path=background_path,
        anim_ms=args.anim_ms,
        volume=args.volume,
        typing_cps=args.typing_cps,
        hold_ms=args.hold_ms,
        show_dialog=not args.no_dialog,
    )
    w.start()

    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        if os.environ.get("ARKNIGHT_DEBUG"):
            raise
        print(f"[{APP_ID}] {exc}", file=sys.stderr)
        raise SystemExit(1)
