# 数据集与已完成实验说明（v0.3.0）

> 版本：0.3.0 · 最后更新：2026-11-26
> 适用范围：`MasterGraduationProject/dataset/` 全部产物，以及基于该数据集完成的模型服务标定实验。
> 本文档面向人（作者、导师、答辩评审）；面向 Agent 的操作手册见 `HANDBOOK.md`，
> 数据卡摘要见 `DATASET_CARD.md`，论文↔文件映射见 `PAPER_MAP.md`，标定操作见 `CALIBRATION_HOWTO.md`。

---

## 0. 这份文档回答什么

1. 这个数据集是什么、为哪篇论文的哪些问题服务；
2. 它包含哪些文件、每个文件的字段与语义；
3. 它是怎么被构造出来的、为什么可信；
4. **已经做了哪些实验**、结果是什么、结论能说到什么程度；
5. 还缺哪些实验、缺什么输入。

本文档严格区分「已实测」与「尚未验证」。凡未做的实验，第 8 节明确列出，不在正文中预写结论。

**版本引用**：本数据集当前版本 `dataset-v0.3.0`（2026-11-26）。引用具体数字时请同时注明版本、部署口径（单卡 27B、串行、32,768 输出、无截断）与样本量（300 条标定 / 3,000 条请求流），否则数字不可复现。
历史版本差异见 `contracts/CHANGELOG.md`。

后续 Agent 要在此基础上写实验时，先读 `AGENT_PLAYBOOK.md`（铁律 / 分工 / 验收 / 常见错误）。

---

## 1. 研究背景与数据集目标

### 1.1 论文主线

论文研究**流式智能体中的缓存价值建模与生命周期控制**：在持续到达的查询流上，判断一个缓存对象
「还值不值得留、能不能安全复用、什么时候必须失效或局部修复」。

### 1.2 数据集的四个对象

数据集把可缓存对象抽象为四类，每类有其独立的复用语义：

| 对象 | 含义 | 复用的前提 | 失效的主要来源 |
|---|---|---|---|
| `resp` | 最终回答 | 证据集与问题意图不变 | 证据文档改版、口径调整 |
| `rag` | 检索上下文 | 文档版本仍在有效期内 | 文档新增/替换、版本切换 |
| `act` | 工具调用及其结果（只读 SQL） | 同一 `act_key` + 参数 + 快照版本 | 数据行变化、口径变更 |
| `plan` | 执行计划 | 同一 `plan_id` 且步骤依赖未变 | 下游工具或字段变化 |

支撑复用的证据分三类：**文本知识**（白皮书/字段卡/笔记）、**语义层指标口径**（指标卡）、
**血缘边**（表—字段—指标—下游的关联关系）。

### 1.3 数据集必须支撑的实验

| 编号 | 实验 | 需要的输入 |
|---|---|---|
| M1 | 异质开销与重复率（动机） | 请求流 + 300 条标定的分阶段耗时 |
| M2 | 静态 TTL / 纯语义基线的问题（动机） | 请求流 + 更新事件 + 双视角真值 |
| A–B | 缓存容量、命中率与有效命中率 | 请求流 + 标签 + 成本剖面 |
| C | 值驱动准入/保留策略 | 成本剖面 + 容量档位 + 策略实现 |
| D | `resp` 双层提升（先复用检索/工具，再生回答） | 分支配对 + 标签 |
| E | 更新与依赖修复（局部修复 vs 全量再生） | 更新事件 + 主张级 ρ 分层 |
| F | 组合长流与原型（可选 Flink） | `events/streams/long_*.jsonl` |

### 1.4 本数据集不负责什么

- 不实现缓存策略本身（没有 LRU/准入/淘汰代码）；
- 不实现自然语言→SQL 生成（`act` 使用题库的 gold SQL，见 7.8）；
- 不替作者做人工标注与主观评分（`labels/to_review.csv` 留给人工）。

---

## 2. 总体规模

| 维度 | 规模 |
|---|---|
| 交付文件 | 74 个（`MANIFEST` 统计），76.6 MB |
| 知识文档 | **6,000 篇**：字段卡 3,600 / 笔记 870 / 白皮书 600 / 指标卡 450 / 工具卡 300 / 计划卡 180；任一快照下可见约 2,000 篇 |
| 数据库快照 | v0 / v1 / v2 各一份 SQLite（9.1 / 9.1 / 9.4 MB）；v0、v1 各 60 表 49,040 行，v2 62 表 49,560 行 |
| 题库 | **200 题**：单表 60 / join 70 / 嵌套聚合 70；主张数分布 1:30、2:40、3:60、4:40、5:30 |
| 语义簇 | **40 簇**，每簇 3–6 题 |
| 请求流 | **3,000 条**（快照 v0:871 / v1:1,309 / v2:820；主张数 1:485、2:803、3:771、4:602、5:339） |
| 请求上下文 | 3,000 条（`req_id → task_id / variant / tenant / reused / cluster_id`） |
| 更新事件 | **40 条**：schema 14 / 指标口径 8 / 数据行 6 / 血缘 6 / 代码表 6；其中负对照 6 条；通知延迟 0.03–3.0 h（中位 1.61 h） |
| 安全复用标签 | **300 条**（150 安全 / 150 不安全），同一批里 10 条双视角分歧 |
| 分支配对 | 120 对，其中 **30 对**已用真实模型回填 |
| 成本剖面 | 222 行（**220 已实测** / 2 行大模型待回填） |
| 模型标定 | **300 条**完整实测 + 20 条思考量补跑 |
| 长流 | seed42–46 各 3,000 条；long_01 / long_02 各 5,000 条 |
| 句向量 | 600 × 512 float32（1.56 MB，L2 归一化） |
| 校验断言 | **48 项**，全部通过 |

