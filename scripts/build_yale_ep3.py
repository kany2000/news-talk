#!/usr/bin/env python3
"""耶鲁公开课系列·第三期「集体恐慌 L5.6.7」— 中文语音版合成
流程：中文对话稿 → edge-tts 男女声分段 TTS → ffprobe 精准时长 → 精准 SRT →
      按 topic_idx 切图 concat → ffmpeg 合成 16:9 视频 → 烧录字幕"""
import sys, os, json, subprocess, time, asyncio
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
os.environ["PYTHONIOENCODING"] = "utf-8"

import shutil
_ffmpeg = shutil.which("ffmpeg")
if _ffmpeg:
    _dir = os.path.dirname(os.path.realpath(_ffmpeg))
    os.environ["PATH"] = _dir + os.pathsep + os.environ.get("PATH", "")

BASE = Path(r"E:\projects\news-talk")
EP_DIR = BASE / "yale大学公开课系列讲谈" / "第三期"
AUDIO_DIR = EP_DIR / "audio"
IMG_DIR = EP_DIR / "images"
OUTPUT_DIR = EP_DIR / "output"
AUDIO_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_FEMALE = "xiaoxiao"
VOICE_MALE = "yunyang"
OUTPUT_VIDEO = OUTPUT_DIR / "耶鲁博弈论_集体恐慌_v5.mp4"
OUTPUT_SUB = OUTPUT_DIR / "耶鲁博弈论_集体恐慌_v5_字幕版.mp4"

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{time.strftime('%H:%M:%S')}] {msg.encode('utf-8','replace').decode('gbk','replace')}", flush=True)

def run_cmd(cmd, timeout=300, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=False, timeout=timeout, cwd=cwd)
    if r.returncode != 0:
        log(f"CMD FAILED: {' '.join(str(c) for c in cmd)}")
        log(f"ERR: {(r.stderr or b'').decode('utf-8', errors='replace')[-300:]}")
        return None
    return (r.stdout or b'').decode('utf-8', errors='replace')

# ===== Step 1: 加载中文对话稿 =====
log("=== Step 1: 加载中文对话稿 ===")
dialogue_path = BASE / "scripts" / "对话稿_第三期_yale.py"
with open(dialogue_path, "rb") as f:
    code = f.read().decode("utf-8")
ns = {}
exec(code, ns)
SCENE = ns["SCENE"]
log(f"Loaded {len(SCENE)} lines (topic_idx 0~15)")

# ===== Step 2: MiMo TTS 中文合成 =====
log("=== Step 2: TTS (MiMo mimo-v2.5-tts) ===")
import json as _json, base64 as _b64, urllib.request as _urlreq, wave as _wave

# 加载 .env
for _line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip())
MIMO_KEY = os.environ.get("MIMO_TTS_API_KEY", "")
MIMO_URL = "https://api.xiaomimimo.com/v1/chat/completions"
VOICE_MAP = {"female": "xiaoxiao", "male": "yunyang"}
STYLE_MAP = {"female": "温柔专业的女声，播报内容，语速适中", "male": "沉稳专业的男声，播报内容，语速适中"}

def mimo_synth(text, voice, timeout=120, retries=3):
    payload = _json.dumps({
        "model": "mimo-v2.5-tts",
        "messages": [
            {"role": "user", "content": STYLE_MAP[voice]},
            {"role": "assistant", "content": text},
        ],
        "voice_id": VOICE_MAP[voice],
    }).encode()
    for attempt in range(retries):
        try:
            req = _urlreq.Request(MIMO_URL, data=payload,
                headers={"api-key": MIMO_KEY, "Content-Type": "application/json"}, method="POST")
            with _urlreq.urlopen(req, timeout=timeout) as r:
                resp = _json.loads(r.read())
            audio_b64 = resp.get("choices", [{}])[0].get("message", {}).get("audio", {}).get("data", "")
            if not audio_b64:
                raise Exception("no audio data in response")
            return _b64.b64decode(audio_b64)
        except Exception as e:
            log(f"  mimo retry {attempt+1}: {str(e)[:80]}")
            time.sleep(3)
    raise Exception("mimo all retries failed")

def pcm_to_wav(pcm_bytes, path, rate=24000):
    with _wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm_bytes)

combined_mp3 = AUDIO_DIR / "dialogue_zh.mp3"
meta_path = AUDIO_DIR / "segments_meta_zh.json"

if meta_path.exists():
    log("元数据已存在，跳过 TTS（复用已合成音频）")
    with open(meta_path, encoding="utf-8") as f:
        segments_meta = json.load(f)
