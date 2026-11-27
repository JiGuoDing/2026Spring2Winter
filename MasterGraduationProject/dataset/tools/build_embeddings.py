"""真实句向量构建：BGE-small-zh-v1.5（ONNX）→ dataset/embeddings/query_embeddings.npz。

为什么走 ONNX 而不是 sentence-transformers
------------------------------------------
本机没有 torch / sentence-transformers / transformers，也不允许为了一次向量化安装
~2 GB 的 torch。BAAI/bge-small-zh-v1.5 的 ONNX 导出（Xenova/bge-small-zh-v1.5）
只需 onnxruntime + numpy，模型本体 94.85 MB，CPU 推理即可。分词用 tokenizers
（0.44 MB 的 Rust 绑定），装不上时回退到纯 Python 的 BERT WordPiece（本脚本内置，
已在 600 条问句上与 tokenizers 逐 token 比对一致，见 README 第 4 节）。

输出
----
``dataset/embeddings/query_embeddings.npz``（确定性 ZIP，键固定）：
  - ``query_texts``  : 去重后的唯一问句（``<U`` 数组，按 request_stream 首次出现排序）
  - ``embeddings``   : float32 N×512，**L2 归一化**（CLS pooling）
  - ``model`` / ``dim`` / ``normalized`` / ``pooling`` : 元数据（0 维字符串/整型数组）
``query_embeddings.meta.json``、``MANIFEST.json``、``README.md`` 见同目录说明。

确定性
------
同一脚本、同一输入、同一模型文件，两次构建的 ``query_embeddings.npz`` 逐字节相同：
  - 推理用单线程 CPUExecutionProvider；
  - 按 token 长度排序后定长分批，padding 位置由 attention_mask 屏蔽；
  - NPZ 用固定 ZIP 时间戳（1980-01-01）自写，规避 numpy.savez 写入当前时间导致的哈希漂移；
  - 元数据不含时间戳。脚本会打印 ``matrix_sha256`` 与 ``npz_sha256`` 供比对。

禁止事项
--------
``config/params.json`` 的 ``embedding.note`` 明确禁止用 TF-IDF / 随机向量冒充语义向量。
本脚本只输出真实 BGE 模型推理结果；网络或依赖不可用时写 ``STATUS.md`` 说明失败原因，
不生成 npz，绝不写占位向量。

用法
----
    python dataset/tools/build_embeddings.py --dry-run          # 只校验，不下载、不写文件
    python dataset/tools/build_embeddings.py                    # 首次运行会下载模型到 embeddings/cache/
    python dataset/tools/build_embeddings.py --verify-tokenizer # 额外做 tokenizers vs 纯 Python 分词比对
    python dataset/tools/build_embeddings.py --out /tmp/emb --limit 50   # 调试用
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

SCRIPT_VERSION = "0.2.0"

HERE = Path(__file__).resolve().parent          # dataset/tools
DATASET = HERE.parent                           # dataset/
EMB_DIR = DATASET / "embeddings"
CACHE_DIR = EMB_DIR / "cache" / "Xenova--bge-small-zh-v1.5"

STREAM = DATASET / "events" / "request_stream.jsonl"
PARAMS = DATASET / "config" / "params.json"

NPZ_NAME = "query_embeddings.npz"
META_NAME = "query_embeddings.meta.json"
MANIFEST_NAME = "MANIFEST.json"
STATUS_NAME = "STATUS.md"

MODEL_ID = "BAAI/bge-small-zh-v1.5"
ONNX_REPO = "Xenova/bge-small-zh-v1.5"
ONNX_COMMIT = "75c43b069aac4d136ba6bc1122f995fedcfd2781"   # 2025-07-22，与本机缓存的 sha256 一致
MAX_LEN = 512
POOLING = "cls"
NORMALIZE = "l2"

# 固定下载清单：commit + size + sha256 三重校验，保证"同一份权重"可跨机器复现。
# sha256 来自 HuggingFace LFS oid / 下载后本地复核，改上游文件即校验失败。
MODEL_FILES: dict[str, dict] = {
    "onnx/model.onnx": {
        "size": 94_851_877,
        "sha256": "69a0b846f4f116b5e6aabf9546ea6754d02264f3211a13a1bd69b31b8040749a",
    },
    "tokenizer.json": {
        "size": 439_125,
        "sha256": "48cea5d44424912a6fd1ea647bf4fe50b55ab8b1e5879c3275f80e339e8fae26",
    },
    "vocab.txt": {
        "size": 109_540,
        "sha256": "45bbac6b341c319adc98a532532882e91a9cefc0329aa57bac9ae761c27b291c",
    },
    "config.json": {
        "size": 716,
        "sha256": "d4193ead3a810fd694fa8a31d7fc72fbaebc0668b603e398734bf2f6538ff42f",
    },
    "tokenizer_config.json": {
        "size": 367,
        "sha256": "e6f3b96db926a37d4039995fbf5ad17de158dfb8f6343d607e4dbaad18d75f5a",
    },
    "special_tokens_map.json": {
        "size": 125,
        "sha256": "b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3",
    },
}
HF_BASE = f"https://huggingface.co/{ONNX_REPO}/resolve/{ONNX_COMMIT}"


# ------------------------------------------------------------------ 基础工具
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def line_count(path: Path) -> int:
    with path.open("rb") as f:
        return sum(1 for _ in f)


class BuildError(RuntimeError):
    """环境/依赖/模型层面的失败；真实构建时据此写 STATUS.md。"""


# ------------------------------------------------------------------ 参数与输入
def load_params() -> dict:
    data = json.loads(PARAMS.read_text(encoding="utf-8"))
    block = data.get("embedding") or {}
    problems: list[str] = []
    if block.get("model") != MODEL_ID:
        problems.append(f"embedding.model={block.get('model')!r}，本脚本只实现 {MODEL_ID!r}")
    if int(block.get("dim", -1)) != 512:
        problems.append(f"embedding.dim={block.get('dim')!r}，BGE-small-zh-v1.5 为 512")
    if block.get("normalize") != NORMALIZE:
        problems.append(f"embedding.normalize={block.get('normalize')!r}，要求 {NORMALIZE!r}")
    expected = f"embeddings/{NPZ_NAME}"
    if block.get("path") != expected:
        problems.append(f"embedding.path={block.get('path')!r}，要求 {expected!r}")
    if problems:
        raise BuildError("config/params.json 的 embedding 块与本脚本不一致：\n  - " + "\n  - ".join(problems))
    return block


def load_unique_texts(stream: Path, limit: int = 0) -> tuple[list[str], int]:
    """按首次出现顺序返回去重问句；返回 (texts, 原始行数)。"""
    texts: list[str] = []
    seen: set[str] = set()
    rows = 0
    with stream.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows += 1
            q = row.get("query_text")
            if not isinstance(q, str) or not q:
                raise BuildError(f"{stream} 第 {rows} 行 query_text 非法：{q!r}")
            if q not in seen:
                seen.add(q)
                texts.append(q)
                if limit and len(texts) >= limit:
                    break
    if not texts:
        raise BuildError(f"{stream} 中没有可用 query_text")
    return texts, rows


# ------------------------------------------------------------------ 分词器
def load_vocab(path: Path) -> dict[str, int]:
    """读 BERT 词表。

    注意不能用 ``str.splitlines()``：词表第 343 项是 U+2028（Unicode 行分隔符），
    splitlines() 会把它拆成两行，导致其后所有 token id 整体错位。
    """
    raw = path.read_text(encoding="utf-8", newline="")
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return {(line[:-1] if line.endswith("\r") else line): i for i, line in enumerate(lines)}


def _is_control(ch: str) -> bool:
    if ch in ("\t", "\n", "\r"):
        return False
    return unicodedata.category(ch).startswith("C")


def _is_whitespace(ch: str) -> bool:
    return ch in (" ", "\t", "\n", "\r") or unicodedata.category(ch) == "Zs"


def _is_cjk(cp: int) -> bool:
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0x20000 <= cp <= 0x2A6DF or 0x2A700 <= cp <= 0x2B73F
            or 0x2B740 <= cp <= 0x2B81F or 0x2B820 <= cp <= 0x2CEAF
            or 0xF900 <= cp <= 0xFAFF or 0x2F800 <= cp <= 0x2FA1F)


def _is_punctuation(ch: str) -> bool:
    cp = ord(ch)
    if 33 <= cp <= 47 or 58 <= cp <= 64 or 91 <= cp <= 96 or 123 <= cp <= 126:
        return True
    return unicodedata.category(ch).startswith("P")


def _clean_text(text: str) -> str:
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if cp == 0 or cp == 0xFFFD or _is_control(ch):
            continue
        out.append(" " if _is_whitespace(ch) else ch)
    return " ".join("".join(out).split())


def _tokenize_chinese_chars(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if _is_cjk(ord(ch)):
            out.extend((" ", ch, " "))
        else:
            out.append(ch)
    return "".join(out)


def _basic_split(text: str) -> list[str]:
    """BERT BasicTokenizer：CJK 逐字、ASCII 标点独立、按空白切分。"""
    toks: list[str] = []
    for tok in _tokenize_chinese_chars(text).split():
        cur: list[str] = []
        for ch in tok:
            if _is_punctuation(ch):
                if cur:
                    toks.append("".join(cur))
                    cur = []
                toks.append(ch)
            else:
                cur.append(ch)
        if cur:
            toks.append("".join(cur))
    return toks


def _wordpiece(token: str, vocab: dict[str, int], unk: str = "[UNK]",
               max_chars: int = 100) -> list[str]:
    """贪心最长匹配；续接子词加 ``##`` 前缀。"""
    if len(token) > max_chars:
        return [unk]
    if token in vocab:
        return [token]
    pieces: list[str] = []
    start = 0
    while start < len(token):
        end = len(token)
        found: str | None = None
        while start < end:
            piece = token[start:end] if start == 0 else "##" + token[start:end]
            if piece in vocab:
                found = piece
                break
            end -= 1
        if found is None:
            return [unk]
        pieces.append(found)
        start = end
    return pieces


