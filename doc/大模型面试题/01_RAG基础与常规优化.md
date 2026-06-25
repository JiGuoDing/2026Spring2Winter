# Prompt

## 角色定位

你是 RAG (Retrieval-Augmented Generation) 方向的资深技术专家，熟悉检索增强生成的基础原理、数据预处理、分块策略、Rerank、检索优化、幻觉治理和工程落地。

## 使用场景

我正在准备大模型应用和 RAG 方向的技术面试。本文件聚焦 RAG 基础能力与常规优化问题，回答需要兼顾面试表达、原理理解和工程实践。

## 回答目标

请围绕问题给出系统、严谨、可复盘的回答，帮助我理解 RAG 为什么存在、如何工作、工程中如何优化，以及面试时如何自然表达。

## 回答要求

1. 先给出一句话定义或核心结论。
2. 解释 RAG 的核心流程，包括离线索引、在线检索、上下文构造和生成回答。
3. 对 Rerank、数据清洗、分块、检索优化和幻觉治理等问题，要说明问题背景、核心机制、工程做法和常见坑。
4. 如果涉及参数选择，例如 Top-K、chunk size、overlap、rerank Top-N，需要说明选择依据和权衡。
5. 回答要区分“理论上怎么做”和“工程中怎么落地”，避免只讲概念。
6. 最后补充知识扩展，并给出一段可直接用于面试复述的总结。

## 输出格式

建议使用“定义 → 背景问题 → 核心流程或机制 → 工程优化 → 优缺点 → 知识扩展 → 面试回答”的结构。

## 风格约束

- 使用中文和 Markdown。
- 术语首次出现时尽量给出英文原名。
- 如果出现括号，请使用英文括号 ()，不要使用中文括号。
- 回答要准确、具体、有条理，不要泛泛而谈。

---

## 1. RAG

### 1.1 什么是 RAG？RAG 的主要流程是什么？

RAG (Retrieval-Augmented Generation，检索增强生成) 是一种将信息检索 (Retrivel) 与大模型生成相结合的技术框架。

纯粹依赖 LLM 本身存在以下问题：

- 知识时效性差
- 幻觉问题
- 私域知识缺失
- 上下文长度限制

核心思想：不要让模型凭记忆回答，而是先去查资料，再基于查到的内容生成回答

**RAG 的主要流程**

- 阶段一：离线索引 (Indexing)
  - 原始文档 (PDF/Word/网页...) -> 文档加载与解析 -> 文本分块 -> Embedding 模型编码 (向量) -> 存入向量数据库 (Vector DB)
  - 文档分块：将长文档切成若干小块 (如每块 512 token)，避免单块过长导致语义稀释
  - Embedding 编码：使用嵌入模型 (如 BGE) 将文本块转为**稠密向量**，语义相近的文本在向量空间中距离近
  - 向量数据库：常用 `FAISS`, `Milvus`, `Chroma`, `Pinecone` 等存储向量，支持快速相似度检索
- 阶段二：在线检索生成 (Retrieval + Generation)
  - 用户提问 -> Query Embedding 编码 -> 向量数据库相似度检索 (Top-K) -> 召回相关文档块 (Context) -> 构建 Prompt (Query + Context) -> LLM 生成最终答案 -> 返回给用户
  - 完整流程图

```text
┌─────────────┐     Embedding      ┌──────────────────┐
│  用户提问   │ ────────────────→  │                  │
│  "XXX是什么"│                    │   向量数据库     │
└─────────────┘                    │  (预先存好文档块)│
        │                          │                  │
        │      Top-K 相关文档块    │                  │
        │ ←──────────────────────  └──────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  构建 Prompt：                          │
│  "根据以下资料回答问题：                │
│   [检索到的文档块 1]                    │
│   [检索到的文档块 2]                    │
│   ...                                   │
│   问题：XXX是什么？"                    │
└─────────────────────────────────────────┘
        ↓
┌─────────────┐
│     LLM     │  →  生成答案
└─────────────┘
```

RAG 的优缺点

优点

- 知识可实时更新，无需重新训练模型
- 有效减少幻觉，答案有据可查
- 支持私域知识接入
- 相比全量微调，成本极低

局限性

- 检索质量直接影响生成质量 (Garbage in, Garbage out)
- 对多跳推理 (需关联多份文档) 支持较弱
- Embedding 模型可能无法捕捉复杂语义
- 系统链路较长，延迟相对较高

一句话总结：RAG =  **检索** (找到相关资料) + **增强** (把资料喂给模型) + **生成** (基于资料回答)，本质上是给大模型配了一个"实时查阅的外部记忆"。

### 1.2 什么是 RAG 中的 Rerank？具体需要怎么做？

在标准 RAG 流程中，检索阶段通常使用 **向量相似度搜索 (Bi-Encoder)** 来找回候选文档。这种方式的本质是将 Query 和 Document 分别独立编码成向量，再计算 **余弦相似度**。

这种方式存在一个根本性缺陷：Query 和 Document 之间没有充分的 token 级别的交互，编码是独立的，模型无法捕捉细粒度的语义匹配关系。

**Rerank** 的本质就是：在召回的候选集上做二次精细排序，把真正相关的文档筛选到顶部，再送入 LLM。

#### Rerank 在 RAG 中的位置

完整的 RAG + Rerank 流程如下：

```plaintext
用户 Query
    ↓
[第一阶段] 向量检索 (召回 Top-K，K 较大，如 50~100)
    ↓
候选文档集合 {d1, d2, ..., dk}
    ↓
[第二阶段] Reranker 精排 (重新评分并排序)
    ↓
筛选 Top-N (N 较小，如 3~10)
    ↓
拼接进 Prompt → LLM 生成答案
```

> 为什么不直接用 Reranker 做召回？因为 Reranker (Cross-Encoder) 需要对每个 (Query, Doc) 对单独计算，复杂度是 O(n)，当文档库有几百万条时，直接用 Reranker 检索代价极大。因此先用快速的向量检索缩小候选范围，再用 Reranker 精排。

#### Rerank 的具体实现方法

##### 方法一：Corss-Encoder Reranker (主流)

原理：Cross-Encoder 将 Query 和 Document **拼接在一起** 输入到模型，让两者的 token 之间充分交互 (通过 Self-Attention)，最终输出一个相关性分数。

```plaintext
Input:  [CLS] Query [SEP] Document [SEP]
            ↓ (Transformer, Self-Attention 全交互)
Output: 相关性分数 score ∈ [0, 1]
```

与 Bi-Encoder 对比：

```plaintext
Bi-Encoder:
  q_vec = Encoder(Query)          # 独立编码
  d_vec = Encoder(Document)       # 独立编码
  score = cosine(q_vec, d_vec)    # 向量空间中比较

Cross-Encoder:
  score = Encoder([Query; Document])  # 拼接后联合编码，充分交互
```

代表模型

- BAAI/bge-reranker-base
- cross-encoder/ms-marco-MiniL-L-6-v2
- Cohere Rerank API

代码示例

```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-reranker-base')
model = AutoModelForSequenceClassification.from_pretrained('BAAI/bge-reranker-base')
model.eval()

query = "什么是机器学习？"
# 第一阶段召回的候选文档
candidates = [
    "机器学习是人工智能的一个分支，让计算机从数据中学习。",
    "深度学习使用神经网络处理复杂任务。",
    "监督学习需要标注数据进行训练。",
]

# 构造 (query, doc) 对
pairs = [[query, doc] for doc in candidates]

# 编码并打分
with torch.no_grad():
    inputs = tokenizer(pairs, padding=True, truncation=True,
                       return_tensors='pt', max_length=512)
    scores = model(**inputs, return_dict=True).logits.view(-1).float()

# 按分数排序
ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
for doc, score in ranked:
    print(f"Score: {score:.4f} | Doc: {doc}")
```

##### 方法二：LLM-based Reranker

利用 LLM 本身的语言理解能力来判断相关性，主要有三种粒度

(1) Pointwise (逐点打分)

