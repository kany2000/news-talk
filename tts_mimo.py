#!/usr/bin/env python3
"""MiMo TTS — 生产级 API 封装（api.xiaomimimo.com）"""
import urllib.request, json, os, time, sys, base64, io
from pathlib import Path

# 从 .env 加载本地配置
if os.path.exists(os.path.join(os.path.dirname(__file__), ".env")):
    with open(os.path.join(os.path.dirname(__file__), ".env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
API_KEY = os.environ.get("MIMO_TTS_API_KEY", "")
MODEL = "mimo-v2.5-tts"
VOICE_FEMALE = "xiaoxiao"
VOICE_MALE = "yunyang"

def gen_audio(text, output_path, voice_id=VOICE_FEMALE, timeout=120):
    """生成 TTS 音频并保存到文件"""
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "请朗读以下文本"},
            {"role": "assistant", "content": text},
        ],
        "voice_id": voice_id,
        "speed": 1.0,
        "volume": 1.0,
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL, data=payload,
        headers={
            "api-key": API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))

        audio_data_b64 = resp.get("choices", [{}])[0].get("message", {}).get("audio", {}).get("data")
        if not audio_data_b64:
            raise Exception(f"MiMo TTS error: no audio data in response")

        audio_bytes = base64.b64decode(audio_data_b64)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        size_kb = len(audio_bytes) // 1024
        print(f"✓ MiMo TTS: {output_path} ({size_kb}KB)", file=sys.stderr)
        return output_path

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"✗ MiMo HTTP {e.code}: {body[:200]}", file=sys.stderr)
        if e.code == 401:
            print("  请检查 MIMO_TTS_API_KEY 是否有效", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"✗ MiMo Network Error: {e.reason}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"✗ MiMo Error: {e}", file=sys.stderr)
        raise


def synthesize(text, voice_gender="female", output_path=None):
    """兼容 step1_gen_audio.py 的接口"""
    voice = VOICE_FEMALE if voice_gender == "female" else VOICE_MALE
    if output_path is None:
        output_path = f"/tmp/mimo_{int(time.time())}.wav"
    return gen_audio(text, output_path, voice_id=voice)


def get_ffmpeg_path():
    """兼容 step1_gen_audio.py 的接口"""
    return "ffmpeg"


if __name__ == "__main__":
    test_text = "各位听众，欢迎收听新闻大家谈，我是晓晓。今天我们来聊聊行为经济学。"
    test_output = "/tmp/mimo_test.wav"
    try:
        gen_audio(test_text, test_output, voice_id=VOICE_FEMALE)
    except Exception as e:
        print(f"测试失败: {e}", file=sys.stderr)