---

## 3. 目录与文件职责

```
dataset/
├── config/params.json            单一参数源（版本、种子、规模、目标区间）
├── contracts/                    契约文件：CONTRACT.md、CHANGELOG.md、tables.json
├── schema/                       5 个 JSON Schema（文档、任务、请求流、更新事件、标签）
├── common/                       确定性三件套 + 公共工具
│   ├── ids.py                    唯一 ID 生成入口（含 block_id / cluster_id 校验）
│   ├── seeds.py                  唯一随机源 rng(stage, name)
│   └── io.py                     稳定 JSONL 读写、哈希、句向量加载
├── knowledge/
│   ├── build.py                  文档生成器（6 类模板 + 版本演进）
│   ├── docs.jsonl                6,000 篇文档（含多版本正文）
│   ├── version_changes.jsonl     文档级版本变更记录
│   └── selfcheck.py              文档层自检
├── events/
│   ├── docs_versioned.jsonl      按版本展开的文档视图（6,000 行）
│   ├── request_stream.jsonl      3,000 条请求（时分秒有序）
│   ├── request_context.jsonl     req_id → task_id / 变体 / 租户 / 复用标记
│   ├── update_events.jsonl       40 条更新事件（含 effective_at 与通知延迟）
│   ├── act_plan_pool.json        100 个 act + 60 个 plan（工具/计划目录）
│   ├── calibration_sample.jsonl  300 条标定抽样（req_id / snapshot / task_id）
│   ├── real_calibration_300.csv  ★ 300 条标定实测结果（七列）
│   ├── real_calibration_300.template.csv  空白模板
│   ├── streams/                  seed42–46（各 3,000）、long_01/02（各 5,000）
│   └── MANIFEST.json             事件层清单
├── tasks/tasks.jsonl             200 题：gold SQL、三层真值、主张与证据
├── db/
│   ├── snapshots/v0|v1|v2.sqlite 只读快照
│   ├── executor.py               只读执行器（三层保护）
│   ├── compare.py                结果比对（列序/行序无关、浮点 6 位）
│   └── MANIFEST.json             快照哈希
├── costs/path_costs.csv          222 行成本剖面（含并发列与 measured/mock 状态）
├── labels/
│   ├── safe_reuse.jsonl          300 条双视角复用标签
│   ├── branch_pairs.jsonl        120 对分支（30 对已回填模型耗时）
│   └── to_review.csv             60 条人工复核清单
├── embeddings/
│   ├── query_embeddings.npz      600×512 句向量
│   ├── query_embeddings.meta.json
│   └── calibration/              标定过程产物（进度、分支明细、元数据、归档）
├── verify/verify.py              48 项断言（P0–P6）
├── tools/                        生成、统计、审计、标定、回溯等工具
├── fixtures/                     小样本（供读者快速试跑）
├── MANIFEST.json                 全量文件清单 + 哈希 + 行数
├── HANDBOOK.md                   Agent 操作手册
├── DATASET_CARD.md               数据卡
├── PAPER_MAP.md                  论文↔数据映射
├── CALIBRATION_HOWTO.md          标定操作指南
└── REPORT.md                     本文档
```

---

## 4. 数据模型

### 4.1 请求与对象角色

每条请求携带 `obj_types`，标明它涉及哪些缓存对象。3,000 条请求的分布：

| 角色组合 | 条数 |
|---|---|
| `rag + resp` | 1,076 |
| `act + resp` | 970 |
| `act + plan + rag + resp` | 954 |
| 其他 | 0（其余组合计 0，见校验断言） |

请求字段：`req_id / timestamp / query_text / query_emb / snapshot / plan_id / act_key /
gold_doc_ids / gold_fact_spans / obj_types / domain / permission / cluster_id`。

`query_emb` 在 JSONL 中保持 `null`；向量按 `query_text` 通过
`common/io.py::embedding_lookup()` 从 npz 中取，避免 3,000×512 摊进 JSONL。

### 4.2 双时间戳与双视角真值（v0.2.0 核心设计）

更新事件有两个时刻：

| 字段 | 语义 |
|---|---|
| `effective_at` | 文档新版本**生效**的时刻（世界真实变化） |
| `timestamp` | 系统**收到通知**的时刻 |
| `notification_delay_s` | `timestamp − effective_at`，实测 0.03–3.0 h，中位 1.61 h |

因此同一条复用有两个正确性视角：

- **真值视角 `safe`**：按 `effective_at` 判断，代表「客观上答案是否仍然正确」；
- **系统视角 `safe_system`**：按 `timestamp` 判断，代表「系统当时是否知道它过期」。

不变式为 `safe_system ⇒ safe`（系统认为安全的，客观上必须安全）。
反过来 `safe ∧ ¬safe_system` 表示**系统保守地误失效**（10 条），这类样本用于观察通知延迟带来的
「本可复用却被丢弃」损失；`¬safe ∧ safe_system` 在构造上为 0 行。

### 4.3 标签体系

