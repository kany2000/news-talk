#!/usr/bin/env python3
"""修复 Yale EP1 字幕错别字"""
import re
from pathlib import Path

SRT = Path("E:/projects/news-talk/yale大学公开课系列讲谈/audio/subtitles.srt")
text = SRT.read_text(encoding="utf-8")

# 错别字映射
REPLACEMENTS = [
    ("梦魅以求", "梦寐以求"),
    ("晃能篇", "幻灯片"),
    ("求图困境", "囚徒困境"),
    ("传审", "传神"),
    ("必引", "B minus"),
    ("居于大的悲伦", "巨大的悲剧"),
    ("双书", "双输"),
    ("吴效", "无效"),
    ("抵效", "低效"),
    ("内就", "内疚"),
    ("扩分", "扣分"),
    ("韩类", "含泪"),
    ("战优策略", "占优策略"),
    ("占优策略", "占优策略"),  # 确保一致
    ("剧震", "矩阵"),
    ("辩量", "变量"),
    ("价值习惯", "驾驶习惯"),
    ("代容", "代入"),
    ("优展", "骤降"),
    ("拒绝", "咀嚼"),
    ("结构期", "结构体系"),
    ("总确", "正确"),
    ("摘", "这"),
    ("风填汽车", "丰田汽车"),
    ("命审", "命运"),
    ("归述", "龟速"),
    ("作响称入", "坐享其成"),
    ("将不将", "降不降"),
    ("分文", "份额"),
    ("运动", "运转"),
    ("每具", "美剧"),
    ("黑道家族", "黑道家族"),  # 正确, 保留
    ("系", "系统"),  # 上下文: 内心系 -> 内心系统
    ("Bm", "B minus"),
    ("Bb", "B plus"),
    ("Bminers", "B minus"),
    ("壁盖", "B minus"),
    ("壁Plus", "B plus"),
    ("双壁盖", "双B minus"),
    ("双壁Plus", "双B plus"),
    ("pan", "嗯"),
    ("She", "嗯"),
    ("fe", "嗯"),
    ("bl", "嗯"),
    ("的p", "的"),  # 手误
]

count = 0
for old, new in REPLACEMENTS:
    n = text.count(old)
    if n > 0:
        text = text.replace(old, new)
        count += n
        print(f"  {old} -> {new}  ({n}处)")

SRT.write_text(text, encoding="utf-8")
print(f"\n共修复 {count} 处错别字")