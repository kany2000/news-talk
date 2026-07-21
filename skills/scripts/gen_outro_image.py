#!/usr/bin/env python3
"""生成第二期 outro 配图 — 以 intro.jpg 模糊为背景，7条话题标题列表"""
import sys, os, json, io, urllib.request, urllib.parse
sys.path.append('/home/kan/shared/news-talk')
PIL = None
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL = True
except:
    PIL = False

IMG_DIR = '/home/kan/shared/news-talk/images'

# 7条话题（全中文，无英文缩写，防止乱码）
topics = [
    "1. 长鑫科技首次公开募股",
    "2. 信维通信十一亿收购加强MLCC多层陶瓷电容布局",
    "3. 阿里云下调GLM五点二快速模式价格",
    "4. 海南将成中国首个禁燃油车省份",
    "5. 功夫女足预测票房三十点三亿",
    "6. 玩具总动员五经典IP知识产权回归",
    "7. 孩子总把网络烂梗挂嘴边怎么办",
]

outro_path = f'{IMG_DIR}/outro_text.jpg'

if PIL:
    # ===== 背景：intro.jpg 模糊 + 暗色叠加 =====
    intro_path = f'{IMG_DIR}/intro.jpg'
    if os.path.exists(intro_path) and os.path.getsize(intro_path) > 10000:
        bg = Image.open(intro_path).convert('RGB')
        bg = bg.resize((1920, 1080), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
        # 暗色叠加半透明层，让文字更清晰
        overlay = Image.new('RGBA', (1920, 1080), (0, 0, 0, 140))
        bg.paste(overlay, (0, 0), overlay)
    else:
        # Fallback: solid dark blue
        bg = Image.new('RGB', (1920, 1080), (20, 20, 40))
    draw = ImageDraw.Draw(bg)

    # ===== 字体加载（优先 Windows，回退 Linux） =====
    font_paths = [
        # Windows
        'C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/simsun.ttc',
        # Linux
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
    ]
    font_big = None
    font_mid = None
    font_small = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font_big = ImageFont.truetype(fp, 48)
                font_mid = ImageFont.truetype(fp, 32)
                font_small = ImageFont.truetype(fp, 24)
                break
            except Exception:
                continue

    if not font_big:
        print("⚠ 未找到中文字体，使用 PIL 默认字体（中文可能显示为框）")

    # ===== 标题 =====
    title = "-- 本期话题回顾 --"
    bbox = draw.textbbox((0,0), title, font=font_big) if font_big else (0,0,200,30)
    tw = bbox[2] - bbox[0]
    draw.text(((1920 - tw) // 2, 50), title, fill=(255, 200, 50), font=font_big)

    # ===== 话题列表 =====
    y_start = 170
    for i, t in enumerate(topics):
        y = y_start + i * 100
        if font_mid:
            bbox = draw.textbbox((0,0), t, font=font_mid)
            tw = bbox[2] - bbox[0]
            num_text = f"{i+1}. "
            rest_text = t[len(num_text):] if t.startswith(f"{i+1}.") else t
            draw.text(((1920 - tw) // 2, y), f"{i+1}. ", fill=(255, 220, 100), font=font_mid)
            nw = draw.textbbox((0,0), f"{i+1}. ", font=font_mid)
            nw = nw[2] - nw[0]
            draw.text(((1920 - tw) // 2 + nw, y), rest_text, fill=(220, 220, 255), font=font_mid)

    # ===== 页脚 =====
    footer = "感谢收听，欢迎在评论区分享你的看法"
    if font_small:
        bbox = draw.textbbox((0,0), footer, font=font_small)
        tw = bbox[2] - bbox[0]
        draw.text(((1920 - tw) // 2, 1000), footer, fill=(150, 150, 180), font=font_small)

    bg.save(outro_path, 'JPEG', quality=92)
    print(f"✅ Outro 配图: {outro_path} ({os.path.getsize(outro_path)//1024}KB)")
else:
    # Fallback: use Sensenova to generate
    print("PIL not available, use Sensenova")
    from gen_news_talk_images import gen_image
    prompt = "news broadcast ending screen, dark blue background, list of 7 news topics in Chinese text, elegant typography, professional news design, 16:9, no people"
    data, source = gen_image(prompt)
    with open(outro_path, 'wb') as f:
        f.write(data)
    print(f"✅ Sensenova Outro: {outro_path} ({len(data)//1024}KB, {source})")