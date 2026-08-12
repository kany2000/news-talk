#!/usr/bin/env python3
"""第三期配图：耶鲁博弈论·集体恐慌 L5.6.7
配图引擎：Sensenova 优先（sensenova-u1-fast），失败自动回退 Pollinations（需求：sensenova 优先，Pollinations 备用）
图片顺序 = 语音顺序（按话题切分），intro/话题/outro 输出到 第三期/images/"""
import sys, os, json, io, time, urllib.request, urllib.parse
from pathlib import Path
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = Path(r"E:\projects\news-talk")
IMG_DIR = BASE / "yale大学公开课系列讲谈" / "第三期" / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

SENSENOVA_URL = "https://token.sensenova.cn/v1/images/generations"
SENSENOVA_KEY = os.environ.get("SENSENOVA_KEY", "")
SENSENOVA_MODEL = "sensenova-u1-fast"
SENSENOVA_SIZE = "2752x1536"

FACE_BOOST = ", photorealistic, sharp detailed realistic human face, perfect facial features, no distortion, no deformation, natural proportions"
NO_TEXT = ", no text, no words, no letters, no numbers, no watermarks, no captions, no signs, no writing"

# ===== 话题列表（按音频内容顺序，序号=图片文件名）=====
TOPICS = [
    "十美元投资游戏 — 90% 门槛的集体赌局",
    "纳什均衡 — 没有后悔的状态",
    "帕累托优势 — 全员投资的好均衡",
    "坏均衡 — 无人敢动的教室",
    "第一轮破产 — 盲目冒险者出局",
    "理性恐慌 — 集体失灵源自个体理性",
    "协调博弈 — 与囚徒困境截然相反",
    "银行挤兑 — 北岩银行的崩溃",
    "网络效应 — Excel 与约会软件",
    "政治初选 — 羊群效应",
    "帕特里克的五秒发言 — 打破僵局",
    "共同知识 — 从“我知道”到“大家都知道”",
    "领导力是火花 — 焦点机制",
    "去中心化的悬念 — 没有焦点的世界",
]

PROMPTS = {
    "intro": (
        "Yale University large amphitheater lecture hall, rising tiers of wooden seats, filled with 250 students sitting in ascending rows, professor at podium holding a ten dollar bill, green chalkboard, academic atmosphere, warm cinematic lighting, wide angle shot, 16:9"
        + NO_TEXT
    ),
    "01": (
        "a single ten dollar bill on a wooden desk, classroom setting, students hands raised in the background, an invisible 90 percent threshold line drawn in glowing light, collective investment game rules, dramatic lighting"
        + NO_TEXT
    ),
    "02": (
        "two balanced scales in perfect equilibrium, each side holding identical weight, concept of Nash equilibrium as a state of no regrets, split path of two valid outcomes, clean academic diagram style, soft studio light"
        + NO_TEXT
    ),
    "03": (
        "a classroom full of students all raising hands together to invest, golden glow of shared success, everyone benefiting equally, Pareto optimal outcome, warm optimistic atmosphere, upward energy"
        + FACE_BOOST + NO_TEXT
    ),
    "04": (
        "a silent classroom where nobody raises their hand, students frozen staring at ten dollar bills on desks, cold blue anxious atmosphere, bad equilibrium of mutual fear, nobody dares to move first"
        + FACE_BOOST + NO_TEXT
    ),
    "05": (
        "split classroom scene, half students eagerly investing while other half holds back, fifty percent participation failing to reach the threshold, dramatic divide down the middle, financial loss, contrasting light and shadow"
        + FACE_BOOST + NO_TEXT
    ),
    "06": (
        "a crowd of identical people stampeding toward an exit, each individual looking perfectly logical and calm, but together causing a panic, individual rationality creating collective disaster, paradox visualization, cinematic"
        + FACE_BOOST + NO_TEXT
    ),
    "07": (
        "two contrasting game theory diagrams side by side, prisoner's dilemma with handcuffs and betrayal arrows on one side, coordination game with synchronized figures and mutual benefit on the other side, opposite mechanics, academic comparison"
        + NO_TEXT
    ),
    "08": (
        "a crowd of panicked depositors rushing the doors of a British bank building, queue stretching down the street, vault being emptied, bank run chaos, desperate atmosphere, news camera angle, cinematic"
        + FACE_BOOST + NO_TEXT
    ),
    "09": (
        "network of connected user icons forming a glowing constellation, spreadsheet software interface and smartphone app icons in the network, network effect value, one central hub everyone connects to, technology, blue and teal glow"
        + NO_TEXT
    ),
    "10": (
        "election campaign rally with voters flocking toward one leading candidate, bandwagon effect, a map of early primary states Iowa and New Hampshire in the background, momentum arrows, political primary season, cinematic"
        + FACE_BOOST + NO_TEXT
    ),
    "11": (
        "a student standing up in a huge lecture hall, speaking to 250 seated students, microphone in hand, five seconds of powerful speech, moment of breaking the frozen silence, spotlight on the speaker, everyone turning to listen"
        + FACE_BOOST + NO_TEXT
    ),
    "12": (
        "a public announcement echoing across a lecture hall, sound waves reaching every seat simultaneously, everyone hearing the same message at the same time, common knowledge concept, ripple of understanding spreading through the crowd, visualization"
        + FACE_BOOST + NO_TEXT
    ),
    "13": (
        "a single match striking and igniting a spark in darkness, the spark spreading into a chain reaction of light across a dark room, leadership as focal point, aligning collective expectations, warm glow against dark background"
        + NO_TEXT
    ),
    "14": (
        "a vast decentralized digital network of anonymous nodes floating in dark space, cryptocurrency symbols and trading charts, no central leader or focal point, distributed system without a single voice, futuristic uncertainty, deep blue and purple"
        + NO_TEXT
    ),
    "outro": (
        "open deep ocean water, a lone diver descending into blue darkness, keep diving deep concept, contemplative mood, light rays from surface fading, cinematic underwater photography, 16:9"
        + NO_TEXT
    ),
}