对每个 (Query, Doc) 对独立让 LLM 打分

```plaintext
Prompt:
"请判断以下文档与问题的相关性，给出 1-10 的分数。
问题：{query}
文档：{doc}
分数："
```

(2) Pairwise (成对比较)

每次让 LLM 比较两篇文档，哪篇更相关。最终用胜负关系排序。

```plaintext
Prompt:
"以下哪篇文档更能回答问题？
问题：{query}
文档A：{doc_a}
文档B：{doc_b}
回答 A 或 B："
```

(3) Listwise (列表排序)

一次性输入所有候选文档，让 LLM 直接输出排序结果。

```plaintext
Prompt:
"以下是与问题相关的文档列表，请按相关性从高到低重新排列文档编号。
问题：{query}
[1] {doc_1}
[2] {doc_2}
...
[k] {doc_k}
排序结果："
```

> Listwise 的挑战：文档数量多时，Context 过长；LLM 存在位置偏差 (倾向于将靠前或靠后的文档排高)。RankGPT 提出了 滑动窗口策略 来解决这个问题。

##### 方法三：混合索引 + 融合排序 (RRF)

这不是纯粹的 Reranker，而是在召回阶段结合多路检索结果，通过 **倒数排名融合 (Reciprocal Rank Fusion, RRF)** 来得到更好的排序。

$$
RRF\_{score}(d) = \sum\_{i=1}^{n}\frac{1}{k+r\_{i}(d)}
$$

其中 $r\_{i}(d)$ 是文档 $d$ 在第 $i$ 路检索结果中的排名，$k$ 通常取 60。

```plaintext
向量检索结果:  d1(rank=1), d3(rank=2), d2(rank=3)
BM25检索结果:  d2(rank=1), d1(rank=2), d4(rank=3)
        ↓ RRF 融合
最终排序:  d1, d2, d3, d4
```

#### 关键超参数与工程细节

- 第一阶段召回的 K 值：K 太小则 Reranker 无从发挥，K 太大则 Reranker 延迟上升，通常 K = 50 \~ 100。
- Reranker 输出的 Top-N：最终送入 LLM 的文档数，通常 N = 3 \~ 10，受 LLM 上下文窗口约束。
- Reranker 的 max\_length：Cross-Encoder 对输入长度有限制 (通常 512 tokens)，长文档需要先做截断或分块。
- Lost in the Middle 问题：LLM 对 Prompt 中间位置的内容关注度低，因此 Reranker 后最相关的文档最好放在最前或最后。

### 1.3 在 RAG 应用中为了优化检索精度，其中的数据清洗和预处理怎么做？

#### 为什么数据清洗对 RAG 至关重要？

在 RAG 系统中，检索质量的上限由数据质量决定，可以用一个公式来理解

```plaintext
最终回答质量 = f(检索质量 × 生成质量)
```

如果检索到的文档本身含有噪声、冗余或格式混乱，即使使用最强的 LLM 也无法生成高质量的回答。这就是所谓的 **"Garbage In, Garbage Out"** 原则。

> 💡 核心目标：让每一个进入向量数据库的文本块 (Chunk) 都是语义完整、信息密度高、噪声低的。

#### 数据清洗与预处理的完整流程

```plaintext
原始数据
   │
   ▼
[第一阶段] 文档解析与抽取
   │
   ▼
[第二阶段] 文本清洗 (噪声去除)
   │
   ▼
[第三阶段] 文本规范化
   │
   ▼
[第四阶段] 智能分块 (Chunking)
   │
   ▼
[第五阶段] 去重与质量过滤
   │
   ▼
[第六阶段] 元数据增强 (Metadata Enrichment)
   │
   ▼
高质量 Chunk → 向量化 → 向量数据库
```

#### 各阶段详细解析

##### 第一阶段：文档解析与抽取

不同格式的文档需要不同的解析策略，解析质量直接影响后续所有步骤

| 文档类型   | 常见问题                   | 推荐工具                          |
| ---------- | -------------------------- | --------------------------------- |
| PDF        | 乱码、多栏混排、表格变文本 | PyMuPDF, pdfplumber, Unstructured |
| Word/PPT   | 样式标签混入正文           | python-docx, python-pptx          |
| HTML       | 大量无关标签、导航栏、广告 | BeautifulSoup, Trafilatura        |
| 扫描版 PDF | 需要 OCR                   | PaddleOCR, Tesseract              |
| 表格数据   | 结构信息丢失               | pandas + 特殊处理                 |

##### 第二阶段：文本清洗 (噪声去除)

```python
import re
from typing import str

class TextCleaner:
    """
    文本清洗器：分层次处理不同类型的噪声
    """

    def clean(self, text: str) -> str:
        """按顺序执行清洗流水线"""
        text = self._remove_html_tags(text)
        text = self._remove_urls(text)
        text = self._remove_special_chars(text)
        text = self._normalize_whitespace(text)
        text = self._remove_headers_footers(text)
        text = self._remove_page_numbers(text)
        return text.strip()

    def _remove_html_tags(self, text: str) -> str:
        """去除 HTML 标签，但保留标签内的文本内容"""
        # 先处理特殊 HTML 实体
        text = text.replace(" ", " ").replace("&", "&")
        text = text.replace("<", "<").replace(">", ">")
        # 去除所有标签
        return re.sub(r'<[^>]+>', '', text)

    def _remove_urls(self, text: str) -> str:
        """
        去除 URL，但注意：有时 URL 本身含有语义信息
        策略：去除 URL 但保留其前后文本
        """
        return re.sub(r'https?://\S+|www\.\S+', '[链接]', text)

    def _remove_special_chars(self, text: str) -> str:
        """
        去除特殊字符，但需要保留有语义的标点
        注意：不能暴力去除所有非字母数字字符！
        """
        # 去除零宽字符 (常见于爬虫数据)
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        # 去除控制字符 (但保留换行符)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # 将多种引号统一
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """
        规范化空白字符
        - 将 \t 转为空格
        - 将多个连续空格合并为一个
        - 将多个连续换行合并为两个 (保留段落结构)
        """
        text = text.replace('\t', ' ')
        text = re.sub(r' {2,}', ' ', text)       # 多空格 → 单空格
        text = re.sub(r'\n{3,}', '\n\n', text)   # 多换行 → 双换行
        return text

    def _remove_headers_footers(self, text: str) -> str:
        """
        去除文档中常见的页眉页脚模式
        例如："第 X 页 共 Y 页"、"公司名称 版权所有" 等
        """
        # 去除 "第X页/共X页" 类型的页码信息
        text = re.sub(r'第\s*\d+\s*页\s*[，,/]\s*共\s*\d+\s*页', '', text)
        # 去除版权声明行 (通常出现在每页底部)
        text = re.sub(r'Copyright.*?\d{4}.*?\n', '', text, flags=re.IGNORECASE)
        return text

    def _remove_page_numbers(self, text: str) -> str:
        """去除单独成行的页码数字"""
        # 匹配单独一行只有数字的情况
        return re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
```

##### 第三阶段：文本规范化

规范化的目的是消除语义相同但表达不同带来的检索偏差

