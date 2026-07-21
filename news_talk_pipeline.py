#!/usr/bin/env python3
"""
新闻大家谈 — 全自动管线 v2
1. NotebookLM 生成中文播客（限制5-10分钟）
2. 下载 MP3
3. Sensenova 配图（优先）→ Pollinations 备选
4. 转写字幕（faster-whisper）
5. FFmpeg 合成 16:9 视频 + 烧录字幕
"""
import subprocess, json, time, os, re, sys, io, math
from pathlib import Path

BASE = Path("/home/kan/shared/news-talk")
AUDIO_DIR = BASE / "audio"
IMAGES_DIR = BASE / "images"
OUTPUT_DIR = BASE / "output"
NOTEBOOK_ID = "7e23139b-cff2-4aba-8b83-7f6f5eb5e9be"
OUTPUT_VIDEO = OUTPUT_DIR / "新闻大家谈_首期.mp4"
OUTPUT_SUB = OUTPUT_DIR / "新闻大家谈_首期_字幕版.mp4"
TITLE = "新闻大家谈"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def log(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def run(cmd, timeout=600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        log(f"CMD FAILED ({r.returncode}): {' '.join(str(c) for c in cmd)}")
        log(f"STDERR: {r.stderr[-500:]}")
        return None
    return r.stdout

def notebooklm(cmd, timeout=600):
    full_cmd = ["notebooklm"] + cmd
    log(f"notebooklm {' '.join(cmd)}")
    return run(full_cmd, timeout=timeout)

# ===== Step 1: 生成播客（限10分钟内） =====
log("=== Step 1: 生成中文播客 ===")
# 用更明确的时长控制 prompt
out = notebooklm([
    "generate", "audio",
    "今日科技新闻,双人中文对话,自然生动,时长5到10分钟,不要太长",  # ← 时长控制
    "--format", "deep-dive",
    "--language", "zh_Hans",
    "--wait", "--timeout", "600"
], timeout=620)
if not out:
    log("播客生成失败，退出")
    sys.exit(1)
log("播客生成成功")

# ===== Step 2: 下载 MP3 =====
log("=== Step 2: 下载 MP3 ===")
mp3_path = AUDIO_DIR / "podcast.mp3"
out = notebooklm(["download", "audio", "--latest", "--force", str(mp3_path)], timeout=300)
if not out or not mp3_path.exists():
    out = notebooklm(["download", "audio", "--force", str(mp3_path)], timeout=300)
if mp3_path.exists():
    size_mb = mp3_path.stat().st_size / 1024 / 1024
    log(f"MP3 下载成功: {size_mb:.1f}MB")
else:
    log("MP3 下载失败，退出")
    sys.exit(1)

# 获取时长
dur = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_path)],
    capture_output=True, text=True, timeout=10)
duration = float(dur.stdout.strip()) if dur.returncode == 0 else 300
log(f"播客时长: {duration/60:.1f} 分钟")
if duration > 660:  # >11 min
    log(f"⚠ 超过10分钟({duration/60:.1f}min)，下次用更短的 prompt")

# ===== Step 3: 获取话题列表 =====
log("=== Step 3: 获取话题列表 ===")
out = notebooklm([
    "ask", "逐条列出本期播客讨论的新闻话题,按时间顺序,每条用一句话概括。格式: 编号. 话题名: 一句话概括"
], timeout=60)
if out:
    answer = out
    log(f"话题列表:\n{answer}")
else:
    answer = "1. SK海力士纳斯达克上市; 2. OpenAI驳斥商业机密诉讼; 3. 马斯克要求全员用Grok; 4. FansAI收购新映科技; 5. 长鑫科技IPO"
    log("话题问答失败，使用默认列表")

# 解析话题标题
topic_titles = []
for line in answer.splitlines():
    m = re.match(r'\d+\s*[.、]\s*\S[^:;，]+', line)
    if m:
        # Extract first segment as title
        title = m.group(0).split(':')[0].split('：')[0].strip()
        # Remove leading number
        title = re.sub(r'^\d+\s*[.、]\s*', '', title)
        if title:
            topic_titles.append(title)
    # Also try semicolon-split format
if not topic_titles:
    # Fallback: split by semicolons
    parts = answer.replace('；', ';').split(';')
    for p in parts:
        m = re.search(r'\d+\s*[.、]\s*(.+)', p.strip())
        if m:
            topic_titles.append(m.group(1).split(':')[0].split('：')[0].strip())

if not topic_titles:
    topic_titles = [
        "SK海力士纳斯达克上市",
        "OpenAI驳斥商业机密诉讼",
        "马斯克要求全员用Grok",
        "FansAI收购新映科技",
        "长鑫科技IPO",
    ]
log(f"解析出 {len(topic_titles)} 个话题: {topic_titles}")

# ===== Step 4: Sensenova 配图 =====
log("=== Step 4: Sensenova 配图 ===")
log("详见 gen_news_talk_images.py → 集成在此")
# 导入图片生成模块
sys.path.insert(0, str(BASE))
from gen_news_talk_images import generate_all, TOPIC_PROMPTS

