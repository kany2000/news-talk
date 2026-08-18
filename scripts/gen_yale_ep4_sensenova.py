#!/usr/bin/env python3
"""第四期配图：耶鲁博弈论·隔离 L8.9.10
配图引擎：Sensenova 优先（sensenova-u1-fast），失败自动回退 Pollinations
生成后自动去右下角 sensenova 水印（cv2.inpaint）"""
import sys, os, json, io, time, urllib.request, urllib.parse
from pathlib import Path
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = Path(r"E:\projects\news-talk")
IMG_DIR = BASE / "yale大学公开课系列讲谈" / "第四期" / "images"
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

TOPICS = [
    "谢林模型 — 诺贝尔奖的隔离数学",
    "双城镇 — 东镇与西镇的幸福规则",
    "完美混合 — 人人都想要的五五开",
    "现场实验 — 教室里的乌托邦崩塌",
    "弱均衡 — 铅笔尖上的五五开",
    "引爆点 — 微小偏差引发多米诺",
    "强均衡 — 没人敢做第一个跨线者",
    "社会学错觉 — 宏观不等于微观",
    "无需恶意 — 对零点的恐惧就够了",
    "第三均衡 — 放弃选择权的悖论",
    "校车政策 — 六十年代的现实实验",
    "哈佛宿舍 — 自由选择的崩塌",
    "数字回音室 — 逃离数字零点",
    "设计系统的教训 — 结构决定结果",
]

PROMPTS = {
    "intro": (
        "Yale University large amphitheater lecture hall, rising tiers of wooden seats, filled with students sitting in ascending rows, professor at podium, green chalkboard, academic atmosphere, warm cinematic lighting, wide angle shot, 16:9"
        + NO_TEXT
    ),
    "01": (
        "a chessboard with pieces dividing into two separate clusters, a chess king and queen separated from pawns, mathematical model of segregation, an elegant diagram with a Nobel Prize medal silhouette in soft light, strategic thinking, cinematic, 16:9"
        + NO_TEXT
    ),
    "02": (
        "two towns on a map connected by a road, East town and West town divided, one town with tall figures and one with short figures, balance scales showing happiness scores zero point five and one, schematic game model visualization, cinematic, 16:9"
        + NO_TEXT
    ),
    "03": (
        "a perfectly balanced see-saw with tall and short figures equally mixed on both sides, fifty fifty split visualization, everyone at peak happiness, warm golden balanced light, utopian equilibrium, cinematic, 16:9"
        + NO_TEXT
    ),
    "04": (
        "a lecture hall with students seated in perfectly alternating tall and short rows, then a dramatic split moment with motion blur as the pattern unravels, integration collapsing into two separated crowds, cinematic dramatic lighting"
        + FACE_BOOST + NO_TEXT
    ),
    "05": (
        "a pencil perfectly balanced on its tip, tense fragile equilibrium, barely visible breeze lines blowing, ready to fall at any moment, unstable balance metaphor, dramatic side lighting, shallow depth of field, cinematic, 16:9"
        + NO_TEXT
    ),
    "06": (
        "dominoes falling in a chain reaction, one tiny domino tipping over causing a cascade of many larger dominoes, tipping point concept, the first small movement triggering unstoppable snowball effect, dynamic motion, cinematic, 16:9"
        + NO_TEXT
    ),
    "07": (
        "a chalk line drawn across a street separating two groups, nobody dares to cross the line first, tense standoff, one foot hesitating at the boundary, strong equilibrium trap, dramatic lighting, cinematic, 16:9"
        + FACE_BOOST + NO_TEXT
    ),
    "08": (
        "a magnifying glass over a macro painting made of tiny individual dots, the big picture of segregation made of small diverse dots, macro outcome versus micro preferences, illusion concept, cinematic, 16:9"
        + NO_TEXT
    ),
    "09": (
        "a diverse crowd standing in a bright mixed area, one figure stepping back into a dim uniform group of identical silhouettes, running away from being the odd one out, fear of the zero concept, contrasting light and shadow, cinematic, 16:9"
        + FACE_BOOST + NO_TEXT
    ),
    "10": (
        "a giant hat with random names being drawn out, lottery of residence, people receiving random housing assignments, paradox of giving up choice for happiness, government random allocation concept, cinematic, 16:9"
        + FACE_BOOST + NO_TEXT
    ),
    "11": (
        "a yellow school bus driving across town carrying diverse children to school, 1960s American school busing policy, integration effort, historical setting, hopeful morning light, cinematic, 16:9"
        + FACE_BOOST + NO_TEXT
    ),
    "12": (
        "Harvard university residential houses on campus, students choosing houses and grouping into separate cliques, one house filled with athletes and another with academics, segregation by choice, campus aerial view, cinematic, 16:9"
        + FACE_BOOST + NO_TEXT
    ),
    "13": (
        "a person scrolling a phone feed inside a bubble of identical opinions, surrounded by many separate bubbles each with uniform content, digital echo chamber, online segregation concept, blue screen glow, cinematic, 16:9"
        + FACE_BOOST + NO_TEXT
    ),
    "14": (
        "an architect's hands drawing a blueprint of a city with mixed diverse zones, designing a system with structure that prevents segregation, urban planning concept, blueprint glowing with balance, cinematic, 16:9"
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

def save_jpg(data, path):
    img = Image.open(io.BytesIO(data)).convert("RGB")
    if img.size != (1920, 1080):
        img = img.resize((1920, 1080), Image.LANCZOS)
    img.save(path, "JPEG", quality=90)

def remove_watermark(path):
    """去除右下角 sensenova 水印（cv2.inpaint telea）"""
    try:
        import cv2
        import numpy as np
        arr = np.fromfile(str(path), dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.rectangle(mask, (w-680, h-110), (w, h), 255, -1)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        dst = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
        ext = str(path).rsplit('.', 1)[-1]
        cv2.imencode('.' + ext, dst, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(str(path))
        return True
    except Exception as e:
        print(f"  [WARN] watermark removal failed: {str(e)[:80]}")
        return False

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
        try:
            data, src = gen_sensenova(prompt)
        except Exception as e:
            print(f"  [FALLBACK] sensenova 失败: {str(e)[:100]} → Pollinations", flush=True)
            data, src = gen_pollinations(prompt)
        save_jpg(data, path)
        if src == "sensenova":
            remove_watermark(path)
        ok_count += 1
        print(f"  [OK] {name} [{src}] {path.stat().st_size//1024}KB ({time.time()-t0:.0f}s)", flush=True)
    except Exception as e:
        print(f"  [FAIL] {name}: {str(e)[:100]}", flush=True)
    time.sleep(2)

print(f"\n完成: {ok_count}/{len(PROMPTS)} 张生成成功")
print(f"输出目录: {IMG_DIR}")