```python
import unicodedata
from opencc import OpenCC  # 简繁转换

class TextNormalizer:

    def __init__(self):
        # 初始化简繁转换器 (根据业务场景决定方向)
        self.cc = OpenCC('t2s')  # 繁体 → 简体

    def normalize(self, text: str) -> str:
        text = self._unicode_normalize(text)
        text = self._traditional_to_simplified(text)
        text = self._normalize_numbers(text)
        text = self._expand_abbreviations(text)
        return text

    def _unicode_normalize(self, text: str) -> str:
        """
        Unicode 规范化：将全角字符转为半角
        例如："Ａ" (全角) → "A" (半角)
             "１２３" → "123"
        """
        # NFKC 规范化：兼容等价 + 组合形式
        text = unicodedata.normalize('NFKC', text)
        return text

    def _traditional_to_simplified(self, text: str) -> str:
        """繁简统一，避免同一概念因繁简差异导致检索遗漏"""
        return self.cc.convert(text)

    def _normalize_numbers(self, text: str) -> str:
        """
        数字格式统一
        例如："一百万" → 保留原文 (中文数字有时含义不同)
             "1,000,000" → "1000000" (去除千分位符便于匹配)
        """
        # 去除数字中的千分位逗号
        text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
        return text

    def _expand_abbreviations(self, text: str, 
                               abbr_dict: dict = None) -> str:
        """
        展开领域内的缩写，提升召回率
        例如：NLP → 自然语言处理
        注意：需要根据具体业务领域维护缩写词典
        """
        if abbr_dict is None:
            abbr_dict = {
                "LLM": "大语言模型 (LLM)",
                "RAG": "检索增强生成 (RAG)",
                "NLP": "自然语言处理 (NLP)",
            }

        for abbr, full_form in abbr_dict.items():
            # 仅在缩写单独出现时替换，避免误替换
            text = re.sub(rf'\b{abbr}\b', full_form, text)

        return text
```

##### 第四阶段：智能分块 (Chunking) —— 最核心环节

分块策略直接决定检索粒度，是 RAG 预处理中影响最大的环节

常见分块策略对比

| 策略         | 原理                        | 优点           | 缺点               | 适用场景       |
| ------------ | --------------------------- | -------------- | ------------------ | -------------- |
| 固定大小分块 | 按 token/字符数切割         | 简单快速       | 可能截断语义       | 快速原型       |
| 句子级分块   | 按句号等标点切割            | 语义较完整     | 块太小、上下文不足 | 短文档         |
| 段落级分块   | 按段落切割                  | 语义完整       | 长度不均匀         | 结构化文档     |
| 递归字符分块 | 按层级分隔符递归切割        | 兼顾语义和长度 | 参数需调优         | 通用场景       |
| 语义分块     | 用 embedding 相似度判断边界 | 语义最完整     | 计算成本高         | 高质量要求场景 |

##### 第五阶段：去重与质量过滤

```python
from datasketch import MinHash, MinHashLSH
import hashlib

class ChunkQualityFilter:

    def __init__(self, min_length: int = 50, max_length: int = 2000):
        self.min_length = min_length  # 过短的块信息量不足
        self.max_length = max_length  # 过长的块检索精度下降
        # 使用 MinHash LSH 进行高效近似去重
        self.lsh = MinHashLSH(threshold=0.8, num_perm=128)
        self.seen_hashes = set()

    def filter(self, chunks: list[str]) -> list[str]:
        """综合过滤流水线"""
        filtered = []
        for chunk in chunks:
            if self._length_filter(chunk) \
               and self._quality_filter(chunk) \
               and not self._is_duplicate(chunk):
                filtered.append(chunk)
        return filtered

    def _length_filter(self, chunk: str) -> bool:
        """过滤过短或过长的块"""
        return self.min_length <= len(chunk) <= self.max_length

    def _quality_filter(self, chunk: str) -> bool:
        """
        质量过滤：过滤低信息量的块
        判断标准：
        1. 中文字符占比 (过低说明可能是乱码或纯符号)
        2. 字符多样性 (过低说明是重复字符)
        """
        # 计算中文字符占比
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', chunk)
        chinese_ratio = len(chinese_chars) / len(chunk) if chunk else 0

        # 对于中文文档，中文字符应占一定比例
        # 注意：代码文档、英文文档需要调整此策略
        if chinese_ratio < 0.1 and not self._is_code(chunk):
            return False

        # 计算唯一字符多样性
        unique_ratio = len(set(chunk)) / len(chunk)
        if unique_ratio < 0.1:  # 多样性极低，可能是 "aaaa..." 类噪声
            return False

        return True

    def _is_code(self, chunk: str) -> bool:
        """判断是否是代码块，代码块有不同的质量标准"""
        code_indicators = ['def ', 'class ', 'import ', 'function', '{', '}']
        return any(indicator in chunk for indicator in code_indicators)

    def _is_duplicate(self, chunk: str) -> bool:
        """
        使用 MinHash 进行近似去重
        相比精确 hash，能识别出内容高度相似 (而非完全相同) 的重复
        """
        # 生成 MinHash 签名
        m = MinHash(num_perm=128)
        for word in chunk.split():
            m.update(word.encode('utf8'))

        # 检查是否与已有内容高度相似
        result = self.lsh.query(m)
        if result:
            return True  # 发现近似重复

        # 将当前 chunk 加入索引
        key = hashlib.md5(chunk.encode()).hexdigest()
        if key not in self.seen_hashes:
            self.lsh.insert(key, m)
            self.seen_hashes.add(key)

        return False
```

##### 第六阶段：元数据增强 (Metadata Enrichment)

元数据是 RAG 检索的隐藏武器，可以实现混合索引和过滤

```python
from datetime import datetime

def enrich_metadata(chunk: str, 
                     source_doc: dict,
                     chunk_index: int) -> dict:
    """
    为每个 chunk 附加丰富的元数据
    这些元数据可以用于：
    1. 混合检索 (向量相似度 + 元数据过滤)
    2. 引用溯源 (告诉用户答案来自哪里)
    3. 权重调整 (标题/摘要类块权重更高)
    """

    # 自动生成摘要标题 (可选：调用 LLM 生成)
    # 简单版：取前 50 个字符作为标题
    auto_title = chunk[:50].replace('\n', ' ') + "..."

    return {
        # --- 来源信息 ---
        "source": source_doc.get("file_path", "unknown"),
        "doc_title": source_doc.get("title", ""),
        "author": source_doc.get("author", ""),
        "created_at": source_doc.get("created_at", ""),

        # --- 位置信息 ---
        "chunk_index": chunk_index,        # 在文档中的第几块
        "page_number": source_doc.get("page_number", -1),
        "section": source_doc.get("section_title", ""),  # 所属章节

        # --- 内容信息 ---
        "chunk_length": len(chunk),
        "chunk_type": source_doc.get("element_type", "text"),  # text/table/title
        "auto_title": auto_title,

        # --- 时间信息 (用于时效性过滤) ---
        "indexed_at": datetime.now().isoformat(),

        # --- 质量信息 ---
        "language": detect_language(chunk),  # 语种检测
    }

# 最终产出的数据结构
final_chunk = {
    "text": "经过清洗的高质量文本内容...",
    "metadata": {
        "source": "docs/product_manual_v2.pdf",
        "doc_title": "产品手册 V2.0",
        "chunk_index": 3,
        "page_number": 5,
        "section": "第二章 安装指南",
        "chunk_type": "text",
        "indexed_at": "2024-01-15T10:30:00",
        "language": "zh"
    }
}
```

#### 总结：关键决策点

```plaintext
数据清洗决策树
│
├── 文档类型？
│   ├── PDF → 选择合适的解析器，注意多栏/表格
│   └── HTML → 优先去除导航栏等无关内容
│
├── 分块大小如何确定？
│   ├── Embedding 模型的最大输入长度 (如 bge-m3 = 8192 tokens)
│   ├── LLM 的上下文窗口大小
│   └── 经验值：256~512 tokens 是常见选择
│
├── 是否需要语义分块？
│   ├── 数据量小、质量要求高 → 是
│   └── 数据量大、追求效率 → 递归字符分块
│
└── 元数据设计原则
    └── 根据实际查询场景设计，而非越多越好
```

### 1.4 在做 RAG 时，怎么规避语义被切割掉的问题？

这是 RAG 落地里最常见、也最容易被低估的问题之一。

所谓"语义被切割掉"，本质是 Chunk 切分边界和语义边界不一致，导致以下后果：

- 关键定义被截断在两块中间，单块检索命中后信息不完整
- 因果链、条件约束、代码上下文被拆开，LLM 只能看到局部片段
- 向量表示被稀释，检索召回率和排序质量同时下降

面试里可以先给一句结论：**不要把 Chunking 当成固定长度切片问题，而要把它当成"语义边界建模 + 检索补偿"的系统工程问题。**