300 条标签 = 150 安全 + 150 不安全，全部由谓词生成（`judged_by=predicate`），
每条带 `reasons`、`cached_doc_ids`、`confidence`、`divergence_reason`。

不安全样本按负类型分层，保证策略在不同失败模式上都被检验：

| 类型 | 含义 | 条数 |
|---|---|---|
| N1 | 实体不匹配（问的是 A 表，缓存来自 B 表） | 30 |
| N2 | 权限不匹配 | 30 |
| N3 | 已过期但看起来正确（最危险） | 35 |
| N4 | 时间窗不匹配 | 30 |
| N6 | 推理链断裂（证据缺失一环） | 25 |
| — | 安全样本 | 150 |

同簇硬负样本占比 100%：不安全样本的缓存对象与其同属一个语义簇，靠语义相似度无法区分，
必须依赖版本与血缘信息。这正是本文方法要利用的信号。

### 4.4 语义簇

`cluster_id = cls_{domain}_{topic}`，共 40 簇、每簇 3–6 题。
同簇任务共享至少 1 篇证据文档，因此：

- 支持**簇级反馈**（一题的经验可迁移到同簇其他题）；
- 支持**同簇硬负样本**（语义近但版本/权限不同，必须判不安全）；
- 为实验 D「先复用检索/工具」提供天然的跨请求复用候选。

### 4.5 更新事件

40 条事件覆盖 5 类变更：schema（14）、指标口径（8）、数据行（6）、血缘（6）、代码表（6）。
其中 30 条 `answer_impact=changed`（会改变答案），10 条 `unchanged`；
6 条 `negative_control=true`（代码表变更，构造上不会命中任何请求），用于检验策略不会
「为了命中率而误判」。

事件与请求的关联通过 `changed_chunk_ids` 与请求的 `gold_fact_spans` 求交确定，
校验断言「更新影响面」要求 40 条事件都至少影响一条请求（负对照除外）。

### 4.6 执行计划池

`act_plan_pool.json` 含 100 个 `act` 与 60 个 `plan`：

- `act`：`act_key`、`act_cost`、`downstream_tools`、`readonly`；
- `plan`：`plan_id`、`steps`、依赖的 act。

下游梯度与计划完成率已做异质性约束（非空比 ≥0.65、下游档位 ≥4），避免所有工具卡退化成同一形态。

---

## 5. 构造方法

### 5.1 确定性三件套

| 模块 | 职责 | 约束 |
|---|---|---|
| `common/ids.py` | 全部 ID 生成 | 任何 ID 不得在别处拼接 |
| `common/seeds.py` | `rng(stage, name)` 唯一随机源 | 禁止直接用 `random` / `numpy.random` |
| `common/io.py` | JSONL 读写、哈希、稳定排序 | 保证同输入同字节 |

已验证：重新生成 `knowledge/docs.jsonl`、`events/request_stream.jsonl`、`tasks/tasks.jsonl`
得到与交付版本**完全相同的 SHA-256**。`branch_pairs.jsonl` 例外——它含真实 `perf_counter`
测量，按设计非确定性。

### 5.2 契约优先级

`schema/` > `config/params.json` > `contracts/tables.json`。
任何对 `schema/`、`contracts/`、`config/`、`common/` 的改动都必须登记到
`contracts/CHANGELOG.md`（原因、影响范围、已通知对象）。

### 5.3 生成门禁 P0–P6

| 阶段 | 内容 | 断言数 |
|---|---|---|
| P0 | 交付完整性 | 8 |
| P1 | 知识层 | 6 |
| P2 | 事件层基础 | 6 |
| P3 | 题库 | 6 |
| P4 | 事件层深度（时间戳、影响面、簇一致性） | 14 |
| P5 | 剖面与标签 | 5 |
| P6 | 交付文档与句向量状态 | 3 |
| **合计** | | **48** |

`python dataset/verify/verify.py --all` → 全部通过。

### 5.4 关键设计与修复记录（带原因）

| 版本 | 问题 | 处理 |
|---|---|---|
| v0.1.1 | `tool_01` 两位 ID 无法表达 100 个工具 | 改三位 `tool_001`，同步 3 条正则 |
| v0.1.2 | 12 小时流内 v2 快照请求数为 0 | 时间跨度 12 h → 18 h |
| v0.2.0 | 每题材恒为 2 条主张，ρ 固定 0.5，C3 无法分层 | 主张数改为 1–5 条（30/40/60/40/30） |
| v0.2.0 | 33/40 更新事件不影响任何请求 | 重选事件，补「更新影响面」断言 |
| v0.2.0 | 通知延迟与生效时刻混用，无法区分「已知过期」与「静默过期」 | 引入 `effective_at` + `notification_delay_s` 双时间戳 |
| v0.2.0 | 15 条 N3 样本的缓存时间戳晚于生效时刻，逻辑上不可能 | 修正样本；发现 `¬safe ∧ safe_system` 结构上不可能，不变式改为 `safe_system ⇒ safe` |
| v0.2.0 | 成本测量过快（validity_check 0.44 µs），测的是空转 | 加入真实工作量重测（8.1 µs / 1.2 µs），并补 `check_full`、`locate_full_scan` 上界 |
| v0.3.0 | `local-small-7b` 把 27B 模型误标为 7B | 改名 `local-qwen3-8-27b`，脚本别名与文档同步 |
| v0.3.0 | 标定脚本 `resp` 阶段未注入 SQL 执行结果，87% 回答为拒答 | 新增 `stage_exec_result()`，拒答率降至 0 |

