"""下载 bge-reranker-v2-m3 INT8 量化 ONNX 模型至 dataset/embeddings/cache/（不进 MANIFEST）。

优先使用 huggingface_hub.hf_hub_download，支持 HF_ENDPOINT（如 https://hf-mirror.com）。
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "embeddings" / "cache" / "bge-reranker-v2-m3-onnx"

CANDIDATES = [
    ("onnx-community/bge-reranker-v2-m3-ONNX", "onnx/model_quantized.onnx", "tokenizer.json"),
    ("woxpas-ai/bge-reranker-v2-m3-onnx", "onnx/model_quantized.onnx", "tokenizer.json"),
]


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target_onnx = CACHE_DIR / "model_quantized.onnx"
    target_tok = CACHE_DIR / "tokenizer.json"
    if target_onnx.is_file() and target_tok.is_file() and target_onnx.stat().st_size > 10_000_000:
        print(f"已存在缓存模型：{target_onnx} ({target_onnx.stat().st_size/1e6:.1f} MB)")
        return 0

    endpoints = [os.environ.get("HF_ENDPOINT") or "https://huggingface.co", "https://hf-mirror.com"]
    last_err: Exception | None = None
    for ep in endpoints:
        os.environ["HF_ENDPOINT"] = ep
        for repo_id, onnx_file, tok_file in CANDIDATES:
            try:
                print(f"尝试从 {ep} 下载 {repo_id} ({onnx_file}, {tok_file}) ...")
                p_tok = hf_hub_download(repo_id=repo_id, filename=tok_file)
                p_onnx = hf_hub_download(repo_id=repo_id, filename=onnx_file)
                shutil.copy2(p_tok, target_tok)
                shutil.copy2(p_onnx, target_onnx)
                (CACHE_DIR / "source.txt").write_text(f"{ep} | {repo_id} | {onnx_file}\n", encoding="utf-8")
                print(f"下载完成：{target_onnx} ({target_onnx.stat().st_size/1e6:.1f} MB)")
                return 0
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                print(f"  失败 ({repo_id} @ {ep}): {type(exc).__name__}: {exc}")
    print(f"ERROR: 全部源均下载失败: {last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
