#!/usr/bin/env python3
"""生成 Yale 博弈论第三期封面图 — 3种尺寸（标题放大版）"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFont

BASE = r"E:\projects\news-talk"
EP_DIR = os.path.join(BASE, "yale大学公开课系列讲谈", "第三期")
OUT_DIR = os.path.join(BASE, "yale大学公开课系列讲谈", "cover", "第三期")
os.makedirs(OUT_DIR, exist_ok=True)

BG_PATH = os.path.join(EP_DIR, "images", "intro.jpg")
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_LIGHT = "C:/Windows/Fonts/msyh.ttc"

SIZES = {
    "16-9": (1920, 1080),
    "4-3":  (1440, 1080),
    "3-4":  (1080, 1440),
}

TITLE = "新闻大家谈"
SUBTITLE = "为什么理性会引发集体恐慌"
SUBTITLE2 = "耶鲁博弈论 · 教室里的 90% 门槛"
TAG = "博弈论 · 纳什均衡 · 羊群效应 · 银行挤兑"

def fit_font(draw, text, font_path, max_w, start_size, max_h=0):
    """自动缩字号使文本不超宽（可选不超高）"""
    size = start_size
    while size > 30:
        f = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=f)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw <= max_w and (max_h == 0 or th <= max_h):
            return f, tw, th
        size -= 4
    f = ImageFont.truetype(font_path, 30)
    bbox = draw.textbbox((0, 0), text, font=f)
    return f, bbox[2]-bbox[0], bbox[3]-bbox[1]

def create_cover(label, w, h):
    img = Image.new("RGB", (w, h), (0, 0, 0))
    bg = Image.open(BG_PATH).convert("RGB")
    bg_w, bg_h = bg.size
    scale = max(w / bg_w, h / bg_h)
    new_w, new_h = int(bg_w * scale), int(bg_h * scale)
    bg_resized = bg.resize((new_w, new_h), Image.LANCZOS)
    left, top = (new_w - w) // 2, (new_h - h) // 2
    bg_cropped = bg_resized.crop((left, top, left + w, top + h))

    # 上亮下暗渐变遮罩（保文字对比度）
    overlay = Image.new("L", (w, h), 0)
    for y in range(h):
        alpha = int(120 * (y / h))  # 顶部 0 → 底部 120
        draw_o = ImageDraw.Draw(overlay)
        draw_o.line([(0, y), (w, y)], fill=alpha)
    bg_cropped = Image.composite(Image.new("RGB", (w, h), (10, 10, 12)), bg_cropped, overlay)

    draw = ImageDraw.Draw(bg_cropped)

    vertical = label == "3-4"

    # 顶部品牌条
    bar_h = int(h * 0.10)
    draw.rectangle([(0, 0), (w, bar_h)], fill=(15, 15, 18))
    f_brand = ImageFont.truetype(FONT_BOLD, int(h * 0.045))
    bbox = draw.textbbox((0, 0), TITLE, font=f_brand)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, bar_h // 2 - bbox[3] // 2), TITLE, fill=(255, 255, 255), font=f_brand)

    # 主副标题（大字号，竖版放中上部）
    if vertical:
        title_area_y = int(h * 0.30)
        f_sub = ImageFont.truetype(FONT_BOLD, int(h * 0.068))
        f_sub2 = ImageFont.truetype(FONT_BOLD, int(h * 0.036))
        f_tag = ImageFont.truetype(FONT_LIGHT, int(h * 0.030))
        accent_y = title_area_y - int(h * 0.045)
    else:
        title_area_y = int(h * 0.42)
        f_sub = ImageFont.truetype(FONT_BOLD, int(h * 0.075))
        f_sub2 = ImageFont.truetype(FONT_BOLD, int(h * 0.042))
        f_tag = ImageFont.truetype(FONT_LIGHT, int(h * 0.034))
        accent_y = title_area_y - int(h * 0.05)

    # 红色强调线
    aw = int(w * 0.09)
    draw.rectangle([((w - aw) // 2, accent_y), ((w + aw) // 2, accent_y + int(h * 0.008))], fill=(230, 50, 50))

    # 副标题1（最大）
    f1, tw1, th1 = fit_font(draw, SUBTITLE, FONT_BOLD, int(w * 0.92), f_sub.size, int(h * 0.16))
    sh = 4
    draw.text(((w - tw1) // 2 + sh, title_area_y + sh), SUBTITLE, fill=(0, 0, 0), font=f1)
    draw.text(((w - tw1) // 2, title_area_y), SUBTITLE, fill=(255, 255, 255), font=f1)

    # 副标题2（金色）
    y2 = title_area_y + th1 + int(h * 0.025)
    f2, tw2, th2 = fit_font(draw, SUBTITLE2, FONT_BOLD, int(w * 0.90), f_sub2.size, int(h * 0.09))
    draw.text(((w - tw2) // 2, y2), SUBTITLE2, fill=(255, 200, 50), font=f2)

    # 底部标签
    tag_y = h - int(h * 0.055)
    f3, tw3, th3 = fit_font(draw, TAG, FONT_LIGHT, int(w * 0.92), f_tag.size)
    draw.text(((w - tw3) // 2, tag_y - th3 // 2), TAG, fill=(200, 200, 200), font=f3)

    out_path = os.path.join(OUT_DIR, f"新闻大家谈封面_{label}.jpg")
    bg_cropped.save(out_path, "JPEG", quality=95)
    print(f"  {label} ({w}x{h}): {os.path.getsize(out_path)//1024}KB -> {os.path.basename(out_path)}")
    return out_path

print("生成第三期封面图（标题放大版）...")
for label, (w, h) in SIZES.items():
    create_cover(label, w, h)
print(f"\n完成！3 张封面已保存到 {OUT_DIR}")
