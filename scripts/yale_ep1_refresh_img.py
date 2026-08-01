#!/usr/bin/env python3
"""重新生成指定图片并重制视频。用法: python scripts/yale_ep1_refresh_img.py <编号, 如 11>"""
import os, sys, subprocess, time, io, re
from pathlib import Path
from PIL import Image
import requests

num = int(sys.argv[1]) if len(sys.argv) > 1 else 11
BASE = Path(__file__).resolve().parent.parent
EP_DIR = BASE / "yale大学公开课系列讲谈"
IMG_DIR = EP_DIR / "images"
OUTPUT_DIR = EP_DIR / "output"
AUDIO_DIR = EP_DIR / "audio"

PROMPTS = {
    1: "Yale economics professor Ben Polak standing in front of chalkboard, teaching game theory, writing Alpha Beta, students watching from desks, clear separation between teacher and board, academic lecture, cinematic, 16:9",
    2: "strategic interaction, business competitors watching each other, Ford vs Toyota, market competition, interconnected decisions, cinematic, 16:9",
    3: "perfect competition farmers market vs monopoly single giant corporation, economic spectrum, small sellers vs one dominant company, minimal, cinematic, 16:9",
    4: "person looking at multiple options, confused decision making, path diverging, what do you really want, philosophical, cinematic, 16:9",
    5: "extremely selfish person, calculating expression, only cares about own benefit, ruthless decision, dark lighting, cinematic portrait, 16:9",
    6: "dominant strategy concept, highway with carpool lane, fast lane always winning, game theory visual, clear path, cinematic, 16:9",
    7: "prisoner's dilemma, two prisoners in separate cells, handcuffs, dilemma concept, dark moody lighting, cinematic, 16:9",
    8: "Pareto efficiency concept, two people both stuck in mud, visible better outcome nearby, frustration, economic theory, cinematic, 16:9",
    9: "dorm room with moldy bread and cheese, messy roommate, price war signs, two businesses competing, real life application, cinematic, 16:9",
    10: "Business contract signing, two hands shaking across desk, legal documents, binding agreement, professional attire, corporate setting, cinematic lighting, 16:9",
    11: "angry angel, torn between morality and self interest, guilt and anger, emotional conflict, dramatic lighting, cinematic, 16:9",
    12: "Empty narrow corridor, mirror reflection, two paths crossing, dilemma of choosing direction, coordination concept, minimalist photography, cinematic, 16:9",
    13: "Yale students in experiment, data and statistics, only 15 percent cooperate, shocking result, academic research, cinematic, 16:9",
    14: "poker game hidden cards, face down, information asymmetry, unknown opponent, mystery, blurred background, cinematic lighting, 16:9",
}

TITLES = {
    1: "成绩陷阱 — Alpha/Beta博弈",
    2: "战略情境",
    3: "完全竞争与垄断",
    4: "收益(Payoffs)",
    5: "极度自私者",
    6: "严格占优策略",
    7: "囚徒困境",
    8: "帕雷托无效",
    9: "现实中的囚徒困境",
    10: "破解困境",
    11: "愤怒的天使",
    12: "协调问题与换位思考",
    13: "耶鲁实验",
    14: "信息不对称",
}

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")
    except UnicodeEncodeError:
        print(f"[{time.strftime('%H:%M:%S')}] {msg.encode('utf-8','replace').decode('gbk','replace')}")

def gen_pollinations(prompt, path, timeout=120):
    q = requests.utils.quote(f"{prompt}?width=1920&height=1080&model=flux&nologo=true&nofeed=true")
    url = f"https://image.pollinations.ai/prompt/{q}"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://pollinations.ai/",
            })
            if r.status_code == 200:
                img = Image.open(io.BytesIO(r.content))
                if img.size != (1920, 1080):
                    img = img.resize((1920, 1080), Image.LANCZOS)
                img.convert("RGB").save(path, "JPEG", quality=90)
                return True, len(r.content)
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
    return False, str(e)

def ffmpeg(args, timeout=120):
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
    return r.returncode == 0

