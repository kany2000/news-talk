#!/usr/bin/env python3
"""News Talk Episode 3 — English version pipeline"""
import sys, os, json, subprocess, time, asyncio
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import shutil
_ffmpeg = shutil.which("ffmpeg")
if _ffmpeg:
    _dir = os.path.dirname(os.path.realpath(_ffmpeg))
    os.environ["PATH"] = _dir + os.pathsep + os.environ.get("PATH", "")

BASE = Path(__file__).resolve().parent
AUDIO_DIR = BASE / "audio"
OUTPUT_DIR = BASE / "output"
AUDIO_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

EPISODE = "第三期"
IMG_DIR = BASE / "images" / EPISODE
OUTPUT_VIDEO = OUTPUT_DIR / f"新闻大家谈_{EPISODE}_EN版.mp4"
OUTPUT_SUB = OUTPUT_DIR / f"新闻大家谈_{EPISODE}_EN版_字幕.mp4"

VOICE_FEMALE = "en-US-JennyNeural"
VOICE_MALE = "en-US-GuyNeural"

def log(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def run_cmd(cmd, timeout=300, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=False, timeout=timeout, cwd=cwd)
    if r.returncode != 0:
        log(f"CMD FAILED: {' '.join(str(c) for c in cmd)}")
        log(f"ERR: {(r.stderr or b'').decode('utf-8', errors='replace')[-300:]}")
        return None
    return (r.stdout or b'').decode('utf-8', errors='replace')

# ===== Step 1: Load dialogue =====
log("=== Step 1: Load English script ===")
dialogue_path = BASE / "scripts" / "对话稿_第三期_en.py"
with open(dialogue_path, "rb") as f:
    code = f.read().decode("utf-8")
ns = {}
exec(code, ns)
SCENE = ns["SCENE"]
log(f"Loaded {len(SCENE)} lines")

# ===== Step 2: Generate audio (edge-tts English) =====
log("=== Step 2: TTS ===")
import edge_tts

combined_mp3 = AUDIO_DIR / "dialogue_combined_en.mp3"
meta_path = AUDIO_DIR / "segments_meta_en.json"

if combined_mp3.exists() and meta_path.exists():
    log(f"Audio exists, skip TTS")
    with open(meta_path) as f:
        segments_meta = json.load(f)
else:
    segments_meta = []
    for i, (speaker, text, topic_idx) in enumerate(SCENE):
        out = AUDIO_DIR / f"seg_en_{i:03d}.mp3"
        voice = VOICE_FEMALE if speaker == "female" else VOICE_MALE
        log(f"TTS [{i+1}/{len(SCENE)}] {speaker}: {text[:30]}...")

        async def synth():
            tts = edge_tts.Communicate(text, voice)
            audio = b""
            async for chunk in tts.stream():
                if chunk["type"] == "audio":
                    audio += chunk["data"]
            return audio
        audio_bytes = asyncio.run(synth())
        if not audio_bytes:
            log(f"TTS FAILED: empty audio")
            sys.exit(1)
        with open(out, "wb") as f:
            f.write(audio_bytes)
        segments_meta.append({
            "idx": i, "speaker": speaker, "text": text,
            "topic_idx": topic_idx, "path": str(out)
        })
        time.sleep(0.3)

    # Duration from ffmpeg
    for s in segments_meta:
        r = subprocess.run(["ffmpeg", "-i", s["path"], "-f", "null", "-"],
            capture_output=True, text=True, timeout=15)
        for line in (r.stderr or "").splitlines():
            if "Duration" in line:
                parts = line.strip().split(",")[0].split("Duration:")[-1].strip()
                h, m, sec = parts.split(":")
                s["duration"] = int(h) * 3600 + int(m) * 60 + float(sec)
                break
        else:
            s["duration"] = 0

    t = 0.0
    for s in segments_meta:
        s["start"] = t
        s["end"] = t + s["duration"]
        t = s["end"]
    total = sum(s["duration"] for s in segments_meta)
    log(f"Total: {total:.1f}s = {total/60:.1f}min")

    with open(meta_path, "w") as f:
        json.dump(segments_meta, f, ensure_ascii=False, indent=2)

    # Concat MP3s
    concat_list = AUDIO_DIR / "concat_en.txt"
    with open(concat_list, "w") as f:
        for s in segments_meta:
            f.write(f"file '{s['path']}'\n")
    combined_wav = AUDIO_DIR / "dialogue_combined_en.wav"
    run_cmd(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(combined_wav)], timeout=120)
    run_cmd(["ffmpeg", "-y", "-i", str(combined_wav),
        "-codec:a", "libmp3lame", "-b:a", "192k", str(combined_mp3)], timeout=120)
    log(f"Audio: {combined_mp3}")

