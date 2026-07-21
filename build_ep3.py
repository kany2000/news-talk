#!/usr/bin/env python3
"""新闻大家谈 第三期 — 全自动管线（Windows 适配版）"""
import sys, os, json, subprocess, time, math
from pathlib import Path

# Windows GBK 兼容
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = Path(__file__).resolve().parent
AUDIO_DIR = BASE / "audio"
IMG_DIR = BASE / "images"
OUTPUT_DIR = BASE / "output"
AUDIO_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

EPISODE = "第三期"
OUTPUT_VIDEO = OUTPUT_DIR / f"新闻大家谈_{EPISODE}_对话版.mp4"
OUTPUT_SUB = OUTPUT_DIR / f"新闻大家谈_{EPISODE}_对话版_字幕.mp4"

# 话题列表（用于配图）
TOPIC_TITLES = [
    "确认偏误 投资心理",
    "损失厌恶 行为经济学",
    "可得性启发 媒体放大效应",
    "赌徒谬误 概率认知",
    "世界杯下注 情感偏差",
    "热手谬误 投资心理",
    "理性投资 破解方法",
]

def log(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def run_cmd(cmd, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        log(f"CMD FAILED: {' '.join(str(c) for c in cmd)}")
        log(f"ERR: {r.stderr[-300:]}")
        return None
    return r.stdout

# ===== Step 1: 生成配图 =====
log("=== Step 1: 生成配图 ===")
sys.path.insert(0, str(BASE))
from gen_news_talk_images import generate_all, gen_image, build_prompt, TOPIC_PROMPTS
import gen_news_talk_images as gni

# 强制重新生成
results = generate_all(TOPIC_TITLES, force=True)
if not results:
    log("配图全部失败，退出")
    sys.exit(1)

# 检查图片
existing_intro = IMG_DIR / "intro.jpg"
existing_outro = IMG_DIR / "outro.jpg"
topic_images = []
for i in range(1, len(TOPIC_TITLES) + 1):
    p = IMG_DIR / f"{i:02d}.jpg"
    if p.exists() and p.stat().st_size > 10000:
        topic_images.append(str(p))
log(f"配图就绪: intro + {len(topic_images)} 话题 + outro")

# ===== Step 2: 生成音频（MiMo TTS）=====
log("=== Step 2: 生成音频 ===")
# 从中文文件名导入对话稿
dialogue_path = BASE / "scripts" / "对话稿_第三期.py"
with open(dialogue_path, "rb") as f:
    code = f.read().decode("utf-8")
ns = {}
exec(code, ns)
SCENE = ns["SCENE"]

# 适配本地 tts_mimo.py 的 gen_audio 接口
sys.path.insert(0, str(BASE))
from tts_mimo import gen_audio

VOICE_MAP = {"female": "xiaoxiao", "male": "yunyang"}

segments_meta = []
for i, (speaker, text, topic_idx) in enumerate(SCENE):
    out = AUDIO_DIR / f"seg_{i:03d}.wav"
    voice = VOICE_MAP[speaker]
    log(f"TTS [{i+1}/{len(SCENE)}] {speaker}: {text[:30]}...")
    try:
        gen_audio(text, str(out), voice_id=voice)
        segments_meta.append({
            "idx": i, "speaker": speaker, "text": text,
            "topic_idx": topic_idx, "path": str(out)
        })
        time.sleep(0.5)
    except Exception as e:
        log(f"TTS FAILED: {e}")
        sys.exit(1)

# ffprobe 取每段时长
for s in segments_meta:
    dur = run_cmd([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", s["path"]
    ], timeout=10)
    s["duration"] = float(dur.strip()) if dur else 0

# 累计时间戳
t = 0.0
for s in segments_meta:
    s["start"] = t
    s["end"] = t + s["duration"]
    t = s["end"]

total = sum(s["duration"] for s in segments_meta)
log(f"总时长: {total:.1f}s = {total/60:.1f}min")

# 保存元数据
meta_path = AUDIO_DIR / "segments_meta.json"
with open(meta_path, "w") as f:
    json.dump(segments_meta, f, ensure_ascii=False, indent=2)
log(f"元数据: {meta_path}")

# 合并 WAV → MP3
concat_list = AUDIO_DIR / "concat.txt"
with open(concat_list, "w") as f:
    for s in segments_meta:
        f.write(f"file '{s['path']}'\n")

combined_wav = AUDIO_DIR / "dialogue_combined.wav"
run_cmd([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", str(concat_list), "-c", "copy", str(combined_wav)
], timeout=120)

combined_mp3 = AUDIO_DIR / "dialogue_combined.mp3"
run_cmd([
    "ffmpeg", "-y", "-i", str(combined_wav),
    "-codec:a", "libmp3lame", "-b:a", "192k", str(combined_mp3)
], timeout=120)
log(f"合并音频: {combined_mp3}")

# ===== Step 3: 生成 SRT 字幕 =====
log("=== Step 3: 生成字幕 ===")
srt_lines = []
for i, s in enumerate(segments_meta, 1):
    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        sec = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
    srt_lines.append(str(i))
    srt_lines.append(f"{fmt(s['start'])} --> {fmt(s['end'])}")
    srt_lines.append(s["text"])
    srt_lines.append("")

srt_path = AUDIO_DIR / "dialogue.srt"
with open(srt_path, "w", encoding="utf-8") as f:
    f.write("\n".join(srt_lines))
log(f"SRT: {srt_path} ({len(segments_meta)} 条)")

# ===== Step 4: 合成视频 =====
log("=== Step 4: 合成视频 ===")

# topic_idx → 图片
topic_image_map = {
    0: str(IMG_DIR / "intro.jpg"),
    1: str(IMG_DIR / "01.jpg"),
    2: str(IMG_DIR / "02.jpg"),
    3: str(IMG_DIR / "03.jpg"),
    4: str(IMG_DIR / "04.jpg"),
    5: str(IMG_DIR / "05.jpg"),
    6: str(IMG_DIR / "06.jpg"),
    7: str(IMG_DIR / "07.jpg"),
    8: str(IMG_DIR / "outro.jpg"),
}

# 合并相邻同话题段
image_segments = []
current_topic = None
current_start = None
for s in segments_meta:
    t = s["topic_idx"]
    if t != current_topic:
        if current_topic is not None:
            image_segments.append((current_topic, current_start, s["start"]))
        current_topic = t
        current_start = s["start"]
if current_topic is not None:
    image_segments.append((current_topic, current_start, segments_meta[-1]["end"]))

# 生成 HD 图片
for idx, path in topic_image_map.items():
    if not os.path.exists(path):
        log(f"⚠ 缺图: {path}")
        continue
    hd = path.replace(".jpg", "_hd.jpg")
    if not os.path.exists(hd):
        run_cmd([
            "ffmpeg", "-y", "-i", path,
            "-vf", "scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-q:v", "2", hd
        ], timeout=30)

# 生成 concat 文件
img_concat = BASE / "img_concat_ep3.txt"
with open(img_concat, "w") as f:
    for topic, start, end in image_segments:
        dur = end - start
        if dur < 0.3:
            continue
        img = topic_image_map.get(topic, "").replace(".jpg", "_hd.jpg")
        if not os.path.exists(img):
            img = topic_image_map.get(topic, "")
        if not os.path.exists(img):
            continue
        f.write(f"file '{img}'\nduration {dur:.3f}\n")

# 一步合成
log("合成视频...")
run_cmd([
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0", "-i", str(img_concat),
    "-i", str(combined_mp3),
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-pix_fmt", "yuv420p", "-r", "24",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    str(OUTPUT_VIDEO)
], timeout=600)

if OUTPUT_VIDEO.exists():
    sz = OUTPUT_VIDEO.stat().st_size / 1024 / 1024
    log(f"✅ 无字幕版: {sz:.1f}MB")
else:
    log("❌ 视频合成失败")
    sys.exit(1)

# ===== Step 5: 烧录字幕 =====
log("=== Step 5: 烧录字幕 ===")
run_cmd([
    "ffmpeg", "-y", "-i", str(OUTPUT_VIDEO),
    "-vf", f"subtitles={srt_path}:force_style='FontName=Noto Sans CJK SC,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'",
    "-c:a", "copy", "-pix_fmt", "yuv420p",
    str(OUTPUT_SUB)
], timeout=600)

if OUTPUT_SUB.exists():
    sz = OUTPUT_SUB.stat().st_size / 1024 / 1024
    log(f"✅ 字幕版: {sz:.1f}MB")
else:
    log("⚠ 字幕烧录失败，无字幕版可用")

# 清理
try:
    img_concat.unlink()
    combined_wav.unlink()
    concat_list.unlink()
except:
    pass

log(f"\n完成!")
log(f"  MP3:   {combined_mp3}")
log(f"  视频:  {OUTPUT_VIDEO}")
if OUTPUT_SUB.exists():
    log(f"  字幕:  {OUTPUT_SUB}")