# 先查已有图片，只生成缺失的
results = generate_all(topic_titles)
if not results:
    log("配图全部失败，退出")
    sys.exit(1)

# 重新整理：intro → topic1..N → outro
existing_intro = IMAGES_DIR / "intro.jpg"
existing_outro = IMAGES_DIR / "outro.jpg"
topic_images = []
for i in range(1, len(topic_titles) + 1):
    p = IMAGES_DIR / f"{i:02d}.jpg"
    if p.exists() and p.stat().st_size > 10000:
        topic_images.append(str(p))

log(f"配图就绪: intro + {len(topic_images)} 话题 + outro")

# ===== Step 5: FFmpeg 合成（含字幕） =====
log("=== Step 5: 合成视频 ===")

# Build slideshow
concat_file = BASE / "concat_list.txt"
# 每张图停留时长（秒）
intro_dur = 8
topic_dur = 20  # 10分钟 / 5话题 ≈ 120s → 够
outro_dur = 8

with open(concat_file, "w") as f:
    if existing_intro.exists():
        f.write(f"file '{existing_intro}'\nduration {intro_dur}\n")
    for img in topic_images:
        f.write(f"file '{img}'\nduration {topic_dur}\n")
    if existing_outro.exists():
        f.write(f"file '{existing_outro}'\nduration {outro_dur}\n")

# 生成无声音频滑条
vid_temp = OUTPUT_DIR / "slides.mp4"
log("生成图片滑条视频...")
run([
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", str(concat_file),
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-pix_fmt", "yuv420p", "-r", "24",
    str(vid_temp)
], timeout=120)

if not vid_temp.exists():
    log("滑条视频生成失败")
    sys.exit(1)

# 合并音频（循环滑条以匹配播客时长）
video_dur = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", str(vid_temp)],
    capture_output=True, text=True, timeout=10)
vid_seconds = float(video_dur.stdout.strip()) if video_dur.returncode == 0 else 0
loop_count = max(1, math.ceil(duration / vid_seconds)) - 1

log(f"滑条: {vid_seconds:.0f}s × {loop_count+1} 循环需填 {duration:.0f}s 播客")

run([
    "ffmpeg", "-y",
    "-stream_loop", str(loop_count), "-i", str(vid_temp),
    "-i", str(mp3_path),
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-c:a", "aac", "-b:a", "128k",
    "-shortest",
    "-pix_fmt", "yuv420p",
    str(OUTPUT_VIDEO)
], timeout=300)

if OUTPUT_VIDEO.exists():
    size_mb = OUTPUT_VIDEO.stat().st_size / 1024 / 1024
    log(f"\n{'='*40}")
    log(f"✅ 视频: {OUTPUT_VIDEO}")
    log(f"   大小: {size_mb:.1f}MB | 时长: {duration/60:.1f}min")
else:
    log("❌ 视频生成失败")
    sys.exit(1)

# ===== Step 6: 烧录字幕 =====
log("=== Step 6: 烧录字幕 ===")
srt_path = OUTPUT_DIR / "新闻大家谈_首期.srt"
try:
    log("加载 faster-whisper...")
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    log("转写中...")
    segments, info = model.transcribe(str(mp3_path), language="zh", beam_size=5)
    segs = list(segments)
    log(f"转写完成: {len(segs)} 段, {info.language}")

    # 写 SRT
    with open(srt_path, "w") as f:
        for i, seg in enumerate(segs, 1):
            def fmt(s): h=int(s//3600); m=int((s%3600)//60); ss=int(s%60); ms=int((s-int(s))*1000); return f"{h:02d}:{m:02d}:{ss:02d},{ms:03d}"
            f.write(f"{i}\n{fmt(seg.start)} --> {fmt(seg.end)}\n{seg.text.strip()}\n\n")
    log(f"SRT: {srt_path}")

    # FFmpeg 烧录
    vf = f"subtitles={srt_path}:force_style='FontName=Noto Sans CJK SC,FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'"
    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(OUTPUT_VIDEO),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        str(OUTPUT_SUB)
    ], capture_output=True, text=True, timeout=600)
    if r.returncode == 0 and OUTPUT_SUB.exists():
        sub_mb = OUTPUT_SUB.stat().st_size / 1024 / 1024
        log(f"✅ 字幕版: {OUTPUT_SUB} ({sub_mb:.0f}MB)")
    else:
        log(f"⚠ 字幕烧录失败: {r.stderr[-200:]}")
except Exception as e:
    log(f"⚠ 字幕步骤失败: {e}")
    log("无字幕版已可用")

# Cleanup
vid_temp.unlink(missing_ok=True)
concat_file.unlink(missing_ok=True)

log(f"\n{'='*40}")
log(f"完成!")
log(f"  MP3:      {mp3_path} ({mp3_path.stat().st_size/1024/1024:.0f}MB, {duration/60:.1f}min)")
log(f"  无字幕版: {OUTPUT_VIDEO} ({OUTPUT_VIDEO.stat().st_size/1024/1024:.0f}MB)")
if OUTPUT_SUB.exists():
    log(f"  字幕版:   {OUTPUT_SUB} ({OUTPUT_SUB.stat().st_size/1024/1024:.0f}MB)")
log(f"{'='*40}")