#!/usr/bin/env python3
"""耶鲁公开课系列·第四期「为什么包容的人最终走向隔离 L8.9.10」— 中文语音版合成
TTS 引擎：豆包语音（火山引擎 seed-tts-2.0）—— 女声=爽快思思 / 男声=云舟（2026-08-16 用户选定）
流程：中文对话稿 → 豆包 TTS 分段 → mp3→wav → PCM 拼接(20ms 淡入淡出防爆音) → 精准 SRT → 合成+烧字幕
字幕：FontSize=16（2026-08-12 用户要求改小）"""
import sys, os, json, subprocess, time, wave
import numpy as np
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE = Path(r"E:\projects\news-talk")
EP_DIR = BASE / "yale大学公开课系列讲谈" / "第四期"
AUDIO_DIR = EP_DIR / "audio"
IMG_DIR = EP_DIR / "images"
OUTPUT_DIR = EP_DIR / "output"
AUDIO_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ffmpeg：signal_pop 自带 9.0.1
FFMPEG = r"E:\projects\signal_pop\bin\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
FFPROBE = r"E:\projects\signal_pop\bin\ffmpeg-9.0.1-essentials_build\bin\ffprobe.exe"
os.environ["PATH"] = str(Path(FFMPEG).parent) + os.pathsep + os.environ.get("PATH", "")

# 豆包凭据（读 signal_pop/.env）
for _line in (Path(r"E:\projects\signal_pop") / ".env").read_text(encoding="utf-8").splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip())

VOICE_FEMALE = "zh_female_shuangkuaisisi_uranus_bigtts"  # 爽快思思（女声）✅用户选定
VOICE_MALE = "zh_male_m191_uranus_bigtts"                # 云舟（男声）✅用户选定
OUTPUT_VIDEO = OUTPUT_DIR / "耶鲁博弈论_隔离_v2.mp4"
OUTPUT_SUB = OUTPUT_DIR / "耶鲁博弈论_隔离_v2_字幕版.mp4"

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{time.strftime('%H:%M:%S')}] {msg.encode('utf-8','replace').decode('gbk','replace')}", flush=True)

def run_cmd(cmd, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=False, timeout=timeout)
    if r.returncode != 0:
        log(f"CMD FAILED: {' '.join(str(c) for c in cmd)}")
        log(f"ERR: {(r.stderr or b'').decode('utf-8', errors='replace')[-300:]}")
        return None
    return (r.stdout or b'').decode('utf-8', errors='replace')

# ===== Step 1: 加载中文对话稿 =====
log("=== Step 1: 加载中文对话稿 ===")
dialogue_path = BASE / "scripts" / "对话稿_第四期_yale.py"
with open(dialogue_path, "rb") as f:
    code = f.read().decode("utf-8")
ns = {}
exec(code, ns)
SCENE = ns["SCENE"]
log(f"Loaded {len(SCENE)} lines")

# ===== Step 2: 豆包 TTS =====
log("=== Step 2: TTS (豆包 seed-tts-2.0) ===")
import base64 as _b64
import urllib.request as _urlreq

DOUBAO_APP_ID = os.environ.get("DOUBAO_APP_ID", "")
DOUBAO_TOKEN = os.environ.get("DOUBAO_ACCESS_TOKEN", "")
VOLC_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

def volc_synth(text, voice, out_mp3, timeout=120, retries=3):
    if not (DOUBAO_APP_ID and DOUBAO_TOKEN):
        raise RuntimeError("未配置 DOUBAO_APP_ID/DOUBAO_ACCESS_TOKEN（signal_pop/.env）")
    payload = json.dumps({
        "user": {"uid": f"news_talk_ep4_{int(time.time())}"},
        "req_params": {
            "text": text,
            "speaker": voice,
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "audio_params": {"format": "mp3", "sample_rate": 24000},
        },
    }).encode()
    for attempt in range(retries):
        try:
            req = _urlreq.Request(VOLC_URL, data=payload, headers={
                "Content-Type": "application/json",
                "X-Api-App-Id": DOUBAO_APP_ID,
                "X-Api-Access-Key": DOUBAO_TOKEN,
                "X-Api-Resource-Id": "seed-tts-2.0",
                "Connection": "keep-alive",
            }, method="POST")
            with _urlreq.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8", errors="replace")
            audio = bytearray()
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                code = obj.get("code")
                if code == 0 and obj.get("data"):
                    audio.extend(_b64.b64decode(obj["data"]))
                elif code != 0 and code != 20000000:
                    raise RuntimeError(f"豆包错误 code={code}: {obj.get('message','')}")
            if not audio:
                raise Exception("empty audio")
            with open(out_mp3, "wb") as f:
                f.write(bytes(audio))
            return out_mp3
        except Exception as e:
            log(f"  doubao retry {attempt+1}: {str(e)[:80]}")
            time.sleep(3)
    raise RuntimeError("doubao all retries failed")

combined_mp3 = AUDIO_DIR / "dialogue_zh.mp3"
meta_path = AUDIO_DIR / "segments_meta_zh.json"
WORK_DIR = BASE / "ep4_work"
_WA = WORK_DIR / "audio"
_WI = WORK_DIR / "img"
_WA.mkdir(parents=True, exist_ok=True)
_WI.mkdir(parents=True, exist_ok=True)

if meta_path.exists():
    log("元数据已存在，跳过 TTS")
    with open(meta_path, encoding="utf-8") as f:
        segments_meta = json.load(f)
