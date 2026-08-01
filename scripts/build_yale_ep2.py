#!/usr/bin/env python3
"""新闻大家谈 — 耶鲁公开课系列：第二期·看透对手"""
import os, sys, json, math, subprocess, io, time, re
os.environ["PYTHONIOENCODING"] = "utf-8"
from pathlib import Path
from PIL import Image
import requests

# ===== 配置 =====
BASE = Path(__file__).resolve().parent.parent
EPISODE = "yale大学公开课系列讲谈"
EP_NO = "第二期"
AUDIO_SRC = BASE / EPISODE / "耶鲁博弈论看透对手(L2.3.4).m4a"

EP_DIR = BASE / EPISODE
EP2_DIR = EP_DIR / EP_NO
AUDIO_DIR = EP2_DIR / "audio"
IMG_DIR = EP2_DIR / "images"
OUTPUT_DIR = EP2_DIR / "output"

for d in [EP2_DIR, AUDIO_DIR, IMG_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 话题列表（按音频内容顺序，序号=图片文件名）
TOPICS = [
    "博弈三要素 — 玩家、策略与收益",
    "囚徒困境 — 价格战与气候峰会",
    "小组作业的摸鱼陷阱 — 激励改变一切",
    "第一法则 — 理性人绝不选劣势策略",
    "汉尼拔的豪赌 — 翻越阿尔卑斯山",
    "猜数字游戏 — 2/3平均数的无限剔除",
    "共同知识 — 粉色帽子的信任链",
    "最佳反应 — 中位选民定理",
    "点球大战 — 数据里的冷酷真相",
    "丰富模型 — 给博弈加一个新变量",
    "纳什均衡 — 合伙人的熬夜博弈",
    "均衡不是天堂 — 锁死所有人的陷阱",
    "力量恰恰是你的弱点 — 委员A的投票特权",
]

IMAGE_PROMPTS = {
    "intro": "Yale University large amphitheater lecture hall, rising tiers of wooden seats, filled with students sitting in ascending rows, professor at podium, green chalkboard, academic atmosphere, warm cinematic lighting, wide angle shot, 16:9",
    "outro": "chess board with gold and silver pieces, strategic thinking, sunset light through window, contemplative mood, cinematic, 16:9",
}

TOPIC_EN_PROMPTS = [
    "three pillars representing game theory basics: a player icon, a fan of strategy cards, and a pile of gold coins as payoffs, minimal elegant diagram style, cinematic lighting, 16:9",
    "prisoner's dilemma, two prisoners in separate cells, handcuffs, dilemma concept, dark moody lighting, cinematic, 16:9",
    "students around a library table secretly gaming on phones while a group project document stays empty, procrastination, laptop glow in dim room, relatable, cinematic, 16:9",
    "lighthouse beam cutting through fog pointing at one clear path among many weak uncertain trails, eliminating dominated strategies, decisive light, cinematic, 16:9",
    "Hannibal leading war elephants and an army over snowy Alpine mountain pass, ancient Rome campaign, epic landscape, dramatic clouds, cinematic, 16:9",
    "classroom students writing numbers on paper, chalkboard with numbers and fractions, guess two thirds of the average game, academic, cinematic, 16:9",
    "two people wearing pink hats facing each other, mutual knowledge puzzle, thought experiment, minimalist composition, soft light, cinematic, 16:9",
    "political spectrum line from left to right with two candidate avatars converging toward the center, median voter theorem, abstract infographic style, cinematic, 16:9",
    "soccer player taking a penalty kick toward goal, goalkeeper diving, football stadium lights, high tension freeze frame, cinematic, 16:9",
    "chalkboard equation being expanded with a new variable, hands adding complexity to a model, evolving mathematics, dynamic, cinematic, 16:9",
    "two exhausted students staring at a shared laptop at 2am, mutual standoff, each waiting for the other to do more work, deadline pressure, dim room, cinematic, 16:9",
    "two people stuck in a mud pit holding each other back, no one dares to move, Nash equilibrium trap, desolate moody landscape, cinematic, 16:9",
    "three committee members at a table voting, one holding a golden gavel of absolute power, subtle tension, political committee room, cinematic, 16:9",
]

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        safe = msg.encode('utf-8', errors='replace').decode('gbk', errors='replace')
        print(f"[{time.strftime('%H:%M:%S')}] {safe}", flush=True)

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

# ===== Step 1: 复制并转换音频 =====
log("=== Step 1: 复制音频 ===")
AUDIO_MP3 = AUDIO_DIR / "audio.mp3"
if not AUDIO_MP3.exists():
    ffmpeg(["-i", str(AUDIO_SRC), "-codec:a", "libmp3lame", "-b:a", "128k", str(AUDIO_MP3)], timeout=300)
    log(f"转换完成: {AUDIO_MP3}")
else:
    log(f"音频已存在: {AUDIO_MP3}")

duration = get_audio_duration(AUDIO_MP3)
log(f"音频时长: {duration/60:.1f} 分钟 ({duration:.0f} 秒)")

# ===== Step 2: 转写字幕（跳过，已由 yale_ep2_transcribe.py 完成）=====
log("=== Step 2: 检查字幕 ===")
SRT_PATH = AUDIO_DIR / "subtitles.srt"
if not SRT_PATH.exists():
    log("[FAIL] 字幕不存在，先运行 yale_ep2_transcribe.py")
    sys.exit(1)
log(f"SRT: {SRT_PATH}")

# ===== Step 3: 生成配图 =====
log("=== Step 3: 生成配图 ===")

def gen_pollinations(prompt, path, timeout=120):
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

intro_path = IMG_DIR / "intro.jpg"
if not intro_path.exists():
    log("生成 intro 配图...")
    ok, info = gen_pollinations(IMAGE_PROMPTS["intro"], intro_path)
    log(f"  [{'OK' if ok else 'FAIL'}] intro: {info}")
    time.sleep(3)

for i, (title, en_prompt) in enumerate(zip(TOPICS, TOPIC_EN_PROMPTS), 1):
    img_path = IMG_DIR / f"{i:02d}.jpg"
    if img_path.exists():
        log(f"  [OK] {i:02d} {title[:15]} (skipped)")
        continue
    log(f"生成 {i:02d} [{title[:15]}]...")
    ok, info = gen_pollinations(en_prompt, img_path)
    log(f"  {'[OK]' if ok else '[FAIL]'} {i:02d}: {info}")
    time.sleep(3)

outro_path = IMG_DIR / "outro.jpg"
if not outro_path.exists():
    log("生成 outro 配图...")
    ok, info = gen_pollinations(IMAGE_PROMPTS["outro"], outro_path)
    log(f"  {'[OK]' if ok else '[FAIL]'} outro: {info}")

all_images = [intro_path] + [IMG_DIR / f"{i:02d}.jpg" for i in range(1, len(TOPICS)+1)] + [outro_path]
missing = [p for p in all_images if not p.exists()]
if missing:
    log(f"[WARN] missing {len(missing)} images, continuing")
    for p in missing:
        log(f"  - {p.name}")

# ===== Step 4: 合成视频 =====
log("=== Step 4: 合成视频（按讲稿时间区间切图）===")

num_images = len([p for p in all_images if p.exists()])
if num_images == 0:
    log("[FAIL] no images available, exit")
    sys.exit(1)

# 每张图的时间区间（秒）— 按讲稿内容切分，保证图片与语音同步
IMG_DURATIONS = {
    "intro": 87.3,
    "01": 46.8,
    "02": 71.5,
    "03": 85.1,
    "04": 19.2,
    "05": 115.6,
    "06": 147.7,
    "07": 93.4,
    "08": 143.4,
    "09": 96.0,
    "10": 98.2,
    "11": 190.5,
    "12": 99.8,
    "13": 85.0,
    "outro": 18.3,
}
total_sec = sum(IMG_DURATIONS.values())
log(f"图片时间区间合计: {total_sec:.1f}s (音频 {duration:.1f}s)")

concat_file = EP2_DIR / "img_concat.txt"
with open(concat_file, "w", encoding="utf-8") as f:
    for p in all_images:
        if p.exists():
            name = p.stem  # intro / 01..14 / outro
            dur = IMG_DURATIONS.get(name, 0)
            if dur <= 0:
                log(f"[WARN] {name} 无时间区间，跳过")
                continue
            hd_path = str(p).replace('.jpg', '_hd.jpg')
            if not os.path.exists(hd_path):
                ffmpeg(["-i", str(p),
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                        "-q:v", "2", hd_path], timeout=30)
            f.write(f"file '{hd_path}'\nduration {dur:.3f}\n")
            log(f"  {name}: {dur:.1f}s")

VIDEO_NO_SUB = OUTPUT_DIR / "耶鲁博弈论_看透对手.mp4"
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
    log("[FAIL] video composition failed")
    sys.exit(1)
sz = VIDEO_NO_SUB.stat().st_size / 1024 / 1024
log(f"[OK] no-sub video: {VIDEO_NO_SUB} ({sz:.1f}MB)")

# ===== Step 5: 烧录字幕 =====
log("=== Step 5: 烧录字幕 ===")
VIDEO_SUB = OUTPUT_DIR / "耶鲁博弈论_看透对手_字幕版.mp4"
if not VIDEO_SUB.exists():
    import shutil
    SRT_TEMP = Path("/tmp/yale_subtitles.srt") if os.name != 'nt' else Path("yale_sub_temp.srt")
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
        log(f"[OK] subtitled: {VIDEO_SUB} ({sz:.1f}MB)")
    else:
        log("[WARN] subtitle burn failed, no-sub version available")
else:
    log(f"字幕版已存在: {VIDEO_SUB}")

log(f"\n{'='*40}")
log(f"完成!")
log(f"  目录: {EP2_DIR}")
log(f"  音频: {AUDIO_MP3}")
log(f"  字幕: {SRT_PATH}")
log(f"  视频: {VIDEO_NO_SUB}")
if VIDEO_SUB.exists():
    log(f"  字幕版: {VIDEO_SUB}")
log(f"  配图: {len([p for p in all_images if p.exists()])}/{len(all_images)} 张")
log(f"{'='*40}")
