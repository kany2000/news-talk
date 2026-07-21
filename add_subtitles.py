#!/usr/bin/env python3
"""为播客 MP3 生成字幕并烧录到视频。用 faster-whisper medium 模型"""
import subprocess, os, sys, json, math
from faster_whisper import WhisperModel

def transcribe(mp3_path, model_size="base"):
    """转写 MP3 → 带时间戳的 segments"""
    print(f"加载模型 {model_size}...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    print("转写中...")
    segments, info = model.transcribe(mp3_path, language="zh", beam_size=5)
    segs = list(segments)  # materialize
    print(f"转写完成: {len(segs)} 段, {info.language} ({info.language_probability:.2%})")
    return segs

def segments_to_srt(segments, srt_path):
    """segments → SRT 字幕文件"""
    with open(srt_path, "w") as f:
        for i, seg in enumerate(segments, 1):
            start = seg.start
            end = seg.end
            text = seg.text.strip()
            # SRT time format: HH:MM:SS,mmm
            def fmt(sec):
                h = int(sec // 3600)
                m = int((sec % 3600) // 60)
                s = int(sec % 60)
                ms = int((sec - int(sec)) * 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            f.write(f"{i}\n{fmt(start)} --> {fmt(end)}\n{text}\n\n")
    print(f"SRT: {srt_path} ({len(segments)} 条)")

def segments_to_ass(segments, ass_path, width=1920, height=1080):
    """segments → ASS 字幕（更美观，支持样式）"""
    with open(ass_path, "w") as f:
        f.write("[Script Info]\n")
        f.write("ScriptType: v4.00+\n")
        f.write("PlayResX: " + str(width) + "\n")
        f.write("PlayResY: " + str(height) + "\n")
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        f.write("Style: Default,Noto Sans CJK SC,36,&H00FFFFFF,&H000000FF,&H80000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,50,50,50,1\n")
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for seg in segments:
            def fmt(sec):
                h = int(sec // 3600)
                m = int((sec % 3600) // 60)
                s = sec % 60
                return f"{h}:{m:02d}:{s:05.2f}"
            start = seg.start
            end = seg.end
            text = seg.text.strip().replace("{", "\\{").replace("}", "\\}")
            f.write(f"Dialogue: 0,{fmt(start)},{fmt(end)},Default,,0,0,0,,{text}\n")
    print(f"ASS: {ass_path} ({len(segments)} 条)")

def burn_subtitles(video_in, subtitle_path, video_out, format="srt"):
    """FFmpeg 烧录字幕到视频"""
    if format == "srt":
        vf = f"subtitles={subtitle_path}:force_style='FontName=Noto Sans CJK SC,FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H40000000,BackColour=&H80000000,BorderStyle=3,Alignment=2,Wrap=0,ScreenAlignment=2,MarginV=40'"
    else:
        vf = f"ass={subtitle_path}"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_in,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        video_out
    ]
    print("烧录字幕... " + " ".join(cmd[:5]) + "...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(f"FFmpeg 错误: {r.stderr[-500:]}")
        return False
    size_mb = os.path.getsize(video_out) / 1024 / 1024
    print(f"✅ 字幕视频: {video_out} ({size_mb:.0f}MB)")
    return True

def full_pipeline(mp3_path, video_in, video_out, srt_out=None, model_size="base"):
    """一步完成: 转写 → SRT → 烧录"""
    if srt_out is None:
        srt_out = os.path.splitext(video_out)[0] + ".srt"

    segs = transcribe(mp3_path, model_size=model_size)
    segments_to_srt(segs, srt_out)
    burn_subtitles(video_in, srt_out, video_out)
    return srt_out

if __name__ == "__main__":
    mp3 = "/home/kan/shared/news-talk/audio/podcast.mp3"
    video = "/home/kan/shared/news-talk/output/新闻大家谈_首期.mp4"
    out = video.replace(".mp4", "_subtitled.mp4")

    if not os.path.exists(mp3):
        print(f"找不到 MP3: {mp3}")
        sys.exit(1)
    if not os.path.exists(video):
        print(f"找不到视频: {video}")
        sys.exit(1)

    full_pipeline(mp3, video, out, model_size="base")