---

## 6. 校验体系

48 项断言按数据层组织，任何一项失败即阻断交付：

- **P0 完整性**：目录齐备、MANIFEST 与文件哈希一致、行数与规模匹配；
- **P1 知识层**：文档计数、块 ID 跨版本稳定、变更自洽；
- **P3 题库**：难度配比、gold SQL 可执行、三层真值齐备、主张数分布、语义簇结构；
- **P4 事件层**：五类更新齐备、无未来快照泄漏、ID 合法、种子流与长流、校准模板、
  引用完整性、更新影响面、双时间戳语义、局部修复比例、act/plan 异质性、簇一致性；
- **P5 剖面与标签**：成本表状态、安全复用标签、双视角分歧样本、分支配对、待复核清单；
- **P6 交付**：文档齐备、数据卡要素、句向量状态。

复现命令：

```bash
python dataset/verify/verify.py --all          # 48 项全绿
python dataset/heal/manifest.py --check        # 或 tools/gen_manifest.py 重建
```

---

## 7. 已完成实验：模型服务标定（v0.3.0）

这是两组实证实验之一（另一组是 7.8 的 M1/M2 动机实验）。它不验证缓存策略，而是测量四类对象在真实模型上的
分阶段耗时与 token 成本，为 M1 与后续实验提供实测参数。

### 7.1 目的

1. 把 `costs/path_costs.csv` 中模型阶段的 `mock=pending` 替换为真机实测；
2. 给出四阶段（plan / rag / act / resp）与端到端的时延分布；
3. 量化「完整生成（含思考）」与「缓存路径」的差距，作为 `ΔT` 的依据；
4. 计算建模时延与实测时延的 MAPE，检验成本剖面是否可用。

### 7.2 实验配置

| 项 | 值 |
|---|---|
| 部署 | 单卡，OpenAI 兼容接口，串行单请求 |
| 服务端模型 | `qwen3.8-27b`（27B） |
| 数据档案槽位 | `local-qwen3-8-27b`（成本表模型列） |
| 最大输出 token | 32,768（plan / resp / cache 同） |
| 上下文窗口 | 65,536 |
| 推理强度 | `reasoning_effort=xhigh`（服务端默认即开启思考，响应含 `reasoning` 字段） |
| 温度 | 0 |
| 超时 / 重试 | 2,700 s / 2 次 |
| `act` 口径 | `template`（复用早期实测的 `t_act_ms`，不重复执行计时；但**执行结果**确实在每次请求中真跑，见 7.8） |
| RAG 口径 | 本地 BM25 top-5，句向量查表，上下文 ≤8,000 字符；不含重排模型 |
| 样本 | `calibration_sample.jsonl` 的 300 条，按模板顺序 |

### 7.3 执行过程与数据完整性

| 事件 | 说明 |
|---|---|
| 首轮 | 上限 4,096 时发现约 1/6 请求「生成到触顶」，病态请求输出为空 ⇒ 数据作废归档 |
| 二次 | 恢复用户指定配置（32,768 / 65,536 / xhigh）重跑 |
| 中断 | 第 259 条后服务端返回 HTTP 502（推理服务停止响应），已落盘 259 条 |
| 续跑 | 服务恢复后预热 5 次，`--resume` 从断点继续，未重跑已完成条目 |
| 完成 | 300/300 + 30 对分支配对 |
| 归档 | 旧配置（4,096）26 条、错误管线 15 条分别归档到 `embeddings/calibration/archive_*/`，不参与统计 |

**数据质量**：触顶 0 条、空输出 0 条（`finish_reason=length` 计数为 0）。
即 300 条全部为完整生成，时延含思考时间，不存在截断偏差。

### 7.4 主要结果

| 阶段 | p50 | p95 | 均值 | 最大 |
|---|---|---|---|---|
| plan | 49.7 s | 86.5 s | 51.8 s | 125.5 s |
| rag | 6.2 ms | 11.3 ms | 6.4 ms | 39.9 ms |
| act | 1.1 ms | 2.0 ms | 1.4 ms | 15.8 ms |
| resp | 98.6 s | 443.2 s | 147.1 s | 798.0 s |
| **端到端** | **154.3 s** | **505.0 s** | 198.9 s | 842.2 s |

token 统计：

| 项 | p50 | p95 | 均值 | 合计 |
|---|---|---|---|---|
| `token_cost`（plan+resp 的 prompt+completion） | 3,686 | 8,853 | 4,340 | **1,302,090** |
| plan completion | 711 | — | 745 | — |
| resp completion | 1,418 | — | 2,111 | — |

分支对比（30 对）：完整路径 p50 = **160.3 s**，缓存路径 p50 = **86.7 s**，
模型段时间节省 **46%**。

### 7.5 思考量（20 条补跑）

主批次 300 条的采集代码在跑批中途才修好，未含 reasoning 字段；另用**相同配置**补跑 20 条，
使用独立进度文件，不计入 300 条统计。

| 指标 | p50 | p95 | max |
|---|---|---|---|
| 思考字符数 | 3,291 | 11,904 | 17,088 |
| 正文字符数 | 448 | 1,222 | — |
| 思考 token 估算 | 1,859 | — | 8,986 |
| **思考占 completion 比例** | **87%** | 92% | — |

思考字符数与 resp 时长的 **Spearman ρ = 0.988**（n = 20）。