#### 一、先理解根因：为什么会被切坏

1. 固定长度切分过于机械
    例如每 512 tokens 硬切，不考虑句子、段落、标题层级。
2. 文档结构丢失
    PDF/网页解析后如果没保留标题、表格、代码块边界，后续再智能切分也很难恢复。
3. 单一路径检索
    只检索子块 (child chunk)，不回溯父块 (parent chunk) 或相邻块，天然容易上下文缺失。
4. 重叠策略失衡
    overlap 太小会丢语义连续性，overlap 太大又会引入重复噪声并抬高索引成本。

#### 二、工程上最有效的规避策略

##### 策略 1：结构感知切分 (Structure-aware Chunking)

先做文档结构化解析，再按语义单元切分：

- 标题-段落-子段落优先
- 表格整体保留
- 代码块整体保留
- 列表项尽量不跨块

这一步的核心不是"切多细"，而是"先保证一个块内部语义自洽"。

##### 策略 2：语义切分 + 动态窗口重叠

建议采用"语义断点优先，长度约束兜底"：

1. 先按句子或段落聚合
2. 接近上限时，在最近语义断点落刀
3. 加入 10% ~ 25% 的 token overlap 保留上下文连续性

可用下面公式理解重叠比例：

$$
overlap\_ratio = \frac{overlap\_tokens}{chunk\_tokens}
$$

经验上，技术文档和规范文档可取更高 overlap，FAQ 或短文本可取更低 overlap。

##### 策略 3：Parent-Child 检索

建立两级索引：

- child chunk 用于高精度召回
- parent chunk 用于补全上下文

在线阶段先命中 child，再回填所属 parent 或 section，最后再喂给 LLM。这样可以同时兼顾"检索精准"和"语义完整"。

##### 策略 4：邻接扩展 (Neighbor Expansion)

即使不做 parent-child，也应在召回后补齐相邻块：

```plaintext
命中 chunk_i
    -> 追加 chunk_(i-1), chunk_(i+1)
    -> 去重 + 长度裁剪
    -> 输入 LLM
```

这是低成本高收益策略，尤其适合教程、论文、技术手册这类强上下文文档。

##### 策略 5：分块质量离线评估

很多团队只评估召回准确率，不评估"切分质量"，这是常见盲点。建议加入以下指标：

- Boundary Break Rate：关键句被边界截断的比例
- Context Completeness：问题所需证据是否在同一检索上下文中
- Redundancy Ratio：重叠带来的冗余比例

只有把切分质量纳入评估，Chunk 策略才能稳定迭代。

##### 策略 6：命题化切割 (Proposition-based Chunking)

核心思想：不要只按段落切，而是把文本拆成最小可检索语义单元"命题" (一个可被判断真假的事实表达)，再按命题聚合为 chunk。

为什么有效：

- 命题天然语义完整，能降低"一句话被切半"导致的信息断裂
- 对细粒度问答更友好，尤其适合定义、结论、参数约束类问题
- 便于后续做证据对齐和引用溯源

一个常见工程做法是两步：

1. 先用规则或 LLM 将段落抽取为命题集合 (subject-predicate-object 或事实句)
2. 再按主题相近性将多个命题打包成检索块，并保留命题级 metadata (proposition_id, source_span)

这种方式特别适合制度文档、技术规范、论文结论段等"信息密度高、句间约束强"的语料。

##### 策略 7：Contextual Retrieval

核心思想：检索时不只看 query 和 chunk 的相似度，还要显式引入 chunk 的上下文信息 (文档标题、章节路径、邻接块、父块摘要等) 共同参与匹配与排序。

可理解为：

$$
score = \alpha \cdot sim(query, chunk) + \beta \cdot sim(query, context\_of\_chunk)
$$

其中 $context\_of\_chunk$ 可以是：

- 父章节标题与摘要
- 前后相邻 chunk 的压缩表示
- 文档级关键词或 taxonomy 标签

工程上通常有两种落地方式：

1. 检索前增强：给每个 chunk 预生成 contextual summary 并一并向量化
2. 检索后增强：命中 chunk 后再拼接 parent/neighbor 做二次 rerank

Contextual Retrieval 的价值在于：即使目标答案分散在多个相邻片段，也能通过上下文信号把"语义链"整体召回，减少断章取义。

#### 三、一个可落地的切分流程 (伪代码)

```python
def build_chunks(document, max_tokens=500, overlap_tokens=80):
     # 1) 结构化解析，保留 heading/table/code 边界
     units = parse_to_semantic_units(document)

     chunks = []
     current = []
     current_tokens = 0

     for unit in units:
          t = token_len(unit)

          # 2) 超限前优先在语义断点切分
          if current_tokens + t > max_tokens and current:
                chunks.append(join_units(current))

                # 3) 通过尾部重叠保持语义连续
                current = tail_by_tokens(current, overlap_tokens)
                current_tokens = token_len(join_units(current))

          current.append(unit)
          current_tokens += t

     if current:
          chunks.append(join_units(current))

     # 4) 为每个 chunk 记录 parent_id / section_id / chunk_index
     return attach_metadata(chunks)
```

这段流程体现了三个关键点：结构先行、语义断点优先、重叠兜底。

#### 四、常见误区和边界条件

1. 误区：Chunk 越小越好
    错误。太小会导致语义碎片化，召回到的块无法独立回答问题。
2. 误区：只要加大 overlap 就能解决
    不完整。overlap 只能缓解边界问题，不能替代结构化切分和检索补偿。
3. 误区：只靠向量相似度即可
    错误。复杂问答往往需要多块证据拼接，必须配合 rerank、邻接扩展或 parent 回填。
4. 边界：超长代码/表格/合同条款
    这类内容通常要专门策略，例如按函数、按章节条款号切分，而不是通用句子切分。

#### 五、面试中的总结话术

可以这样回答：规避语义切割的核心是"切分阶段保证语义单元完整，检索阶段做上下文补偿"。工程上我会使用结构感知切分 + 动态 overlap + 命题化切割，并在检索侧配合 parent-child、邻接扩展和 Contextual Retrieval，再用离线指标持续评估边界截断率和上下文完整性，这样才能在召回率、精度和成本之间取得稳定平衡。

#### 知识扩展

- Reranker：切分质量决定候选集上限，Reranker 决定候选集排序上限，二者是串联关系。
- Context Compression：当做了邻接扩展后，通常需要压缩去噪，避免把冗余上下文带入 LLM。
- Lost in the Middle：即使检索到了完整语义，也要通过重排把关键信息放到 Prompt 更显著位置。
- Graph RAG：当语义跨文档、多跳关联明显时，图结构检索能进一步降低"被切散"带来的推理断裂。

### 1.5 什么是 Advanced RAG？什么是 Modular RAG？

Claude 4.6 回答：

> Naive RAG 是最基础的 RAG 形式，流程是"检索-增强-生成"三步，但存在检索质量差、流程僵化、无法处理复杂问题等局限。
> 
> **Advanced RAG** 在 Naive RAG 基础上，针对三个阶段分别引入优化：在 **检索前** ，使用 Query 改写、Query 扩展、HyDE 等方法优化用户输入，使其更适合检索；在 **检索阶段** ，引入混合检索 (BM25 + 向量检索)、优化 Chunk 策略；在 **检索后** ，使用 Cross-Encoder Reranker 进行重排序，使用 Context Compression 过滤噪声。Advanced RAG 的本质是对线性 RAG 流程的精细化优化。
> 
> **Modular RAG** 则是更高层次的抽象。它将整个 RAG 系统解耦为一系列独立可插拔的模块，包括 Search、Memory、Fusion、Routing、Predict、Rerank 等，这些模块可以按需自由编排，形成不同的 RAG 模式：比如 Iterative RAG (多轮迭代检索)、Recursive RAG (递归分解子问题)、Adaptive RAG (根据问题复杂度动态选择策略)、Self-RAG (LLM 自主决策检索时机和质量)。
> 
> 三者的关系是递进的：Naive RAG 是基础，Advanced RAG 是对其的优化，Modular RAG 是对 Advanced RAG 各种优化技术的系统化和泛化，Advanced RAG 中的每种技术都可以视为 Modular RAG 中某个模块的具体实现。在实际工程中，会根据业务场景的复杂度选择合适的层次：简单问答用 Naive RAG 即可，通用场景用 Advanced RAG，需要处理复杂多跳推理、多数据源、个性化需求时，则采用 Modular RAG 进行灵活编排。

