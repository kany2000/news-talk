#!/usr/bin/env python3
"""新闻大家谈配图 — Sensenova-u1-fast 优先，Pollinations 备选"""
import urllib.request, os, sys, json, io, time
from PIL import Image

# Windows GBK 兼容
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# 从 .env 加载本地配置（仅开发环境）
if os.path.exists(os.path.join(os.path.dirname(__file__), ".env")):
    with open(os.path.join(os.path.dirname(__file__), ".env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

IMG_DIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(IMG_DIR, exist_ok=True)

# Sensenova
SENSENOVA_URL = "https://token.sensenova.cn/v1/images/generations"
SENSENOVA_KEY = os.environ.get("SENSENOVA_KEY", "")
SENSENOVA_MODEL = "sensenova-u1-fast"
SENSENOVA_SIZE = "2752x1536"

# 话题→Prompt映射（新闻大家谈风格）
TOPIC_PROMPTS = {
    "intro": "news talk show studio, wide angle, modern glass desk, multiple screens, warm golden and blue lighting, professional broadcast set, cinematic, no people",
    "outro": "city skyline at dusk, news broadcast ending, rolling credits overlay, warm glow, cinematic aerial view, no people, no text",
}

# 关键词→Prompt 模板（从 signal-pop 适配）
KEYWORD_PROMPTS = [
    ("芯片", "semiconductor factory, wafer production line, blue glow, macro photography, clean room, high tech"),
    ("AI", "artificial intelligence concept, neural network, glowing data streams, digital brain, futuristic tech lab"),
    ("OpenAI", "OpenAI, modern glass office building, AI research lab, blue and purple lighting, data visualization"),
    ("马斯克", "Elon Musk, Tesla factory, futuristic technology, minimalist design, Grok AI interface"),
    ("特斯拉", "Tesla Gigafactory, electric vehicle production line, automation robots, clean industrial design"),
    ("收购", "corporate acquisition, handshake deal, financial background, stock chart, business meeting"),
    ("IPO", "IPO listing, stock exchange, big screen with stock code, financial data visualization, trading floor"),
    ("上市", "company IPO, stock exchange, celebration, bell ringing, financial district"),
    ("融资", "funding round, investment deal, venture capital, money graph going up, business pitch"),
    ("谷歌", "Google headquarters, Googleplex, colorful logo, tech campus, Silicon Valley architecture"),
    ("苹果", "Apple Park, Cupertino, minimalist design, glass walls, product launch event"),
    ("华为", "Huawei R&D center, technology innovation, Chinese tech company, modern office"),
    ("机器人", "humanoid robot, advanced robotics lab, mechanical design, futuristic technology"),
    ("自动驾驶", "self-driving car, LIDAR visualization, autonomous driving, city street, night driving"),
    ("量子", "quantum computer, qubit processor, cryogenic chamber, blue glow, particle physics"),
    ("芯片", "semiconductor, chip fabrication, integrated circuit, wafer, microchip macro"),
    ("手机", "smartphone product shot, glass and metal, screen display, product photography"),
    ("游戏", "video game, gaming setup, RGB lighting, controller, entertainment"),
    ("VR", "VR headset, virtual reality, immersive experience, digital world, neon lights"),
    ("元宇宙", "metaverse concept, digital world, virtual reality, 3D avatars, network connections"),
    ("AI", "AI technology, neural network, deep learning, data science, futuristic"),
    ("科技", "technology concept, digital innovation, modern tech, clean design"),
    ("经济", "economic data, financial charts, market analysis, global economy"),
    ("金融", "financial district, stock market, trading, banking, city skyline"),
    ("医疗", "medical technology, hospital, healthcare innovation, DNA helix, modern clinic"),
    ("能源", "renewable energy, solar panels, wind turbines, green technology, clean energy"),
    ("教育", "education technology, online learning, digital classroom, modern campus"),
    ("太空", "space exploration, rocket launch, SpaceX, NASA, stars, galaxy"),
]

def gen_sensenova(prompt, timeout=120):
    payload = json.dumps({
        "model": SENSENOVA_MODEL, "prompt": prompt,
        "size": SENSENOVA_SIZE, "n": 1,
    }).encode()
    req = urllib.request.Request(
        SENSENOVA_URL, data=payload,
        headers={"Authorization": f"Bearer {SENSENOVA_KEY}",
                 "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    url = resp.get("data", [{}])[0].get("url")
    if not url:
        raise Exception("no URL in response")
    img_req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(img_req, timeout=timeout) as ir:
        img = Image.open(io.BytesIO(ir.read()))
    out = io.BytesIO()
    img.convert("RGB").save(out, "JPEG", quality=88)
    return out.getvalue()

def gen_pollinations(prompt, timeout=120):
    import urllib.parse
    q = urllib.parse.quote(f"{prompt}?width=1920&height=1080&model=flux&nologo=true&nofeed=true")
    url = f"https://image.pollinations.ai/prompt/{q}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Referer": "https://pollinations.ai/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def gen_image(prompt, timeout=120):
    try:
        return gen_sensenova(prompt, timeout), "sensenova"
    except Exception as e:
        print(f"  Sensenova 失败 ({e}) → Pollinations", file=sys.stderr)
        try:
            return gen_pollinations(prompt, timeout), "pollinations"
        except Exception as e2:
            raise Exception(f"均失败: {e} / {e2}")

def build_prompt(title):
    """根据话题标题构建配图 prompt"""
    for kw, template in KEYWORD_PROMPTS:
        if kw in title:
            extra = title.replace(kw, "").strip()[:40]
            return f"{template}, {extra}, photorealistic, cinematic lighting, 16:9" if extra else f"{template}, photorealistic, cinematic lighting, 16:9"
    return f"news illustration, {title[:50]}, modern technology concept, cinematic, photorealistic, 16:9"

def generate_all(topic_titles, force=False):
    """生成所有配图，返回 (name, path) 列表"""
    results = []
    # intro / outro
    for name in ["intro", "outro"]:
        path = os.path.join(IMG_DIR, f"{name}.jpg")
        if os.path.exists(path) and os.path.getsize(path) > 10000 and not force:
            print(f"✓ {name} (已存在)")
            results.append((name, path))
            continue
        prompt = TOPIC_PROMPTS[name]
        print(f"生成 {name}...", end=" ", flush=True)
        try:
            data, source = gen_image(prompt)
            with open(path, "wb") as f:
                f.write(data)
            print(f"✓ [{source}] {len(data)//1024}KB")
            results.append((name, path))
        except Exception as e:
            print(f"✗ {e}")
        time.sleep(2)

    # topics
    for i, title in enumerate(topic_titles, 1):
        name = f"{i:02d}"
        path = os.path.join(IMG_DIR, f"{name}.jpg")
        if os.path.exists(path) and os.path.getsize(path) > 10000 and not force:
            print(f"✓ {name} {title[:20]} (已存在)")
            results.append((name, path))
            continue
        prompt = build_prompt(title)
        print(f"生成 {name}「{title[:20]}」...", end=" ", flush=True)
        try:
            data, source = gen_image(prompt)
            with open(path, "wb") as f:
                f.write(data)
            print(f"✓ [{source}] {len(data)//1024}KB")
            results.append((name, path))
        except Exception as e:
            print(f"✗ {e}")
        time.sleep(2)

    return results

if __name__ == "__main__":
    # 测试模式：用默认话题列表
    test_titles = [
        "SK海力士 登陆纳斯达克",
        "OpenAI 回应商业机密诉讼",
        "马斯克 要求全员用Grok",
        "FansAI 收购新映科技",
        "长鑫科技 IPO启动",
    ]
    generate_all(test_titles)