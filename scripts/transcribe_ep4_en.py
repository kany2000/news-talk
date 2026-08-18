#!/usr/bin/env python3
"""第四期转写：耶鲁博弈论·隔离 L8.9.10 — faster-whisper → 英文 SRT + 文本稿
faster-whisper 内部用 PyAV 解码，m4a 可直接喂入，不依赖 ffmpeg"""
import os, sys, time
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["KMP_BLOCKTIME"] = "1"
from pathlib import Path

BASE = Path(r"E:\projects\news-talk")
EP = BASE / "yale大学公开课系列讲谈"
AUDIO_SRC = EP / "Why_integrated_people_end_up_segregated(L8.9.10).m4a"
EP4_DIR = EP / "第四期"
AUDIO_DIR = EP4_DIR / "audio"
SRT_PATH = AUDIO_DIR / "subtitles_en_raw.srt"
TXT_PATH = EP4_DIR / "transcript_en.txt"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{time.strftime('%H:%M:%S')}] {msg.encode('utf-8','replace').decode('gbk','replace')}", flush=True)

log("加载 faster-whisper base...")
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=2)
log("转写中（直接读 m4a，预计 5-12 分钟）...")
t0 = time.time()
segments, info = model.transcribe(str(AUDIO_SRC), language="en", beam_size=5)
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
