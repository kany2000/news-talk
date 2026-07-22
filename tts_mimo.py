#!/usr/bin/env python3
"""TTS 语音合成 — edge-tts 引擎（微软男声 Yunxi）"""
import os, sys, asyncio, subprocess, json
from pathlib import Path

# 从 .env 加载本地配置
if os.path.exists(os.path.join(os.path.dirname(__file__), ".env")):
    with open(os.path.join(os.path.dirname(__file__), ".env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

VOICE_FEMALE = "zh-CN-XiaoxiaoNeural"  # 晓晓（女声，微软标准）
VOICE_MALE = "zh-CN-YunxiNeural"       # 云扬（男声，微软标准）
MODEL = "edge-tts"


def gen_audio(text, output_path, voice_id=VOICE_FEMALE, timeout=120):
    """edge-tts 合成语音，输出 MP3 文件"""
    import edge_tts

    async def _run():
        tts = edge_tts.Communicate(text, voice_id)
        audio = b""
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio

    audio_bytes = asyncio.run(_run())
    if not audio_bytes:
        raise Exception("edge-tts 返回空音频")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    size_kb = len(audio_bytes) // 1024
    print(f"✓ TTS: {output_path} ({size_kb}KB)", file=sys.stderr)
    return output_path


def synthesize(text, voice_gender="female", output_path=None):
    """兼容 step 脚本的接口"""
    voice = VOICE_FEMALE if voice_gender == "female" else VOICE_MALE
    if output_path is None:
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), f"tts_{hash(text)}.mp3")
    return gen_audio(text, output_path, voice_id=voice)


def get_ffmpeg_path():
    return "ffmpeg"


if __name__ == "__main__":
    test_text = "各位听众，欢迎收听新闻大家谈，我是晓晓。今天我们来聊聊行为经济学。"
    test_output = "/tmp/test_tts.mp3"
    try:
        gen_audio(test_text, test_output, voice_id=VOICE_FEMALE)
        print(f"测试成功: {test_output}")
    except Exception as e:
        print(f"测试失败: {e}", file=sys.stderr)