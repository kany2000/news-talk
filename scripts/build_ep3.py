#!/usr/bin/env python3
"""新闻大家谈 第三期 — 用已有音频重新制作视频"""
import os, sys, json, math, subprocess, io, time, re
os.environ["PYTHONIOENCODING"] = "utf-8"
from pathlib import Path
from PIL import Image
import requests

# ===== 配置 =====
BASE = Path(__file__).resolve().parent.parent  # 脚本在 scripts/，项目根在上一级
EPISODE = "第三期"
AUDIO_SRC = BASE / "audio" / "为什么你一买就跌.m4a"

EP_DIR = BASE / EPISODE
AUDIO_DIR = EP_DIR / "audio"
IMG_DIR = EP_DIR / "images"
OUTPUT_DIR = EP_DIR / "output"

for d in [EP_DIR, AUDIO_DIR, IMG_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 话题列表（来自 cn_prompt.txt，按音频内容顺序）
TOPICS = [
    "确认偏误 — 为什么你只愿意相信自己想相信的",
    "损失厌恶 — 为什么亏钱比赚钱更难受",
    "可得性启发 — 为什么新闻让你觉得股市要崩",
    "赌徒谬误 — 为什么输了就想翻本",
    "情感偏差 — 为什么情绪让你追涨杀跌",
    "热手谬误 — 为什么连胜让你以为运气来了",
    "如何破解这些心理陷阱",
]

# 英文配图 prompt（pollinations 用英文效果好）
IMAGE_PROMPTS = {
    "intro": "news talk show studio, modern glass desk, multiple screens, warm golden and blue lighting, professional broadcast set, cinematic, no people, 16:9",
    "outro": "city skyline at dusk, news broadcast ending, rolling credits, warm glow, cinematic aerial view, no people, 16:9",
}
TOPIC_EN_PROMPTS = [
    "confirmation bias concept, person filtering information, cognitive psychology, minimalist illustration, cinematic lighting, 16:9",
    "loss aversion, stock market chart going down, investor panic facial expression, fear and greed, cinematic, 16:9",
    "availability heuristic, media headlines flooding, news overstimulation brain, cognitive bias illustration, 16:9",
    "gambler's fallacy, roulette wheel, casino betting, probability trap, behavioral economics, dark mood, 16:9",
    "emotional bias trading, stock trader overwhelmed by fear and greed, red green candles, cinematic, 16:9",
    "hot hand fallacy, basketball winning streak, lucky streak concept, sports statistics, 16:9",
    "breaking psychological traps, brain with chains breaking, self improvement, wisdom, bright hopeful light, 16:9",
]

def log(msg):
    """Log with GBK-safe encoding"""
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
    """从 ffmpeg -i 输出解析时长"""
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

# ===== Step 2: 转写字幕 =====
log("=== Step 2: 转写字幕 ===")
SRT_PATH = AUDIO_DIR / "subtitles.srt"
if not SRT_PATH.exists():
    log("加载 faster-whisper...")
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    log("转写中（这步会比较慢）...")
    segments, info = model.transcribe(str(AUDIO_MP3), language="zh", beam_size=5)
    segs = list(segments)
    log(f"转写完成: {len(segs)} 段, {info.language}")

    with open(SRT_PATH, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segs, 1):
            def fmt(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s = int(t % 60)
                ms = int((t - int(t)) * 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            f.write(f"{i}\n{fmt(seg.start)} --> {fmt(seg.end)}\n{seg.text.strip()}\n\n")
    log(f"SRT: {SRT_PATH}")
else:
    log(f"SRT 已存在: {SRT_PATH}")

# ===== Step 3: 生成配图 =====
log("=== Step 3: 生成配图 ===")

def gen_pollinations(prompt, path, timeout=90):
    """用 Pollinations 生成配图"""
    q = requests.utils.quote(f"{prompt}?width=1920&height=1080&model=flux&nologo=true&nofeed=true")
    url = f"https://image.pollinations.ai/prompt/{q}"
    try:
        r = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://pollinations.ai/",
        })
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content))
            # 确保 1920x1080
            if img.size != (1920, 1080):
                img = img.resize((1920, 1080), Image.LANCZOS)
            img.convert("RGB").save(path, "JPEG", quality=90)
            return True, len(r.content)
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

