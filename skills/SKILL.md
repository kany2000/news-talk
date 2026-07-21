---
title: 新闻大家谈播客生成
name: news-talk-pipeline
description: 新闻大家谈双人对话播客 — 两种方式：A) 对话稿 → MiMo TTS 男女声 → 逐句配图对齐 → 精准SRT字幕 → 视频合成；B) NotebookLM 生成播客 → faster-whisper 转写 → 时间线切图 → 合成
---

## 触发条件

当需要生成新闻大家谈播客时触发。

## 流程总览

### 方式 A：对话稿 + MiMo TTS（精准逐句对齐）

```
对话稿(SCENE) ──→ MiMo TTS分段合成(男女交替)
                     ↓
               ffprobe 取每段精准时长
                     ↓
            ┌────────┴────────┐
            ↓                  ↓
       合并 WAV→MP3      生成精准SRT字幕
            ↓                  ↓
       话题图轮播         STYLE: Wrap=0 自动换行
            ↓                  ↓
       ┌────┴─────────────────┴─┐
       ↓   ffmpeg 一步合成        ↓
   输出：对话版.mp4 + 字幕版.mp4
```

### 方式 B：NotebookLM + faster-whisper（快速生成，时间线均分）

```
选题 → 写话题描述文件.txt → notebooklm source add
                              ↓
                   notebooklm generate audio
                   "双人中文对话,时长5到10分钟"
                              ↓
                   notebooklm download audio
                              ↓
                   faster-whisper 转写 → SRT字幕
                              ↓
                   时间线均分：intro 20s → 7话题各~170s → outro 30s
                              ↓
                   ffmpeg 合成视频 + 烧录字幕(Wrap=0)
```

## 步骤

### 1. 写对话稿

对话稿格式：`(speaker, text, topic_idx)` 数组。

- `speaker`: `"female"` 或 `"male"`
- `text`: 一句对话
- `topic_idx`: 0=intro, 1~7=话题, 8=outro

```python
SCENE = [
    ("female", "各位听众，欢迎收听新闻大家谈第二期，我是晓晓。", 0),
    ("male",   "大家好，我是云扬。这期内容挺丰富的。", 0),
    ("female", "第一，长鑫科技IPO启动了，发行价8.66元，7月16号申购。", 1),
    ("male",   "没错，长鑫作为国内存储芯片的龙头，这次上市意义重大。", 1),
    # ... 每条话题2~4句对话
    ("female", "下期再见！", 8),
]
```

保存为 `scripts/对话稿_第N期.py`。

### 2. 生成音频

```bash
cd /home/kan/shared/news-talk/scripts
python3 step1_gen_audio.py
```

内部流程：
1. 逐段调用 MiMo TTS（女声=xiaoxiao，男声=yunyang）
2. ffprobe 取每段 WAV 实际 duration
3. 合并为 single WAV/MP3
4. 保存 `segments_meta.json`（含每段 start/end/topic_idx 精准时间）

### 3. 配图

```bash
cd /home/kan/shared/news-talk
python3 -c "
from gen_news_talk_images import generate_all
generate_all(['长鑫科技IPO','信维通信11亿收购','阿里云下调GLM-5.2','海南禁燃油车','功夫女足票房','玩具总动员5','网络烂梗'], force=True)
"
```

### 4. 合成视频（精准逐段对齐）

```bash
cd /home/kan/shared/news-talk/scripts
python3 step3_compose.py
```

核心：用 `segments_meta.json` 的 topic_idx 合并相邻同话题段 → 每张图精确显示到毫秒，语音说到哪图跟到哪。

### 5. 输出

- `/home/kan/shared/news-talk/output/新闻大家谈_第N期_对话版.mp4` — 无字幕
- `/home/kan/shared/news-talk/output/新闻大家谈_第N期_对话版_字幕.mp4` — 带字幕

## 方式 B：NotebookLM 快速管线

适合快速出片或有现成 notebook 的场景。不需要写对话稿，不需要 MiMo TTS。

### 1. 写话题描述文件

话题内容用纯中文，每条新闻写 2-4 句概述。保存为 `sources/news_talk_epN_sources.txt`。

### 2. 添加 Source 并登录

```bash
notebooklm login                     # 首次认证
notebooklm use <notebook_id>         # 选择 notebook
notebooklm source add sources/news_talk_epN_sources.txt
notebooklm source list               # 确认状态 ready
```

### 3. 生成播客音频

```bash
notebooklm generate audio "今日科技新闻,双人中文对话,自然生动,时长5到10分钟。请重点围绕以下话题展开: ..." --wait --timeout 600
notebooklm download audio --latest --force audio/notebooklm_epN.mp3
```

### 4. 转写字幕

