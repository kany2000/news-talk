## 使用 FFmpeg 合成视频

使用 FFmpeg 合成视频，适用于新闻大家谈项目。

### 步骤

1. **准备音频和配图**：确保音频和配图已经生成。
2. **调用 FFmpeg**：使用 FFmpeg 合成视频。
3. **保存视频**：将生成的视频保存到指定路径。

### 示例代码

```python
import subprocess

mp3_path = "/home/kan/shared/news-talk/audio/podcast_mimo.mp3"
subprocess.run([
    "ffmpeg", "-y",
    "-i", "/home/kan/shared/news-talk/images/intro.jpg",
    "-i", mp3_path,
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-c:a", "aac", "-b:a", "128k",
    "/home/kan/shared/news-talk/output/新闻大家谈_第二期.mp4"
])
```

### 注意事项

- **视频编码**：使用 H.264 编码，确保视频质量。
- **音频编码**：使用 AAC 编码，确保音频质量。
- **错误处理**：捕获并处理 FFmpeg 错误。

### 文件路径

- **视频输出路径**：`/home/kan/shared/news-talk/output/新闻大家谈_第二期.mp4`

### 依赖

- **FFmpeg**：确保 FFmpeg 已安装。

### 使用场景

适用于合成新闻视频，用于新闻大家谈项目。