由此得到的定量判断：

1. **生成预算的绝大部分花在思考上**（87%），正文只占约 13%；
2. **resp 时延的方差几乎完全由思考长度解释**（ρ≈0.99），所以长尾不是噪声，而是「思考变长」；
3. 因此 `ΔT` 的模型段收益应按「跳过整段 resp」计，不能按输出正文长度估算；
4. 也解释了为什么给太小 `max_tokens` 会出现空输出——预算被思考吃满，正文没机会产生。

说明：思考 token 数是按「思考/正文字符占比」折算的估算值，服务端未单独返回
`reasoning_tokens`。若要精确值需引入与模型匹配的 tokenizer。

### 7.6 建模 vs 实测的 MAPE

基线为 `costs/path_costs.csv` 的本地实测 p50：

| 段 | 建模 p50 | 实测 p50 | MAPE |
|---|---|---|---|
| act | 1.160 ms | 1.095 ms | **5.90%** |
| rag | 1.421 ms | 6.161 ms | **76.93%** |
| 本地段合计 | 2.581 ms | 7.256 ms | **64.43%** |

解读：

- `act` 的建模是可靠的（5.9%），说明 SQL 执行耗时可放心用固定成本近似；
- `rag` 的建模基线低估实测约 4 倍（1.42 ms vs 6.16 ms），原因是建模只计入检索查表，
  实测包含 BM25 打分、版本解析与上下文拼装；
- 端到端时延的 99.99% 来自模型段，本地段的 MAPE 偏差对总时长影响可忽略，
  但**若论文单独报本地段 MAPE，必须说明只覆盖 act 与 rag**。

### 7.7 对论文可直接引用的结论

1. 在单卡 27B、无截断、串行条件下，端到端 p50 = **154 s**、p95 = **505 s**；
2. 模型段（plan+resp）占端到端时间的 **99.99%**，本地检索与 SQL 执行合计不足 8 ms；
3. 缓存路径相对完整路径在模型段节省 **46%**；
4. 生成预算的 **87%** 用于思考，思考长度与 resp 时长 ρ = **0.988**；
5. 成本剖面在 `act` 段误差 5.9%、`rag` 段误差 76.9%，可用于整段估算、不可用于本地段精细结论。

### 7.8 动机实验 M1 / M2（2026-11-26 补做）

数据来源为上文标定结果与请求流，完整报告见 `exp_motivation/RESULTS.md`。

**M1 异质开销与重复率**

| 指标 | 值 |
|---|---|
| 模型段（plan+resp）占端到端 | **99.99%** |
| 本地段（rag+act）占比 | 0.004% |
| 请求覆盖 | 3,000 条 / 200 题 / 40 簇 |
| plan 复用率 | 98.1%（60 个 plan） |
| act 复用率 | 97.4%（100 个 act） |
| 与前序请求共享证据文档 | 99.9% |

**M2 静态基线回放**（安全判定复用 `labels/build.py::view_judge(view="truth")`）

| 基线 | 命中率 | 有效命中率 | 过期误用率 | 错失安全复用/千条 |
|---|---|---|---|---|
| ttl_short（0.54 h） | 46.2% | 83.7% | 16.3% | 319 |
| ttl_mid（3.24 h） | 76.6% | 68.5% | 31.5% | 58.3 |
| ttl_long（13.5 h） | 90.5% | 40.3% | 59.7% | 0 |
| semantic（cos ≥ 0.88） | 98.2% | 64.6% | 35.4% | — |

Oracle 上界：80.1% 的请求存在安全复用候选（同题最近 8 条内）。

结论：短 TTL 有效但浪费机会（每千条错失 319 次），长 TTL 命中高但**近六成复用是过期误用**，
纯语义基线误用率达 35.4%。安全复用空间真实存在（80.1%），缺的是区分"能复用 / 已过期"的机制。

**有效性威胁**：TTL 键为 `task_id`（偏宽松，高估命中）、无限容量（命中率是上界）、
真值视角判定、oracle 回看 8 条、只用 seed42 单条流。下一步须在 seed43–46 上复跑给出均值±标准差。

### 7.9 有效性威胁（必须随结果一起报）

| 威胁 | 说明 | 影响范围 |
|---|---|---|
| 单一模型、单一部署 | 只有 `qwen3.8-27b` 单卡串行；`api-large-placeholder` 仍 pending | 结论只代表该部署，不能外推到大模型或并发场景 |
| 无并发档位 | 模型段未测 c=1/8/32；本地阶段才有并发列 | 不能直接支撑「固定容量下的服务能力」结论 |
| 服务重启 | 第 260 条起在服务重启后测得，已预热 | 分位数两套：全 300 条 p95=505.0 s；前 259 条 p95=540.0 s，结论一致 |
| `act` 计时用模板 | `t_act_ms` 为早期实测复用值，非每条重测 | act 段时延是固定近似；但执行结果确实逐条真跑 |
| RAG 检索质量 | BM25 top-5 会漏掉关键字段卡，导致回答口径不全 | 影响回答质量与 token 长度，不影响时延口径的有效性 |
| 无自然语言→SQL | SQL 用题库 `gold_sql`，模型只做规划与作答 | 结果应表述为「固定正确 SQL 条件下的服务时延」，不是「端到端取数能力」 |
| 无自动判分 | 未对 300 条回答做正确性自动比对 | 回答质量不在本实验结论范围内 |
| **本地 rag/act 成本远低于生产** | 本地 BM25 检索 6.2 ms、SQLite 执行 1.1 ms；生产环境的 RAG（向量检索 + 重排 + 多路召回）与 SQL（跨库/分布式/大表扫描）耗时通常高出数个量级 | 「缓存收益主要来自模型段」这一结论只对当前部署成立；act/rag 的缓存收益不能直接用本地毫秒数外推 |

