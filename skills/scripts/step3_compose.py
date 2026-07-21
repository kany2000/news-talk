#!/usr/bin/env python3
"""Step 4 (fixed): Direct FFmpeg compose — new outro image + subtitle width fix"""
import os, json, subprocess

AUDIO_DIR = '/home/kan/shared/news-talk/audio'
IMG_DIR = '/home/kan/shared/news-talk/images'
OUTPUT_DIR = '/home/kan/shared/news-talk/output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

ffmpeg = 'ffmpeg'

with open(f'{AUDIO_DIR}/segments_meta.json') as f:
    segments = json.load(f)

# topic_idx → image (outro now uses outro_text.jpg)
topic_image_map = {
    0: f'{IMG_DIR}/intro.jpg',
    1: f'{IMG_DIR}/01.jpg',
    2: f'{IMG_DIR}/02.jpg',
    3: f'{IMG_DIR}/03.jpg',
    4: f'{IMG_DIR}/04.jpg',
    5: f'{IMG_DIR}/05.jpg',
    6: f'{IMG_DIR}/06.jpg',
    7: f'{IMG_DIR}/07.jpg',
    8: f'{IMG_DIR}/outro_text.jpg',  # ← 改为话题列表图
}

# Build image segments (merge consecutive same topic)
image_segments = []
current_topic = None
current_start = None
for s in segments:
    t = s['topic_idx']
    if t != current_topic:
        if current_topic is not None:
            image_segments.append((current_topic, current_start, s['start']))
        current_topic = t
        current_start = s['start']
if current_topic is not None:
    image_segments.append((current_topic, current_start, segments[-1]['end']))

# Ensure HD resized images exist
for idx, path in topic_image_map.items():
    if not os.path.exists(path):
        print(f"⚠ Missing {path}, skip")
        continue
    hd = path.replace('.jpg', '_hd.jpg')
    if not os.path.exists(hd):
        subprocess.run([ffmpeg, '-y', '-i', path,
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
            '-q:v', '2', hd], capture_output=True, timeout=30)

# Generate concat demuxer input
concat_file = '/tmp/img_concat2.txt'
with open(concat_file, 'w') as f:
    for topic, start, end in image_segments:
        dur = end - start
        if dur < 0.3:
            continue
        img = topic_image_map.get(topic, '').replace('.jpg', '_hd.jpg')
        if not os.path.exists(img):
            img = topic_image_map.get(topic, '')
        if not os.path.exists(img):
            print(f"⚠ Missing HD: {img}")
            continue
        f.write(f"file '{img}'\nduration {dur:.3f}\n")

mp3_path = f'{AUDIO_DIR}/dialogue_combined.mp3'

# Single ffmpeg command
final = f'{OUTPUT_DIR}/新闻大家谈_第二期_对话版.mp4'
r = subprocess.run([ffmpeg, '-y',
    '-f', 'concat', '-safe', '0', '-i', concat_file,
    '-i', mp3_path,
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
    '-pix_fmt', 'yuv420p', '-r', '24',
    '-c:a', 'aac', '-b:a', '192k',
    '-shortest',
    final], capture_output=True, text=True, timeout=600)

if r.returncode != 0:
    print(f"❌ FFmpeg failed: {r.stderr[-300:]}")
    exit(1)

if os.path.exists(final):
    sz = os.path.getsize(final) / 1024 / 1024
    print(f"✅ 无字幕版: {sz:.1f}MB")
    print(f"MEDIA:{final}")

# Burn subtitles with width limit: Wrap=0 enables auto-wrap, MarginV for vertical centering
srt_path = f'{AUDIO_DIR}/dialogue.srt'
final_sub = f'{OUTPUT_DIR}/新闻大家谈_第二期_对话版_字幕.mp4'
r = subprocess.run([ffmpeg, '-y',
    '-i', final,
    '-vf', f"subtitles={srt_path}:force_style='FontName=Noto Sans CJK SC,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'",
    '-c:a', 'copy', '-pix_fmt', 'yuv420p', final_sub],
    capture_output=True, text=True, timeout=600)

if r.returncode == 0 and os.path.exists(final_sub):
    sz = os.path.getsize(final_sub) / 1024 / 1024
    print(f"✅ 字幕版: {sz:.1f}MB")
    print(f"MEDIA:{final_sub}")
else:
    print(f"⚠ 字幕烧录失败: {r.stderr[-200:]}")
    print("无字幕版已可用")