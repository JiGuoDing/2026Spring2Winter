"""读写与哈希工具：统一编码、稳定序列化，保证同内容同哈希。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(_dumps(row) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- 句向量 ---------------------------------------------------------------
def load_query_embeddings(path: Path | None = None):
    """读取 dataset/embeddings/query_embeddings.npz。

    返回 (query_texts, embeddings)。向量已 L2 归一化，行序与 query_texts 对齐。
    未生成时抛 FileNotFoundError，调用方应显式处理而不是静默降级。
    """
    import numpy as np  # 局部导入，避免未用向量的脚本强依赖 numpy

    p = Path(path) if path else (ROOT / "embeddings" / "query_embeddings.npz")
    if not p.is_file():
        raise FileNotFoundError(
            f"{p} 不存在：句向量尚未生成，见 dataset/embeddings/STATUS.md 或 params.embedding")
    z = np.load(p, allow_pickle=False)
    return [str(t) for t in z["query_texts"]], z["embeddings"]


def embedding_lookup(path: Path | None = None) -> dict[str, list[float]]:
    """返回 question_text -> 向量 的字典，便于按请求文本直接查。"""
    texts, mat = load_query_embeddings(path)
    return {t: mat[i].tolist() for i, t in enumerate(texts)}


# ---- 在线/评测字段隔离（v0.4.0） -------------------------------------------
_SPLIT_CACHE: dict | None = None


def load_online_eval_split() -> dict:
    """读取 contracts/ONLINE_EVAL_SPLIT.json。"""
    global _SPLIT_CACHE
    if _SPLIT_CACHE is None:
        _SPLIT_CACHE = read_json(ROOT / "contracts" / "ONLINE_EVAL_SPLIT.json")
    return _SPLIT_CACHE


def strip_eval_fields(record: dict, kind: str) -> dict:
    """返回只保留 online_visible 字段的浅拷贝，防止在线策略读取评测真值。"""
    tables = load_online_eval_split()["tables"]
    if kind not in tables:
        raise KeyError(f"未知表名 {kind}，可选: {sorted(tables)}")
    allowed = set(tables[kind]["online_visible"])
    return {k: v for k, v in record.items() if k in allowed}