#### Advanced RAG

Advanced RAG 是在基础 Naive RAG 架构之上，针对 **检索前 (Pre-Retrieval)、检索中 (Retrieval) 和 检索后 (Post-Retrieval)** 三个阶段分别引入优化策略，以提升整体 RAG 的质量。

```plaintext
┌───────────────────────────────────────────────────────────┐
│                    Advanced RAG Pipeline                  │
│                                                           │
│  Query                                                    │
│    │                                                      │
│    ▼                                                      │
│ ┌──────────────────┐                                      │
│ │  Pre-Retrieval   │  ← Query 优化 (改写/扩展/分解)          │
│ └────────┬─────────┘                                      │
│          │                                                │
│          ▼                                                │
│ ┌──────────────────┐                                      │
│ │    Retrieval     │  ← 混合检索、Chunk优化、Embedding优化   │
│ └────────┬─────────┘                                      │
│          │                                                │
│          ▼                                                │
│ ┌──────────────────┐                                      │
│ │  Post-Retrieval  │  ← Rerank、压缩、过滤                  │
│ └────────┬─────────┘                                      │
│          │                                                │
│          ▼                                                │
│       Generate                                            │
└───────────────────────────────────────────────────────────┘
```

##### Pre-Retrieval (检索前优化)

这一阶段的目标是优化用户的原始 Query，使其更适合检索。

1. Query rewriting (查询改写)
   将用户的口语化、模糊的 Query 改写为更精准的形式。
2. Query Expansion (查询扩展)
   为原始 Query 补充同义词、相关概念，提高召回率。
3. HyDE (Hypothetical Document Embeddings)
   核心思想：与其用 Query 的 Embedding 去匹配文档，不如先让 LLM 生成一个"假设性答案文档"，再用该文档的 Embedding 去检索，因为文档-文档之间的语义相似度往往高于 Query-文档之间的相似度。
   
   ```plaintext
   原始 Query → LLM 生成假设文档 → 对假设文档做 Embedding → 检索真实文档库
   ```
4. Step-back Prompting (后退提示)
   将具体问题抽象到更高层次，先检索高层知识，再回答具体问题。

##### Retrieval 检索中优化

- Hybrid Search (混合搜索)，结合 **稀疏检索 (BM25)** 和 **密集检索 (向量检索)** 的优势
- Chunk 优化策略

##### Post-Retrieval (检索后优化)

- Reranking (重排序)
  用更强的模型 (Cross-Encoder) 对初步检索结果重新排序，精排 top-k。
  
  ```plaintext
  初步检索 (Bi-Encoder, 快但粗糙, 召回100个)
      → Reranker (Cross-Encoder, 慢但精准, 精排取top5)
      → 送入 LLM 生成
  ```
- Context Compression (上下文压缩)
  过滤掉检索文档中与 Query 无关的内容，减少噪声。

#### Modular RAG

核心思想：将 RAG 系统从固定流水线 (Pipeline) 解耦为可自由组合的独立模块 (Module)，每个模块负责特定功能，可以按需编排，形成适应不同任务的 RAG 模式。

##### 核心模块

```plaintext
┌─────────────────────────────────────────────────────────────┐
│                    Modular RAG 模块体系                      │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Search  │  │  Memory  │  │  Fusion  │  │ Routing  │     │
│  │  Module  │  │  Module  │  │  Module  │  │  Module  │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Predict  │  │  Rerank  │  │  Task    │  │  Verify  │     │
│  │  Module  │  │  Module  │  │ Adapter  │  │  Module  │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
```

| 模块           | 功能               | 典型实现                               |
| -------------- | ------------------ | -------------------------------------- |
| Search Module  | 多源异构检索       | 向量库、搜索引擎、数据库、知识图谱     |
| Memory Module  | 利用 LLM 自身知识  | KV Cache、外部记忆存储                 |
| Fusion Module  | 多路检索结果融合   | RRF (Reciprocal Rank Fusion)、加权融合 |
| Routing Module | 动态决策走哪条路径 | Query 分类器、LLM 决策                 |
| Predict Module | LLM 生成中间结果   | 生成假设答案、生成子问题               |
| Rerank Module  | 重排序             | Cross-Encoder、LLM Reranker            |
| Task Adapter   | 适配不同下游任务   | 问答、摘要、代码生成                   |
| Verify Module  | 验证答案可信度     | 事实核查、引用验证                     |

##### 典型的 Modular RAG 编排模式

- 模式一：Iterative RAG (迭代式 RAG)
  多次检索-生成交替，每次检索基于上一轮的结果
  
  ```python
  def iterative_rag(query: str, llm, retriever, max_iterations: int = 3) -> str:
      """
      迭代式 RAG：多轮检索，每轮基于前一轮的中间结果
      适合需要逐步深入的复杂问题
      """
      context = ""
      current_query = query
  
      for i in range(max_iterations):
          # 检索
          docs = retriever.retrieve(current_query)
          new_context = "\n".join(docs)
          context += f"\n[迭代{i+1}]\n" + new_context
  
          # 生成中间答案或下一个子问题
          intermediate_prompt = f"""
          基于以下上下文，回答问题或生成需要进一步查询的子问题。
          如果可以完整回答，请直接回答并在末尾加 [DONE]。
          否则，请输出需要进一步查询的问题。
  
          问题: {query}
          上下文: {context}
          """
          response = llm.generate(intermediate_prompt)
  
          if "[DONE]" in response:
              return response.replace("[DONE]", "").strip()
          else:
              # 用生成的子问题作为下一轮检索的 Query
              current_query = response
  
      # 最终生成
      return llm.generate(f"基于上下文回答：{query}\n上下文：{context}")
  ```

- 模式二：Recursive RAG (递归式 RAG)
  
  将复杂问题分解为子问题，递归解决每个子问题后合并
  
  ```plaintext
  复杂问题
      ├── 子问题1 → 检索1 → 答案1
      ├── 子问题2 → 检索2 → 答案2
      │       └── 子子问题2.1 → 检索 → 答案
      └── 子问题3 → 检索3 → 答案3
           ↓
      合并所有子答案 → 最终答案
  ```

- 模式三：Adaptive RAG (自适应 RAG)
  
  根据 Query 的复杂度，动态选择是否需要检索，以及使用哪种 RAG 策略
  
  ```python
  def adaptive_rag(query: str, llm, retriever) -> str:
      """
      自适应 RAG：根据 query 复杂度动态选择策略
      - 简单事实性问题 → 直接由 LLM 回答 (No RAG)
      - 中等复杂度 → Single-shot RAG
      - 高复杂度 → Iterative/Recursive RAG
      """
      # 路由决策：判断 query 需要哪种策略
      routing_prompt = f"""
      分析以下问题的复杂度，并选择最合适的回答策略：
      - "direct": 问题简单，LLM 可以直接回答，无需检索
      - "single_rag": 需要一次检索即可回答
      - "iterative_rag": 问题复杂，需要多轮检索和推理
  
      问题: {query}
      策略 (只输出策略名):
      """
      strategy = llm.generate(routing_prompt).strip()
  
      if strategy == "direct":
          return llm.generate(query)
      elif strategy == "single_rag":
          docs = retriever.retrieve(query)
          context = "\n".join(docs)
          return llm.generate(f"基于上下文回答：{query}\n上下文：{context}")
      elif strategy == "iterative_rag":
          return iterative_rag(query, llm, retriever)
      else:
          # 默认走 single_rag
          docs = retriever.retrieve(query)
          context = "\n".join(docs)
          return llm.generate(f"基于上下文回答：{query}\n上下文：{context}")
  ```