### 7.10 成本口径的适用边界（重要）

本文测到的 rag 与 act 耗时是**本地实现值**，不能代表生产系统：

| 阶段 | 本地实测（本文） | 实现方式 | 生产场景的差异 |
|---|---|---|---|
| rag | p50 **6.2 ms** | 单机 BM25，语料 2,000 篇，无重排 | 向量库检索 + 多路召回 + 重排模型，通常高出数个量级 |
| act | p50 **1.1 ms** | 单文件只读 SQLite，4.9 万行 | 跨库联邦查询、分布式执行、大表扫描、排队 |

由此产生三条限制：

1. **绝对耗时是与部署强相关的量**。本文给出的 plan/resp 绝对耗时可用于该部署的容量与收益估算；
   rag/act 的毫秒数只说明「在这个本地实现里它们不是瓶颈」，不构成对生产环境的判断。
2. **模型段占比 99.99% 的结论仅对本部署成立**。若把 rag/act 替换为生产级实现，四类对象的
   成本结构会显著变化，`ΔT` 中 act/rag 分量不可忽略，此时「缓存 resp/plan 才划算」的结论需要重算。
3. **act/rag 缓存收益需要单独标定**。数据集在 `costs/path_costs.csv` 保留了相对成本字段
   （`act_cost` 0.02–0.77、并发列 1/8/32），可用于按目标部署缩放；若要主张 act 缓存收益，
   应补一轮带延迟模型的实验（可配置 p50/p95 的远程工具模拟）或在真实环境实测。

论文表述建议：把四类对象的绝对耗时写成「部署相关」，把本文结论限定为
「同一部署下四类对象的相对成本关系，以及基于该关系导出的生命周期策略」；
不要把本地毫秒级数字直接当作生产结论。

---

## 8. 尚未完成的实验
### 7.11 工具调用次数与失败重试未被标定（工具段被低估）

当前标定口径是「每条请求 1 次 rag + 1 次 act，且均为成功调用」。数据集结构显示真实形态远不止：

| 依据 | 数值 | 来源 |
|---|---|---|
| plan 平均步数 | 4.42 | `events/act_plan_pool.json` |
| act 下游工具均值 | 2.42 | 同上（分布：0:20 / 1:20 / 2:7 / 3:4 / 4:49） |
| 失败/重试字段 | **不存在** | `request_stream`、`act_plan_pool` 均无 |

按 `costs/tool_cost_model.json` 的口径（调用次数 × 期望尝试次数，参数已标 assumed）：

| 画像 | 模型段 | 工具段 | 工具占比 | 缓存工具结果可省 |
|---|---|---|---|---|
| P1 当前部署（27B + 本地工具，实测） | 198.87 s | 0.010 s | **0.005%** | 0.010 s |
| P2 慢模型 + 远程工具（假设） | 198.87 s | 2.115 s | **1.05%** | 2.115 s |
| P3 快模型 + 远程工具（假设） | 4.00 s | 2.115 s | **34.6%** | 2.115 s |
| P4 快模型 + 数仓/长排队（假设） | 4.00 s | 8.036 s | **66.8%** | 8.036 s |

两点结论：

1. **旧口径系统性低估**：若按「各 1 次、无重试」计，P4 的工具段只有 2.4 s，比 8.04 s 低 **3.35 倍**
   （调用次数 3.42 倍 × 期望尝试 1.11 倍的复合）。在当前慢模型下这个低估被模型段的绝对量掩盖，
   一旦模型变快（P3/P4），低估会直接改变结论。
2. **P3/P4 下缓存工具结果是主要收益**：工具占比 35%–67%，此时不缓存 act/rag 是明确的决策错误；
   而 P1 下它们只占 0.005%，缓存收益几乎全在 plan/resp。这正说明「按对象区分价值」不是可选优化，
   而是由部署画像决定的。

**未做**：数据集没有构造工具失败与重试事件，因此无法回放「失败一次再成功」的成本；
若要支撑重试相关结论，需要新增 `events/tool_failures.jsonl`（构造事件，标注为 assumed）
与每请求 `attempts` 字段，并在校验中登记。


以下实验**没有**结果，不得在论文中预写结论。

| 编号 | 实验 | 缺什么 | 建议顺序 |
|---|---|---|---|
| A–B | 容量—命中率—有效命中率 | 缓存原型 + 回放器 | 1 |
| C | 值驱动准入/保留 | 策略实现 | 2 |
| D | `resp` 双层提升 | 策略实现 + 分支数据（已有 30 对） | 3 |
| E | 更新与依赖修复 | 修复策略实现 | 4 |
| F | 组合长流 / Flink 原型 | 原型（可选） | 5 |
| — | 60 条人工复核 + κ | 人工标注 | 并行 |
| — | 模型段并发标定（c=8/32） | 独立测量轮次 | 与 A–B 并行 |
| — | 大模型档案回填 | 第二模型部署 | 有资源时 |
| — | act/rag 级缓存收益 | 生产级延迟模型或在真实环境实测（本地毫秒级无法外推） | 视论文定位 |
| — | M1/M2 多种子复跑 | 在 seed43–46 上重复回放 | 与 A–B 并行 |

