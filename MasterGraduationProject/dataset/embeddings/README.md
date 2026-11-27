# 句向量（v0.2.0 · Step 5 通道）

**结论**：`dataset/embeddings/query_embeddings.npz` 已用真实模型生成，不是 TF-IDF、不是随机向量。

| 项 | 值 |
|---|---|
| 模型 | `BAAI/bge-small-zh-v1.5`（ONNX 导出：`Xenova/bge-small-zh-v1.5` @ `75c43b069aac4d136ba6bc1122f995fedcfd2781`） |
| 条数 N | **600**（`request_stream.jsonl` 3000 行按 `query_text` 首次出现去重） |
| 维度 | **512**，`float32` |
| 归一化 | **L2**（逐行）；实测行范数 ∈ [0.999999990, 1.000000010] |
| 池化 | **CLS**（`last_hidden_state[:, 0, :]`） |
| 最大长度 | 512 token（本批实际 47–118，无截断） |
| `matrix_sha256` | `6e6cccc8d73e388cf94b545dabf7ab6302a7b451339b88d9ad5ded5c2f426062` |
| `npz_sha256` | `5a30251c694079056b1077a0f3c7a18ec9ff5f03ecff5a2f1821e54d7f37bcd0` |

> `config/params.json` 的 `embedding.status` 自 v0.2.0 起为 `generated`。本目录只读交付向量文件。
> 覆盖范围：`query_texts` 共 600 条，对应请求流的 **600 个不同问句**（3,000 条请求按 `query_text` 映射）。

## 1. 文件

| 文件 | 说明 |
|---|---|
| `query_embeddings.npz` | 主产物：`query_texts`（`<U` 数组）、`embeddings`（N×512）、`model`/`dim`/`normalized`/`pooling` 元数据 |
| `query_embeddings.meta.json` | 模型 commit、6 个模型文件的 sha256、输入流 sha256、token 长度分布、矩阵/文本/npz 的 sha256 |
| `MANIFEST.json` | `{文件: {rows, sha256}}`，由脚本生成；含 `cache/` 下模型文件与 `README.md` |
| `README.md` | 本文件 |
| `cache/Xenova--bge-small-zh-v1.5/` | HF 模型缓存（94.85 MB ONNX + 分词器，约 96 MB），可用 `--offline` 复用、可删除后重下 |

`cache/` 是下载缓存而非数据产物；删掉后再跑脚本会按 `MODEL_FILES` 中固定的
commit/size/sha256 重新下载并校验。

## 2. 为什么用 ONNX，而不是 sentence-transformers

构建机没有 torch / sentence-transformers / transformers，且不为一次向量化装 ~2 GB 的 torch。
`onnxruntime 1.32` + `numpy 2.5` + `tokenizers 0.23`（约 0.4 MB）即可完成与
sentence-transformers `BAAI/bge-small-zh-v1.5` 等价的前向：BERT WordPiece → 4 层
encoder → 取 CLS → L2 归一化。BGE-zh 检索短 query 按模型卡不需要指令前缀，直接编码原文。

## 3. 复现

```bash
# 1) 只校验：不下载、不写文件
python dataset/tools/build_embeddings.py --dry-run

# 2) 真实构建（首次会下载模型到 embeddings/cache/，之后可加 --offline）
python dataset/tools/build_embeddings.py

# 3) 可选：分词器一致性自检（tokenizers vs 纯 Python WordPiece，逐 token）
python dataset/tools/build_embeddings.py --verify-tokenizer
```

- 确定性由脚本保证：单线程 `CPUExecutionProvider`；按 token 长度排序后定长分批，padding
  由 `attention_mask` 屏蔽；NPZ 用固定 ZIP 时间戳自写（`numpy.savez` 会写入当前时间，
  导致同内容不同哈希）；元数据不含时间戳。
- 本机实测：默认批 32、`--batch-size 8`、`--batch-size 64` 三次构建，
  `query_embeddings.npz` 的 sha256 均为 `5a30251c…`，`np.ndarray` 逐元素相等；
  `query_embeddings.meta.json` 逐字节相同。
- 想自己复核两次构建是否一致：

```bash
python dataset/tools/build_embeddings.py --out /tmp/emb_a
python dataset/tools/build_embeddings.py --out /tmp/emb_b
python - <<'PY'
import hashlib, numpy as np
p = "dataset/embeddings/query_embeddings.npz"
a = np.load("/tmp/emb_a/query_embeddings.npz"); b = np.load("/tmp/emb_b/query_embeddings.npz")
assert (a["query_texts"] == b["query_texts"]).all()
assert np.array_equal(a["embeddings"], b["embeddings"])
print("matrix identical; npz sha256 =",
      hashlib.sha256(open("/tmp/emb_a/query_embeddings.npz", "rb").read()).hexdigest())
PY
```

