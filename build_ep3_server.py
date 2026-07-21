#!/usr/bin/env python3
"""新闻大家谈 第三期 — 服务器端管线"""
import sys, os, json, subprocess, time, math
sys.path.insert(0, '/home/kan/signal_pop/src')
from tts_mimo import synthesize, get_ffmpeg_path

BASE = '/home/kan/shared/news-talk'
AUDIO_DIR = f'{BASE}/audio'
IMG_DIR = f'{BASE}/images'
OUTPUT_DIR = f'{BASE}/output'
EPISODE = '第三期'
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

ffmpeg = get_ffmpeg_path()
ffprobe = 'ffprobe'

def log(msg): print(f'[{time.strftime("%H:%M:%S")}] {msg}')
def run(cmd, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        log(f'CMD FAILED: {r.stderr[-300:]}')
        return None
    return r.stdout

# ===== Load dialogue =====
sys.path.insert(0, f'{BASE}/scripts')
from 对话稿_第三期 import SCENE
log(f'对话稿: {len(SCENE)} 段')

# ===== Step 1: Generate audio =====
log('=== Step 1: MiMo TTS ===')
segments_meta = []
for i, (speaker, text, topic_idx) in enumerate(SCENE):
    out = f'{AUDIO_DIR}/seg_{i:03d}.wav'
    voice = 'female' if speaker == 'female' else 'male'
    log(f'TTS [{i+1}/{len(SCENE)}] {voice}: {text[:30]}...')
    try:
        synthesize(text, voice_gender=voice, output_path=out)
        segments_meta.append({'idx': i, 'speaker': speaker, 'text': text, 'topic_idx': topic_idx, 'path': out})
        time.sleep(0.5)
    except Exception as e:
        log(f'TTS FAILED: {e}')
        sys.exit(1)

for s in segments_meta:
    r = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', s['path']], capture_output=True, text=True, timeout=10)
    s['duration'] = float(r.stdout.strip()) if r.returncode == 0 else 0

t = 0.0
for s in segments_meta:
    s['start'] = t
    s['end'] = t + s['duration']
    t = s['end']

total = sum(s['duration'] for s in segments_meta)
log(f'总时长: {total:.1f}s = {total/60:.1f}min')

meta_path = f'{AUDIO_DIR}/segments_meta.json'
with open(meta_path, 'w') as f:
    json.dump(segments_meta, f, ensure_ascii=False, indent=2)

concat_list = f'{AUDIO_DIR}/concat.txt'
with open(concat_list, 'w') as f:
    for s in segments_meta:
        f.write(f"file '{s['path']}'\n")

combined_wav = f'{AUDIO_DIR}/dialogue_combined.wav'
run([ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', concat_list, '-c', 'copy', combined_wav])
combined_mp3 = f'{AUDIO_DIR}/dialogue_combined.mp3'
run([ffmpeg, '-y', '-i', combined_wav, '-codec:a', 'libmp3lame', '-b:a', '192k', combined_mp3])
log(f'音频: {combined_mp3}')

# ===== Step 2: SRT =====
log('=== Step 2: SRT ===')
srt_lines = []
for i, s in enumerate(segments_meta, 1):
    def fmt(t):
        h = int(t // 3600); m = int((t % 3600) // 60)
        sec = int(t % 60); ms = int((t - int(t)) * 1000)
        return f'{h:02d}:{m:02d}:{sec:02d},{ms:03d}'
    srt_lines.extend([str(i), f"{fmt(s['start'])} --> {fmt(s['end'])}", s['text'], ''])
srt_path = f'{AUDIO_DIR}/dialogue.srt'
with open(srt_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(srt_lines))
log(f'SRT: {srt_path} ({len(segments_meta)} 条)')

# ===== Step 3: Compose video =====
log('=== Step 3: 合成视频 ===')
topic_image_map = {
    0: f'{IMG_DIR}/intro.jpg', 1: f'{IMG_DIR}/01.jpg',
    2: f'{IMG_DIR}/02.jpg', 3: f'{IMG_DIR}/03.jpg',
    4: f'{IMG_DIR}/04.jpg', 5: f'{IMG_DIR}/05.jpg',
    6: f'{IMG_DIR}/06.jpg', 7: f'{IMG_DIR}/07.jpg',
    8: f'{IMG_DIR}/outro.jpg',
}

image_segments = []
current_topic = None; current_start = None
for s in segments_meta:
    t = s['topic_idx']
    if t != current_topic:
        if current_topic is not None:
            image_segments.append((current_topic, current_start, s['start']))
        current_topic = t; current_start = s['start']
if current_topic is not None:
    image_segments.append((current_topic, current_start, segments_meta[-1]['end']))

for idx, path in topic_image_map.items():
    if not os.path.exists(path): continue
    hd = path.replace('.jpg', '_hd.jpg')
    if not os.path.exists(hd):
        run([ffmpeg, '-y', '-i', path,
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
            '-q:v', '2', hd], timeout=30)

img_concat = f'{BASE}/img_concat_ep3.txt'
with open(img_concat, 'w') as f:
    for topic, start, end in image_segments:
        dur = end - start
        if dur < 0.3: continue
        img = topic_image_map.get(topic, '').replace('.jpg', '_hd.jpg')
        if not os.path.exists(img):
            img = topic_image_map.get(topic, '')
        if not os.path.exists(img): continue
        f.write(f"file '{img}'\nduration {dur:.3f}\n")

final = f'{OUTPUT_DIR}/新闻大家谈_{EPISODE}_对话版.mp4'
run([ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', img_concat,
    '-i', combined_mp3, '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
    '-pix_fmt', 'yuv420p', '-r', '24', '-c:a', 'aac', '-b:a', '192k',
    '-shortest', final], timeout=600)

if os.path.exists(final):
    log(f'✅ 无字幕版: {os.path.getsize(final)/1024/1024:.1f}MB')
else:
    log('❌ 合成失败'); sys.exit(1)

final_sub = final.replace('.mp4', '_字幕.mp4')
run([ffmpeg, '-y', '-i', final,
    '-vf', f"subtitles={srt_path}:force_style='FontName=Noto Sans CJK SC,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'",
    '-c:a', 'copy', '-pix_fmt', 'yuv420p', final_sub], timeout=600)

if os.path.exists(final_sub):
    log(f'✅ 字幕版: {os.path.getsize(final_sub)/1024/1024:.1f}MB')

log('\n完成!')
for p in [combined_mp3, final, final_sub]:
    if os.path.exists(p):
        log(f'  {p} ({os.path.getsize(p)/1024/1024:.1f}MB)')