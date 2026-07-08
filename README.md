# Arknights Home Voice Overlay

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?style=flat-square)
![Platform](https://img.shields.io/badge/Target-Linux%20Wayland-555?style=flat-square)
![Status](https://img.shields.io/badge/Project-Fan%20Tool-2E8B57?style=flat-square)

一个模拟《明日方舟》主界面助理语音气泡的桌面浮层脚本。  
A desktop overlay script that simulates the Arknights home assistant voice bubble.

> 中文：这是非商业粉丝项目。仓库内游戏立绘、语音、台词等素材的权利归鹰角网络及其关联方所有；PRTS 仅作为素材来源记录。本项目不对这些素材授予任何再授权，也不构成法律建议。  
> English: This is a non-commercial fan project. Game portraits, voices, dialogue text, and related assets remain the property of Hypergryph and its affiliates; PRTS is only documented as the asset source. This project does not re-license those assets and is not legal advice.

## Contents

- [效果 / Result](#效果--result)
- [功能 / Features](#功能--features)
- [快速开始 / Quick Start](#快速开始--quick-start)
- [配置文件 / Config Files](#配置文件--config-files)
- [命令行参数 / CLI Options](#命令行参数--cli-options)
- [预览截图 / Preview Rendering](#预览截图--preview-rendering)
- [素材来源 / Asset Sources](#素材来源--asset-sources)
- [故障排查 / Troubleshooting](#故障排查--troubleshooting)
- [开发文档 / Developer Docs](#开发文档--developer-docs)

## 效果 / Result

中文：主程序会在屏幕上显示现有人物立绘，并在左下方渲染接近游戏主界面的 `VOICE` 半透明语音气泡。气泡支持打字机效果、长文本自动缩放、淡入淡出、音频结束后自动退出。  
English: The app displays the existing character portrait and renders a `VOICE` bubble near the lower-left corner, close to the Arknights home-screen assistant style. The bubble supports typewriter text, automatic long-text fitting, fade-in/fade-out, and auto exit after audio playback.

示例预览 / Preview:

![Home voice bubble preview](previews/home_voice_bubble.png)

小窗口验证 / Small-window validation:

![Small preview](previews/home_voice_bubble_small.png)

## 功能 / Features

| 中文 | English |
| --- | --- |
| 使用 PySide6 创建透明置顶桌面浮层 | Transparent always-on-top overlay built with PySide6 |
| 保留现有人物图，不替换立绘 | Keeps the existing character images |
| `config.py` 随机播放主页相关语音 | `config.py` randomly selects home-related voice clips |
| `start.py` 只播放问候语音 | `start.py` only plays the greeting clip |
| 每条语音和字幕一一绑定，避免错配 | Each voice clip is bound to its matching subtitle |
| 长台词自动缩字号并限制在气泡内 | Long text auto-fits and is clipped inside the bubble |
| 支持离线渲染预览 PNG | Supports offline PNG preview rendering |

## 快速开始 / Quick Start

### 1. 安装依赖 / Install Dependencies

中文：建议使用虚拟环境。  
English: A virtual environment is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install PySide6 Pillow
```

### 2. 运行随机语音 / Run Random Voice Mode

中文：`config.py` 会从多条凯尔希·思衡托主页语音中随机选择一条，并随机选择现有的两张处理后立绘之一。  
English: `config.py` randomly selects one Kal'tsit the Shimmering Vow home voice clip and one of the two existing processed portraits.

```bash
python main.py config.py
```

### 3. 运行问候语音 / Run Greeting Mode

中文：`start.py` 只播放“问候”语音。  
English: `start.py` only plays the greeting voice.

```bash
python main.py start.py
```

### 4. 渲染预览 / Render a Preview

中文：不打开桌面浮层，只输出一张 PNG。  
English: Render a PNG without opening the desktop overlay.

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble.png \
  --preview-size 1600x900 \
  --typing-cps 0
```

## 配置文件 / Config Files

### `config.py`

中文：随机输出，包含 8 条主页相关语音：任命助理、交谈1、交谈2、交谈3、闲置、戳一下、信赖触摸、问候。  
English: Random mode with eight home-related clips: assistant assignment, talk 1/2/3, idle, tap, trust tap, and greeting.

### `start.py`

中文：只输出问候，适合启动脚本或快捷键绑定。  
English: Greeting-only mode, useful for startup scripts or key bindings.

### 配置结构 / Config Shape

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

字段说明 / Field Reference:

| 字段 / Field | 类型 / Type | 说明 / Description |
| --- | --- | --- |
| `speaker` | `str` | 说话人名称；当前 UI 不显示姓名，但保留元数据。 Speaker metadata; not shown by the current bubble. |
| `side` | `left` / `right` | 立绘进入方向和停靠侧。 Portrait entrance and resting side. |
| `voices` | `list[dict]` | 语音列表，每项绑定一条字幕。 Voice list; each item binds audio to subtitle. |
| `title` | `str` | 语音标题，如“交谈2”。 Voice title, such as `交谈2`. |
| `audio` | `str` | 本地音频路径。 Local audio path. |
| `text` | `str` | 气泡内字幕文本。 Subtitle text in the bubble. |

## 命令行参数 / CLI Options

```bash
python main.py [config] [options]
```

常用参数 / Common options:

| 参数 / Option | 示例 / Example | 用途 / Purpose |
| --- | --- | --- |
| `--volume` | `--volume 0.8` | 调整音量。 Adjust audio volume. |
| `--anim-ms` | `--anim-ms 450` | 立绘滑入/滑出动画时长。 Portrait slide duration. |
| `--typing-cps` | `--typing-cps 0` | 打字速度；`0` 为立即显示全文。 Typewriter speed; `0` shows full text immediately. |
| `--hold-ms` | `--hold-ms 1600` | 音频结束后额外停留时间。 Extra hold time after audio ends. |
| `--side` | `--side left` | 强制立绘从左或右出现。 Force portrait side. |
| `--line` | `--line "Dr.，我在。"` | 临时覆盖字幕。 Temporarily override subtitle text. |
| `--speaker` | `--speaker 凯尔希·思衡托` | 临时覆盖说话人元数据。 Override speaker metadata. |
| `--no-dialog` | `--no-dialog` | 只显示立绘和播放语音，不显示气泡。 Hide the bubble. |
| `--preview` | `--preview out.png` | 渲染预览图。 Render preview image. |

## 预览截图 / Preview Rendering

中文：调 UI 时建议先用 `--preview`，避免反复打开桌面浮层。  
English: Use `--preview` while tuning UI to avoid repeatedly opening the live overlay.

长台词验证 / Long-text validation:

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble_small.png \
  --preview-size 1055x965 \
  --typing-cps 0 \
  --line "你们在最危急的时候带领罗德岛找到了航向，阿米娅无疑已经是成熟的领袖，我也从未怀疑过可露希尔的才能与你的决策。罗德岛不会因为离开谁就无法前行，失去的一切同样造就了现在的罗德岛。"
```

## 素材来源 / Asset Sources

中文：语音来自 PRTS 的 `凯尔希·思衡托/语音记录`，本仓库记录了下载路径和对应语音编号。  
English: Voice files are sourced from PRTS `凯尔希·思衡托/语音记录`; this repository documents the download paths and clip IDs.

- 来源记录 / Source notes: [`assets/voices/char_1052_kalts2/SOURCES.md`](assets/voices/char_1052_kalts2/SOURCES.md)
- 语音目录 / Voice directory: `assets/voices/char_1052_kalts2/`

版权提示 / Copyright notice:

- 中文：仓库公开不代表素材获得了开源许可。非商业用途也不自动等于没有版权风险；如权利方要求移除素材，应及时处理。
- English: Public repository availability does not mean the assets are open-licensed. Non-commercial use does not automatically remove copyright risk; remove assets promptly if requested by rights holders.

## 故障排查 / Troubleshooting

| 问题 / Problem | 处理 / Fix |
| --- | --- |
| 启动后没有窗口 | 检查是否已有实例；程序使用 `/tmp/alpha-floating-widget.lock` 防止重复运行。 Check whether another instance is already running. |
| 没有声音 | 确认音频文件存在，尝试 `--volume 1.0`，并检查系统音频输出。 Ensure audio files exist, try `--volume 1.0`, and check system audio output. |
| Wayland 下不显示 | 默认使用 `QT_QPA_PLATFORM=wayland` 和 layer-shell；不同桌面环境可能需要调整 Qt 平台插件。 The script defaults to Wayland/layer-shell; some desktops may need Qt platform adjustments. |
| 预览失败 | 使用 `QT_QPA_PLATFORM=offscreen`。 Use `QT_QPA_PLATFORM=offscreen`. |
| 字幕过长 | 当前会自动缩字号并裁剪在气泡里；可手动缩短 `text`。 Text auto-fits and clips inside the bubble; you can also shorten `text`. |

## 开发文档 / Developer Docs

中文：面向维护者的架构、配置、渲染和发布流程见：  
English: Maintainer-facing architecture, config, rendering, and release notes:

- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
