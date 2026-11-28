"""现代六阶段块级标准 RAG 引擎（v0.5.0，2025–2026 顶会范式）。

六阶段流水线：
  1. Pre-Filter       : 按 RBAC 偏序 PRIV[doc.perm] <= PRIV[req.perm] 与系统已知版本 sys_ver(doc, ts) 过滤活跃块；
  2. Contextual BM25  : 中文 bigram + 英文标识符分词，在带上下文前缀块上召回 Top-30；
  3. Dense Search     : 实时调用 bge-small-zh-v1.5 ONNX 编码 query_text，与块向量矩阵内积召回 Top-30；
  4. RRF Fusion       : k=60 融合两路候选至 Top-20；
  5. Neural Reranker  : 调用 bge-reranker-v2-m3 INT8 ONNX 交叉打分，Per-Doc Cap=2，
                        按验证集校准阈值 tau_rerank 动态截断（K in [3, 8]）；
  6. Sides Repacking  : 抗中间遗忘首尾重排 + 8,000 字符预算打包，输出结构化 (doc_id, chunk_id, ver, score)。

可供动机实验与 C1–C4 回放器直接 import 使用。
"""
from __future__ import annotations

import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "labels"))

import build as labels_build  # noqa: E402
from common import io  # noqa: E402

EMB_CACHE = ROOT / "embeddings" / "cache" / "Xenova--bge-small-zh-v1.5"
RERANK_CACHE = ROOT / "embeddings" / "cache" / "bge-reranker-v2-m3-onnx"
CHUNK_NPZ = ROOT / "embeddings" / "chunk_embeddings.npz"
DOCS_PATH = ROOT / "events" / "docs_versioned.jsonl"

_TOK_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[\u4e00-\u9fff]+")


def tokenize_bm25(text: str) -> list[str]:
    out: list[str] = []
    for m in _TOK_RE.finditer(text.lower()):
        w = m.group()
        if w[0].isascii():
            out.append(w)
        else:
            if len(w) == 1:
                out.append(w)
            else:
                for i in range(len(w) - 1):
                    out.append(w[i : i + 2])
    return out


def contextual_text(doc: dict, chunk: dict) -> str:
    return (
        f"[{doc['doc_type']} | {doc['domain']} | {doc['doc_id']}@v{doc['version']} | {doc['permission']}] "
        f"{chunk['text']}"
    )


def sides_repack(items: list[dict], max_chars: int = 8000) -> tuple[list[dict], str]:
    """Lost-in-the-Middle Sides Repacking：最高分放首尾、次相关放中间。"""
    n = len(items)
    if n <= 2:
        ordered = list(items)
    else:
        left: list[dict] = []
        right: list[dict] = []
        for idx, it in enumerate(items):
            if idx % 2 == 0:
                left.append(it)
            else:
                right.append(it)
        ordered = left + list(reversed(right))

    packed: list[dict] = []
    parts: list[str] = []
    used = 0
    for it in ordered:
        seg = f"[{it['doc_id']}@{it['version']}#{it['chunk_id']}] {it['text']}"
        if used + len(seg) > max_chars and packed:
            break
        packed.append(it)
        parts.append(seg)
        used += len(seg) + 1
    return packed, "\n".join(parts)


