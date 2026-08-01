#!/usr/bin/env python3
"""补齐 yale 第1集缺失的 13.jpg 并重新合成视频"""
import os, sys, json, subprocess, time, io, re
from pathlib import Path
from PIL import Image
import requests

BASE = Path(__file__).resolve().parent.parent
EPISODE = "yale大学公开课系列讲谈"
EP_DIR = BASE / EPISODE
IMG_DIR = EP_DIR / "images"
OUTPUT_DIR = EP_DIR / "output"
AUDIO_DIR = EP_DIR / "audio"

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")
    except UnicodeEncodeError:
        safe = msg.encode('utf-8', errors='replace').decode('gbk', errors='replace')
        print(f"[{time.strftime('%H:%M:%S')}] {safe}")

def ffmpeg(args, timeout=120):
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        log(f"FFmpeg FAILED: {r.stderr[-300:]}")
        return False
    return True

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

def gen_pollinations(prompt, path, timeout=90):
    q = requests.utils.quote(f"{prompt}?width=1920&height=1080&model=flux&nologo=true&nofeed=true")
    url = f"https://image.pollinations.ai/prompt/{q}"
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
        return False, str(e)

# ===== Step 1: 补 13.jpg =====
log("=== Step 1: 补 13.jpg ===")
img_path = IMG_DIR / "13.jpg"
topic_prompt = "Yale students in experiment, data and statistics, only 15 percent cooperate, shocking result, academic research, cinematic, 16:9"
topic_title = "耶鲁实验 — 为什么耶鲁学生比普通人更邪恶"

if img_path.exists() and img_path.stat().st_size > 10000:
    log(f"13.jpg 已存在，跳过")
else:
    log(f"生成 13 [{topic_title}]...")
    ok, info = gen_pollinations(topic_prompt, img_path, timeout=120)
    log(f"  {'[OK]' if ok else '[FAIL]'} 13: {info}")
    if not ok:
        log("重试一次...")
        time.sleep(5)
        ok, info = gen_pollinations(topic_prompt, img_path, timeout=120)
        log(f"  {'[OK]' if ok else '[FAIL]'} 13 (retry): {info}")

# 检查所有图片
TOPICS = [
    "成绩陷阱 — 耶鲁课堂上的Alpha/Beta博弈",
    "战略情境 — 什么时候需要猜对手",
    "完全竞争与垄断 — 策略的生存空间",
    "收益(Payoffs) — 你无法得到你想要的，除非你知道你想要什么",
    "极度自私者 — 当你只关心自己的成绩",
    "严格占优策略 — 永远不要使用严格被占优的策略",
    "囚徒困境 — 理性选择如何导致糟糕结果",
    "帕雷托无效 — 明明可以更好，却困在泥潭",
    "现实中的囚徒困境 — 室友的面包与价格战",
    "破解困境 — 合同、法律与重复博弈",
    "愤怒的天使 — 情感如何改变收益矩阵",
    "协调问题与换位思考 — 穿上别人的鞋子",
    "耶鲁实验 — 为什么耶鲁学生比普通人更邪恶",
    "信息不对称 — 当你看不清对方的底牌",
]
all_images = [IMG_DIR / "intro.jpg"] + [IMG_DIR / f"{i:02d}.jpg" for i in range(1, len(TOPICS)+1)] + [IMG_DIR / "outro.jpg"]
missing = [p for p in all_images if not p.exists() or p.stat().st_size <= 10000]
if missing:
    log(f"[WARN] 仍有 {len(missing)} 张缺失:")
    for p in missing:
        log(f"  - {p.name}")
    sys.exit(1)
log(f"全部 {len(all_images)} 张配图就绪")

# ===== Step 2: 重新合成视频 =====
log("=== Step 2: 合成视频 ===")
AUDIO_MP3 = AUDIO_DIR / "audio.mp3"
duration = get_audio_duration(AUDIO_MP3)
log(f"音频时长: {duration/60:.1f} 分钟 ({duration:.0f} 秒)")

num_images = len(all_images)
img_duration = duration / num_images
log(f"每张图: {img_duration:.1f}s ({num_images} 张图填 {duration:.0f}s)")

# 生成 concat 文件
concat_file = EP_DIR / "img_concat.txt"
with open(concat_file, "w", encoding="utf-8") as f:
    for p in all_images:
        if p.exists():
            hd_path = str(p).replace('.jpg', '_hd.jpg')
            if not os.path.exists(hd_path):
                ffmpeg(["-i", str(p),
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                        "-q:v", "2", hd_path], timeout=30)
            f.write(f"file '{hd_path}'\nduration {img_duration:.3f}\n")

# 合成视频（无字幕版）
VIDEO_NO_SUB = OUTPUT_DIR / "耶鲁博弈论_成绩陷阱.mp4"
log("合成视频（无字幕）...")
ok = ffmpeg([
    "-f", "concat", "-safe", "0", "-i", str(concat_file),
    "-i", str(AUDIO_MP3),
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-pix_fmt", "yuv420p", "-r", "24",
    "-c:a", "aac", "-b:a", "128k",
    "-shortest",
    str(VIDEO_NO_SUB)
], timeout=600)

if not ok or not VIDEO_NO_SUB.exists():
    log("[FAIL] 视频合成失败")
    sys.exit(1)
sz = VIDEO_NO_SUB.stat().st_size / 1024 / 1024
log(f"[OK] 无字幕版: {sz:.1f}MB")

# ===== Step 3: 烧录字幕 =====
log("=== Step 3: 烧录字幕 ===")
SRT_PATH = AUDIO_DIR / "subtitles.srt"
VIDEO_SUB = OUTPUT_DIR / "耶鲁博弈论_成绩陷阱_字幕版.mp4"

SRT_TEMP = Path("yale_sub_temp.srt")
import shutil
shutil.copy2(str(SRT_PATH), str(SRT_TEMP))
vf = f"subtitles={SRT_TEMP}:force_style='FontName=SimHei,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'"
ok = ffmpeg([
    "-i", str(VIDEO_NO_SUB),
    "-vf", vf,
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-c:a", "copy",
    "-pix_fmt", "yuv420p",
    str(VIDEO_SUB)
], timeout=600)
if SRT_TEMP.exists():
    SRT_TEMP.unlink()
if ok and VIDEO_SUB.exists():
    sz = VIDEO_SUB.stat().st_size / 1024 / 1024
    log(f"[OK] 字幕版: {sz:.1f}MB")
else:
    log("[WARN] 字幕烧录失败，无字幕版可用")

log(f"\n{'='*40}")
log(f"完成!")
log(f"  视频: {VIDEO_NO_SUB} ({VIDEO_NO_SUB.stat().st_size/1024/1024:.1f}MB)")
if VIDEO_SUB.exists():
    log(f"  字幕版: {VIDEO_SUB} ({VIDEO_SUB.stat().st_size/1024/1024:.1f}MB)")
log(f"{'='*40}")