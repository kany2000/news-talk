#!/usr/bin/env bash
set -euo pipefail
cd /home/kan/shared/news-talk
rm -f output/slides.mp4 output/新闻大家谈_首期.mp4

# Build concat
{
  echo "ffconcat version 1.0"
  for pair in "intro 10" "01 20" "02 20" "03 20" "04 20" "05 20" "06 20" "07 20" "08 20" "outro 10"; do
    name="${pair% *}"
    dur="${pair#* }"
    if [ -f "images/${name}.jpg" ]; then
      echo "file images/${name}.jpg"
      echo "duration ${dur}"
    fi
  done
} > concat2.txt

echo "=== Step 1: slides ==="
ffmpeg -y -f concat -safe 0 -i concat2.txt \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1" \
  -c:v libx264 -preset ultrafast -crf 26 -pix_fmt yuv420p -r 24 \
  output/slides.mp4 2>&1 | tail -3

echo "=== Step 2: merge audio ==="
ffmpeg -y -stream_loop -1 -i output/slides.mp4 \
  -i audio/podcast.mp3 \
  -c:v libx264 -preset ultrafast -crf 26 \
  -c:a aac -b:a 128k -shortest -pix_fmt yuv420p \
  output/新闻大家谈_首期.mp4 2>&1 | tail -5

ls -sh output/新闻大家谈_首期.mp4
echo "=== DONE ==="