- 失败处理：网络/依赖/权重校验失败时脚本写 `STATUS.md` 说明失败阶段与已尝试路径，
  **不生成 npz**；成功构建会自动删除旧的 `STATUS.md`。绝不写占位向量。

## 4. 分词一致性证据

`tokenizers` 读 `tokenizer.json`（`do_lower_case=false`，`BertNormalizer` + `BertPreTokenizer`）
与脚本内置的纯 Python BERT WordPiece（读 `vocab.txt`）在全部 **600/600** 条问句上逐 token
一致（`--verify-tokenizer` 输出）。两个实现都避开了 `str.splitlines()` 的坑：词表第 343 项是
U+2028，按 Unicode 行分隔符切会使其后所有 token id 整体错位。

## 5. 加载示例：按 `query_text` 取向量

```python
import json
import numpy as np

with np.load("dataset/embeddings/query_embeddings.npz", allow_pickle=False) as d:
    texts = [str(t) for t in d["query_texts"]]     # (600,)
    emb = d["embeddings"]                          # (600, 512) float32, 每行 L2≈1
    print(str(d["model"]), int(d["dim"]), str(d["normalized"]))

by_text = {t: i for i, t in enumerate(texts)}

query = "帮我查一下：2024-02-01 至 2024-02-29 期间，回填日志按事件类型统计调用次数与平均耗时"
vec = emb[by_text[query]]                          # (512,) float32

# 批量把请求流的 query_text 映射成向量（不要改 events/，这里只演示读取侧用法）
with open("dataset/events/request_stream.jsonl", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        v = emb[by_text[row["query_text"]]]
        # row["query_emb"] 目前为 null，由 events 写者/lead 决定何时回填；本目录不写 events/
```

语义自检（本机实测）：同题 3 种改写的平均余弦 **0.9848**（n=600 对），
跨题随机配对平均余弦 **0.7356**（n=7945 对）——同题明显高于跨题，说明是真实语义编码。
向量是 BGE 原生前向结果，**没有**做任何"论文友好"的后处理。

## 6. 模型标定通道（Step 5 的另一半）

脚本：`dataset/tools/run_model_calibration.py`（本仓库本次只交付脚本和 dry-run）。

```bash
# 只校验环境变量、文件列名、路径与写回计划；不发起任何真实调用、不写 measured 数值
python dataset/tools/run_model_calibration.py --dry-run

# 真实运行（作者填自己的模型；OpenAI 兼容接口，vLLM/Ollama 用 /v1 即可）
export LLM_BASE_URL=http://127.0.0.1:8000/v1
export LLM_API_KEY=...            # 非 localhost 必填
export LLM_MODEL=your-model-name
python dataset/tools/run_model_calibration.py --model-alias local-small-7b
```

真实运行做的事：对 `events/real_calibration_300.template.csv` 的 300 条请求跑
plan / rag / act / resp 四段并计时计 token，输出 `events/real_calibration_300.csv`；
把 `costs/path_costs.csv` 中属于所选模型别名的 2 行 `mock=pending` 回填为
`measured=backfill`（两行分别对应 `partial_repair/rewrite` 与 `full_regen/generate` 的
p50 墙钟）；对 `labels/branch_pairs.jsonl` 抽样回填 `t_model_full_ms`/`t_model_cache_ms`/
`g_e2e_ms`；过程明细写到 `embeddings/calibration/`。两个模型别名各跑一次才能把 4 行
`mock=pending` 全部回填——脚本不把一个模型的值复制到另一个占位模型上。
`--dry-run` 下 `costs/`、`labels/`、`events/` 一个字节都不会变。

## 7. 已知限制

1. 向量只覆盖 600 条唯一问句；`request_stream.jsonl` 里 3000 行共享同一批 `query_text`，
   回填时按文本查表即可，不需要重算。
2. 模型是 4 层 512 维小模型（BGE-small），不是 bge-large；这与 `params.embedding.model`
   的契约一致，换大模型必须同步改 `config/params.json`（lead 写）。
3. `cache/` 约 96 MB，占仓库体积；如交付包不需要离线复现，可删除该目录，
   脚本会按固定 sha256 重新下载。