def gen_sensenova(prompt, timeout=180, retries=3):
    payload = json.dumps({
        "model": SENSENOVA_MODEL, "prompt": prompt,
        "size": SENSENOVA_SIZE, "n": 1,
    }).encode()
    for attempt in range(retries):
        try:
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
                data = ir.read()
            return data, "sensenova"
        except Exception as e:
            print(f"    sensenova retry {attempt+1}: {str(e)[:80]}", flush=True)
            time.sleep(5)
    raise Exception("sensenova all retries failed")

def gen_pollinations(prompt, timeout=180):
    q = urllib.parse.quote(f"{prompt}?width=1920&height=1080&model=flux&nologo=true&nofeed=true")
    url = f"https://image.pollinations.ai/prompt/{q}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://pollinations.ai/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), "pollinations"

def gen_image(prompt, path):
    """Sensenova 优先，Pollinations 备用"""
    try:
        data, src = gen_sensenova(prompt)
    except Exception as e:
        print(f"  [FALLBACK] sensenova 失败: {str(e)[:100]} → Pollinations", flush=True)
        data, src = gen_pollinations(prompt)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    if img.size != (1920, 1080):
        img = img.resize((1920, 1080), Image.LANCZOS)
    img.save(path, "JPEG", quality=90)
    return src, len(data)

print(f"用 Sensenova（优先）/ Pollinations（备用）生成 {len(PROMPTS)} 张配图 ...")
ok_count = 0
for name, prompt in PROMPTS.items():
    path = IMG_DIR / f"{name}.jpg"
    if path.exists() and path.stat().st_size > 10000:
        print(f"  [SKIP] {name} 已存在", flush=True)
        ok_count += 1
        continue
    print(f"生成 {name} ...", flush=True)
    try:
        t0 = time.time()
        src, size = gen_image(prompt, path)
        ok_count += 1
        print(f"  [OK] {name} [{src}] {size//1024}KB ({time.time()-t0:.0f}s)", flush=True)
    except Exception as e:
        print(f"  [FAIL] {name}: {str(e)[:100]}", flush=True)
    time.sleep(2)

print(f"\n完成: {ok_count}/{len(PROMPTS)} 张生成成功")
print(f"输出目录: {IMG_DIR}")
