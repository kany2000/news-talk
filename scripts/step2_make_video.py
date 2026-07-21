#!/usr/bin/env python3
"""Step 2-4: SRT + image timing + FFmpeg compose"""
import sys, os, json, subprocess, math

AUDIO_DIR = '/home/kan/shared/news-talk/audio'
IMG_DIR = '/home/kan/shared/news-talk/images'
OUTPUT_DIR = '/home/kan/shared/news-talk/output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

ffmpeg = 'ffmpeg'
ffprobe = 'ffprobe'

# Load segment metadata
with open(f'{AUDIO_DIR}/segments_meta.json') as f:
    segments = json.load(f)

# ===== Step 2: Generate SRT =====
# Each segment = 1 subtitle entry (accurate timing from WAV files)
srt_lines = []
for i, s in enumerate(segments, 1):
    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        sec = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
    speaker_tag = "👩" if s['speaker'] == 'female' else "👨"
    srt_lines.append(str(i))
    srt_lines.append(f"{fmt(s['start'])} --> {fmt(s['end'])}")
    srt_lines.append(f"{speaker_tag} {s['text']}")
    srt_lines.append("")

srt_path = f'{AUDIO_DIR}/dialogue.srt'
with open(srt_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(srt_lines))
print(f"SRT: {srt_path} ({len(segments)} entries)")

# ===== Step 3: Image timing =====
# Map topic_idx → image file
topic_image_map = {
    0: f'{IMG_DIR}/intro.jpg',
    1: f'{IMG_DIR}/01.jpg',
    2: f'{IMG_DIR}/02.jpg',
    3: f'{IMG_DIR}/03.jpg',
    4: f'{IMG_DIR}/04.jpg',
    5: f'{IMG_DIR}/05.jpg',
    6: f'{IMG_DIR}/06.jpg',
    7: f'{IMG_DIR}/07.jpg',
    8: f'{IMG_DIR}/outro.jpg',
}

# Build image segments (merge consecutive same-topic_idx)
image_segments = []
current_topic = None
current_start = None
current_end = None

for s in segments:
    t = s['topic_idx']
    if t != current_topic:
        if current_topic is not None:
            image_segments.append((current_topic, current_start, s['start']))
        current_topic = t
        current_start = s['start']
    current_end = s['end']

# Last segment
if current_topic is not None:
    image_segments.append((current_topic, current_start, current_end))

print(f"\n图像段落 ({len(image_segments)} 段):")
total_dur = 0
for topic, start, end in image_segments:
    dur = end - start
    total_dur += dur
    img = os.path.basename(topic_image_map.get(topic, ''))
    print(f"  {start:7.1f}s → {end:7.1f}s ({dur:5.1f}s) topic={topic} img={img}")

print(f"  总视频时长: {total_dur:.1f}s")

# ===== Step 4: Compose video =====
# Ensure images are 1920x1080
for idx, path in topic_image_map.items():
    if not os.path.exists(path):
        print(f"⚠ Image missing: {path}")
        continue
    hd = path.replace('.jpg', '_hd.jpg')
    if not os.path.exists(hd):
        subprocess.run([ffmpeg, '-y', '-i', path,
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
            '-q:v', '2', hd], capture_output=True, timeout=30)

# Generate image videos for each segment with exact duration
parts = []
for i, (topic, start, end) in enumerate(image_segments):
    dur = end - start
    if dur < 0.5:
        continue
    img_hd = topic_image_map.get(topic, '').replace('.jpg', '_hd.jpg')
    if not os.path.exists(img_hd):
        print(f"⚠ HD image missing: {img_hd}, fallback to original")
        img_hd = topic_image_map.get(topic, '')
    if not os.path.exists(img_hd):
        print(f"⚠ Image {img_hd} not found")
        continue
    out = f'/tmp/vpart_{i:03d}.mp4'
    duration_str = f"{dur:.3f}"
    r = subprocess.run([ffmpeg, '-y',
        '-loop', '1', '-i', img_hd,
        '-c:v', 'libx264', '-t', duration_str,
        '-pix_fmt', 'yuv420p', '-r', '24',
        '-preset', 'fast', '-crf', '23',
        '-vf', 'scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
        out], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"  FAIL part {i}: {r.stderr[-200:]}")
        continue
    parts.append(out)
    print(f"  part {i}: {dur:.1f}s")

if not parts:
    print("❌ No video parts generated")
    sys.exit(1)

# Concat all parts
concat_file = '/tmp/vconcat.txt'
with open(concat_file, 'w') as f:
    for p in parts:
        f.write(f"file '{p}'\n")

video_noaud = '/tmp/video_noaudio.mp4'
subprocess.run([ffmpeg, '-y', '-f', 'concat', '-safe', '0',
    '-i', concat_file,
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
    '-pix_fmt', 'yuv420p', video_noaud],
    capture_output=True, timeout=120)

# Add audio
mp3_path = f'{AUDIO_DIR}/dialogue_combined.mp3'
final = f'{OUTPUT_DIR}/新闻大家谈_第二期_对话版.mp4'
subprocess.run([ffmpeg, '-y',
    '-i', video_noaud, '-i', mp3_path,
    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
    '-shortest', final],
    capture_output=True, timeout=120)

# Burn subtitles
final_sub = f'{OUTPUT_DIR}/新闻大家谈_第二期_对话版_字幕.mp4'
subprocess.run([ffmpeg, '-y',
    '-i', final,
    '-vf', f"subtitles={srt_path}:force_style='FontName=Noto Sans CJK SC,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'",
    '-c:a', 'copy',
    '-pix_fmt', 'yuv420p',
    final_sub],
    capture_output=True, timeout=600)

print(f"\n✅ 完成!")
for fpath, label in [(final, '无字幕'), (final_sub, '字幕')]:
    sz = os.path.getsize(fpath) / 1024 / 1024
    print(f"  {label}: {os.path.basename(fpath)} ({sz:.1f}MB)")

# Cleanup
for p in parts:
    try: os.unlink(p)
    except: pass
try: os.unlink(video_noaud)
except: pass