# ===== Step 3: SRT =====
log("=== Step 3: Subtitles ===")
srt_path = AUDIO_DIR / "dialogue_en.srt"
if srt_path.exists():
    log(f"SRT exists, skip")
else:
    srt_lines = []
    for i, s in enumerate(segments_meta, 1):
        def fmt(t):
            h = int(t // 3600); m = int((t % 3600) // 60)
            sec = int(t % 60); ms = int((t - int(t)) * 1000)
            return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
        srt_lines.extend([str(i), f"{fmt(s['start'])} --> {fmt(s['end'])}", s["text"], ""])
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    log(f"SRT: {srt_path} ({len(segments_meta)} entries)")

# ===== Step 4: Compose video =====
log("=== Step 4: Compose video ===")
if OUTPUT_VIDEO.exists():
    log(f"Video exists, skip")
else:
    topic_image_map = {
        0: str(IMG_DIR / "intro_hd.jpg"),
        1: str(IMG_DIR / "01_hd.jpg"), 2: str(IMG_DIR / "02_hd.jpg"),
        3: str(IMG_DIR / "03_hd.jpg"), 4: str(IMG_DIR / "04_hd.jpg"),
        5: str(IMG_DIR / "05_hd.jpg"), 6: str(IMG_DIR / "06_hd.jpg"),
        7: str(IMG_DIR / "07_hd.jpg"), 8: str(IMG_DIR / "outro_hd.jpg"),
    }
    for idx, path in topic_image_map.items():
        orig = path.replace("_hd.jpg", ".jpg")
        if not os.path.exists(orig):
            continue
        if not os.path.exists(path):
            run_cmd(["ffmpeg", "-y", "-i", orig,
                "-vf", "scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                "-q:v", "2", path], timeout=30)

    image_segments = []
    ct = None; cs = None
    for s in segments_meta:
        t = s["topic_idx"]
        if t != ct:
            if ct is not None:
                image_segments.append((ct, cs, s["start"]))
            ct = t; cs = s["start"]
    if ct is not None:
        image_segments.append((ct, cs, segments_meta[-1]["end"]))

    img_concat = BASE / "img_concat_en.txt"
    with open(img_concat, "w", encoding="utf-8") as f:
        for topic, start, end in image_segments:
            dur = end - start
            if dur < 0.3: continue
            img = topic_image_map.get(topic, "")
            if not os.path.exists(img): continue
            f.write(f"file '{img}'\nduration {dur:.3f}\n")

    log("Composing video...")
    run_cmd(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(img_concat), "-i", str(combined_mp3),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "24",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(OUTPUT_VIDEO)], timeout=600)
    if OUTPUT_VIDEO.exists():
        log(f"Video: {OUTPUT_VIDEO.stat().st_size/1024/1024:.1f}MB")
    else:
        log("Video failed"); sys.exit(1)

# ===== Step 5: Burn subtitles =====
log("=== Step 5: Burn subtitles ===")
if OUTPUT_SUB.exists():
    log(f"Subtitled version exists, skip")
elif not OUTPUT_VIDEO.exists():
    log("No source video")
else:
    rel_srt = "audio/dialogue_en.srt"
    rel_vid = f"output/新闻大家谈_{EPISODE}_EN版.mp4"
    rel_sub = f"output/新闻大家谈_{EPISODE}_EN版_字幕.mp4"
    style = f"subtitles={rel_srt}:force_style=FontName=SimHei\\,FontSize=18\\,PrimaryColour=&H00FFFFFF\\,OutlineColour=&H40000000\\,BackColour=&H80000000\\,BorderStyle=3\\,Alignment=2\\,Wrap=0\\,ScreenAlignment=2\\,MarginV=40"
    run_cmd(["ffmpeg", "-y", "-i", rel_vid, "-vf", style,
        "-c:a", "copy", "-pix_fmt", "yuv420p", rel_sub],
        timeout=600, cwd=str(BASE))
    if OUTPUT_SUB.exists():
        log(f"Subtitled: {OUTPUT_SUB.stat().st_size/1024/1024:.1f}MB")
    else:
        log("Subtitle burn failed")

log("\nDone!")
for p in [combined_mp3, OUTPUT_VIDEO, OUTPUT_SUB]:
    if p.exists():
        log(f"  {p.name} ({p.stat().st_size/1024/1024:.1f}MB)")