class PythonWordPieceEncoder:
    """纯 Python 回退分词器：与 tokenizers 的 bert-base-chinese WordPiece 逐 token 一致。"""

    name = "python-wordpiece-fallback"

    def __init__(self, vocab_path: Path) -> None:
        self.vocab = load_vocab(vocab_path)
        self.cls = self.vocab["[CLS]"]
        self.sep = self.vocab["[SEP]"]

    def encode(self, text: str) -> list[int]:
        ids = [self.cls]
        for token in _basic_split(_clean_text(text)):
            for piece in _wordpiece(token, self.vocab):
                ids.append(self.vocab[piece])
        content = ids[1:]
        if len(content) > MAX_LEN - 2:
            content = content[: MAX_LEN - 2]
        return [self.cls, *content, self.sep]


class HFTokenizerEncoder:
    """tokenizers 后端（优先）：直接读 Xenova 导出的 tokenizer.json。"""

    def __init__(self, tokenizer_json: Path) -> None:
        try:
            from tokenizers import Tokenizer  # noqa: PLC0415
            import tokenizers  # noqa: PLC0415
        except Exception as exc:  # pragma: no cover - 依赖缺失路径
            raise BuildError(
                "未安装 tokenizers 且未指定纯 Python 回退。修复："
                "`python -m pip install tokenizers`（约 0.4 MB），或加 --tokenizer python"
            ) from exc
        self._tok = Tokenizer.from_file(str(tokenizer_json))
        self._tok.enable_truncation(max_length=MAX_LEN)
        self.name = f"tokenizers=={tokenizers.__version__}"

    def encode(self, text: str) -> list[int]:
        return list(self._tok.encode(text).ids)


