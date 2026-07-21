#!/usr/bin/env python3
"""Step 1: Generate alternating male/female audio segments with MiMo TTS"""
import sys, os, json, time
sys.path.insert(0, '/home/kan/signal_pop/src')
from tts_mimo import synthesize, get_ffmpeg_path
import subprocess

# Load dialogue script
from 对话稿_第二期 import SCENE

AUDIO_DIR = '/home/kan/shared/news-talk/audio'
os.makedirs(AUDIO_DIR, exist_ok=True)

# Generate each segment
segments_meta = []
for i, (speaker, text, topic_idx) in enumerate(SCENE):
    out = f'{AUDIO_DIR}/seg_{i:03d}.wav'
    voice = 'female' if speaker == 'female' else 'male'
    print(f"[{i+1}/{len(SCENE)}] {voice}: {text[:30]}...")
    try:
        synthesize(text, voice_gender=voice, output_path=out)
        segments_meta.append({'idx': i, 'speaker': speaker, 'text': text, 'topic_idx': topic_idx, 'path': out})
        time.sleep(0.5)  # rate limit
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

# Get durations from WAV files
ffprobe = 'ffprobe'
for s in segments_meta:
    r = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1', s['path']],
                       capture_output=True, text=True, timeout=10)
    s['duration'] = float(r.stdout.strip()) if r.returncode == 0 else 0

# Calculate cumulative timestamps
t = 0.0
for s in segments_meta:
    s['start'] = t
    s['end'] = t + s['duration']
    t = s['end']

total = sum(s['duration'] for s in segments_meta)
print(f"\n总时长: {total:.1f}s = {total/60:.1f}min")

# Save metadata for later steps
meta_path = f'{AUDIO_DIR}/segments_meta.json'
with open(meta_path, 'w') as f:
    json.dump(segments_meta, f, ensure_ascii=False, indent=2)
print(f"元数据: {meta_path}")

# Concatenate all WAVs into one
ffmpeg = get_ffmpeg_path()
concat_list = f'{AUDIO_DIR}/concat.txt'
with open(concat_list, 'w') as f:
    for s in segments_meta:
        f.write(f"file '{s['path']}'\n")

combined_wav = f'{AUDIO_DIR}/dialogue_combined.wav'
subprocess.run([ffmpeg, '-y', '-f', 'concat', '-safe', '0',
                '-i', concat_list, '-c', 'copy', combined_wav],
               capture_output=True, timeout=120)

# Convert to MP3
combined_mp3 = f'{AUDIO_DIR}/dialogue_combined.mp3'
subprocess.run([ffmpeg, '-y', '-i', combined_wav,
                '-codec:a', 'libmp3lame', '-b:a', '192k', combined_mp3],
               capture_output=True, timeout=120)

print(f"\n合并音频: {combined_mp3}")
print(f"大小: {os.path.getsize(combined_mp3)//1024}KB")
print("\n✅ Step 1 完成")