- 模拟四：Self-RAG
  
  让 LLM 自己决定何时检索、检索什么、如何评估检索结果的质量，通过特殊的反射 token 控制整个流程。

### 1.6 RAG 检索优化策略有哪些？

这个问题的核心，不是简单地把 `Top-K` 调大，而是要系统性地提升 **召回率 (Recall)**、**精度 (Precision)** 和 **上下文可用性**，同时控制延迟和成本。更准确地说，RAG 的检索优化应该围绕四个层次展开：**检索前优化 Query**、**检索中优化召回机制**、**检索后优化排序与压缩**、**工程侧优化稳定性与成本**。

#### 一、先明确优化目标

RAG 检索阶段的目标通常不是“找到最相似的一段”，而是“在有限上下文窗口内，尽可能把能支撑答案的证据块找全、排对、压紧”。因此可以把检索效果理解为一个综合问题：

$$
score = \alpha \cdot recall + \beta \cdot precision + \gamma \cdot coverage - \delta \cdot latency
$$

其中：

- `recall` 决定有没有把关键证据召回上来。
- `precision` 决定召回上来的内容是不是足够相关。
- `coverage` 决定是否覆盖了问题所需的多个证据片段。
- `latency` 决定这个方案能不能在线上稳定落地。

#### 二、检索前优化 (Pre-Retrieval)

这一层的目标是让用户 Query 更适合被检索系统理解，因为真实用户问题往往短、口语化、指代不清，直接拿去做向量检索很容易漏召回。

##### 1. Query Rewrite (查询改写)

把口语化、歧义化的问题改写成更适合检索的表达。比如：

- 原始问题：`RAG 检索怎么提效果？`
- 改写后：`RAG 中提升检索召回率、精度和上下文完整性的常见方法有哪些？`

改写的价值在于显式补全关键词、消歧和结构化问题，但要注意不要把原意改偏，否则会出现 query drift (查询漂移)。

##### 2. Query Expansion (查询扩展)

给原 Query 补充同义词、缩写、领域术语和相关概念，例如把“精排”扩展成“rerank / cross-encoder / 重排序”。这对 BM25 和稀疏检索尤其有效，因为它们更依赖词项匹配。

##### 3. Multi-Query Retrieval (多查询检索)

让 LLM 生成多个不同角度的子 Query，再并行检索后合并结果。它适合概念边界模糊、表述方式多样的问题，能显著提高召回率。

##### 4. HyDE (Hypothetical Document Embeddings)

先让 LLM 生成一个“假设性答案文档”，再用这个假设文档去做向量检索。它的本质是把 query-space 拉近到 document-space，缓解“短 query 和长文档语义分布不一致”的问题。

##### 5. Query Routing (查询路由)

先判断问题类型，再选择不同检索策略。例如：

- 事实型问题 → 直接走向量检索 + rerank
- 术语精确匹配问题 → 强化 BM25
- 多跳推理问题 → 多轮检索或图检索

这类路由能避免所有问题都用同一套检索策略，减少无效召回。

#### 三、检索中优化 (Retrieval)

这一层决定“从库里怎么找”。如果语料、索引和召回器本身设计不合理，后面的 rerank 也只能在错误候选集里做排序。

##### 1. Hybrid Search (混合检索)

同时使用稀疏检索 (BM25) 和稠密检索 (Embedding Search) 是最常见、也最稳妥的策略。

- BM25 擅长精确词项命中，适合术语、编号、专有名词。
- 向量检索擅长语义匹配，适合同义改写、表达多样的问题。

实际工程里常用两种融合方式：

```text
BM25 召回 Top-K1
向量召回 Top-K2
结果去重后融合
再交给 reranker
```

也可以直接做分数融合：

$$
final\_score = \lambda \cdot score\_{dense} + (1 - \lambda) \cdot score\_{sparse}
$$

##### 2. Metadata Filtering (元数据过滤)

在检索时先加结构化约束，例如文档类型、时间范围、业务线、权限、语言、章节标题等。这样可以显著减少搜索空间，提高命中质量。

典型场景包括：

- 只查最新版本文档
- 只查某个产品线的知识库
- 只查中文内容或某个部门文档

##### 3. Chunk 策略优化

检索质量很大程度上取决于切分质量。常见做法包括：

- 结构感知切分，优先按标题、段落、表格、代码块切分
- 使用适度 overlap 保持上下文连续性
- 采用 Parent-Child 索引，child 负责召回，parent 负责补全语义

如果 chunk 太大，会稀释向量语义；如果 chunk 太小，会导致答案证据不完整。

##### 4. 多向量或多粒度索引

同一段文档可以同时建立多种表示，例如：

- chunk 级向量，用于细粒度检索
- section 级向量，用于结构化召回
- document 级摘要向量，用于粗召回

这种方式特别适合长文档、技术规范和论文检索，因为不同问题对应的最佳粒度不同。

##### 5. Contextual Retrieval

检索时不仅看 chunk 本身，还把标题、章节路径、父块摘要、邻接块等上下文编码进去。这样可以缓解“局部块单独看不完整”的问题，特别适合技术手册、制度文档和多层级知识库。

#### 四、检索后优化 (Post-Retrieval)

这一层是把“召回上来的候选集”变成“真正可喂给 LLM 的上下文”。很多 RAG 系统最后效果差，不是因为没召回，而是因为候选集太噪、顺序不对、上下文太长。

##### 1. Rerank (重排序)

用 Cross-Encoder 或 LLM Reranker 对候选文档重新打分。它能补足向量检索的粗糙性，适合把真正相关的证据排到前面。

##### 2. Context Compression (上下文压缩)

把候选块中与问题无关的句子删掉，只保留证据句。这样可以在不丢信息的前提下减少 token 浪费，提升最终生成质量。

##### 3. Neighbor Expansion (邻接扩展)

命中一个 chunk 后，自动补齐前后相邻块，避免关键解释被切断。这对教程、论文和 FAQ 特别有效。

##### 4. 去重与多样性控制

如果多个候选块语义高度重复，就会浪费上下文窗口。可以用去重、MMR (Maximum Marginal Relevance) 或聚类式筛选，在相关性和多样性之间做平衡。

#### 五、工程实践里的关键参数

实际落地时，最容易出问题的不是某个单点算法，而是参数组合不合理。

- `Top-K` 不是越大越好，K 太大只会把噪声一起带进来。
- `rerank` 的候选集不能太小，否则精排没有发挥空间。
- `chunk size` 要与文档类型和模型上下文窗口联动调整。
- `overlap` 只能缓解边界问题，不能替代结构化切分。

一个比较稳妥的在线链路通常是：

```text
Query -> Rewrite/Expand -> Hybrid Retrieve -> Metadata Filter -> Rerank -> Compress -> LLM
```

##### 示例伪代码

```python
def rag_retrieve(query, retriever, reranker, compressor):
     # 1) 改写与扩展 Query
     rewritten_query = rewrite_query(query)
     expanded_queries = expand_query(rewritten_query)

     # 2) 多路召回
     candidates = []
     for q in expanded_queries:
          candidates.extend(retriever.hybrid_search(q, top_k=50))

     # 3) 去重 + 元数据过滤
     candidates = deduplicate(candidates)
     candidates = filter_by_metadata(candidates, source="internal_docs")

     # 4) 精排
     ranked = reranker.rank(query, candidates)

     # 5) 上下文压缩
     top_docs = ranked[:8]
     compressed_context = compressor.compress(query, top_docs)

     return compressed_context
```

#### 六、常见误区

1. 误区：只要把 `Top-K` 调大，召回就会变好。
    实际上会把噪声一起放大，后续 rerank 和压缩成本也会上升。
2. 误区：向量检索足够了。
    对数字、编号、专有名词、代码符号等场景，BM25 往往更可靠。
3. 误区：Query 改写越激进越好。
    改写过头会导致语义漂移，检索到不该检索的内容。
4. 误区：只优化检索器，不看切分和元数据。
    语料结构不好，检索上限也会被锁死。

