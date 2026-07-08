# Development Guide / 开发者文档

This document is bilingual. Each section includes Chinese first, followed by English.  
本文档为中英双语，中文在前，英文在后。

## 1. 项目定位 / Project Scope

中文：本项目是一个本地桌面浮层脚本，用 PySide6 模拟《明日方舟》主界面助理语音气泡。它不是游戏客户端、不是自动化工具，也不接入游戏进程。  
English: This project is a local desktop overlay script that uses PySide6 to simulate the Arknights home assistant voice bubble. It is not a game client, automation tool, or game-process integration.

中文：当前仓库包含游戏素材，因此公开维护时应保持非商业、署名来源清晰、可按权利方要求移除素材。  
English: The repository currently contains game assets. Keep the project non-commercial, document asset sources clearly, and remove assets if requested by rights holders.

## 2. 目录结构 / Repository Layout

```text
.
├── main.py                         # PySide6 overlay runtime
├── config.py                       # Random voice config
├── start.py                        # Greeting-only config
├── process.py                      # PNG alpha-border cropping helper
├── 1.png / 2.png                   # Original character images
├── processed_png/                  # Cropped portrait assets
├── assets/voices/char_1052_kalts2/ # Downloaded voice files and source notes
├── previews/                       # Rendered UI previews
└── docs/DEVELOPMENT.md             # This file
```

中文：`main.py.bak` 和 `process.py.bak` 是历史备份文件，目前仍被 git 跟踪。后续如果要整理仓库，可以在单独提交中确认是否删除。  
English: `main.py.bak` and `process.py.bak` are historical backup files and are still tracked. If you want to clean the repository later, remove them in a dedicated commit after review.

## 3. 运行流程 / Runtime Flow

中文：

1. `parse_args()` 读取命令行参数。
2. `load_config()` 动态加载 `config.py` 或 `start.py`。
3. `choose_scene()` 从有效图片和音频中随机选择一个 `Scene`。
4. `Overlay` 创建全屏透明置顶窗口。
5. 立绘 `QLabel` 从屏幕左侧或右侧滑入。
6. `DialogueLayer` 绘制 `VOICE` 气泡并执行文字打字效果。
7. `QMediaPlayer` 播放音频。
8. 音频结束后等待 `hold_ms`，气泡淡出，立绘滑出，程序退出。

English:

1. `parse_args()` reads CLI options.
2. `load_config()` dynamically loads `config.py` or `start.py`.
3. `choose_scene()` randomly selects a valid `Scene` from available images and clips.
4. `Overlay` creates a full-screen transparent always-on-top window.
5. The portrait `QLabel` slides in from the left or right.
6. `DialogueLayer` paints the `VOICE` bubble and handles typewriter text.
7. `QMediaPlayer` plays audio.
8. After audio ends and `hold_ms` elapses, the bubble fades out, the portrait slides out, and the app exits.

## 4. 数据模型 / Data Model

### `DialogueClip`

中文：表示一条语音和它对应的字幕。  
English: Represents one voice clip and its matching subtitle.

```python
@dataclass(frozen=True)
class DialogueClip:
    audio_path: Path
    title: str
    line: str
```

### `SceneEntry`

中文：表示一个立绘和它的候选语音列表。  
English: Represents one portrait and its candidate voice clips.

```python
@dataclass(frozen=True)
class SceneEntry:
    image_path: Path
    clips: list[DialogueClip]
    speaker: str
    side: str | None
```

### `Scene`

中文：实际运行时选中的图片、音频、字幕和方向。  
English: The selected image, audio, subtitle, and direction for one run.

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

## 5. 配置约定 / Config Contract

中文：推荐使用 `voices` 列表，每一项都包含 `audio` 和 `text`。不要把音频列表和字幕列表拆开随机，否则会错配。  
English: Prefer a `voices` list where every item contains both `audio` and `text`. Do not randomize separate audio and subtitle lists, because that can mismatch clips and captions.

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

中文：路径可以是相对路径；相对路径会以配置文件所在目录为基准解析。  
English: Paths may be relative; relative paths are resolved from the config file directory.

## 6. UI 渲染 / UI Rendering

中文：`draw_dialogue_hud()` 是气泡视觉的核心。它负责：

- 计算气泡位置和尺寸。
- 绘制斜切角半透明面板。
- 绘制 `VOICE` 标签。
- 根据文本高度自动选择字体大小。
- 用裁剪路径限制文字只出现在面板内部。
- 绘制完成提示小三角。

English: `draw_dialogue_hud()` is the visual core of the bubble. It:

