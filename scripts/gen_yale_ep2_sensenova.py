#!/usr/bin/env python3
"""用 Sensenova 重新生成 Yale EP2 全部配图
每个话题 prompt 结合讲稿内容，且图片顺序=语音顺序，按时间区间切换"""
import sys, os, json, io, time, urllib.request
from pathlib import Path
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = Path(r"E:\projects\news-talk")
IMG_DIR = BASE / "yale大学公开课系列讲谈" / "第二期" / "images"
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

# ===== 每个话题 prompt 结合讲稿内容 =====
PROMPTS = {
    "intro": (
        "a person standing before a giant translucent chess board, gazing at a shadowy rival figure on the other side, x-ray like lines revealing the rival's planned next move, ability to predict opponent's decision, futuristic game theory visualization"
        + FACE_BOOST + NO_TEXT
    ),
    "01": (
        "three pillars as game theory essentials: a chess player piece representing the player, a fan of strategy cards representing strategies, a pile of gold coins representing payoffs, three essential elements with equal weight, elegant minimal composition"
        + NO_TEXT
    ),
    "02": (
        "two companies in a price war, red price tags slashed downward on both sides, factories emitting smoke, planet earth dimming, prisoner's dilemma of price wars and climate inaction, dramatic contrasting lighting"
        + NO_TEXT
    ),
    "03": (
        "group of students around a library table, all secretly playing on phones and gaming while a shared group project document stays empty on a laptop, everyone promised not to slack off but all slacking, procrastination atmosphere, warm dim library"
        + FACE_BOOST + NO_TEXT
    ),
    "04": (
        "a lighthouse beam cutting through fog, illuminating one clear strong path while several weak uncertain branching paths fade away, eliminating dominated strategies, decisive beam of light"
        + NO_TEXT
    ),
    "05": (
        "Carthaginian general Hannibal leading an army with war elephants over a snowy Alpine mountain pass to attack Rome, epic ancient battlefield landscape, while a map below shows the safer coastal route, dramatic snowstorm clouds"
        + FACE_BOOST + NO_TEXT
    ),
    "06": (
        "classroom full of students writing numbers on paper, teacher at chalkboard, chalkboard showing arithmetic of two thirds of the average, iterative elimination arrows going from 100 to 67 to 45 to 30 to 1, guessing game energy"
        + FACE_BOOST + NO_TEXT
    ),
    "07": (
        "two people wearing pink hats standing face to face, each seeing the other's pink hat, thinking about whether the other knows, layered bubble thoughts showing mutual knowledge chains, thought experiment about common knowledge"
        + FACE_BOOST + NO_TEXT
    ),
    "08": (
        "a horizontal political spectrum line from far left to far right with numbers, two candidate avatars at the ends, arrows showing both converging toward the center, along a street below two gas stations huddled together at the midpoint, median voter theorem"
        + FACE_BOOST + NO_TEXT
    ),
    "09": (
        "professional soccer penalty statistics chart floating above a soccer field, three arrows from the penalty spot toward left post, right post and center of goal, labels showing different success rates, the center arrow pressed down lower than the two side arrows, analyst studying data, conclusion that shooting center is never best for professionals, sports data visualization, cinematic"
        + FACE_BOOST + NO_TEXT
    ),
    "10": (
        "amateur player about to kick a penalty with full force, eyes closed swinging hard, ball blasting straight down the middle of the goal and flying into the net, goalkeeper diving to the side too slow to react, ball already inside goal net, powerful kick, dynamic action, stadium lights"
        + FACE_BOOST + NO_TEXT
    ),
    "11": (
        "two exhausted students staring at a shared laptop document at 2am, each waiting for the other to do more work, mutual standoff over effort, deadline clock on wall, nobody dares to type or leave, dim blue night light"
        + FACE_BOOST + NO_TEXT
    ),
    "12": (
        "two people stuck deep in a mud pit, each holding the other back, neither dares to move because moving first means losing, Nash equilibrium trap visualized, gloomy desolate landscape"
        + FACE_BOOST + NO_TEXT
    ),
    "13": (
        "three committee members sitting at a voting table, one member holding a large golden gavel of absolute tie-breaking power, the other two members quietly exchanging glances to ally against the powerful one, subtle political tension"
        + FACE_BOOST + NO_TEXT
    ),
    "outro": (
        "a chess board with gold and silver pieces at sunset, one hand about to move a piece from a new perspective, thinking about standing in the opponent's shoes, warm closing contemplative mood"
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
            return data
        except Exception as e:
            print(f"    retry {attempt+1}: {str(e)[:80]}")
            time.sleep(5)
    raise Exception("all retries failed")

def save_jpg(data, path, size=(1920, 1080)):
    img = Image.open(io.BytesIO(data)).convert("RGB")
    if img.size != size:
        img = img.resize(size, Image.LANCZOS)
    img.save(path, "JPEG", quality=90)
    return len(data)

print(f"用 Sensenova 重新生成 {len(PROMPTS)} 张配图（结合讲稿）...")
ok_count = 0
for name, prompt in PROMPTS.items():
    path = IMG_DIR / f"{name}.jpg"
    print(f"生成 {name}...", flush=True)
    try:
        t0 = time.time()
        data = gen_sensenova(prompt)
        sz = save_jpg(data, path)
        ok_count += 1
        print(f"  OK {name} {sz//1024}KB ({time.time()-t0:.0f}s)")
    except Exception as e:
        print(f"  FAIL {name}: {str(e)[:100]}")
    time.sleep(2)

print(f"\n完成: {ok_count}/{len(PROMPTS)} 张生成成功")
