#!/usr/bin/env python3
import urllib.request, json, os, time, sys

# 从 .env 加载本地配置（仅开发环境）
if os.path.exists(os.path.join(os.path.dirname(__file__), ".env")):
    with open(os.path.join(os.path.dirname(__file__), ".env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_URL = "https://api.mimovoice.com/v1/tts/synthesize"
API_KEY = os.environ.get("MIMO_TTS_API_KEY", "")
MODEL = "mimo-v2.5-tts"
VOICE_FEMALE = "xiaoxiao"
VOICE_MALE = "yunyang"

def gen_audio(text, output_path, voice_id=VOICE_FEMALE, timeout=120):
    payload = json.dumps({
        "model": MODEL,
        "input": text,
        "voice_id": voice_id,
        "speed": 1.0,
        "volume": 1.0
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL, data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
        
        audio_url = resp.get("data", {}).get("audio_url")
        if not audio_url:
            raise Exception(f"MiMo TTS API error: {resp.get('message', 'No audio URL')}")
        
        # Download audio
        audio_req = urllib.request.Request(audio_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(audio_req, timeout=timeout) as ar:
            audio_data = ar.read()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        
        print(f"✅ MiMo TTS 音频生成成功: {output_path} ({len(audio_data)//1024}KB)")
        return output_path
        
    except urllib.error.HTTPError as e:
        print(f"MiMo TTS HTTP Error: {e.code} - {e.reason}", file=sys.stderr)
        if e.code == 401:
            print("请检查 MiMo API Key 是否有效", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"MiMo TTS Network Error: {e.reason}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"MiMo TTS Unexpected Error: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    test_text = "这是一段新闻播报的测试文本，用于测试小米米模语音合成服务。"
    test_output = "/tmp/mimo_test_audio.mp3"
    try:
        gen_audio(test_text, test_output, voice_id=VOICE_FEMALE)
    except Exception as e:
        print(f"测试失败: {e}", file=sys.stderr)