#### 七、面试时可以怎么总结

可以这样回答：RAG 的检索优化不能只看单一检索器，而要从 Query、索引、召回、排序和压缩五个层面一起做。工程上通常先用 Query Rewrite、Multi-Query 和 HyDE 提升检索入口，再用 Hybrid Search、Metadata Filter 和更合理的 Chunk 策略扩大有效候选集，最后通过 Rerank、Context Compression 和 Neighbor Expansion 把真正可用的证据压紧到 LLM 上。真正稳定的 RAG 不是“召回更多”，而是“在有限上下文里召回得更准、更全、更省”。

#### 知识扩展

- Reranker：负责把候选集从“可用”变成“更准确的排序结果”。
- Chunking：决定了文档被如何切分，直接影响召回上限。
- Hybrid Search：融合稀疏检索和稠密检索，通常是线上最稳的方案。
- HyDE：适合短 Query 和长文档语义不对齐的场景。
- Context Compression：解决“召回很多但上下文窗口不够”的问题。
- Graph RAG：当问题需要多跳关联时，图结构检索可以进一步提升覆盖率。

### 1.7 面试中如何系统介绍 RAG 技术？常用 RAG pipeline 如何拆解？有哪些更高阶优化手段？

如果面试官让你完整介绍 RAG，建议你按"目标 -> 流程 -> 优化 -> 边界"这条主线回答，而不是只讲一个向量检索。

一句话定义可以这样说：RAG (Retrieval-Augmented Generation) 是把外部知识检索系统与 LLM 生成能力耦合起来的框架，目的是在不微调主模型的前提下，提升答案的时效性、可解释性和私域适配能力。

#### 一、先讲清楚为什么需要 RAG

纯 LLM 回答通常有四个工程痛点：

1. 知识滞后：参数知识截止后无法自动更新。
2. 幻觉风险：模型会生成"看起来对"但无法溯源的内容。
3. 私域缺失：企业内部文档、规范、FAQ 不在预训练语料中。
4. 成本问题：靠频繁微调更新知识，迭代慢且成本高。

RAG 的核心价值是把"知识更新"从模型训练问题改造成检索系统问题。

#### 二、常用 RAG pipeline 拆解

实际项目里最常见的是两段式 pipeline：离线构建索引 + 在线问答。

```text
离线 Indexing
文档采集 -> 解析清洗 -> 语义分块 -> 向量化 -> 建索引 (Vector/BM25/Hybrid)

在线 Serving
用户问题 -> Query 改写/扩展 -> 多路召回 -> Rerank -> 上下文压缩 -> Prompt 编排 -> LLM 生成 -> 引用回传
```

##### 1. 离线 Indexing

- 文档采集：统一接入 PDF、Wiki、网页、工单、代码库等异构数据源。
- 解析清洗：去页眉页脚、广告、噪声字符，保留标题层级和结构信息。
- 语义分块：优先结构感知切分，控制 chunk size 和 overlap，避免语义断裂。
- 向量化与索引：常见是 dense index + sparse index 共存，便于混合检索。
- 元数据增强：补充 doc_id、section、时间戳、权限标签，支持过滤与溯源。

##### 2. 在线 Serving

- Query 预处理：rewrite、expand、multi-query，降低口语化输入的漏召回。
- 多路召回：向量检索、BM25、规则检索并行召回，扩大有效候选集。
- 重排序：Cross-Encoder 或 LLM reranker 精排，把可用证据排到前列。
- 上下文构建：压缩无关句、拼接相邻块或 parent 块，控制 token 预算。
- 生成与引用：LLM 基于证据回答，并返回来源片段提升可审计性。

可以把它抽象为一个目标函数：

$$
Quality \approx f(Recall, Precision, Coverage, Faithfulness, Latency, Cost)
$$

这也是面试里常说的"RAG 不是单指标优化，而是多目标权衡"。

#### 三、更高阶的优化手段

下面这部分是区分"会用 RAG"和"能做 RAG 系统设计"的关键。

##### 1. Pre-Retrieval 优化

- HyDE：先生成假设文档再检索，缓解短 query 与长文档语义错位。
- Query Routing：先分类问题，再路由到 FAQ、向量库、图谱或 SQL 检索器。
- Decomposition：把复杂问题拆成子问题，走多轮检索再合并证据。

##### 2. Retrieval 优化

- Hybrid Search + RRF 融合：稳定提升术语匹配和语义匹配的综合能力。
- Parent-Child Retrieval：child 负责高精度命中，parent 负责语义补全。
- Contextual Retrieval：召回时引入标题路径、邻接块摘要等上下文特征。
- Multi-Vector Index：同一文档建立多粒度向量，适配不同问题粒度。

##### 3. Post-Retrieval 优化

- Rerank Cascade：轻量模型初筛 + 重模型精排，平衡延迟和效果。
- Context Compression：句级证据抽取，减少噪声和 token 浪费。
- Diversity Control：通过 MMR 或聚类抑制重复块，提升证据覆盖度。
- Lost in the Middle 重排：把关键证据放在 Prompt 前后高注意区域。

##### 4. 系统级优化

- 缓存分层：query cache、embedding cache、结果 cache，降低均值延迟。
- 质量守护：低置信度触发拒答或追问，避免"强行回答"。
- 在线评估：构建 retrieval hit、citation faithfulness、answer correctness 指标闭环。
- 灰度与回滚：检索策略升级走 A/B 测试，避免一次性全量切换。

#### 四、工程落地时的关键参数与经验值

- `chunk_size`：常见 300 ~ 800 tokens，技术文档可偏大，FAQ 可偏小。
- `overlap`：常见 10% ~ 20%，过高会增加冗余与索引成本。
- `retrieve_top_k`：常见 20 ~ 100，取决于后续 rerank 能力。
- `final_top_n`：常见 3 ~ 8，受模型窗口和任务复杂度影响。
- `rerank_budget_ms`：需要和接口 SLA 联动约束，通常单次 50 ~ 200ms。

一个典型在线链路可以写成：

```text
Query
-> Rewrite/Route
-> Hybrid Retrieve (Top-K)
-> Rerank (Top-N)
-> Compress/Assemble Context
-> Generate with Citations
-> Guardrail Check
```

#### 五、常见误区与边界条件

1. 误区：把 Top-K 调大就等于优化。
    噪声会同步放大，且上下文窗口被无效内容占用。
2. 误区：只优化检索，不管生成。
    Prompt 结构、引用约束和拒答策略同样决定最终可信度。
3. 误区：忽略权限与数据新鲜度。
    企业场景里权限过滤和增量更新通常是第一优先级。
4. 边界：多跳推理、跨表计算、强事务一致性问题。
    这类问题通常需要 Graph RAG、Tool Calling 或工作流编排系统配合。

#### 六、面试可直接复述的总结

可以这样回答：RAG 的本质是让 LLM 从"参数记忆"转向"外部证据驱动"。我在设计 pipeline 时会分离线索引和在线问答两条链路，在线链路默认采用 Query 优化、混合召回、Rerank、上下文压缩和引用生成五段式。进一步优化会做路由、分层 Rerank、Parent-Child 检索和质量守护，并用线上指标闭环持续调参。最终目标不是单点提高召回，而是在正确性、可解释性、延迟和成本之间达到可运营的平衡。

#### 知识扩展

- Agentic RAG：在 RAG 基础上引入规划与工具调用，适合多步任务和复杂工作流。
- Graph RAG：通过实体关系图建模跨文档关联，适合多跳问答与因果链推理。
- Self-RAG：让模型在生成过程中自评是否需要继续检索，强化可控性。
- Long Context Engineering：与 RAG 互补，决定"检索多少"和"如何放入上下文"。
- Evaluation Framework：离线评测集 + 在线埋点是持续优化 RAG 的基础设施。

### 1.8 RAG 的幻觉问题如何处理？有哪些可行方案？

