#!/usr/bin/env python3
"""新闻大家谈 第三期 — 全自动管线（Windows 适配版）"""
import sys, os, json, subprocess, time, math
from pathlib import Path

# Windows GBK 兼容
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Windows ffmpeg/ffprobe 路径修复
import shutil
_ffmpeg = shutil.which("ffmpeg")
if _ffmpeg:
    _dir = os.path.dirname(os.path.realpath(_ffmpeg))
    os.environ["PATH"] = _dir + os.pathsep + os.environ.get("PATH", "")
# ffprobe 可能不在 PATH 中，用 cmd 定位
import subprocess as _sp
_ffprobe = _sp.run(["cmd", "/c", "where", "ffprobe"], capture_output=True, text=True, timeout=5).stdout.strip()
if _ffprobe and os.path.exists(_ffprobe):
    _ffprobe_dir = os.path.dirname(_ffprobe)
    os.environ["PATH"] = _ffprobe_dir + os.pathsep + os.environ.get("PATH", "")

BASE = Path(__file__).resolve().parent
AUDIO_DIR = BASE / "audio"
IMG_DIR = BASE / "images" / EPISODE
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

def run_cmd(cmd, timeout=300, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=False, timeout=timeout, cwd=cwd)
    if r.returncode != 0:
        log(f"CMD FAILED: {' '.join(str(c) for c in cmd)}")
        err = r.stderr.decode('utf-8', errors='replace')[-300:] if r.stderr else ''
        log(f"ERR: {err}")
        return None
    return r.stdout.decode('utf-8', errors='replace') if r.stdout else ''

# ===== Step 1: 生成配图（已有则跳过）=====
log("=== Step 1: 配图 ===")
sys.path.insert(0, str(BASE))
import gen_news_talk_images
from gen_news_talk_images import generate_all

# 检查是否所有图片已存在
expected_images = ["intro.jpg", "outro.jpg"] + [f"{i:02d}.jpg" for i in range(1, len(TOPIC_TITLES) + 1)]
all_images_exist = all((IMG_DIR / img).exists() and (IMG_DIR / img).stat().st_size > 10000 for img in expected_images)

if all_images_exist:
    log("所有配图已存在，跳过")
else:
    missing = [img for img in expected_images if not (IMG_DIR / img).exists() or (IMG_DIR / img).stat().st_size <= 10000]
    log(f"缺失 {len(missing)} 张图: {missing}，生成中...")
    # 设置输出目录为 images/{EPISODE}/
    gen_news_talk_images.IMG_DIR = str(IMG_DIR)
    results = generate_all(TOPIC_TITLES)
    if not results:
        log("配图全部失败，退出")
        sys.exit(1)

# ===== Step 2: 生成音频（已有则跳过）=====
log("=== Step 2: 音频 ===")
combined_mp3 = AUDIO_DIR / "dialogue_combined.mp3"
meta_path = AUDIO_DIR / "segments_meta.json"

if combined_mp3.exists() and meta_path.exists():
    log(f"音频已存在: {combined_mp3}，跳过 TTS")
    with open(meta_path) as f:
        segments_meta = json.load(f)
else:
    # 从中文文件名导入对话稿
    dialogue_path = BASE / "scripts" / "对话稿_第三期.py"
    with open(dialogue_path, "rb") as f:
        code = f.read().decode("utf-8")
    ns = {}
    exec(code, ns)
    SCENE = ns["SCENE"]

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

    # 取每段时长（wave 模块）
    import wave as _wave
    for s in segments_meta:
        with _wave.open(s["path"], "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            s["duration"] = frames / rate if rate else 0

    # 累计时间戳
    t = 0.0
    for s in segments_meta:
        s["start"] = t
        s["end"] = t + s["duration"]
        t = s["end"]

    total = sum(s["duration"] for s in segments_meta)
    log(f"总时长: {total:.1f}s = {total/60:.1f}min")

    # 保存元数据
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
    run_cmd([
        "ffmpeg", "-y", "-i", str(combined_wav),
        "-codec:a", "libmp3lame", "-b:a", "192k", str(combined_mp3)
    ], timeout=120)
    log(f"合并音频: {combined_mp3}")

# ===== Step 3: 生成 SRT 字幕（已有则跳过）=====
srt_path = AUDIO_DIR / "dialogue.srt"
if srt_path.exists():
    log(f"SRT 已存在: {srt_path}，跳过")
else:
    log("=== Step 3: 字幕 ===")
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
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    log(f"SRT: {srt_path} ({len(segments_meta)} 条)")

# ===== Step 4: 合成视频（已有则跳过）=====
if OUTPUT_VIDEO.exists():
    log(f"视频已存在: {OUTPUT_VIDEO}，跳过合成")
else:
    log("=== Step 4: 合成视频 ===")

    # topic_idx → 图片（用 posix 路径避免编码问题）
    topic_image_map = {
        0: str(IMG_DIR / "intro_hd.jpg"),
        1: str(IMG_DIR / "01_hd.jpg"),
        2: str(IMG_DIR / "02_hd.jpg"),
        3: str(IMG_DIR / "03_hd.jpg"),
        4: str(IMG_DIR / "04_hd.jpg"),
        5: str(IMG_DIR / "05_hd.jpg"),
        6: str(IMG_DIR / "06_hd.jpg"),
        7: str(IMG_DIR / "07_hd.jpg"),
        8: str(IMG_DIR / "outro_hd.jpg"),
    }

    # 确保 HD 图片存在
    for idx, path in topic_image_map.items():
        orig = path.replace("_hd.jpg", ".jpg")
        if not os.path.exists(orig):
            log(f"⚠ 缺图: {orig}")
            continue
        if not os.path.exists(path):
            run_cmd([
                "ffmpeg", "-y", "-i", orig,
                "-vf", "scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                "-q:v", "2", path
            ], timeout=30)

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

    # 生成 concat 文件（用 posix 路径 + UTF-8 编码）
    img_concat = BASE / "img_concat_ep3.txt"
    with open(img_concat, "w", encoding="utf-8") as f:
        for topic, start, end in image_segments:
            dur = end - start
            if dur < 0.3:
                continue
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

# ===== Step 5: 烧录字幕（已有则跳过）=====
if OUTPUT_SUB.exists():
    log(f"字幕版已存在: {OUTPUT_SUB}，跳过")
elif not OUTPUT_VIDEO.exists():
    log("⚠ 无字幕版不存在，无法烧录字幕")
else:
    log("=== Step 5: 烧录字幕 ===")
    # 用相对路径避免 Windows 盘符: 问题；逗号用 \, 转义
    rel_srt = "audio/dialogue.srt"
    rel_vid = f"output/新闻大家谈_{EPISODE}_对话版.mp4"
    rel_sub = f"output/新闻大家谈_{EPISODE}_对话版_字幕.mp4"
    style = f"subtitles={rel_srt}:force_style=FontName=SimHei\\,FontSize=18\\,PrimaryColour=&H00FFFFFF\\,OutlineColour=&H40000000\\,BackColour=&H80000000\\,BorderStyle=3\\,Alignment=2\\,Wrap=0\\,ScreenAlignment=2\\,MarginV=40"
    run_cmd([
        "ffmpeg", "-y", "-i", rel_vid,
        "-vf", style,
        "-c:a", "copy", "-pix_fmt", "yuv420p",
        rel_sub
    ], timeout=600, cwd=str(BASE))

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