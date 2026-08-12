#!/usr/bin/env python3
"""第三期转写：耶鲁博弈论·集体恐慌 L5.6.7 — faster-whisper → 英文 SRT + 文本稿"""
import os, sys, time
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["KMP_BLOCKTIME"] = "1"
from pathlib import Path

BASE = Path(r"E:\projects\news-talk")
EP = BASE / "yale大学公开课系列讲谈"
AUDIO_SRC = EP / "Why_Rationality_Triggers_Collective_Panic(L5.6.7).m4a"
EP3_DIR = EP / "第三期"
AUDIO_DIR = EP3_DIR / "audio"
AUDIO_MP3 = AUDIO_DIR / "audio.mp3"
SRT_PATH = AUDIO_DIR / "subtitles_en_raw.srt"
TXT_PATH = EP3_DIR / "transcript_en.txt"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{time.strftime('%H:%M:%S')}] {msg.encode('utf-8','replace').decode('gbk','replace')}", flush=True)

# Step 0: 转 mp3
if not AUDIO_MP3.exists():
    import subprocess
    r = subprocess.run(["ffmpeg", "-y", "-i", str(AUDIO_SRC), "-codec:a", "libmp3lame", "-b:a", "128k", str(AUDIO_MP3)],
                       capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        log(f"FFMPEG FAIL: {r.stderr[-200:]}")
        sys.exit(1)
    log(f"转码完成: {AUDIO_MP3.name}")

# Step 1: 转写（英文）
log("加载 faster-whisper base...")
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=2)
log("转写中（18分钟英文音频，CPU 预计 5-15 分钟）...")
t0 = time.time()
segments, info = model.transcribe(str(AUDIO_MP3), language="en", beam_size=5)
segs = list(segments)
log(f"转写完成: {len(segs)} 段, lang={info.language} p={info.language_probability:.2f}，耗时 {time.time()-t0:.0f}s")

def fmt(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

with open(SRT_PATH, "w", encoding="utf-8") as f:
    for i, seg in enumerate(segs, 1):
        f.write(f"{i}\n{fmt(seg.start)} --> {fmt(seg.end)}\n{seg.text.strip()}\n\n")

with open(TXT_PATH, "w", encoding="utf-8") as f:
    for seg in segs:
        f.write(seg.text.strip() + "\n")

log(f"SRT: {SRT_PATH}")
log(f"TXT: {TXT_PATH}")
print("DONE_TRANSCRIBE")
