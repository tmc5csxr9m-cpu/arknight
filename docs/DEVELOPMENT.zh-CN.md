# 开发者文档

本文档面向维护者，说明项目架构、数据流、渲染流程、动画实现、素材维护、测试方式和发布前检查。

## 目录

- [项目边界](#项目边界)
- [仓库结构](#仓库结构)
- [入口流程](#入口流程)
- [核心数据模型](#核心数据模型)
- [配置加载机制](#配置加载机制)
- [随机选择逻辑](#随机选择逻辑)
- [窗口与图层结构](#窗口与图层结构)
- [气泡渲染细节](#气泡渲染细节)
- [动画与生命周期](#动画与生命周期)
- [音频播放](#音频播放)
- [预览渲染](#预览渲染)
- [图片预处理](#图片预处理)
- [新增语音流程](#新增语音流程)
- [新增立绘流程](#新增立绘流程)
- [质量检查](#质量检查)
- [公开发布检查](#公开发布检查)
- [常见维护任务](#常见维护任务)
- [未来改进方向](#未来改进方向)

<a id="项目边界"></a>
## 项目边界

本项目只是一个本地桌面浮层：

- 不读取游戏进程内存。
- 不修改游戏文件。
- 不自动操作游戏客户端。
- 不接入任何官方接口。
- 不上传用户数据。

当前目标是模拟主界面助理语音气泡，而不是剧情对话 UI。之前的剧情式底部字幕条已经被替换，后续 UI 调整也应以主界面 `VOICE` 气泡为参照。

版权维护原则：

- 项目可以公开展示代码，但游戏素材不应被描述为开源素材。
- 语音、立绘、台词来源必须记录清楚。
- 非商业用途并不自动消除版权风险。
- 如权利方要求移除素材，应优先处理。

<a id="仓库结构"></a>
## 仓库结构

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

关键文件：

| 文件 | 作用 |
| --- | --- |
| `main.py` | 运行时入口，包含配置加载、场景选择、Qt 浮层、绘制和播放逻辑。 |
| `config.py` | 随机语音配置。 |
| `start.py` | 只播放问候语音的配置。 |
| `process.py` | PNG 透明边界裁剪工具。 |
| `processed_png/` | 裁剪后的立绘。 |
| `assets/voices/.../SOURCES.md` | 语音来源记录。 |
| `previews/` | UI 预览图。 |

`main.py.bak` 和 `process.py.bak` 是历史备份文件，当前仍被 git 跟踪。清理它们时应单独提交，避免和功能改动混在一起。

<a id="入口流程"></a>
## 入口流程

运行命令：

```bash
python main.py config.py
```

执行流程：

1. 设置 Qt 环境变量。
2. 导入 PySide6。
3. `parse_args()` 读取参数。
4. `load_config()` 加载配置文件。
5. `choose_scene()` 从有效候选中选出一个 `Scene`。
6. 创建 `QApplication`。
7. 如果传入 `--preview`，调用 `render_preview()` 后退出。
8. 如果是真实浮层，创建单实例锁。
9. 创建 `Overlay`。
10. `Overlay.start()` 显示全屏透明窗口。
11. 立绘滑入。
12. 气泡淡入、文字开始打字、音频开始播放。
13. 音频结束后等待 `hold_ms`。
14. 气泡淡出、立绘滑出。
15. 退出应用。

<a id="核心数据模型"></a>
## 核心数据模型

### `DialogueClip`

表示一条语音和它对应的一条字幕。

```python
@dataclass(frozen=True)
class DialogueClip:
    audio_path: Path
    title: str
    line: str
```

维护规则：

- `audio_path` 必须指向本地可播放文件。
- `line` 应与语音内容一致。
- `title` 用于调试、配置可读性和未来扩展。

### `SceneEntry`

表示一张图和它的一组候选语音。

```python
@dataclass(frozen=True)
class SceneEntry:
    image_path: Path
    clips: list[DialogueClip]
    speaker: str
    side: str | None
```

### `ConfigBundle`

配置加载后的集合。

```python
@dataclass(frozen=True)
class ConfigBundle:
    entries: list[SceneEntry]
    background_path: Path | None
```

### `Scene`

一次运行真正使用的场景。

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

<a id="配置加载机制"></a>
## 配置加载机制

`load_config(config_path)` 使用 `importlib.util.spec_from_file_location()` 动态加载 Python 配置文件。

要求：

- 配置文件必须定义 `myconfig`。
- `myconfig` 必须是非空 `dict`。
- key 是图片路径。
- value 可以是旧格式，也可以是推荐的新格式。

推荐新格式：

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

兼容旧格式：

```python
myconfig = {
    "processed_png/1_3_cropped.png": ["voice1.mp3", "voice2.mp3"],
}
```

旧格式没有字幕绑定，只适合简单播放。新维护应优先使用 `voices`。

路径解析由 `resolve_path()` 处理：

- `~/...` 会展开。
- 相对路径以配置文件所在目录为基准。
- 最终返回绝对路径。

<a id="随机选择逻辑"></a>
## 随机选择逻辑

`choose_scene()` 会先过滤无效项：

- 图片不存在：跳过该 `SceneEntry`。
- 音频不存在：跳过该 `DialogueClip`。
- 某张图没有有效语音：跳过该图。

之后随机选择：

1. 从有效 `SceneEntry` 中随机选一张图。
2. 从该图的有效 `clips` 中随机选一条语音。
3. 如果命令行传入 `--line`，使用命令行字幕。
4. 如果未传 `--line`，使用 clip 自带字幕。
5. 如果 clip 没有字幕，使用 `DEFAULT_LINES` 兜底。
6. 根据命令行 `--side`、配置 `side` 或随机值决定立绘方向。

注意：字幕和音频必须在同一个 `DialogueClip` 内绑定，避免“语音 A 播放，字幕 B 显示”的错配。

<a id="窗口与图层结构"></a>
## 窗口与图层结构

`Overlay` 是顶层窗口：

- `FramelessWindowHint`
- `Tool`
- `WindowStaysOnTopHint`
- `WindowTransparentForInput`
- `WA_TranslucentBackground`
- `WA_NoSystemBackground`
- `WA_TransparentForMouseEvents`

图层从底到顶：

1. 可选背景图 `background_label`
2. 立绘 `label`
3. 对话层 `dialog_layer`

Wayland / Niri 下顶层窗口不移动，只移动内部 `QLabel`。这是为了让动画更稳定，避免真实窗口移动造成闪烁或层级异常。

<a id="气泡渲染细节"></a>
## 气泡渲染细节

核心函数：`draw_dialogue_hud()`

主要步骤：

1. 根据屏幕宽高计算气泡尺寸。
2. 创建斜切角 `QPainterPath`。
3. 绘制面板阴影。
4. 绘制半透明渐变面板。
5. 绘制顶部高光和底部弱边线。
6. 绘制 `VOICE` 标签。
7. 计算文本区域。
8. 用 `fit_font_to_rect()` 自动选择字号。
9. 设置 clip path，限制文字只出现在面板内。
10. 绘制轻阴影文字。
11. 如果打字完成，绘制右下角小三角。

### 文本适配

`fit_font_to_rect()` 使用 `QTextDocument` 进行测量：

```python
doc = QTextDocument()
doc.setDocumentMargin(0)
doc.setDefaultFont(font)
doc.setPlainText(text)
doc.setTextWidth(rect.width())
doc.size().height()
```

它从最大字号向最小字号递减，找到能放进文本区域的最大字号。

### 视觉原则

主界面气泡不是剧情字幕框，因此不要：

- 大面积底部黑条
- 过亮白字
- 厚描边
- 明显卡片式圆角
- 过强投影

当前实现偏向：

- 深色半透明面板
- 轻微玻璃层次
- 弱边线
- 低描边文字
- 明确的 `VOICE` 标签

<a id="动画与生命周期"></a>
## 动画与生命周期

### 立绘动画

立绘使用 `QPropertyAnimation(self.label, b"pos")`：

- 进入：`OutCubic`
- 退出：`InCubic`
- 默认时长：`DEFAULT_ANIM_MS = 500`

方向：

- `left`：从屏幕左侧外滑入。
- `right`：从屏幕右侧外滑入。

### 气泡动画

气泡使用 `QGraphicsOpacityEffect`：

- 淡入：180ms，`OutCubic`
- 淡出：220ms，`OutCubic`

原因：

- 消失不再突兀。
- 不移动气泡位置，避免和主界面 UI 产生额外割裂感。
- 只动画 opacity，开销低。

### 退出顺序

1. 音频播放结束。
2. 等待 `hold_ms`。
3. 如果文字还没打完，等待打字完成。
4. `dialog_layer.fade_out()`。
5. 立绘滑出。
6. `QApplication.quit()`。

<a id="音频播放"></a>
## 音频播放

使用：

- `QMediaPlayer`
- `QAudioOutput`
- `QUrl.fromLocalFile()`

音频结束判断：

```python
if status == QMediaPlayer.MediaStatus.EndOfMedia:
    self.request_exit()
```

错误处理：

```python
self.player.errorOccurred.connect(lambda *_: self.request_exit())
```

如果播放失败，程序会正常走退出流程，而不是挂住。

<a id="预览渲染"></a>
## 预览渲染

`render_preview()` 不创建真实浮层，直接绘制到 `QImage`：

1. 创建指定尺寸的 `QImage`。
2. 填充深色背景。
3. 可选绘制背景图。
4. 绘制缩放后的立绘。
5. 调用 `draw_dialogue_hud()` 绘制气泡。
6. 保存 PNG。

常规预览：

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble.png \
  --preview-size 1600x900 \
  --typing-cps 0
```

小尺寸验证：

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble_small.png \
  --preview-size 1055x965 \
  --typing-cps 0
```

提交 UI 改动前必须检查：

- 文字没有越界。
- 长台词不会被硬裁到不可读。
- 气泡没有遮挡主体脸部。
- 小窗口下布局仍可接受。

<a id="图片预处理"></a>
## 图片预处理

`process.py` 用 Pillow 裁掉 PNG 四周完全透明边界。

入口：

```bash
python process.py config.py --out-dir processed_png --out-config processed_config.py
```

核心逻辑：

```python
img = Image.open(src).convert("RGBA")
bbox = img.getchannel("A").getbbox()
cropped = img.crop(bbox)
cropped.save(dst, format="PNG")
```

注意：

- 不调色。
- 不预乘 alpha。
- 不改变透明度。
- 只裁剪 alpha 全 0 的外边界。

<a id="新增语音流程"></a>
## 新增语音流程

1. 在 PRTS 语音记录页面确认干员语音 key。
2. 确认中文资源路径，例如 `voice_cn/char_1052_kalts2`。
3. 下载音频到 `assets/voices/<voice-key>/`。
4. 更新 `SOURCES.md`，记录页面、资源路径、文件名和语音标题。
5. 在 `config.py` 添加 `voices` 项。
6. 确认 `audio` 和 `text` 一一匹配。
7. 运行编译检查。
8. 渲染预览。

下载示例：

```bash
curl -L --fail -o assets/voices/char_1052_kalts2/cn_003.mp3 \
  https://torappu.prts.wiki/assets/audio/voice_cn/char_1052_kalts2/cn_003.mp3
```

<a id="新增立绘流程"></a>
## 新增立绘流程

1. 放入原始 PNG。
2. 临时写一个配置让 `process.py` 识别图片。
3. 运行 `process.py` 裁剪透明边界。
4. 用 `view_image` 或系统图片查看器检查裁剪结果。
5. 在正式配置中引用 `processed_png/...`。
6. 渲染预览检查立绘位置。

立绘尺寸由 `calc_size()` 控制：

```python
max_w = int(screen_w * 0.56)
max_h = int(screen_h * 0.96)
scale = min(max_w / img_w, max_h / img_h)
```

如果人物过大或过小，优先调整这里，而不是修改源图。

<a id="质量检查"></a>
## 质量检查

基础检查：

```bash
python -m py_compile main.py process.py config.py start.py
```

配置检查：

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

预览检查：

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble.png \
  --preview-size 1600x900 \
  --typing-cps 0
```

敏感信息检查：

```bash
git grep -I -n -E '(gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |OPENSSH |DSA |EC |PGP )?PRIVATE KEY-----|Bearer [A-Za-z0-9._-]{30,})' -- . ':!*.png' ':!*.mp3'
```

<a id="公开发布检查"></a>
## 公开发布检查

公开仓库前检查：

- `git status --short --branch` 干净。
- 没有 `.env`。
- 没有 token、key、pem、p12、secret。
- 未跟踪参考截图已加入 `.gitignore`。
- README 版权说明不过度承诺。
- 语音和立绘来源记录完整。
- 预览图能显示。
- 编译检查通过。

改公开：

```bash
gh repo edit --visibility public --accept-visibility-change-consequences
```

改回私有：

```bash
gh repo edit --visibility private --accept-visibility-change-consequences
```

<a id="常见维护任务"></a>
## 常见维护任务

### 更新 README 预览图

```bash
QT_QPA_PLATFORM=offscreen python main.py config.py \
  --preview previews/home_voice_bubble.png \
  --preview-size 1600x900 \
  --typing-cps 0
```

### 验证 `config.py` 是随机模式

```bash
python - <<'PY'
from pathlib import Path
from main import load_config
bundle = load_config(Path("config.py"))
print([len(entry.clips) for entry in bundle.entries])
PY
```

应输出每张图 8 条候选。

### 验证 `start.py` 只问候

```bash
python - <<'PY'
from pathlib import Path
from main import load_config
bundle = load_config(Path("start.py"))
print([[clip.title for clip in entry.clips] for entry in bundle.entries])
PY
```

应只看到 `问候`。

### 排查音频播放失败

检查文件：

```bash
file assets/voices/char_1052_kalts2/*.mp3
```

如果 Qt 无法播放 mp3，先确认系统 GStreamer / FFmpeg 后端是否正常。

<a id="未来改进方向"></a>
## 未来改进方向

可能的改进：

- 拆分 `main.py` 为 `config_loader.py`、`rendering.py`、`overlay.py`。
- 添加单元测试覆盖配置解析。
- 给不同屏幕比例建立更多预览样例。
- 增加自动字体基线调整，进一步贴近游戏截图。
- 支持自定义主题参数，而不是直接改绘制代码。
- 清理历史 `.bak` 文件。
- 增加 `requirements.txt` 或 `pyproject.toml`。

返回：

- [中文说明](../README.zh-CN.md)
- [开发文档入口](DEVELOPMENT.md)