**已完成**：M1、M2（见 7.8）。

---

## 9. 使用指南

### 9.1 常用命令

```bash
# 全量校验（48 项）
python dataset/verify/verify.py --all

# 重建文件清单
python dataset/tools/gen_manifest.py

# 统计概览
python dataset/tools/stats.py

# 样本速览
python dataset/tools/sample_view.py --req-id r000001

# 回溯某条标定记录的完整 trace
python dataset/tools/show_calibration_record.py --req-id r000002

# 标定结果汇总（分位数、token、质量标记）
python dataset/tools/calibration_report.py --split 259

# 思考量统计（20 条补跑文件）
python dataset/tools/reasoning_stats.py --progress dataset/embeddings/calibration/requests_progress_supp.jsonl

# 只读执行一条 SQL
python -c "import sys; sys.path.insert(0,'dataset/db'); import executor; \
print(executor.execute('v0','SELECT COUNT(*) FROM fact_tickets'))"
```

### 9.2 字段速查

| 想知道 | 看哪里 |
|---|---|
| 某请求问什么、涉及哪些对象 | `events/request_stream.jsonl` |
| 某请求对应哪道题 | `events/request_context.jsonl` |
| 某题的真值、主张、证据 | `tasks/tasks.jsonl` |
| 文档某版本正文 | `events/docs_versioned.jsonl`（按 `doc_id` + 版本筛选） |
| 哪些文档何时变更 | `events/update_events.jsonl`（注意 `effective_at` 与 `timestamp` 两个时刻） |
| 某条复用是否安全（两种视角） | `labels/safe_reuse.jsonl` 的 `safe` / `safe_system` |
| 某路径耗时 | `costs/path_costs.csv`（看 `measured` / `mock` 两列决定能否使用） |
| 300 条标定的时延与 token | `events/real_calibration_300.csv` |
| 标定过程明细 | `embeddings/calibration/requests.jsonl`、`run_meta.json` |

### 9.3 常见陷阱

1. **不要把 `mock=pending` 的值当实测**。成本表里 2 行大模型数据仍为空。
2. **`safe` 与 `safe_system` 不能混用**。报「过期误用为 0」要说明用的是哪个视角。
3. **`token_cost` 是 token 数，不是钱**。换成金额需另行给单价与日期。
4. **`query_emb` 恒为 null**，向量用 `query_text` 查 npz，不要按行号对齐。
5. **请求没有 `task_id`**，必须经 `request_context.jsonl` 映射。
6. **`tasks.jsonl` 没有 `domain`**，需从证据文档的 `domain` 推导。
7. **`branch_pairs.jsonl` 非确定性**（含真实计时），其余文件可复现。
8. **标定 CSV 的 `act` 列是模板值**，不是每条重测。

---

## 10. 版本历史

| 版本 | 日期 | 主要变化 |
|---|---|---|
| v0.1.0 | 2026-11-23 | 首版数据集：知识层、题库、请求流、更新事件、成本剖面、标签、校验 |
| v0.1.1 | 2026-11-24 | 工具 ID 两位改三位 |
| v0.1.2 | 2026-11-24 | 请求流时间跨度 12 h → 18 h，修正 v2 快照无请求 |
| v0.2.0 | 2026-11-25 | 双时间戳与双视角真值；主张数 1–5；语义簇；act/plan 异质性；句向量落盘；48 项断言 |
| v0.3.0 | 2026-11-26 | 300 条模型标定回填；30 对分支回填；20 条思考量；MAPE；模型列改名；文档升版 |
| **v0.4.0** | **2026-11-28** | 冻结 v0.3.0 主干零破坏；补齐在线/评测字段隔离、路径与时序规范、本地回退成本表、逐事件影响面汇总、40 对局部修复先导样本与标定脚本、工具失败重试 sidecar、人工复核评分脚本；断言扩至 54 项 |
| **v0.5.0** | **2026-11-28** | 升级现代六阶段块级重排 RAG（Contextual Chunk 13,770 块 + Hybrid RRF + `bge-reranker-v2-m3` INT8 ONNX 动态截断 + Sides Repacking，300 条实测与 4 组 IR 消融）、4 步只读 `act` 工具链实测、50 条快模型标定通道、P1–P4 多部署画像契约；断言扩至 58 项 |
| **v0.6.0** | **2026-11-28** | **构建 133.7 万行生产规模分析库 + 真实 HTTP/JSON 只读工具网关（`pool_size=4`，`c=1/8/16` 三档并发实测）与硬件无关 `act` 价值硬证据（跨快照数值漂移 21.0%、DB 查询削减上界 93.09%、精确 `resp` 未命中残余复用 85.84%），P3 达成 RAG + ACT 双真机实测；断言扩至 59 项** |

契约级变更的完整原因与影响见 `contracts/CHANGELOG.md`。

---

## 11. 附录

### A. 标定结果文件字段（`events/real_calibration_300.csv`）

| 列 | 含义 | 单位 |
|---|---|---|
| `req_id` | 请求 ID | — |
| `t_plan_ms` | 规划阶段耗时 | ms |
| `t_rag_ms` | 检索阶段耗时 | ms |
| `t_act_ms` | 执行阶段耗时（模板口径） | ms |
| `t_resp_ms` | 回答阶段耗时（含思考） | ms |
| `t_total_ms` | 端到端耗时 | ms |
| `token_cost` | plan+resp 的 prompt+completion 合计 | token |

