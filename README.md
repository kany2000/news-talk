# 新闻大家谈 (News Talk)

自动生成双人对话新闻播客视频的全自动管线。从选题到出片，一条命令完成。

## 管线流程

```
NotebookLM 生成播客 → 下载 MP3 → AI 配图 → 语音转写 → FFmpeg 合成 16:9 视频 + 字幕
```

| 步骤 | 工具 | 说明 |
|------|------|------|
| 1. 播客生成 | NotebookLM | 生成 5-10 分钟双人中文对话 |
| 2. 配图 | Sensenova / Pollinations | 自动匹配话题关键词生成配图 |
| 3. 字幕 | faster-whisper | 中文语音转写，输出 SRT/ASS |
| 4. 合成 | FFmpeg | 图片滑条 + 音频 + 烧录字幕 → MP4 |

## 目录结构

```
news-talk/
├── news_talk_pipeline.py    # 全自动管线（主入口）
├── gen_news_talk_images.py  # 配图模块
├── add_subtitles.py         # 字幕生成 + 烧录
├── build_video.py           # 视频合成
├── tts_mimo.py              # MiMo TTS（备用语音合成）
├── build_video.sh           # 一键构建脚本
├── scripts/                 # 分步脚本
│   ├── step1_gen_audio.py
│   ├── step2_make_video.py
│   ├── step3_compose.py
│   └── gen_outro_image.py
├── skills/                  # 技能文档
├── audio/                   # 音频输出
├── images/                  # 配图输出
├── output/                  # 视频输出
├── .env                     # 本地密钥（不提交）
└── .env.example             # 密钥模板
```

## 前置依赖

- Python 3.10+
- FFmpeg
- faster-whisper
- Pillow
- NotebookLM CLI

## 快速开始

```bash
# 1. 配置 API 密钥
cp .env.example .env
# 编辑 .env，填入你的密钥

# 2. 全自动运行
./news_talk_pipeline.py

# 或分步运行
./scripts/step1_gen_audio.py
./scripts/step2_make_video.py
./scripts/step3_compose.py
```

## 环境变量

| 变量 | 说明 | 来源 |
|------|------|------|
| `SENSENOVA_KEY` | Sensenova 图片生成 API 密钥 | [sensenova.cn](https://sensenova.cn) |
| `MIMO_TTS_API_KEY` | MiMo 语音合成 API 密钥 | [mimovoice.com](https://mimovoice.com) |

## 输出

- `output/*.mp4` — 无字幕版视频
- `output/*_字幕版.mp4` — 烧录字幕版视频
- `output/*.srt` — 字幕文件
- `audio/` — 播客 MP3

## 许可

MIT