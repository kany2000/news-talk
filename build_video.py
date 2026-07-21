#!/usr/bin/env python3
"""Build 新闻大家谈 video from images + podcast audio."""
import subprocess, os, math, json
from pathlib import Path

BASE = Path("/home/kan/shared/news-talk")
IMG = BASE / "images"
AUDIO = BASE / "audio" / "podcast.mp3"
OUT = BASE / "output" / "新闻大家谈_首期.mp4"
TEMP = BASE / "output" / "slides.mp4"

# Get audio duration
r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1", str(AUDIO)],
    capture_output=True, text=True, timeout=10)
audio_dur = float(r.stdout.strip())
print(f"Audio: {audio_dur:.0f}s ({audio_dur/60:.1f}min)")

# Build concat list: intro(10s) + 8 topics(20s each) + outro(10s) = 180s loop
slides = [("intro", 10)]
for i in range(1, 9):
    slides.append((f"{i:02d}", 20))
slides.append(("outro", 10))
loop_dur = sum(d for _, d in slides)
print(f"Loop: {loop_dur}s ({loop_dur/60:.1f}min), {len(slides)} slides")

# Write concat file
concat = BASE / "concat.txt"
with open(concat, "w") as f:
    for name, dur in slides:
        path = IMG / f"{name}.jpg"
        if not path.exists():
            print(f"⚠ Missing {path}, using placeholder")
            continue
        f.write(f"file '{path}'\nduration {dur}\n")

# Generate slideshow video
subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", str(concat),
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-pix_fmt", "yuv420p", "-r", "24",
    str(TEMP)
], check=True, timeout=120)
print(f"Slides: {TEMP.stat().st_size/1024/1024:.0f}MB")

# Merge with audio - loop video to fill audio duration
loops_needed = math.ceil(audio_dur / loop_dur)
print(f"Loops needed: {loops_needed}")

subprocess.run([
    "ffmpeg", "-y",
    "-stream_loop", str(loops_needed - 1), "-i", str(TEMP),
    "-i", str(AUDIO),
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-c:a", "aac", "-b:a", "128k",
    "-shortest",
    "-pix_fmt", "yuv420p",
    str(OUT)
], check=True, timeout=300)

# Cleanup
TEMP.unlink(missing_ok=True)
concat.unlink(missing_ok=True)

size_mb = OUT.stat().st_size / 1024 / 1024
print(f"\n✅ 视频: {OUT}")
print(f"   大小: {size_mb:.1f}MB")
print(f"   时长: {audio_dur/60:.1f}min")