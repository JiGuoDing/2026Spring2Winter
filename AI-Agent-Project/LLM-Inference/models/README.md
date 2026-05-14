# 模型存放目录

请将下载好的模型目录放到此处。

## 推荐模型（适合 2GB 显存）

| 简称 | HuggingFace ID | 显存占用 |
|------|---------------|---------|
| smollm2-135m | HuggingFaceTB/SmolLM2-135M-Instruct | ~0.27 GB |
| smollm2-360m | HuggingFaceTB/SmolLM2-360M-Instruct | ~0.72 GB |
| qwen2.5-0.5b | Qwen/Qwen2.5-0.5B-Instruct | ~1.0 GB |
| tinyllama | TinyLlama/TinyLlama-1.1B-Chat-v1.0 | ~2.2 GB |
| qwen2.5-1.5b | Qwen/Qwen2.5-1.5B-Instruct | ~3.0 GB |

## 下载方式

使用 HuggingFace CLI：

```bash
huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct --local-dir models/qwen2.5-0.5b
```

或使用 Python：

```python
from huggingface_hub import snapshot_download
snapshot_download("Qwen/Qwen2.5-0.5B-Instruct", local_dir="models/qwen2.5-0.5b")
```