- Computes bubble position and size.
- Paints a clipped-corner translucent panel.
- Paints the `VOICE` label.
- Auto-selects font size based on text height.
- Clips text inside the panel path.
- Paints the completion arrow.

中文：文字不要使用过强描边，否则会像“贴”在画面上。当前实现只保留轻微阴影，降低割裂感。  
English: Avoid heavy text outlines; they make captions look pasted on. The current implementation uses only a light shadow to blend text with the panel.

## 7. 动画 / Motion

中文：动画只使用 `pos` 和 `opacity`：

- 立绘滑入/滑出：`QPropertyAnimation(self.label, b"pos")`
- 气泡淡入/淡出：`QGraphicsOpacityEffect` + `QPropertyAnimation`

English: Motion only uses `pos` and `opacity`:

- Portrait slide: `QPropertyAnimation(self.label, b"pos")`
- Bubble fade: `QGraphicsOpacityEffect` + `QPropertyAnimation`

中文：避免动画 `width`、`height`、`top`、`left` 这类布局属性。Qt 里移动控件用 `pos`，透明度用 opacity effect。  
English: Avoid animating layout properties such as `width`, `height`, `top`, and `left`. In Qt, move widgets with `pos` and fade with an opacity effect.

## 8. 预览模式 / Preview Mode

中文：`--preview` 不启动真实浮层，只用 `QImage` 和 `QPainter` 渲染一帧。它适合调 UI、验收长字幕和生成 README 截图。  
English: `--preview` does not open the live overlay. It renders one frame with `QImage` and `QPainter`, which is useful for UI tuning, long-caption validation, and README screenshots.

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble.png \
  --preview-size 1600x900 \
  --typing-cps 0
```

中文：提交 UI 改动前至少生成两张预览：常规 16:9 和一个较小窗口尺寸。  
English: Before committing UI changes, render at least two previews: a normal 16:9 image and one smaller-window image.

## 9. 添加语音 / Adding Voice Clips

中文：

1. 在 PRTS 语音记录页面确认 `语音key` 和中文资源路径。
2. 下载 mp3 到 `assets/voices/<voice-key>/`。
3. 在同目录 `SOURCES.md` 记录来源、文件名和语音标题。
4. 在 `config.py` 或新配置文件中添加 `voices` 条目。
5. 运行 `python -m py_compile main.py config.py start.py process.py`。
6. 渲染预览确认字幕未越界。

English:

1. Confirm the voice key and Chinese resource path from the PRTS voice record page.
2. Download mp3 files into `assets/voices/<voice-key>/`.
3. Document sources, filenames, and voice titles in `SOURCES.md`.
4. Add `voices` entries to `config.py` or a new config file.
5. Run `python -m py_compile main.py config.py start.py process.py`.
6. Render previews to confirm subtitles do not overflow.

## 10. PNG 处理 / PNG Processing

中文：`process.py` 会裁掉 PNG 四周完全透明的边缘，并生成新的配置文件。它不会调色、不会改 alpha。  
English: `process.py` crops fully transparent borders from PNG files and writes a new config. It does not recolor or alter alpha.

```bash
python process.py config.py --out-dir processed_png --out-config processed_config.py
```

中文：如果新增人物图，先用 `process.py` 处理，再手动检查输出图是否仍然完整。  
English: If adding a new portrait, process it with `process.py` first and manually inspect the output.

## 11. 发布前检查 / Pre-Publish Checklist

中文：

- `git status --short --branch` 只应显示预期改动。
- 不提交本地参考截图、`.env`、密钥、证书或凭据。
- 运行高置信度敏感信息扫描。
- 确认 README 的版权说明没有承诺“非商业一定没风险”。
- 渲染预览图。
- 编译检查通过。

English:

- `git status --short --branch` should show only expected changes.
- Do not commit local reference screenshots, `.env` files, keys, certificates, or credentials.
- Run a high-confidence secret scan.
- Ensure the README does not claim that non-commercial use is automatically risk-free.
- Render preview images.
- Pass compile checks.

Useful commands:

```bash
python -m py_compile main.py process.py config.py start.py
git status --short --branch
```

## 12. GitHub 维护 / GitHub Maintenance

中文：仓库公开前请再次确认素材风险和敏感信息风险。公开可用：

```bash
gh repo edit --visibility public --accept-visibility-change-consequences
```

English: Before making the repository public, re-check asset and credential risks. To publish:

```bash
gh repo edit --visibility public --accept-visibility-change-consequences
```

中文：如果要改回私有：

```bash
gh repo edit --visibility private --accept-visibility-change-consequences
```

English: To make it private again:

```bash
gh repo edit --visibility private --accept-visibility-change-consequences
```
