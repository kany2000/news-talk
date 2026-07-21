## 使用 Sensenova 配图引擎生成配图

使用 Sensenova 配图引擎生成高质量配图，适用于新闻大家谈项目。

### 步骤

1. **准备话题标题**：将新闻标题组合成话题标题列表。
2. **调用 Sensenova API**：使用 `generate_all` 函数生成配图。
3. **保存配图**：将生成的配图保存到指定路径。

### 示例代码

```python
from gen_news_talk_images import generate_all

topic_titles = [
    "长鑫科技 IPO",
    "信维通信收购益阳电子科技",
    "阿里云下调GLM-5.2价格",
    "海南禁售燃油车",
    "功夫女足票房",
    "玩具总动员5",
    "网络烂梗"
]
generate_all(topic_titles)
```

### 注意事项

- **API Key**：使用已保存的 Sensenova API Key。
- **图片尺寸**：默认生成 2752×1536 分辨率的图片。
- **错误处理**：捕获并处理 HTTP 和网络错误。

### 文件路径

- **脚本路径**：`/home/kan/shared/news-talk/gen_news_talk_images.py`
- **配图输出路径**：`/home/kan/shared/news-talk/images/`

### 依赖

- **Python 库**：`urllib.request`, `json`, `os`, `time`, `sys`, `PIL`

### 使用场景

适用于生成新闻配图，用于新闻大家谈项目。