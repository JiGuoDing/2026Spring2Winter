"""上下文增强块级向量索引构建（v0.5.0，确定性 ONNX CPU 推理）。

复用本机已缓存的 Xenova/bge-small-zh-v1.5 ONNX（与 query_embeddings.npz 同向量空间），
对 events/docs_versioned.jsonl 中全部 13,770 个版本块构造上下文增强文本：
    [{doc_type} | {domain} | {doc_id}@v{version} | {permission}] {chunk.text}
批量编码为 L2 归一化的 float32 矩阵并写入确定性 ZIP：
    dataset/embeddings/chunk_embeddings.npz
    dataset/embeddings/chunk_embeddings.meta.json
"""
from __future__ import annotations

import hashlib
import io as pyio
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402

CACHE_DIR = ROOT / "embeddings" / "cache" / "Xenova--bge-small-zh-v1.5"
ONNX_PATH = CACHE_DIR / "onnx" / "model.onnx"
TOK_PATH = CACHE_DIR / "tokenizer.json"
DOCS_PATH = ROOT / "events" / "docs_versioned.jsonl"
OUT_NPZ = ROOT / "embeddings" / "chunk_embeddings.npz"
OUT_META = ROOT / "embeddings" / "chunk_embeddings.meta.json"

MAX_LEN = 512
BATCH_SIZE = 64


def contextual_text(doc: dict, chunk: dict) -> str:
    return (
        f"[{doc['doc_type']} | {doc['domain']} | {doc['doc_id']}@v{doc['version']} | {doc['permission']}] "
        f"{chunk['text']}"
    )


def save_deterministic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(arrays):
            buf = pyio.BytesIO()
            np.save(buf, arrays[name], allow_pickle=False)
            zi = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, buf.getvalue())


def encode_texts(texts: list[str], batch_size: int = BATCH_SIZE) -> np.ndarray:
    assert ONNX_PATH.is_file() and TOK_PATH.is_file(), f"缺少本地缓存模型: {CACHE_DIR}"
    tok = Tokenizer.from_file(str(TOK_PATH))
    tok.enable_truncation(max_length=MAX_LEN)
    tok.enable_padding(pad_id=0, pad_token="[PAD]")

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 4
    opts.inter_op_num_threads = 1
    sess = ort.InferenceSession(str(ONNX_PATH), sess_options=opts, providers=["CPUExecutionProvider"])
    in_names = {i.name for i in sess.get_inputs()}

    n = len(texts)
    # 按长度稳定排序，避免单个长块把整批 pad 到过长序列
    order = sorted(range(n), key=lambda i: (len(texts[i]), i))
    out = np.empty((n, 512), dtype=np.float32)
    t0 = time.perf_counter()
    for start in range(0, n, batch_size):
        idxs = order[start : start + batch_size]
        batch = [texts[i] for i in idxs]
        encs = tok.encode_batch(batch)
        input_ids = np.array([e.ids for e in encs], dtype=np.int64)
        attn_mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
        feeds = {"input_ids": input_ids, "attention_mask": attn_mask}
        if "token_type_ids" in in_names:
            feeds["token_type_ids"] = np.zeros_like(input_ids, dtype=np.int64)
        hidden = sess.run(None, feeds)[0]
        cls = hidden[:, 0, :].astype(np.float32)
        norms = np.linalg.norm(cls, axis=1, keepdims=True)
        cls /= np.maximum(norms, 1e-12)
        for j, orig_i in enumerate(idxs):
            out[orig_i] = cls[j]
        done = min(n, start + batch_size)
        if done % 2048 == 0 or done == n:
            print(f"  已编码 {done}/{n} 块 ({time.perf_counter() - t0:.1f}s)", flush=True)
    return out


def main() -> int:
    t0 = time.perf_counter()
    chunk_keys: list[str] = []
    doc_ids: list[str] = []
    versions: list[int] = []
    chunk_ids: list[str] = []
    permissions: list[str] = []
    texts: list[str] = []

    for doc in io.read_jsonl(DOCS_PATH):
        for ch in doc["chunks"]:
            key = f"{doc['doc_id']}@v{doc['version']}::{ch['chunk_id']}"
            chunk_keys.append(key)
            doc_ids.append(doc["doc_id"])
            versions.append(int(doc["version"]))
            chunk_ids.append(ch["chunk_id"])
            permissions.append(doc["permission"])
            texts.append(contextual_text(doc, ch))

    print(f"开始编码 {len(texts)} 个上下文增强块（bge-small-zh-v1.5 ONNX，单线程确定性）...")
    mat = encode_texts(texts)

    save_deterministic_npz(
        OUT_NPZ,
        {
            "chunk_keys": np.array(chunk_keys),
            "doc_ids": np.array(doc_ids),
            "versions": np.array(versions, dtype=np.int32),
            "chunk_ids": np.array(chunk_ids),
            "permissions": np.array(permissions),
            "embeddings": mat,
        },
    )

    elapsed = time.perf_counter() - t0
    mat_sha = hashlib.sha256(mat.tobytes()).hexdigest()
    npz_sha = io.sha256_file(OUT_NPZ)
    meta = {
        "model": "BAAI/bge-small-zh-v1.5",
        "onnx_repo": "Xenova/bge-small-zh-v1.5",
        "count": len(texts),
        "dim": int(mat.shape[1]),
        "normalize": "l2",
        "contextual_prefix": "[doc_type | domain | doc_id@vX | permission] text",
        "matrix_sha256": mat_sha,
        "npz_sha256": npz_sha,
        "bytes": OUT_NPZ.stat().st_size,
    }
    io.write_json(OUT_META, meta)
    print(f"完成 {OUT_NPZ}（{mat.shape}, {meta['bytes']/1e6:.2f} MB, {elapsed:.1f}s, sha256={npz_sha[:16]}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
