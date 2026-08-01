#!/usr/bin/env python3
"""生成 Yale 博弈论系列封面图 — 3种尺寸"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

BASE = r"E:\projects\news-talk"
OUT_DIR = os.path.join(BASE, "yale大学公开课系列讲谈", "cover", "第一期")
os.makedirs(OUT_DIR, exist_ok=True)

BG_PATH = os.path.join(BASE, "images", "yale_cover_bg.jpg")
FONT_PATH = "C:/Windows/Fonts/msyhbd.ttc"  # 微软雅黑粗体
FONT_PATH_LIGHT = "C:/Windows/Fonts/msyh.ttc"

# 尺寸定义
SIZES = {
    "16-9": (1920, 1080),
    "4-3":  (1440, 1080),
    "3-4":  (1080, 1440),
}

# 标题
TITLE = "新闻大家谈"
SUBTITLE = "耶鲁博弈论：成绩陷阱"
TAG = "博弈论 · 囚徒困境 · 占优策略"

def create_cover(bg, w, h, label):
    """创建封面图"""
    img = Image.new("RGB", (w, h), (0, 0, 0))

    # 缩放背景填满宽度
    bg_w, bg_h = bg.size
    scale = max(w / bg_w, h / bg_h)
    new_w = int(bg_w * scale)
    new_h = int(bg_h * scale)
    bg_resized = bg.resize((new_w, new_h), Image.LANCZOS)

    # 居中裁剪
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    bg_cropped = bg_resized.crop((left, top, left + w, top + h))

    # 暗色渐变叠加
    overlay = Image.new("RGB", (w, h), (0, 0, 0))
    for y in range(h):
        opacity = int(80 * (1 - y / h))
        for x in range(w):
            overlay.putpixel((x, y), (opacity, opacity, opacity))
    bg_cropped = Image.blend(bg_cropped, overlay, 0.35)

    # 底部渐变条
    draw = ImageDraw.Draw(bg_cropped)
    for y in range(h - 180, h):
        alpha = int(180 * (1 - (h - y) / 180))
        draw.rectangle([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    draw = ImageDraw.Draw(bg_cropped)

    # 尝试加载字体
    try:
        font_title = ImageFont.truetype(FONT_PATH, 120)
        font_sub = ImageFont.truetype(FONT_PATH, 56)
        font_tag = ImageFont.truetype(FONT_PATH_LIGHT, 32)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_tag = ImageFont.load_default()

    # 标题位置
    if label == "3-4":
        title_y = h // 3
        sub_y = title_y + 150
        tag_y = sub_y + 100
        accent_y = title_y - 30
    else:
        title_y = h // 2 - 80
        sub_y = title_y + 150
        tag_y = sub_y + 100
        accent_y = title_y - 30

    # 红色装饰条
    accent_w = 80
    accent_h = 6
    accent_x = (w - accent_w) // 2
    draw.rectangle([(accent_x, accent_y), (accent_x + accent_w, accent_y + accent_h)], fill=(220, 40, 40))

    # 标题阴影
    shadow_offset = 3
    title_bbox = font_title.getbbox(TITLE)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((w - title_w) // 2 + shadow_offset, title_y + shadow_offset),
              TITLE, fill=(0, 0, 0, 128), font=font_title)
    draw.text(((w - title_w) // 2, title_y), TITLE, fill=(255, 255, 255), font=font_title)

    # 副标题
    sub_color = (255, 200, 50)  # 金色
    sub_bbox = font_sub.getbbox(SUBTITLE)
    sub_w = sub_bbox[2] - sub_bbox[0]
    draw.text(((w - sub_w) // 2, sub_y), SUBTITLE, fill=sub_color, font=font_sub)

    # 标签
    tag_color = (180, 180, 180)
    tag_bbox = font_tag.getbbox(TAG)
    tag_w = tag_bbox[2] - tag_bbox[0]
    draw.text(((w - tag_w) // 2, tag_y), TAG, fill=tag_color, font=font_tag)

    # 保存
    out_path = os.path.join(OUT_DIR, f"新闻大家谈封面_{label}.jpg")
    bg_cropped.save(out_path, "JPEG", quality=95)
    sz = os.path.getsize(out_path) / 1024
    print(f"  {label} ({w}x{h}): {sz:.0f}KB → {out_path}")
    return out_path

# 主流程
print("生成封面图...")
bg = Image.open(BG_PATH)
bg = bg.resize((bg.width * 2, bg.height * 2), Image.LANCZOS)

results = []
for label, (w, h) in SIZES.items():
    path = create_cover(bg, w, h, label)
    results.append(path)

print(f"\n完成！3 张封面图已保存到 {OUT_DIR}")