def build_encoder(backend: str, cache_dir: Path):
    """返回 (encoder, 说明)。backend: auto / tokenizers / python。"""
    if backend == "python":
        return PythonWordPieceEncoder(cache_dir / "vocab.txt"), "python-wordpiece-fallback（--tokenizer python）"
    try:
        return HFTokenizerEncoder(cache_dir / "tokenizer.json"), "tokenizers"
    except BuildError:
        if backend == "tokenizers":
            raise
        return (PythonWordPieceEncoder(cache_dir / "vocab.txt"),
                "python-wordpiece-fallback（tokenizers 不可用）")


def verify_tokenizer_parity(cache_dir: Path, texts: list[str], verbose: bool = True) -> int:
    """tokenizers 与纯 Python 分词逐 token 比对，返回不一致条数。"""
    ref = HFTokenizerEncoder(cache_dir / "tokenizer.json")
    fallback = PythonWordPieceEncoder(cache_dir / "vocab.txt")
    bad = 0
    for text in texts:
        if ref.encode(text) != fallback.encode(text):
            bad += 1
            if verbose and bad <= 3:
                print(f"  [WARN] 分词不一致：{text[:40]!r}")
    if verbose:
        print(f"  分词一致性：{len(texts) - bad}/{len(texts)} 条逐 token 相同（不一致 {bad} 条）")
    return bad