else:
    segments_meta = []
    for i, (speaker, text, topic_idx) in enumerate(SCENE):
        out = AUDIO_DIR / f"seg_zh_{i:03d}.mp3"
        log(f"TTS [{i+1}/{len(SCENE)}] {speaker}: {text[:26]}...")
        pcm = mimo_synth(text, speaker)
        wav_tmp = AUDIO_DIR / f"seg_zh_{i:03d}.wav"
        pcm_to_wav(pcm, wav_tmp)
        r = subprocess.run(["ffmpeg", "-y", "-i", str(wav_tmp), "-codec:a", "libmp3lame", "-b:a", "192k", str(out)],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0 or not out.exists():
            log(f"WAV→MP3 FAILED line {i}")
            sys.exit(1)
        # 沙箱禁止 unlink，临时 wav 保留在 audio 目录（命名 seg_zh_*.wav，最后统一清理）
        segments_meta.append({
            "idx": i, "speaker": speaker, "text": text,
            "topic_idx": topic_idx, "path": str(out)
        })
        time.sleep(0.5)

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

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(segments_meta, f, ensure_ascii=False, indent=2)

# ===== 中间产物工作区（纯 ASCII 路径，绕开 ffmpeg concat 中文路径编码问题）=====
WORK_DIR = BASE / "ep3_work"
_WA = WORK_DIR / "audio"
_WI = WORK_DIR / "img"
_WA.mkdir(parents=True, exist_ok=True)
_WI.mkdir(parents=True, exist_ok=True)

# Concat MP3s（segments_meta 的 path 已指向 ASCII 工作区文件）
if not combined_mp3.exists():
    concat_list = WORK_DIR / "concat_audio.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for s in segments_meta:
            f.write(f"file '{s['path']}'\n")
    combined_wav = WORK_DIR / "dialogue.wav"
    run_cmd(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(combined_wav)], timeout=180)
    run_cmd(["ffmpeg", "-y", "-i", str(combined_wav),
        "-codec:a", "libmp3lame", "-b:a", "192k", str(combined_mp3)], timeout=180)
    log(f"Audio: {combined_mp3}")
else:
    log(f"合并音频已存在: {combined_mp3}")

# ===== Step 3: 精准 SRT =====
log("=== Step 3: 精准字幕 ===")
srt_path = AUDIO_DIR / "subtitles_zh.srt"
if srt_path.exists():
    log("SRT 已存在，跳过")
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

# ===== Step 4: 合成视频 =====
log("=== Step 4: 合成视频 ===")
# 图片已由配图脚本输出为 1920x1080，直接复制到 ASCII 工作区
topic_image_map = {
    0: str(_WI / "intro.jpg"),
    1: str(_WI / "01.jpg"), 2: str(_WI / "02.jpg"),
    3: str(_WI / "03.jpg"), 4: str(_WI / "04.jpg"),
    5: str(_WI / "05.jpg"), 6: str(_WI / "06.jpg"),
    7: str(_WI / "07.jpg"), 8: str(_WI / "08.jpg"),
    9: str(_WI / "09.jpg"), 10: str(_WI / "10.jpg"),
    11: str(_WI / "11.jpg"), 12: str(_WI / "12.jpg"),
    13: str(_WI / "13.jpg"), 14: str(_WI / "14.jpg"),
    15: str(_WI / "outro.jpg"),
}
img_src_names = {
    0: "intro.jpg", 1: "01.jpg", 2: "02.jpg", 3: "03.jpg", 4: "04.jpg",
    5: "05.jpg", 6: "06.jpg", 7: "07.jpg", 8: "08.jpg", 9: "09.jpg",
    10: "10.jpg", 11: "11.jpg", 12: "12.jpg", 13: "13.jpg", 14: "14.jpg",
    15: "outro.jpg",
}
for idx, name in img_src_names.items():
    orig = IMG_DIR / name
    dst = _WI / name
    if orig.exists():
        shutil.copy2(orig, dst)  # 每次强制覆盖，保证用最新（去水印/重做）配图
    if not dst.exists():
        log(f"[WARN] 缺图: {orig}")

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

log("Composing video...")
if not OUTPUT_VIDEO.exists():
    ok = run_cmd(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(img_concat), "-i", str(combined_mp3),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "24",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        "-t", f"{segments_meta[-1]['end']:.3f}",
        str(OUTPUT_VIDEO)], timeout=900)
    if OUTPUT_VIDEO.exists():
        log(f"Video: {OUTPUT_VIDEO.stat().st_size/1024/1024:.1f}MB")
    else:
        log("Video failed"); sys.exit(1)
else:
    log(f"视频已存在: {OUTPUT_VIDEO}")

# ===== Step 5: 烧录字幕 =====
log("=== Step 5: 烧录字幕 ===")
if OUTPUT_SUB.exists():
    log(f"字幕版已存在: {OUTPUT_SUB}")
else:
    import shutil as _sh
    SRT_TEMP = Path("yale_sub_temp_zh.srt")
    _sh.copy2(str(srt_path), str(SRT_TEMP))
    vf = f"subtitles={SRT_TEMP}:force_style='FontName=SimHei,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'"
    ok = run_cmd(["ffmpeg", "-y", "-i", str(OUTPUT_VIDEO),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        str(OUTPUT_SUB)], timeout=900)
    try:
        if SRT_TEMP.exists():
            SRT_TEMP.unlink()
    except Exception:
        pass  # 沙箱回收站不可用时忽略临时文件清理失败
    if OUTPUT_SUB.exists():
        log(f"Subtitled: {OUTPUT_SUB.stat().st_size/1024/1024:.1f}MB")
    else:
        log("Subtitle burn failed, no-sub version available")

log("\nDone!")
for p in [combined_mp3, srt_path, OUTPUT_VIDEO, OUTPUT_SUB]:
    if p.exists():
        log(f"  {p.name} ({p.stat().st_size/1024/1024:.1f}MB)")