def get_audio_duration(path):
    r = subprocess.run(["ffmpeg", "-i", str(path), "-f", "null", "-"],
                       capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
    for line in r.stderr.split('\n'):
        if 'Duration' in line:
            m = re.search(r'Duration: (\d+):(\d+):(\d+)\.(\d+)', line)
            if m:
                h, m_, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                return h*3600 + m_*60 + s + ms/100
    return 0

# ===== Step 1: 重新生成图片 =====
log(f"=== Step 1: 重新生成 {num:02d}.jpg ===")
img_path = IMG_DIR / f"{num:02d}.jpg"
prompt = PROMPTS.get(num)
title = TITLES.get(num, f"Topic {num}")

if not prompt:
    log(f"[FAIL] 编号 {num} 没有对应 prompt")
    sys.exit(1)

# 删除旧的
if img_path.exists():
    img_path.unlink()
    log(f"已删除旧 {num:02d}.jpg")
# 也删掉对应的 _hd.jpg
hd_path = IMG_DIR / f"{num:02d}_hd.jpg"
if hd_path.exists():
    hd_path.unlink()
    log(f"已删除旧 {num:02d}_hd.jpg")

log(f"生成 {num:02d} [{title}]...")
ok, info = gen_pollinations(prompt, img_path)
log(f"  {'[OK]' if ok else '[FAIL]'} {num:02d}: {info}")
if not ok:
    sys.exit(1)

# ===== Step 2: 重新合成视频 =====
log("=== Step 2: 合成视频 ===")
AUDIO_MP3 = AUDIO_DIR / "audio.mp3"
duration = get_audio_duration(AUDIO_MP3)
log(f"音频时长: {duration/60:.1f} 分钟")

all_images = [IMG_DIR / "intro.jpg"] + [IMG_DIR / f"{i:02d}.jpg" for i in range(1, 15)] + [IMG_DIR / "outro.jpg"]
all_images = [p for p in all_images if p.exists()]
num_images = len(all_images)
img_duration = duration / num_images
log(f"每张图: {img_duration:.1f}s ({num_images} 张)")

# 生成 HD 图
for p in all_images:
    hd = str(p).replace('.jpg', '_hd.jpg')
    if not os.path.exists(hd):
        ffmpeg(["-i", str(p), "-vf", "scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2", "-q:v", "2", hd], timeout=30)

concat_file = EP_DIR / "img_concat.txt"
with open(concat_file, "w", encoding="utf-8") as f:
    for p in all_images:
        hd = str(p).replace('.jpg', '_hd.jpg')
        f.write(f"file '{hd}'\nduration {img_duration:.3f}\n")

VIDEO_NO_SUB = OUTPUT_DIR / "耶鲁博弈论_成绩陷阱.mp4"
log("合成视频...")
ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(AUDIO_MP3),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "24",
        "-c:a", "aac", "-b:a", "128k", "-shortest",
        str(VIDEO_NO_SUB)], timeout=600)
sz = VIDEO_NO_SUB.stat().st_size / 1024 / 1024
log(f"[OK] 无字幕版: {sz:.1f}MB")

# ===== Step 3: 烧录字幕 =====
log("=== Step 3: 烧录字幕 ===")
SRT_PATH = AUDIO_DIR / "subtitles.srt"
VIDEO_SUB = OUTPUT_DIR / "耶鲁博弈论_成绩陷阱_字幕版.mp4"

import shutil
SRT_TEMP = Path("yale_sub_temp.srt")
shutil.copy2(str(SRT_PATH), str(SRT_TEMP))
vf = f"subtitles={SRT_TEMP}:force_style='FontName=SimHei,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'"
ffmpeg(["-i", str(VIDEO_NO_SUB), "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy", "-pix_fmt", "yuv420p",
        str(VIDEO_SUB)], timeout=600)
SRT_TEMP.unlink(missing_ok=True)
if VIDEO_SUB.exists():
    sz = VIDEO_SUB.stat().st_size / 1024 / 1024
    log(f"[OK] 字幕版: {sz:.1f}MB")

log(f"\n完成! 视频大小: {VIDEO_NO_SUB.stat().st_size/1024/1024:.1f}MB / {VIDEO_SUB.stat().st_size/1024/1024:.1f}MB")