RAG 里的幻觉问题，本质上不是“模型不会说话”，而是“模型在证据不足、证据冲突或证据使用不当时，仍然倾向于生成看起来合理但实际上没有依据的内容”。所以处理幻觉不能只靠一句“请基于资料回答”，而要从检索、上下文构建、生成约束、答案校验和拒答策略五个层面一起做。

#### 一、先理解 RAG 为什么还会幻觉

即使接入了检索，RAG 仍然可能出现幻觉，常见原因有：

1. 检索召回不到关键证据。
    模型只能基于不完整上下文补全答案，容易凭参数记忆臆测。
2. 召回了但噪声太多。
    无关 chunk 混进上下文后，模型会被错误线索带偏。
3. 证据之间存在冲突。
    多个文档版本不一致时，模型可能“选一个看起来最顺的说法”。
4. Prompt 约束太弱。
    如果没有明确要求“只能依据证据回答”，模型会自然补全。
5. 生成阶段没有校验。
    模型生成完直接返回，没有做事实一致性检查。

所以，RAG 的幻觉治理目标不是“让模型绝不幻觉”，而是“尽量让回答可溯源、可拒答、可校验”。

#### 二、最有效的总体思路

可以把防幻觉链路抽象成这样：

```text
Query
  ↓
Retrieve evidence
  ↓
Filter and rerank
  ↓
Generate with grounding constraint
  ↓
Verify answer against evidence
  ↓
Return answer or refuse
```

核心原则只有一句话：**没有证据就不编，有证据就要显式引用，有冲突就要澄清，有低置信度就要拒答或追问。**

#### 三、可行的解决方案

##### 方案一：提升检索质量，让证据先“找对”

幻觉很多时候不是生成问题，而是检索问题。只要证据没找准，后面再强的模型也只能猜。

常用做法包括：

1. Hybrid Search。
    结合 BM25 和向量检索，减少纯语义召回漏掉关键词的情况。
2. Rerank。
    用 Cross-Encoder 或 LLM reranker 把真正相关的证据排到前面。
3. Query Rewrite / Expansion。
    把口语化问题改写成更适合检索的形式，减少漏召回。
4. Parent-Child Retrieval。
    child 负责精确命中，parent 负责补全上下文，降低断章取义。
5. Neighbor Expansion。
    把命中文档附近的上下文一起带上，避免片段化导致误解。

这类方法的目标是先把“能支撑答案的证据”尽量找全，否则模型只能在空白处发挥想象力。

##### 方案二：给生成阶段加强约束，让模型“只能基于证据说话”

这是最直接也最常用的手段。Prompt 里不能只说“请回答问题”，而要明确限定回答边界。

例如可以要求模型：

```text
1. 只能依据给定上下文回答。
2. 如果上下文没有足够证据，明确回答“无法从资料中确定”。
3. 回答时尽量标注引用片段或来源编号。
4. 不要补充上下文中没有出现的新事实。
```

示例 Prompt：

```text
请仅根据以下资料回答问题。
如果资料不足以支持结论，请直接说“资料不足，无法确定”，不要猜测。
回答时请给出引用来源编号。

资料：
[1] ...
[2] ...

问题：...
```

这类约束的关键不是“让模型更保守”，而是让它在证据不足时有明确的退出机制。

##### 方案三：做上下文压缩和去噪，减少错误线索干扰

很多幻觉来自“检索到了很多东西，但真正相关的信息被噪声淹没了”。

常见做法有：

1. Context Compression。
    先抽取与问题相关的句子，再送入 LLM。
2. Evidence Selection。
    先做证据句级筛选，而不是整段 chunk 直接塞给模型。
3. 去重与多样性控制。
    防止同义重复内容占满上下文窗口。
4. Lost in the Middle 重排。
    把最关键证据放到 prompt 前后更显著的位置。

这类手段的目标是减少“错证据”对模型的诱导，让模型更容易聚焦于真正有用的信息。

##### 方案四：引入答案校验或事实核查步骤

生成完直接返回，通常是幻觉控制最弱的一环。更稳妥的做法是增加一个 verify 阶段。

可以采用以下方式：

1. Rule-based Check。
    检查回答是否引用了上下文中不存在的实体、数字或结论。
2. NLI / Entailment Check。
    用蕴含模型判断答案是否能被证据支持。
3. LLM Self-Check。
    让模型自评“回答中的每一句是否都能在证据中找到支撑”。
4. Citation Verification。
    检查每个引用片段是否真的支持对应结论。

如果校验失败，就不要直接返回，而是改成“资料不足”或重新检索。对于高风险场景，这一步几乎是必需的。

##### 方案五：设置拒答和追问机制，避免强行回答

RAG 幻觉治理里，一个经常被忽略但非常重要的能力是“拒答能力”。

当出现以下情况时，应触发拒答或追问：

1. 检索结果置信度过低。
2. 证据之间明显冲突。
3. 问题本身缺少关键信息，无法唯一确定答案。
4. 检索到的内容与问题主题不匹配。

例如：

```text
如果检索证据不足，请不要猜测答案。
可以返回：
1. 当前资料不足，无法给出确定结论。
2. 请补充问题中的时间、版本或业务背景。
```

这比“硬回答一个可能错的答案”更适合生产环境，因为很多企业场景里，错答的代价远高于不答。

##### 方案六：做多轮检索或分解问题，减少一步到位的误判

对于复杂问题，单轮 RAG 很容易因为一次检索不完整而产生幻觉。可以先拆问题，再逐步检索和回答。

例如：

```text
复杂问题 -> 拆成子问题1, 子问题2, 子问题3
每个子问题单独检索证据
最后聚合子答案并做一致性检查
```

这种方式尤其适合多跳问答、跨文档总结和需要多项证据拼接的问题，因为它能降低模型“在一次回答里自行补全逻辑链”的概率。

#### 四、工程实践里推荐的组合拳

如果是线上系统，通常不会只用单一手段，而是组合使用：

1. 检索阶段：Hybrid Search + Rerank + Metadata Filter。
2. 上下文阶段：Evidence Selection + Compression + Reorder。
3. 生成阶段：Grounded Prompt + Citation Requirement + Refusal Policy。
4. 校验阶段：Answer Verification + Low-confidence Fallback。

一个比较稳的在线链路可以写成：

```text
Query
-> Retrieve Top-K
-> Rerank Top-N
-> Filter / Compress evidence
-> Generate answer with citations
-> Verify factual consistency
-> Return answer or refuse
```

#### 五、常见误区

1. 误区：Top-K 调大就能解决幻觉。
    错。Top-K 过大只会引入更多噪声，反而让模型更容易被带偏。
2. 误区：只要加了 RAG 就不会幻觉。
    错。RAG 只是把“凭记忆回答”变成“基于证据回答”，但证据找错、用错、校验缺失仍然会幻觉。
3. 误区：Prompt 限制一次就够了。
    不够。Prompt 只能约束输出风格，不能替代检索、压缩和验证。
4. 误区：系统必须给出答案。
    生产上更重要的是可信而不是强答，必要时拒答才是正确策略。

#### 六、面试中可以怎么总结

可以这样回答：RAG 的幻觉问题不能只靠提示词解决，而要从“找对证据、压掉噪声、限制生成、校验事实、必要时拒答”五个环节一起治理。工程上我通常会先用 Hybrid Search 和 Rerank 提高证据质量，再用 grounded prompt 约束模型只基于证据生成，同时增加事实校验和低置信度拒答机制。对于复杂问题，还会拆成多轮检索或子问题求解，降低一步到位的误判风险。最终目标不是让模型永远不出错，而是让错误可发现、可拦截、可回退。

#### 知识扩展

- Faithfulness Evaluation：衡量答案是否严格依赖证据，是幻觉治理的核心指标。
- Citation Grounding：给答案加来源引用，便于追溯和审核。
- Answer Verification：在返回前做事实一致性检查，和幻觉抑制直接相关。
- Self-RAG：让模型自己判断是否继续检索或是否可信，属于更主动的幻觉控制。
- Guardrail System：从产品层面约束模型输出边界，和拒答策略强相关。