# ------------------------------------------------------------------ 模型缓存
def check_model_cache(cache_dir: Path) -> list[dict]:
    """只读检查缓存文件状态，不下载。"""
    rows: list[dict] = []
    for rel, spec in MODEL_FILES.items():
        path = cache_dir / rel
        item = {"file": rel, "size": spec["size"], "sha256": spec["sha256"],
                "present": path.is_file()}
        if item["present"]:
            item["actual_size"] = path.stat().st_size
            item["actual_sha256"] = sha256_file(path)
            item["ok"] = (item["actual_size"] == spec["size"]
                          and item["actual_sha256"] == spec["sha256"])
        else:
            item["ok"] = False
        rows.append(item)
    return rows


def _download(rel: str, dest: Path, spec: dict, retries: int = 3) -> None:
    url = f"{HF_BASE}/{rel}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            h = hashlib.sha256()
            total = 0
            with urllib.request.urlopen(urllib.request.Request(url), timeout=180) as resp, \
                    tmp.open("wb") as f:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    h.update(chunk)
                    total += len(chunk)
            if total != spec["size"]:
                raise BuildError(f"{rel} 大小不符：{total} != {spec['size']}")
            if h.hexdigest() != spec["sha256"]:
                raise BuildError(f"{rel} sha256 不符：{h.hexdigest()} != {spec['sha256']}")
            os.replace(tmp, dest)
            return
        except Exception as exc:  # noqa: BLE001 - 统一重试
            last = exc
            tmp.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(2 * attempt)
    raise BuildError(f"下载失败（{retries} 次）：{url}\n  最后错误：{last}")


def ensure_model_cache(cache_dir: Path, allow_download: bool, verbose: bool = True) -> dict:
    """确保缓存文件齐全且 sha256 正确；必要时从固定 commit 下载。"""
    if allow_download:
        cache_dir.mkdir(parents=True, exist_ok=True)
    provenance = {
        "repo": ONNX_REPO,
        "commit": ONNX_COMMIT,
        "requested_model": MODEL_ID,
        "hf_base": HF_BASE,
        "files": {},
    }
    for rel, spec in MODEL_FILES.items():
        path = cache_dir / rel
        need = True
        if path.is_file():
            ok = path.stat().st_size == spec["size"] and sha256_file(path) == spec["sha256"]
            if ok:
                need = False
            elif not allow_download:
                raise BuildError(f"缓存文件校验失败且 --offline 禁止重下载：{path}")
            elif verbose:
                print(f"  缓存文件已损坏，重新下载：{rel}")
        if need:
            if not allow_download:
                raise BuildError(f"模型缓存缺失：{path}；去掉 --offline 或手动放到该路径")
            if verbose:
                print(f"  下载 {rel}（{spec['size']} B，固定 commit {ONNX_COMMIT[:12]}）…")
            _download(rel, path, spec)
        provenance["files"][rel] = {"size": spec["size"], "sha256": spec["sha256"]}
    write_json(cache_dir / "provenance.json", provenance)
    return provenance


