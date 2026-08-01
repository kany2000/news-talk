# 新闻大家谈 — 多平台发布指南

## 视频制作流程（含英文字幕 + 发布文案）

每个视频（尤其耶鲁公开课系列）制作完成后，**必须额外生成**：

**① 英文字幕文件**
1. 中文 SRT 转写并修正错别字
2. 翻译成英文，输出 `audio/subtitles_en.srt`（保留原时间戳，术语准确）
3. 只出英文字幕文件，**不做英文字幕版的视频**（不烧录英文硬字幕）
4. 参考脚本：`scripts/translate_ep2_en.py`（Python 内嵌段号→英文翻译表）

**② 全平台发布文案 MD**
1. 写 `发布文案.md` 放进当期 `output/` 目录
2. 覆盖 7 平台：B站/抖音/快手/小红书/微信视频号/YouTube/Facebook
3. 每平台含标题/正文/标签；YouTube/Facebook 用英文
4. 注明封面尺寸（B站 16:9，抖音/快手/小红书/视频号 3:4）
5. 参考：`yale大学公开课系列讲谈/第二期/output/发布文案.md`

## 工具

`social-auto-upload` at `E:\projects\social-auto-upload\`

## 已登录平台（cookie 有效）

| 平台 | 账号 | 登录状态 |
|------|------|---------|
| Bilibili | her2home | ✅ |
| 抖音 | her2home | ✅ |
| 快手 | her2home | ✅ |
| 小红书 | her2home | ✅ |
| 视频号 | signalpop | ✅ |
| YouTube | her2home | ❌ 需重新登录 |

## 通用发布命令

```bash
cd E:\projects\social-auto-upload

# B站（知识区 tid=171）
python sau_cli.py bilibili upload-video \
  --account her2home \
  --file "视频路径" \
  --title "标题" \
  --desc "简介" \
  --tid 171 \
  --tags "标签1,标签2"

# 抖音
python sau_cli.py douyin upload-video \
  --account her2home \
  --file "视频路径" \
  --title "标题" \
  --desc "描述" \
  --tags "标签1,标签2" \
  --thumbnail "封面图_3-4.jpg"

# 快手
python sau_cli.py kuaishou upload-video \
  --account her2home \
  --file "视频路径" \
  --title "标题" \
  --desc "描述" \
  --tags "标签1,标签2" \
  --thumbnail "封面图.jpg"

# 小红书
python sau_cli.py xiaohongshu upload-video \
  --account her2home \
  --file "视频路径" \
  --title "标题" \
  --desc "描述" \
  --tags "标签1,标签2" \
  --thumbnail "封面图.jpg"

# 视频号
python sau_cli.py tencent upload-video \
  --account signalpop \
  --file "视频路径" \
  --title "标题" \
  --desc "描述" \
  --tags "标签1,标签2" \
  --thumbnail "封面图_3-4.jpg"

# YouTube（需要先重新登录）
python sau_cli.py youtube login --account her2home
python sau_cli.py youtube upload-video \
  --account her2home \
  --file "视频路径" \
  --title "Title" \
  --desc "Description" \
  --tags "tag1,tag2"
```

## 发布流程

1. 我确认哪些平台 cookie 有效
2. 我逐个平台执行上传命令
3. 如果遇到问题（如登录过期、页面变化），我会告诉你需要做什么

## 注意事项

- **快手**：浏览器自动化发布时，最后一步页面跳转检测可能超时，但视频实际已发布。如果失败，需要手动去快手创作者后台检查确认
- **YouTube**：cookie 容易过期，需要定期重新登录
- **封面图**：抖音/视频号需要 3:4 竖版封面，B站用 16:9 横版封面
- **B站分区 tid**：171=知识区, 124=财经, 181=科技