```bash
python3 -c "
from faster_whisper import WhisperModel
model = WhisperModel('base', device='cpu', compute_type='int8')
segments, info = model.transcribe('audio/notebooklm_epN.mp3', language='zh', beam_size=5)
segs = list(segments)
# 写 SRT
srt_lines = []
for i, seg in enumerate(segs, 1):
    def fmt(t): h=int(t//3600); m=int((t%3600)//60); sec=int(t%60); ms=int((t-int(t))*1000)
        return f'{h:02d}:{m:02d}:{sec:02d},{ms:03d}'
    srt_lines.extend([str(i), f\"{fmt(seg.start)} --> {fmt(seg.end)}\", seg.text.strip(), ''])
with open('audio/notebooklm_epN.srt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(srt_lines))
"
```

### 5. 合成视频

按时间线均分：
- intro (jpg): 20s
- 话题 1-7 (01.jpg-07.jpg): 各 ~170s (总长扣除 intro+outro 后均分)
- outro (outro_text.jpg): 30s

FFmpeg concat demuxer 合成 + 烧录字幕（Wrap=0 自动换行）。

## 核心坑

### ⚠️ TTS 乱码
- **edge-tts 中英混排必乱码** — 数字/英文缩写（IPO, MLCC, GLM-5.2, 30.3亿）会被读成英文音素乱码
- **必须用 MiMo TTS**（`api.xiaomimimo.com/v1/chat/completions`，header `api-key`）
- 脚本路径：`/home/kan/signal_pop/src/tts_mimo.py`（生产级），**不是** `/home/kan/shared/news-talk/tts_mimo.py`（过时）
- **MLCC 防误读** — MiMo TTS 会把纯 `MLCC` 读成数字乱码（"1150"）。修复：对话文本里**彻底去掉 `MLCC` 字样**，直接写中文 `多层陶瓷电容`。同理所有英文缩写（IPO、DRAM、IP 等）也应全部替换为纯中文，不能保留"缩写+中文解释"后缀写法——TTS 读到英文字母就开始拼读，中文解释来不及补救。
- **后半句英文/数字暴雷** — 句末如有 `30.3亿`、`Fast mode` 等，可能被当成英文发音。修复：中文数字全写成汉字形式（"三十点三亿"、"五点二"），句末不保留裸露英文片段。

### ⚠️ 音画同步
- **不能固定秒数切图**（如图14s/话题 → 语音长度不同必然错位）
- 必须用 ffprobe 取每段实际 duration 做 concat duration
- topic_idx 合并相邻段归一图

### ⚠️ 字幕
- 不用 faster-whisper（逐字时间戳有偏移）
- 直接用 WAV 段的 ffprobe 时长做每句 SRT 时间戳，精度到毫秒
- **字幕出屏/超长** — 长句字幕会被截断在屏幕外。修复：FFmpeg subtitle filter 加 `Wrap=0,ScreenAlignment=2,MarginV=40`。`Wrap=0` 启用自动换行，`MarginV=40` 底部留白，超长句自动折两行。已在 `step2_make_video.py`、`step3_compose.py`、`add_subtitles.py`、`news_talk_pipeline.py` 中统一修复。

### ⚠️ 结尾图
- notebooklm login 认证约24-48小时过期
- 用双人对话稿方案（本 skill）替代，无需 NotebookLM
- `gen_outro_image.py` 以 blurred intro.jpg 为背景 + 暗色叠加 + 话题列表纯中文，font fallback 含 Windows/Linux 路径

### ⚠️ NotebookLM 注意事项
- `notebooklm login` 认证 24-48h 过期，过期后需重新 `notebooklm login` 或 `notebooklm login --browser-cookies chrome`
- 播客较长时（>15min），转写用 faster-whisper `base` 模型够用，时间戳不需精准对齐话题
- 时间线均分法（intro 20s → 7话题各~170s → outro 30s）图片切换与语音话题不对齐，但不影响观看体验
- 如需精准话题对齐，方式 A（对话稿+MiMo TTS）仍是首选

## 文件

| 文件 | 用途 |
|------|------|
| `scripts/对话稿_第N期.py` | 对话稿（话题列表 → 双人对白） |
| `scripts/step1_gen_audio.py` | MiMo TTS 分段合成 + 合并 + 元数据 |
| `scripts/step3_compose.py` | ffmpeg 精准合成视频 + 烧录字幕（Wrap=0） |
| `scripts/gen_outro_image.py` | PIL 绘制话题列表结尾图（outro_text.jpg） |
| `scripts/../gen_news_talk_images.py` | Sensenova 配图引擎 |
| `/home/kan/signal_pop/src/tts_mimo.py` | MiMo TTS API 封装（生产级） |
| `sources/news_talk_epN_sources.txt` | NotebookLM 话题描述文件（方式 B） |
| `audio/notebooklm_epN.mp3` | NotebookLM 生成播客音频（方式 B） |
| `audio/notebooklm_epN.srt` | faster-whisper 转写字幕（方式 B） |

## 路径

- 项目：`/home/kan/shared/news-talk/`
- 音频：`audio/` | 配图：`images/` | 输出：`output/`
- 脚本：`scripts/`
- TTS 引擎：`/home/kan/signal_pop/src/tts_mimo.py`