## MiMo TTS API 中文合成

### 核心端点

| 项目 | 值 |
|------|------|
| 端点 | `https://api.xiaomimimo.com/v1/chat/completions` |
| 认证方式 | Header `api-key` (**非** `Authorization: Bearer`) |
| 模型 | `mimo-v2.5-tts` |
| 女声 | `xiaoxiao`, 男声 | `yunyang` |

### OpenAI 兼容格式

```json
{
  "model": "mimo-v2.5-tts",
  "messages": [
    {"role": "user", "content": "温柔专业的女声，播报新闻，语速适中"},
    {"role": "assistant", "content": "要合成的文本"}
  ],
  "voice_id": "xiaoxiao"
}
```

响应 → `choices[0].message.audio.data` → base64 PCM16 24kHz mono WAV。

### 长文本分段

单次约 500 字上限。用 `synthesize_long_text()`：
- 按新闻条目分段（第1条、第2条...）
- 逐段 API → 合并 PCM → WAV
- 返回精确时长列表 → 精准 SRT

### 错误排除

- **401**：API key 过期。确认用 `api-key` header 而非 `Authorization`
- **404**：端点必须是 `/v1/chat/completions`，不是 `/v1/tts/synthesize` 或 `/v1/audio/speech`
- **SSL EOF**：Python SSL 握手问题，先用 curl 验证

### 脚本路径

- ✅ **生产级实现**：`/home/kan/signal_pop/src/tts_mimo.py`
- ❌ **过时代码**：`/home/kan/shared/news-talk/tts_mimo.py`（错误端点 `api.mimovoice.com`、错误 auth header，不可用）

### 测试

```bash
curl -s -X POST https://api.xiaomimimo.com/v1/chat/completions \
  -H "api-key: sk-c6iihcqs7cldniegn6zkhi4rv5ea6balu913wbrrddeo5odm" \
  -H "Content-Type: application/json" \
  -d '{"model":"mimo-v2.5-tts","messages":[{"role":"user","content":"温柔女声新闻播报"},{"role":"assistant","content":"测试中文语音"}],"voice_id":"xiaoxiao"}'
```