# 生成 intro
intro_path = IMG_DIR / "intro.jpg"
if not intro_path.exists():
    log("生成 intro 配图...")
    ok, info = gen_pollinations(IMAGE_PROMPTS["intro"], intro_path)
    log(f"  [OK] intro: {info}")
    time.sleep(3)

# 生成话题配图
for i, (title, en_prompt) in enumerate(zip(TOPICS, TOPIC_EN_PROMPTS), 1):
    img_path = IMG_DIR / f"{i:02d}.jpg"
    if img_path.exists():
        log(f"  [OK] {i:02d} {title[:15]} (skipped)")
        continue
    log(f"生成 {i:02d} [{title[:15]}]...")
    ok, info = gen_pollinations(en_prompt, img_path)
    log(f"  {'[OK]' if ok else '[FAIL]'} {i:02d}: {info}")
    time.sleep(3)

# 生成 outro
outro_path = IMG_DIR / "outro.jpg"
if not outro_path.exists():
    log("生成 outro 配图...")
    ok, info = gen_pollinations(IMAGE_PROMPTS["outro"], outro_path)
    log(f"  {'[OK]' if ok else '[FAIL]'} outro: {info}")

# 检查所有图片
all_images = [intro_path] + [IMG_DIR / f"{i:02d}.jpg" for i in range(1, len(TOPICS)+1)] + [outro_path]
missing = [p for p in all_images if not p.exists()]
if missing:
    log(f"[WARN] missing {len(missing)} images, continuing")
    for p in missing:
        log(f"  - {p.name}")

# ===== Step 4: 合成视频 =====
log("=== Step 4: 合成视频 ===")

# 计算每张图停留时长
num_images = len([p for p in all_images if p.exists()])
if num_images == 0:
    log("[FAIL] no images available, exit")
    sys.exit(1)

# 每张图时长 = 总时长 / 图片数
img_duration = duration / num_images
log(f"each image: {img_duration:.1f}s ({num_images} images fill {duration:.0f}s)")

# 生成 concat 文件（用 UTF-8 编码，避免中文路径乱码）
concat_file = EP_DIR / "img_concat.txt"
with open(concat_file, "w", encoding="utf-8") as f:
    for p in all_images:
        if p.exists():
            # 确保 1920x1080
            hd_path = str(p).replace('.jpg', '_hd.jpg')
            if not os.path.exists(hd_path):
                ffmpeg(["-i", str(p),
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                        "-q:v", "2", hd_path], timeout=30)
            f.write(f"file '{hd_path}'\nduration {img_duration:.3f}\n")

# 合成视频（无字幕版）
VIDEO_NO_SUB = OUTPUT_DIR / "新闻大家谈_第三期.mp4"
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
VIDEO_SUB = OUTPUT_DIR / "新闻大家谈_第三期_字幕版.mp4"
if not VIDEO_SUB.exists():
    # 使用 SRT 烧录字幕
    vf = f"subtitles={SRT_PATH}:force_style='FontName=SimHei,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'"
    ok = ffmpeg([
        "-i", str(VIDEO_NO_SUB),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        str(VIDEO_SUB)
    ], timeout=600)
    if ok and VIDEO_SUB.exists():
        sz = VIDEO_SUB.stat().st_size / 1024 / 1024
        log(f"[OK] subtitled: {VIDEO_SUB} ({sz:.1f}MB)")
    else:
        log("[WARN] subtitle burn failed, no-sub version available")
else:
    log(f"字幕版已存在: {VIDEO_SUB}")

log(f"\n{'='*40}")
log(f"完成!")
log(f"  目录: {EP_DIR}")
log(f"  音频: {AUDIO_MP3}")
log(f"  字幕: {SRT_PATH}")
log(f"  视频: {VIDEO_NO_SUB}")
if VIDEO_SUB.exists():
    log(f"  字幕版: {VIDEO_SUB}")
log(f"  配图: {len([p for p in all_images if p.exists()])}/{len(all_images)} 张")
log(f"{'='*40}")