class ModernRAGPipeline:
    """现代六阶段块级 RAG 流水线（支持 4 种消融模式）。"""

    def __init__(self, load_reranker: bool = True, threads: int = 4) -> None:
        self.ds = labels_build.Dataset()
        z = np.load(CHUNK_NPZ, allow_pickle=False)
        self.chunk_keys = [str(x) for x in z["chunk_keys"]]
        self.doc_ids = [str(x) for x in z["doc_ids"]]
        self.versions = z["versions"].astype(np.int32)
        self.chunk_ids = [str(x) for x in z["chunk_ids"]]
        self.perms = [str(x) for x in z["permissions"]]
        self.perm_levels = np.array([labels_build.PRIV[p] for p in self.perms], dtype=np.int32)
        self.embeddings = z["embeddings"].astype(np.float32)

        # 读取块正文与上下文前缀文本（与 chunk_keys 同序）
        self.raw_texts: list[str] = []
        self.ctx_texts: list[str] = []
        self.doc_ver_to_indices: dict[tuple[str, int], list[int]] = defaultdict(list)
        idx = 0
        for doc in io.read_jsonl(DOCS_PATH):
            dv = (doc["doc_id"], int(doc["version"]))
            for ch in doc["chunks"]:
                self.raw_texts.append(ch["text"])
                self.ctx_texts.append(contextual_text(doc, ch))
                self.doc_ver_to_indices[dv].append(idx)
                idx += 1
        assert idx == len(self.chunk_keys), f"块数不一致: {idx} != {len(self.chunk_keys)}"

        # 预建 Contextual BM25 倒排索引
        self.n_chunks = len(self.ctx_texts)
        self.doc_lens = np.zeros(self.n_chunks, dtype=np.float32)
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, txt in enumerate(self.ctx_texts):
            toks = tokenize_bm25(txt)
            self.doc_lens[i] = len(toks)
            tf = Counter(toks)
            for term, cnt in tf.items():
                self.postings[term].append((i, cnt))
        self.avgdl = float(self.doc_lens.mean()) if self.n_chunks else 1.0
        self.idf: dict[str, float] = {
            t: math.log((self.n_chunks - len(pl) + 0.5) / (len(pl) + 0.5) + 1.0)
            for t, pl in self.postings.items()
        }

        # 加载 Query 实时编码器（bge-small-zh-v1.5 ONNX）
        self.q_tok = Tokenizer.from_file(str(EMB_CACHE / "tokenizer.json"))
        self.q_tok.enable_truncation(max_length=512)
        opts_q = ort.SessionOptions()
        opts_q.intra_op_num_threads = threads
        self.q_sess = ort.InferenceSession(
            str(EMB_CACHE / "onnx" / "model.onnx"), sess_options=opts_q, providers=["CPUExecutionProvider"]
        )
        self.q_in_names = {i.name for i in self.q_sess.get_inputs()}

        # 加载现代神经重排器（bge-reranker-v2-m3 INT8 ONNX）
        self.rerank_sess = None
        self.rerank_tok = None
        self.rerank_in_names: set[str] = set()
        if load_reranker:
            onnx_p = RERANK_CACHE / "model_quantized.onnx"
            tok_p = RERANK_CACHE / "tokenizer.json"
            assert onnx_p.is_file() and tok_p.is_file(), f"缺少重排模型，请先运行 download_reranker.py: {RERANK_CACHE}"
            self.rerank_tok = Tokenizer.from_file(str(tok_p))
            self.rerank_tok.enable_truncation(max_length=512)
            self.rerank_tok.enable_padding(pad_id=1, pad_token="<pad>")
            opts_r = ort.SessionOptions()
            opts_r.intra_op_num_threads = threads
            self.rerank_sess = ort.InferenceSession(
                str(onnx_p), sess_options=opts_r, providers=["CPUExecutionProvider"]
            )
            self.rerank_in_names = {i.name for i in self.rerank_sess.get_inputs()}

        self._active_cache: dict[tuple[str, int], tuple[np.ndarray, set[int]]] = {}

    def _active_indices(self, timestamp: str, perm_level: int) -> tuple[np.ndarray, set[int]]:
        """阶段 1：RBAC (PRIV[doc.perm] <= PRIV[req.perm]) 与 sys_ver(doc, ts) 前置过滤。"""
        # 缓存键：按系统已知版本变化边界（每分钟级或直接按 (ts, perm_level) 缓存）
        key = (timestamp, perm_level)
        hit = self._active_cache.get(key)
        if hit is not None:
            return hit
        active: list[int] = []
        for doc_id in self.ds.docs:
            v = self.ds.sys_ver(doc_id, timestamp)
            for idx in self.doc_ver_to_indices[(doc_id, v)]:
                if self.perm_levels[idx] <= perm_level:
                    active.append(idx)
        arr = np.array(active, dtype=np.int32)
        res = (arr, set(active))
        if len(self._active_cache) < 64:
            self._active_cache[key] = res
        return res

    def encode_query(self, query_text: str) -> np.ndarray:
        enc = self.q_tok.encode(query_text)
        ids = np.array([enc.ids], dtype=np.int64)
        mask = np.array([enc.attention_mask], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self.q_in_names:
            feeds["token_type_ids"] = np.zeros_like(ids, dtype=np.int64)
        hidden = self.q_sess.run(None, feeds)[0]
        vec = hidden[0, 0, :].astype(np.float32)
        vec /= max(float(np.linalg.norm(vec)), 1e-12)
        return vec

    def bm25_search(self, query_text: str, active_set: set[int], top_k: int = 30) -> list[tuple[int, float]]:
        k1, b = 1.5, 0.75
        scores: dict[int, float] = defaultdict(float)
        for term in tokenize_bm25(query_text):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for idx, tf in self.postings[term]:
                if idx not in active_set:
                    continue
                dl = self.doc_lens[idx]
                scores[idx] += idf * (tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * dl / self.avgdl))
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def dense_search(self, q_vec: np.ndarray, active_arr: np.ndarray, top_k: int = 30) -> list[tuple[int, float]]:
        sims = self.embeddings[active_arr] @ q_vec
        k = min(top_k, len(sims))
        if k <= 0:
            return []
        part = np.argpartition(sims, -k)[-k:]
        top_local = part[np.argsort(sims[part])[::-1]]
        return [(int(active_arr[i]), float(sims[i])) for i in top_local]

    @staticmethod
    def rrf_fuse(bm25_list: list[tuple[int, float]], dense_list: list[tuple[int, float]],
                 k_rrf: int = 60, top_k: int = 20) -> list[tuple[int, float]]:
        fused: dict[int, float] = defaultdict(float)
        for rank, (idx, _) in enumerate(bm25_list, 1):
            fused[idx] += 1.0 / (k_rrf + rank)
        for rank, (idx, _) in enumerate(dense_list, 1):
            fused[idx] += 1.0 / (k_rrf + rank)
        return sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def rerank(self, query_text: str, cand_indices: list[int]) -> list[tuple[int, float]]:
        assert self.rerank_sess is not None and self.rerank_tok is not None
        if not cand_indices:
            return []
        pairs = [(query_text, self.ctx_texts[i]) for i in cand_indices]
        encs = self.rerank_tok.encode_batch(pairs)
        ids = np.array([e.ids for e in encs], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self.rerank_in_names:
            feeds["token_type_ids"] = np.zeros_like(ids, dtype=np.int64)
        logits = self.rerank_sess.run(None, feeds)[0].reshape(-1).astype(np.float64)
        probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -30.0, 30.0)))
        scored = [(cand_indices[i], float(probs[i])) for i in range(len(cand_indices))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def retrieve(
        self,
        req: dict,
        mode: str = "hybrid_rrf_rerank_dynamic",
        tau_rerank: float = 0.25,
        k_min: int = 3,
        k_max: int = 8,
        per_doc_cap: int = 2,
        rerank_top_k: int = 12,
    ) -> dict:
        """执行指定模式的检索并返回结果与各阶段精确墙钟耗时（ms）。"""
        perm_level = labels_build.PRIV[req["permission"]]
        t0 = time.perf_counter()
        active_arr, active_set = self._active_indices(req["timestamp"], perm_level)
        t_prefilter = (time.perf_counter() - t0) * 1000.0

        t_q_enc = 0.0
        t_bm25 = 0.0
        t_dense = 0.0
        t_rrf = 0.0
        t_rerank = 0.0

        bm25_res: list[tuple[int, float]] = []
        dense_res: list[tuple[int, float]] = []

        if mode in ("bm25_only", "hybrid_rrf", "hybrid_rrf_rerank_dynamic"):
            t1 = time.perf_counter()
            bm25_res = self.bm25_search(req["query_text"], active_set, top_k=30)
            t_bm25 = (time.perf_counter() - t1) * 1000.0

        if mode in ("dense_only", "hybrid_rrf", "hybrid_rrf_rerank_dynamic"):
            t1 = time.perf_counter()
            q_vec = self.encode_query(req["query_text"])
            t_q_enc = (time.perf_counter() - t1) * 1000.0
            t2 = time.perf_counter()
            dense_res = self.dense_search(q_vec, active_arr, top_k=30)
            t_dense = (time.perf_counter() - t2) * 1000.0

        if mode == "bm25_only":
            ranked = bm25_res
        elif mode == "dense_only":
            ranked = dense_res
        else:
            t1 = time.perf_counter()
            fused = self.rrf_fuse(bm25_res, dense_res, k_rrf=60, top_k=rerank_top_k)
            t_rrf = (time.perf_counter() - t1) * 1000.0
            if mode == "hybrid_rrf":
                ranked = fused
            else:
                t2 = time.perf_counter()
                ranked = self.rerank(req["query_text"], [i for i, _ in fused])
                t_rerank = (time.perf_counter() - t2) * 1000.0

        # Per-Doc Cap + Dynamic Cutoff（仅 dynamic 模式按阈值截断）
        t_pack0 = time.perf_counter()
        selected: list[dict] = []
        doc_cnt: dict[str, int] = defaultdict(int)
        for idx, sc in ranked:
            did = self.doc_ids[idx]
            if doc_cnt[did] >= per_doc_cap:
                continue
            if mode == "hybrid_rrf_rerank_dynamic" and len(selected) >= k_min and sc < tau_rerank:
                break
            doc_cnt[did] += 1
            selected.append({
                "doc_id": did,
                "version": int(self.versions[idx]),
                "chunk_id": self.chunk_ids[idx],
                "score": round(sc, 6),
                "text": self.raw_texts[idx],
            })
            if len(selected) >= k_max:
                break

        packed, context_str = sides_repack(selected, max_chars=8000)
        t_repack = (time.perf_counter() - t_pack0) * 1000.0
        t_total = t_prefilter + t_q_enc + t_bm25 + t_dense + t_rrf + t_rerank + t_repack

        return {
            "items": packed,
            "context_chars": len(context_str),
            "k_returned": len(packed),
            "timings_ms": {
                "prefilter": round(t_prefilter, 4),
                "query_encode": round(t_q_enc, 4),
                "bm25": round(t_bm25, 4),
                "dense": round(t_dense, 4),
                "rrf": round(t_rrf, 4),
                "rerank": round(t_rerank, 4),
                "repack": round(t_repack, 4),
                "e2e_rag": round(t_total, 4),
            },
        }