else:
    segments_meta = []
    for i, (speaker, text, topic_idx) in enumerate(SCENE):
        voice = VOICE_FEMALE if speaker == "female" else VOICE_MALE
        mp3 = _WA / ("seg_%03d.mp3" % i)
        log(f"TTS [{i+1}/{len(SCENE)}] {speaker}: {text[:24]}...")
        volc_synth(text, voice, str(mp3))
        wav = _WA / ("seg_%03d.wav" % i)
        run_cmd([FFMPEG, "-y", "-i", str(mp3), "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1", str(wav)], timeout=60)
        # 时长（wav 精确）
        with wave.open(str(wav), "rb") as w:
            dur = w.getnframes() / w.getframerate()
        segments_meta.append({
            "idx": i, "speaker": speaker, "text": text,
            "topic_idx": topic_idx, "path": str(wav), "duration": dur
        })
        time.sleep(0.3)

    t = 0.0
    for s in segments_meta:
        s["start"] = t
        s["end"] = t + s["duration"]
        t = s["end"]
    log(f"Total: {t:.1f}s = {t/60:.1f}min")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(segments_meta, f, ensure_ascii=False, indent=2)

# ===== Step 3: PCM 拼接（20ms 淡入淡出防爆音）=====
if not combined_mp3.exists():
    FADE = 480  # 20ms @ 24kHz
    fade_in = np.linspace(0, 1, FADE, dtype=np.float64)
    fade_out = np.linspace(1, 0, FADE, dtype=np.float64)
    chunks = []
    for s in segments_meta:
        with wave.open(str(Path(s["path"])), "rb") as w:
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
        n = len(data)
        if n > FADE * 2:
            data[:FADE] *= fade_in
            data[-FADE:] *= fade_out
        else:
            data *= 0.5
        chunks.append(data)
    merged = np.concatenate(chunks)
    merged = np.clip(merged, -32767, 32767).astype(np.int16)
    full_wav = WORK_DIR / "dialogue_full.wav"
    with wave.open(str(full_wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(merged.tobytes())
    run_cmd([FFMPEG, "-y", "-i", str(full_wav), "-codec:a", "libmp3lame", "-b:a", "192k", str(combined_mp3)], timeout=180)
    log(f"Audio: {combined_mp3}")
else:
    log(f"合并音频已存在: {combined_mp3}")

# ===== Step 4: 精准 SRT =====
log("=== Step 4: 精准字幕 (FontSize=16) ===")
srt_path = AUDIO_DIR / "subtitles_zh.srt"
if not srt_path.exists():
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
else:
    log(f"SRT 已存在")

# ===== Step 5: 合成视频 =====
log("=== Step 5: 合成视频 ===")
img_src_names = {0: "intro.jpg", 1: "01.jpg", 2: "02.jpg", 3: "03.jpg", 4: "04.jpg",
                 5: "05.jpg", 6: "06.jpg", 7: "07.jpg", 8: "08.jpg", 9: "09.jpg",
                 10: "10.jpg", 11: "11.jpg", 12: "12.jpg", 13: "13.jpg", 14: "14.jpg",
                 15: "outro.jpg"}
topic_image_map = {}
for idx, name in img_src_names.items():
    orig = IMG_DIR / name
    dst = _WI / name
    if orig.exists():
        run_cmd([FFMPEG, "-y", "-i", str(orig),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-q:v", "2", str(dst)], timeout=30)
    else:
        log(f"[WARN] 缺图: {orig}")
    topic_image_map[idx] = str(dst)

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

img_concat = WORK_DIR / "concat_img.txt"
with open(img_concat, "w", encoding="utf-8") as f:
    for topic, start, end in image_segments:
        dur = end - start
        if dur < 0.3: continue
        img = topic_image_map.get(topic, "")
        if not os.path.exists(img): continue
        f.write(f"file '{img}'\nduration {dur:.3f}\n")

if not OUTPUT_VIDEO.exists():
    log("Composing video...")
    audio_total = segments_meta[-1]["end"]
    ok = run_cmd([FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", str(img_concat), "-i", str(combined_mp3),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "24",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        "-t", f"{audio_total:.3f}",
        str(OUTPUT_VIDEO)], timeout=900)
    if OUTPUT_VIDEO.exists():
        log(f"Video: {OUTPUT_VIDEO.stat().st_size/1024/1024:.1f}MB")
    else:
        log("Video failed"); sys.exit(1)
else:
    log(f"视频已存在: {OUTPUT_VIDEO}")

# ===== Step 6: 烧录字幕（FontSize=16）=====
log("=== Step 6: 烧录字幕 ===")
if OUTPUT_SUB.exists():
    log(f"字幕版已存在: {OUTPUT_SUB}")
else:
    import shutil as _sh
    SRT_TEMP = Path("yale_sub_temp_ep4.srt")  # 相对路径：subtitles filter 不支持盘符/反斜杠
    _sh.copy2(str(srt_path), str(SRT_TEMP))
    vf = f"subtitles={SRT_TEMP}:force_style='FontName=SimHei,FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'"
    ok = run_cmd([FFMPEG, "-y", "-i", str(OUTPUT_VIDEO),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        str(OUTPUT_SUB)], timeout=900)
    try:
        if SRT_TEMP.exists():
            SRT_TEMP.unlink()
    except Exception:
        pass
    if OUTPUT_SUB.exists():
        log(f"Subtitled: {OUTPUT_SUB.stat().st_size/1024/1024:.1f}MB")
    else:
        log("Subtitle burn failed, no-sub version available")

log("\nDone!")
for p in [combined_mp3, srt_path, OUTPUT_VIDEO, OUTPUT_SUB]:
    if p.exists():
        log(f"  {p.name} ({p.stat().st_size/1024/1024:.1f}MB)")
