---
template: doc
theme: auto
lang: zh
title: KVShare：多租户下“部分重算”的 KV 复用
subtitle: arXiv 2025 · ctx / multi-tenant
source: arXiv:2503.16525v2 [cs.CL], 2025-05-16, 22 pp. (preprint, under review)
outline: right
---

现有多租户服务只有前缀完全一致才能复用 KV，固定长度分块又让命中率很低；KVShare 用自适应长度匹配 + 双阶段高偏差 token 重算 + 命中率感知调度，在恢复精度的同时把 TTFT 最多降 9.39×，对第一章最有用的是“复用必须配验证/重算成本”的取舍。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | KVShare: An LLM Service System with Efficient and Effective Multi-Tenant KV Cache Reuse |
| 作者 | Huan Yang, Renji Zhang, Mingzhe Huang, Weijun Wang, Yin Tang, Yuanchun Li, Yunxin Liu, Deyu Zhang |
| 机构 | Central South University；Tsinghua University |
| 发表 | arXiv 2025 预印本；论文标注 “Preprint. Under review.”，正式发表信息论文未给出 |
| 正式版本 | arXiv v2，2025-05-16；会议/期刊页码与 DOI 论文未给出 |
| arXiv / DOI | arXiv:2503.16525v2 [cs.CL]；DOI 论文未给出 |
| 本地原文 | `paper_source/KVShare_arXiv2503.16525.pdf`（22 页） |
| 代码/数据 | 未发现公开代码；ShareGPT、InstructionV2、LMSys、WildChat、SAMSum、GSM8K、DROP |
| 版本边界 | 基于 vLLM 0.4.1，约 2K 行 Python；单张 NVIDIA L40S；3 个模型 |

## B 问题与动机

长上下文把 KV 复用推到多租户场景：不同用户的请求可能包含相同模板、相同文档块或相同系统提示，但前缀并不完全一致。前缀缓存只能处理“从第一个 token 起完全相同”的情况，跨请求复用因此漏掉大量机会。

直接复用相同 token 块的 KV 会引入注意力偏差：同一段 token 在不同前缀下，其 KV 并不相同；把它搬到另一个请求，注意力矩阵会偏离原值。CacheBlend、EPIC 用固定长度分块，再重算一部分关键 token 来修复偏差；但可复用块往往非连续、长度不一，固定分块会降低命中率。

第二个问题是调度。多租户请求的 KV 命中率差异很大，传统连续批处理把高命中率与低命中率请求混在一批，低命中率请求的长计算会掩盖高命中率请求的加速收益，抬高平均 TTFT。

## C 方法机制

KVShare 有四个组件：KV Retriever、Cache-Aware Scheduler、DHD Selector、KV Writer。

检索侧用滚动哈希做自适应长度匹配：对目标与候选 token 序列建立滑动窗口哈希索引，命中后逐 token 校验，得到可复用的非连续片段；片段长度随请求变化，不固定。命中率因此高于固定分块方案。

重算侧的核心是 Dual-Stage High Deviation（DHD）。论文对注意力输出做一阶展开：

`ΔH = H' − H ≈ (∂H/∂K)·ΔK + (∂H/∂V)·ΔV`

其中 `∂H/∂V = A`，即注意力矩阵本身是 Jacobian。由此得到 token 重要性分数：

`Score_i = (Σ_j Softmax(Q_j K_i^T / √d_k)) · ||ΔV_i||_1`

也就是“该 token 收到的累计注意力 × 其 value 偏差的 L1 范数”。按分数取 Top-r% 重算。论文发现 K 方向与 V 方向选出的 token 有 80%–90% 重叠，因此只算 V 方向也能接近完整 Jacobian 的精度。

prefill 阶段按上述分数重算；decode 阶段注意力分布会漂移（attention drift），原先的列和 `α` 失效，因此每步用当前解码 token 对复用 token 的注意力重新加权，再选 Top-r% 重算。调度侧则按 KV 命中率降序排序请求，优先把高命中率请求送入 batch，避免被低命中率请求拖尾。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 精度主实验 | L40S；Qwen2.5-7B、Llama3.1-8B、Yi1.5-9B；GSM8K、DROP、SAMSum；4 个重算比例 | 仅 prefill 重算时，平均比 CacheBlend 高 9.48%、比 EPIC 高 29.98%；加 decode 重算后，比 SOTA 平均高 20.38% | 重算关键 token 能把精度拉回接近全量重算 |
| 端到端 TTFT | 真实多租户指令，QPS 0–30；20% 重算比例 | 30 QPS 下 TTFT 稳定在 881 ms 以下；对比 FR/CacheBlend/EPIC 明显更低 | 命中率差异大时，调度比单纯提高命中率更关键 |
| 吞吐 | 同上 | QPS 超过 8 后吞吐平均为 FR 的 1.2× | 高并发下复用收益才显现 |
| 调度消融 | 开/关 cache-aware scheduler | TTFT 最大降低 33.8% | 按命中率分批是独立增益 |
| 代价 | 每步增加 1/2/3/5 个重算 token | TPOT 约翻倍；每多一个 token 约多 1× 惩罚 | 精度修复不是免费的，直接冲击 TPOT SLO |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | 对应 `ctx` 的跨租户共享块：模板、系统提示、文档片段；对象边界是“可匹配的 token 片段”，不是整段会话 |
| 价值建模 | 复用收益 = 命中率 × 省掉的 prefill；复用成本 = 重算比例 × decode 开销；质量约束 = 重算后精度接近全量重算。论文的 `Score_i` 可作为“哪些 token 值得保留/重算”的价值密度 |
| 生命周期 | 检索 → 加载 → 部分重算（刷新）→ 写回；重算比例是可调的“验证强度”，但论文没有 TTL、驱逐或版本失效 |
| Flink 映射 | 以 `tenantId` + `prefixHash` keyBy；`ValueState<HitRate>` 记录请求命中率；`MapState<blockId, KVRef>` 存块；调度可用 keyed priority queue + timer 实现“按命中率分批”；checkpoint 保存命中统计 |
| 可写缺口 | 论文把重算当精度修复，没有把 TPOT 成本写进价值函数，也没有安全/隔离维度。第一章可写“SLO 约束下的部分复用”：用 `benefit(hit) − cost(recompute) − risk` 决定复用比例，并在 Flink 中做命中率感知的准入与降级 |

## F 局限与边界

论文是 preprint，未正式发表；实验只在单张 L40S 上做，没有多节点、PD 分离或远端存储。模型只覆盖 3 个 7B–9B 级模型，长上下文百万 token 的场景未实测。DHD 依赖注意力矩阵与 `ΔV`，需要额外计算与显存；论文自己报告 TPOT 约翻倍，这是明确的代价边界。安全维度完全未讨论：跨租户共享正是 PromptPeek 一类侧信道的入口。质量评估只用 GSM8K、DROP、SAMSum 三个数据集，代码与 Agent 工具链未覆盖。

## G 引用信息

```bibtex
@misc{yang2025kvshare,
  title  = {KVShare: An LLM Service System with Efficient and Effective Multi-Tenant KV Cache Reuse},
  author = {Yang, Huan and Zhang, Renji and Huang, Mingzhe and Wang, Weijun and Tang, Yin and
            Li, Yuanchun and Liu, Yunxin and Zhang, Deyu},
  year   = {2025},
  eprint = {2503.16525},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  note   = {arXiv v2, 16 May 2025; preprint under review}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 4–6 页 DHD 与调度；第 7–10 页实验；第 11 页 Limitations；第 14–15 页自适应匹配算法。