# ------------------------------------------------------------------ 推理
def embed_texts(texts: list[str], encoder, cache_dir: Path, dim: int,
                batch_size: int, verbose: bool = True) -> tuple["object", dict]:
    """单线程 CPUExecutionProvider 推理；CLS pooling；返回 float32 N×dim。"""
    try:
        import numpy as np  # noqa: PLC0415
        import onnxruntime as ort  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover - 依赖缺失路径
        raise BuildError(f"缺少 numpy / onnxruntime：{exc}") from exc

    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    so.inter_op_num_threads = 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    model_path = cache_dir / "onnx" / "model.onnx"
    try:
        sess = ort.InferenceSession(str(model_path), sess_options=so,
                                    providers=["CPUExecutionProvider"])
    except Exception as exc:  # noqa: BLE001
        raise BuildError(f"onnxruntime 无法加载 {model_path}：{exc}") from exc
    input_names = {i.name for i in sess.get_inputs()}
    output_name = sess.get_outputs()[0].name

    ids_list = [encoder.encode(t) for t in texts]
    lengths = [len(ids) for ids in ids_list]
    stats = {"min": min(lengths), "max": max(lengths),
             "p50": sorted(lengths)[len(lengths) // 2],
             "truncated": sum(1 for n in lengths if n >= MAX_LEN)}
    if verbose:
        print(f"  分词：{len(texts)} 条，token 数 min/median/max = "
              f"{stats['min']}/{stats['p50']}/{stats['max']}（上限 {MAX_LEN}）")

    out_matrix = np.zeros((len(texts), dim), dtype=np.float32)
    order = sorted(range(len(texts)), key=lambda i: (lengths[i], i))
    started = time.perf_counter()
    for start in range(0, len(order), batch_size):
        batch = order[start:start + batch_size]
        width = max(lengths[i] for i in batch)
        input_ids = np.zeros((len(batch), width), dtype=np.int64)
        attention_mask = np.zeros((len(batch), width), dtype=np.int64)
        for row, idx in enumerate(batch):
            ids = ids_list[idx]
            input_ids[row, :len(ids)] = ids
            attention_mask[row, :len(ids)] = 1
        feed = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in input_names:
            feed["token_type_ids"] = np.zeros_like(input_ids)
        hidden = sess.run([output_name], feed)[0]          # [B, L, 512]
        out_matrix[batch, :] = hidden[:, 0, :].astype(np.float32, copy=False)  # CLS
    if verbose:
        n_batches = (len(order) + batch_size - 1) // batch_size
        print(f"  推理：{len(texts)} 条 / {n_batches} 批，用时 {time.perf_counter() - started:.1f}s")
    return out_matrix, stats


def l2_normalize(matrix):
    """float64 求范数后转回 float32，使每行 float32 范数 ≈ 1（误差 < 1e-6）。"""
    import numpy as np  # noqa: PLC0415

    norms = np.linalg.norm(matrix.astype(np.float64), axis=1, keepdims=True)
    if np.any(norms == 0.0):
        raise BuildError("出现零向量，无法 L2 归一化")
    return (matrix.astype(np.float64) / norms).astype(np.float32)


# ------------------------------------------------------------------ 确定性落盘
def _npy_bytes(array) -> bytes:
    import numpy as np  # noqa: PLC0415

    # 0 维元数据（model/dim/normalized/pooling）保持 0 维；仅矩阵需要 C 连续化。
    payload = np.ascontiguousarray(array) if np.ndim(array) > 0 else np.asarray(array)
    buf = io.BytesIO()
    np.lib.format.write_array(buf, payload, allow_pickle=False)
    return buf.getvalue()


def save_npz_deterministic(path: Path, arrays: dict) -> None:
    """与 np.savez 兼容的 NPZ，但 ZIP 时间戳固定，内容相同则文件哈希相同。"""
    tmp = path.with_name(path.name + ".part")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, array in arrays.items():
            info = zipfile.ZipInfo(name + ".npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o600 << 16
            zf.writestr(info, _npy_bytes(array))
    os.replace(tmp, path)


def write_manifest(out_dir: Path, npz_rows: int, verbose: bool = True) -> dict:
    """{文件: {rows, sha256}}；本脚本生成，不手写。cache/ 也纳入校验。"""
    import numpy as np  # noqa: PLC0415

    entries: dict[str, dict] = {}
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(out_dir).as_posix()
        parts = rel.split("/")
        # 跳过清单自身、失败记录、调试/临时目录（_det1 等）与字节码缓存
        if rel in (MANIFEST_NAME, STATUS_NAME):
            continue
        if any(part.startswith("_") or part == "__pycache__" for part in parts):
            continue
        if rel == NPZ_NAME:
            rows = npz_rows
        elif path.suffix.lower() in (".onnx", ".npz"):
            rows = npz_rows if rel == NPZ_NAME else 0
        else:
            try:
                rows = line_count(path)
            except OSError:
                rows = 0
        entries[rel] = {"rows": rows, "sha256": sha256_file(path)}
    write_json(out_dir / MANIFEST_NAME, entries)
    if verbose:
        print(f"  MANIFEST.json：{len(entries)} 个文件")
    return entries


def write_status(out_dir: Path, stage: str, exc: BaseException, attempted: list[str]) -> Path:
    path = out_dir / STATUS_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 句向量构建失败（STATUS）",
        "",
        f"- 脚本：`dataset/tools/build_embeddings.py` v{SCRIPT_VERSION}",
        f"- 失败阶段：`{stage}`",
        f"- 错误：`{type(exc).__name__}: {exc}`",
        "",
        "## 已尝试的路径",
        "",
        *[f"{i}. {item}" for i, item in enumerate(attempted, start=1)],
        "",
        "## 当前结论",
        "",
        "未生成 `query_embeddings.npz`。按 `config/params.json` 的约定，`query_emb` 保持 `null`，",
        "**不得**用 TF-IDF、哈希向量或随机向量冒充语义向量。",
        "",
        "## 可尝试的修复",
        "",
        "1. 确认可访问 `huggingface.co`，重跑本脚本（模型缓存在 `dataset/embeddings/cache/`）；",
        "2. 若缺少依赖：`python -m pip install onnxruntime numpy tokenizers`；",
        "3. 若只需离线运行：把 `MODEL_FILES` 中的 6 个文件按原相对路径放入缓存目录后重跑；",
        "4. 修复后重跑成功会自动删除本文件。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


# ------------------------------------------------------------------ 主流程
def build(out_dir: Path, *, backend: str = "auto", batch_size: int = 32,
          allow_download: bool = True, limit: int = 0, verbose: bool = True) -> dict:
    """真实构建；失败时写 STATUS.md 并抛出异常。成功返回元数据 dict。"""
    import numpy as np  # noqa: PLC0415

    started = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    stage = "params"
    try:
        block = load_params()
        dim = int(block["dim"])
        stage = "input"
        texts, total_rows = load_unique_texts(STREAM, limit=limit)
        if verbose:
            print(f"  输入：{STREAM.relative_to(DATASET)} {total_rows} 行 → 去重 {len(texts)} 条问句")
        stage = "model-cache"
        provenance = ensure_model_cache(CACHE_DIR, allow_download=allow_download, verbose=verbose)
        stage = "tokenizer"
        encoder, encoder_desc = build_encoder(backend, CACHE_DIR)
        if verbose:
            print(f"  分词器：{encoder_desc}")
        stage = "inference"
        matrix, token_stats = embed_texts(texts, encoder, CACHE_DIR, dim,
                                          batch_size, verbose=verbose)
        stage = "normalize"
        matrix = l2_normalize(matrix)
        norms = np.linalg.norm(matrix.astype(np.float64), axis=1)
        if verbose:
            print(f"  L2 范数：min {norms.min():.9f} / max {norms.max():.9f} / "
                  f"mean {norms.mean():.9f}（目标 1.0）")

        stage = "write"
        text_array = np.array(texts, dtype=str)
        arrays = {
            "query_texts": text_array,
            "embeddings": np.ascontiguousarray(matrix, dtype=np.float32),
            "model": np.array(MODEL_ID),
            "dim": np.array(dim, dtype=np.int64),
            "normalized": np.array(NORMALIZE),
            "pooling": np.array(POOLING),
        }
        npz_path = out_dir / NPZ_NAME
        save_npz_deterministic(npz_path, arrays)
        npz_sha = sha256_file(npz_path)
        matrix_sha = sha256_bytes(np.ascontiguousarray(arrays["embeddings"]).tobytes())
        texts_sha = sha256_bytes("\n".join(texts).encode("utf-8"))

        meta = {
            "schema_version": 1,
            "script": {"name": "build_embeddings.py", "version": SCRIPT_VERSION},
            "artifact": NPZ_NAME,
            "n": len(texts),
            "dim": dim,
            "dtype": "float32",
            "normalized": NORMALIZE,
            "pooling": POOLING,
            "model": {
                "id": MODEL_ID,
                "onnx_repo": ONNX_REPO,
                "onnx_commit": ONNX_COMMIT,
                "onnx_sha256": MODEL_FILES["onnx/model.onnx"]["sha256"],
                "max_length": MAX_LEN,
                "tokenizer": encoder_desc,
            },
            "source": {
                "file": STREAM.relative_to(DATASET).as_posix(),
                "sha256": sha256_file(STREAM),
                "rows_scanned": total_rows,
                "unique_texts": len(texts),
                "limit": limit,
                "order": "first_occurrence",
            },
            "token_length": token_stats,
            "norm_stats": {
                "min": round(float(norms.min()), 9),
                "max": round(float(norms.max()), 9),
                "mean": round(float(norms.mean()), 9),
            },
            "matrix_sha256": matrix_sha,
            "query_texts_sha256": texts_sha,
            "npz_sha256": npz_sha,
        }
        write_json(out_dir / META_NAME, meta)

        status = out_dir / STATUS_NAME
        if status.exists():
            status.unlink()
        write_manifest(out_dir, npz_rows=len(texts), verbose=verbose)

        elapsed = time.perf_counter() - started
        if verbose:
            print(f"  完成：N={len(texts)} dim={dim} 用时 {elapsed:.1f}s")
            print(f"  matrix_sha256 = {matrix_sha}")
            print(f"  npz_sha256    = {npz_sha}")
        return meta
    except BuildError as exc:
        write_status(out_dir, stage, exc, [
            f"onnxruntime + numpy 直接推理（未使用 torch/sentence-transformers）",
            f"模型固定 commit：{ONNX_REPO}@{ONNX_COMMIT}，文件清单见 MODEL_FILES",
            f"分词后端：{backend}",
        ])
        raise


def load_existing(out_dir: Path) -> dict | None:
    """读取已有 npz 的摘要（供 dry-run 展示现状），只读。"""
    npz = out_dir / NPZ_NAME
    if not npz.is_file():
        return None
    try:
        import numpy as np  # noqa: PLC0415
    except Exception:  # pragma: no cover
        return {"error": "numpy 不可用"}
    try:
        with np.load(npz, allow_pickle=False) as data:
            emb = data["embeddings"]
            norms = np.linalg.norm(emb.astype(np.float64), axis=1)
            return {
                "n": int(emb.shape[0]),
                "dim": int(emb.shape[1]),
                "dtype": str(emb.dtype),
                "norm_min": float(norms.min()),
                "norm_max": float(norms.max()),
                "npz_sha256": sha256_file(npz),
                "matrix_sha256": sha256_bytes(np.ascontiguousarray(emb).tobytes()),
            }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def dry_run(out_dir: Path, backend: str) -> int:
    """只校验：不下载、不写文件、不生成 npz。"""
    print(f"[DRY-RUN] build_embeddings.py v{SCRIPT_VERSION}")
    problems: list[str] = []
    warnings: list[str] = []
    try:
        block = load_params()
        print(f"  契约：model={block['model']} dim={block['dim']} "
              f"normalize={block['normalize']} path={block['path']} status={block.get('status')}")
        print("  说明：params.embedding.status 仍为 pending，由 lead 在向量生成后更新；本脚本不改 config/")
    except BuildError as exc:
        print(f"  [FAIL] {exc}")
        return 1
    try:
        texts, total_rows = load_unique_texts(STREAM)
        print(f"  输入：{STREAM.relative_to(DATASET)} {total_rows} 行 → 去重 {len(texts)} 条问句"
              f"（首现排序，max {max(len(t) for t in texts)} 字符）")
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] 读取请求流失败：{exc}")
        return 1

    runtime: list[str] = []
    try:
        import numpy as np  # noqa: PLC0415
        runtime.append(f"numpy {np.__version__}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"numpy 不可用：{exc}")
    try:
        import onnxruntime as ort  # noqa: PLC0415
        runtime.append(f"onnxruntime {ort.__version__}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"onnxruntime 不可用：{exc}；修复：python -m pip install onnxruntime")
    try:
        import tokenizers  # noqa: PLC0415
        runtime.append(f"tokenizers {tokenizers.__version__}（可用，纯 Python 回退仍保留）")
    except Exception:  # noqa: BLE001
        warnings.append("tokenizers 未安装，将使用纯 Python BERT WordPiece 回退（本机已验证与 tokenizers 一致）")
    print("  运行时：" + " / ".join(runtime) if runtime else "  运行时：无")

    cache_rows = check_model_cache(CACHE_DIR)
    for item in cache_rows:
        if item["present"] and item["ok"]:
            mark = "OK"
        elif item["present"]:
            mark = "SHA256/大小不符（真实运行会重下载）"
            warnings.append(f"缓存损坏：{item['file']}")
        else:
            mark = "缺失（真实运行会从 HF 下载）"
            warnings.append(f"缓存缺失：{item['file']}")
        print(f"  模型文件：{item['file']:<28} {item['size']:>10} B  sha256={item['sha256'][:12]}…  {mark}")
    print(f"  分词后端：{backend}（auto=tokenizers 优先，否则 python-wordpiece）")

    # 输出路径
    if out_dir.exists():
        writable = os.access(out_dir, os.W_OK)
        print(f"  输出目录：{out_dir}（{'可写' if writable else '不可写'}）")
        if not writable:
            problems.append(f"输出目录不可写：{out_dir}")
    else:
        parent = out_dir.parent
        if parent.exists() and os.access(parent, os.W_OK):
            print(f"  输出目录：{out_dir}（不存在，运行时会创建）")
        else:
            problems.append(f"输出目录父级不可写：{parent}")

    existing = load_existing(out_dir)
    if existing is None:
        print("  现状：query_embeddings.npz 尚未生成")
    elif "error" in existing:
        print(f"  现状：已有 npz 但读取失败（{existing['error']}）——真实运行会覆盖")
    else:
        print(f"  现状：已有 npz  N={existing['n']} dim={existing['dim']} "
              f"范数 [{existing['norm_min']:.6f}, {existing['norm_max']:.6f}] "
              f"npz_sha256={existing['npz_sha256'][:16]}…")
    if (out_dir / STATUS_NAME).is_file():
        print(f"  注意：存在 {STATUS_NAME}（上次构建失败记录），成功构建后会删除")

    for w in warnings:
        print(f"  [WARN] {w}")
    for p in problems:
        print(f"  [FAIL] {p}")
    if problems:
        print("[DRY-RUN] 校验失败；未下载、未写任何文件")
        return 1
    print("  计划动作：下载缺失模型 → 分词 → ONNX 推理 → CLS + L2 归一化 → 写 npz/meta/MANIFEST")
    print("  预计：600 条问句在 CPU 上约 10–40 s（单线程推理）")
    print(f"[DRY-RUN] 校验通过；未下载、未写任何文件（输出目录 {out_dir}）")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="构建真实句向量（BGE-small-zh-v1.5 ONNX）→ embeddings/query_embeddings.npz")
    ap.add_argument("--dry-run", action="store_true", help="只校验参数/输入/依赖/路径，不下载不写文件")
    ap.add_argument("--out", default=str(EMB_DIR), help="输出目录（默认 dataset/embeddings）")
    ap.add_argument("--tokenizer", choices=["auto", "tokenizers", "python"], default="auto",
                    help="分词后端（auto=tokenizers 优先，缺失时用纯 Python WordPiece）")
    ap.add_argument("--batch-size", type=int, default=32, help="推理批大小（默认 32）")
    ap.add_argument("--offline", action="store_true", help="禁止下载，缓存缺失即失败")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 条唯一问句（调试用）")
    ap.add_argument("--verify-tokenizer", action="store_true",
                    help="构建前额外做 tokenizers vs 纯 Python 分词逐 token 比对")
    args = ap.parse_args(argv)
    out_dir = Path(args.out).resolve()

    if args.dry_run:
        return dry_run(out_dir, args.tokenizer)

    try:
        if args.verify_tokenizer:
            texts, _ = load_unique_texts(STREAM, limit=args.limit)
            bad = verify_tokenizer_parity(CACHE_DIR, texts)
            if bad:
                raise BuildError(f"分词一致性检查失败：{bad}/{len(texts)} 条不一致，拒绝继续")
        build(out_dir, backend=args.tokenizer, batch_size=args.batch_size,
              allow_download=not args.offline, limit=args.limit)
    except BuildError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        print(f"[FAIL] 已写 {out_dir / STATUS_NAME}；未生成 {NPZ_NAME}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        print("[FAIL] 用户中断；未生成 npz", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