明细（含 prompt/completion 拆分、finish_reason、检索命中文档）见
`embeddings/calibration/requests.jsonl`。

### B. 复现标定的步骤

```powershell
# 1. 准备凭据（不要提交到仓库）
copy dataset\.env.example dataset\.env
notepad dataset\.env      # 填 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL_SMALL

# 2. 校验环境（不联网、不写数据）
python dataset/tools/run_calibration_from_env.py --dry-run

# 3. 全量（约 17 小时，支持中断续跑）
$env:LLM_MAX_TOKENS_RESP='32768'; $env:LLM_MAX_TOKENS_PLAN='32768'
$env:LLM_MAX_TOKENS_CACHE='32768'; $env:LLM_CONTEXT_WINDOW='65536'
$env:LLM_REASONING_EFFORT='xhigh'; $env:LLM_TIMEOUT_S='2700'; $env:LLM_MAX_RETRIES='2'
python dataset/tools/run_calibration_from_env.py --alias small --resume

# 4. 结束删除凭据
Remove-Item dataset\.env
```

**配置纪律**：生成参数（max_tokens / 上下文 / 推理强度 / 超时 / 重试）由作者指定，
执行方不得自行下调；任何调整须先同步并获得同意。此前擅自下调到 4,096 的数据已归档作废。

### C. 安全与凭据

- `dataset/.env` 已在 `.gitignore` 中；脚本只打印掩码后的 base URL，不打印密钥；
- 标定完成后应立即删除 `.env`；若密钥曾出现在共享位置，应在服务端轮换；
- 数据集本身不含任何凭据、个人信息或真实企业数据（全部为合成数据）。

### D. 术语表

| 术语 | 含义 |
|---|---|
| 缓存对象 | `resp` / `rag` / `act` / `plan` 四类可复用产物 |
| 安全复用 | 复用后答案与重新计算一致（真值视角） |
| 系统视角 | 按系统收到通知的时刻判断，代表当时可得的信息 |
| 局部修复比例 ρ | 一次更新中「只需局部修复」的主张占比，目标 65–75%，实测 **73.0%**（805/1,102 对） |
| 硬负样本 | 语义相近但版本/权限不同、必须判为不可复用的样本 |
| 触顶 | `finish_reason=length`，生成达到 `max_tokens` 上限 |
| 空输出 | `content` 为空（思考占满预算） |

---

*文档生成于 v0.3.0 交付时；后续版本变更请同步更新第 10 节与 `contracts/CHANGELOG.md`。*


### E. 交付状态、归档与易混淆文件

**标定产物归档**（都不参与统计，勿误用）：

| 目录 | 内容 | 为什么作废 |
|---|---|---|
| `embeddings/calibration/archive_config_v1/` | 46 条，上限 512 token 的旧配置 | 回答被截断，时延低估约 5 倍 |
| `embeddings/calibration/archive_config_4096/` | 26 条，上限 4,096 | 约 1/6 请求触顶、部分输出为空 |
| `embeddings/calibration/archive_config_v2_r3/` | 1 条（`r000003`）+ 损坏文件 | 该条在 8,192 上限下用满预算仍空输出 |
| `embeddings/calibration/archive_wrong_pipeline_no_sql_result/` | 15 条 | resp 未注入 SQL 执行结果，87% 为拒答 |

**有效数据文件**：

| 文件 | 内容 |
|---|---|
| `embeddings/calibration/requests_progress.jsonl` | 300 条主标定明细（含 prompt/completion 拆分、finish_reason、命中文档） |
| `embeddings/calibration/requests_progress_supp.jsonl` | 20 条思考量补跑（含 reasoning 字段；主 300 条无此字段） |
| `embeddings/calibration/requests.jsonl` | 落盘时的 300 条快照（与 progress 同源） |
| `embeddings/calibration/run_meta.json`、`writeback.json` | 本批次配置、MAPE、回填清单 |

**易混淆点**：

1. `MANIFEST.json` **只覆盖数据目录**，不含仓库根部的 `.md` 文档；文档改动不会改变 MANIFEST。
2. 句向量 `query_embeddings.npz` 只有 **600 条**（600 个不同问句），不是 3,000 条；
   一条问句可能被多条请求复用，取向量必须按 `query_text` 查表。
3. `labels/branch_pairs.jsonl` 共 120 对，只有 **30 对**回填了模型耗时；
   其余 `t_model_full_ms` / `t_model_cache_ms` 为空，不可当实测。
4. `labels/to_review.csv` 60 条人工复核**尚未做**，κ 与人工一致性指标为空。
5. `costs/path_costs.csv` 的 `measured` 列取值是 `1`（本地实测）或 `backfill`（作者回填）或空，
   不是布尔值；`act_cost` 是相对单位，不是毫秒。
6. `request_stream.jsonl` 与 `events/streams/seed42.jsonl` **逐字节相同**；seed43–46 是同一批请求、
   不同热点迁移时刻；long_01/02 是 5,000 条、仍跨 18 小时。
7. `fixtures/` 是供快速试跑的小样本，不是交付数据，勿用于统计。
8. `verify.py --all` 全绿是**构造与一致性**的保证，不代表下游实验结论正确。
