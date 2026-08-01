#!/usr/bin/env python3
"""第二期转写：耶鲁博弈论·看透对手 — openai-whisper small → SRT"""
import os, sys, time
os.environ["PYTHONIOENCODING"] = "utf-8"
from pathlib import Path
import whisper

BASE = Path(r"E:\projects\news-talk")
EP = BASE / "yale大学公开课系列讲谈"
AUDIO_SRC = EP / "耶鲁博弈论看透对手(L2.3.4).m4a"
EP2_DIR = EP / "第二期"
AUDIO_DIR = EP2_DIR / "audio"
AUDIO_MP3 = AUDIO_DIR / "audio.mp3"
SRT_PATH = AUDIO_DIR / "subtitles.srt"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{time.strftime('%H:%M:%S')}] {msg.encode('utf-8','replace').decode('gbk','replace')}", flush=True)

# Step 0: 转 mp3（whisper 直接吃 m4a 也行，但统一 mp3 方便后续合成）
if not AUDIO_MP3.exists():
    import subprocess
    r = subprocess.run(["ffmpeg", "-y", "-i", str(AUDIO_SRC), "-codec:a", "libmp3lame", "-b:a", "128k", str(AUDIO_MP3)],
                       capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        log(f"FFMPEG FAIL: {r.stderr[-200:]}")
        sys.exit(1)
    log(f"转码完成: {AUDIO_MP3.name}")

# Step 1: 转写
log("加载 faster-whisper base...")
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
log("转写中（23分钟音频，CPU 预计 5-15 分钟）...")
t0 = time.time()
segments, info = model.transcribe(str(AUDIO_MP3), language="zh", beam_size=5)
segs = list(segments)
log(f"转写完成: {len(segs)} 段, {info.language}，耗时 {time.time()-t0:.0f}s")

def fmt(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

with open(SRT_PATH, "w", encoding="utf-8") as f:
    for i, seg in enumerate(segs, 1):
        f.write(f"{i}\n{fmt(seg.start)} --> {fmt(seg.end)}\n{seg.text.strip()}\n\n")

# 同时存纯文本稿，便于人工阅读/整理话题
TXT = EP2_DIR / "transcript.txt"
with open(TXT, "w", encoding="utf-8") as f:
    for seg in segs:
        f.write(seg.text.strip() + "\n")

log(f"SRT: {SRT_PATH}")
log(f"TXT: {TXT}")
print("DONE_TRANSCRIBE")
