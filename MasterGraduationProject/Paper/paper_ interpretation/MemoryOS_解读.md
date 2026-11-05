---
template: doc
theme: auto
lang: zh
title: MemoryOS：把 Agent 对话记忆做成三级存储
subtitle: EMNLP 2025 · ctx
source: EMNLP 2025, pp. 25961–25970
outline: right
---

长对话超出固定上下文窗口，MemoryOS 借鉴操作系统把记忆分成短期、中期、长期三层：短期按 FIFO 队列滚动，中期按话题分段分页，长期保存用户/Agent 画像，并用 heat 分数决定提升与淘汰。对第一章最有用的是，它给出了“语义状态分层 + 热度生命周期”的完整设计。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Memory OS of AI Agent |
| 作者 | Jiazheng Kang, Mingming Ji, Zhe Zhao, Ting Bai |
| 机构 | Beijing University of Posts and Telecommunications；Tencent AI Lab |
| 发表 | 2025 Conference on Empirical Methods in Natural Language Processing（EMNLP 2025），pp. 25961–25970 |
| 正式版本 | EMNLP 2025，10 页；本地 PDF 为 ACL 排版版 |
| arXiv / DOI | 论文未给出 arXiv 编号；DOI 论文未给出 |
| 本地原文 | `paper_source/MemoryOS_EMNLP2025.pdf` |
| 代码/数据 | https://github.com/BAI-LAB/MemoryOS；GVD、LoCoMo 两个公开对话记忆数据集 |
| 版本边界 | 本地 PDF 为 EMNLP 2025 正式排版版；实验模型为 GPT-4o-mini、Qwen2.5-3B/7B |

## B 问题与动机

LLM 的上下文窗口固定，长对话要么截断，要么把全部历史塞进 prompt。截断会丢失早期事实，造成前后不一致；全塞进去会超出窗口，成本和延迟都上升。

现有记忆机制大致分三类。知识组织型（A-Mem、TiM）把记忆组织成语义网络或思维链；检索型（MemoryBank、AI-town、EmotionalRAG）用向量库/情感状态检索；架构型（MemGPT、SCM）用读写调用和双缓冲管理上下文。它们各自解决一个维度，缺少统一的“存储—更新—检索—生成”框架。

论文的目标是把操作系统里的分层存储、分段分页、热度淘汰搬到 Agent 记忆：短期保存最近对话，中期保存话题摘要，长期保存用户画像和偏好。

## C 方法机制

**三层存储。**

- STM（Short-Term Memory）：保存实时对话，单位是“对话页” `page_i = {Q_i, R_i, T_i}`，即用户 query、模型 response、时间戳。STM 是一个固定长度队列，实验设为 7 页。
- MTM（Mid-Term Memory）：保存话题段（segment），每段由同一话题的多个对话页组成。MTM 用“分段分页”结构，段内再分页；实验最大长度 2000。
- LPM（Long-term Personal Memory）：保存用户画像和 Agent 画像。用户侧包括静态 User Profile、动态 User KB、User Traits；Agent 侧包括 Agent Profile、Agent Traits。User KB 和 Agent Traits 各维护 100 条固定队列，FIFO。

**对话链。** 每个对话页带一个 `meta_chain`。论文用 LLM 做两步：先判断新页与前面页的上下文相关性，决定接链还是重置；再把链上所有页总结成 `meta_chain`。这让 STM 不只是滑动窗口，还保留短期的上下文结构。

**STM→MTM 的 FIFO。** 新页追加到 STM 队尾；STM 达到最大容量时，最老的页按 FIFO 移到 MTM。MTM 用相似度把页归入话题段：

`F_score = cos(e_s, e_p) + F_Jaccard(K_s, K_p)`

`e_s`、`e_p` 是段和页的 embedding，`K_s`、`K_p` 是 LLM 总结的关键词集合。相似度超过阈值 `θ=0.6` 的页并入同一段；段内容由 LLM 总结。

**热度。** MTM 段的删除与向 LPM 的提升都用 heat：

`Heat = α·N_visit + β·L_interaction + γ·R_recency`

`N_visit` 是段被检索的次数，`L_interaction` 是段内对话页总数，`R_recency = exp(−Δt/μ)` 是时间衰减，`Δt` 是距上次访问的秒数，`μ=1e7`。实验取 `α=β=γ=1`。

MTM 超过容量时，淘汰 heat 最低的段。heat 超过阈值 `τ=5` 的段提升到 LPM；提升后 `L_interaction` 重置为 0，heat 下降，避免长期占用。

**检索。** STM 全量检索；MTM 两阶段：先按 `F_score` 选 top-m 段（m=5），再在段内按语义相似度选 top-k 页（GVD k=5，LoCoMo k=10）；LPM 的 User KB 和 Agent Traits 各取 top-10 条，User Profile/Agent Profile/User Traits 全量使用。检索后更新段的 `N_visit` 和 `R_recency`。

**生成。** 把 STM 最近上下文、MTM 相关页、LPM 画像拼成最终 prompt，交给 LLM 生成回答。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| GVD | 8×H20；GPT-4o-mini、Qwen2.5-7B；15 个虚拟用户、10 天对话 | GPT-4o-mini：Acc 93.3、Corr 91.2、Cohe 92.3；A-Mem 为 90.4、86.5、91.4；提升 3.2%、5.4%、1.0% | GVD 较简单，基线普遍高；MemoryOS 仍有稳定小幅提升 |
| LoCoMo | 平均 300 轮、约 9K token；GPT-4o-mini、Qwen2.5-3B | GPT-4o-mini 平均 F1 提升 49.11%，BLEU-1 提升 46.18%；平均排名 1.0（F1 与 BLEU-1 都是第一） | 长对话、跨会话记忆是主要收益场景 |
| 效率 | LoCoMo；统计 token 消耗与 LLM 调用次数 | MemoryOS 3,874 token、4.9 次调用；MemGPT 16,977 token、4.3 次；A-Mem* 2,712 token、13.0 次 | 比 MemGPT 省 token，比 A-Mem 少调用；不是“用更多算力换质量” |
| 消融 | GVD 与 LoCoMo；去掉 MTM、LPM、Chain | MTM 影响最大，LPM 次之，Chain 最小；去掉整个 MemoryOS 性能大幅下降 | 中层话题段是核心；长期画像提供个性化；对话链是辅助 |
| top-k | LoCoMo；k=5/10/20/30/40 | 性能随 k 增大而提升，但超过阈值后收益递减；k=10 兼顾效果与开销 | 检索不是越多越好，噪声会抵消收益 |

## E 对第一章的用法

下表把论文事实映射到第一章；其中 Flink 映射与可写缺口是我们的推断。

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `ctx` 的语义层：对话页（Q/R/T）、话题段（摘要 + 页集合）、用户/Agent 画像（结构化事实/偏好）。它不是 KV 张量，而是“可检索、可总结、可提升”的语义状态；可作为 `ctx` 中“冻结摘要/结构化事实”的参考实现。 |
| 价值建模 | `Heat = 访问次数 + 交互长度 + 时间衰减`，把“未来复用概率”拆成频次、深度、新近度三项；`τ=5` 决定是否提升到长期记忆；`L_interaction` 重置避免“老段永久占位”。这是第一章“价值 = 收益 × 概率 − 成本”的一个可解释基线，但缺少字节成本和重算成本。 |
| 生命周期 | 写入 STM；FIFO 迁移到 MTM；按话题分段；按 heat 淘汰最低段；heat 超阈值提升到 LPM；检索后更新访问计数与 recency；LPM 的 User KB/Agent Traits 用 100 条 FIFO。没有 TTL，时间衰减承担“软过期”。 |
| Flink 映射 | `userId` 作 key，用三个并行的 `MapState`（STM/MTM/LPM）或一个复合 `ValueState` 保存层级；`ValueState` 存 heat 分量与 `lastAccess`；`TimerService` 做 recency 衰减和 FIFO 推进；`checkpoint` 保存层级；`compaction` 合并段/页；语义检索放外部向量库，Flink 只存元数据与热度。 |
| 可写缺口 | 容量（STM 7、MTM 2000、LPM 100）是经验值，没有按字节成本或质量约束求解；话题分段依赖 LLM，缺少动态合并；没有 KV 级成本，也没有“复用风险”。可写“语义记忆 + KV 缓存”的统一价值模型，把 heat 扩展为“收益/字节/风险”。 |

## F 局限与边界

论文第 6 节明确两个限制。第一，STM 窗口、MTM 段数等容量是经验设定，没有认知模型或理论依据；未来要用人类记忆机制推导更原则化的配置。第二，话题分段依赖 LLM 的抽取能力，缺少动态合并机制；重叠或演化的话题会产生冗余，未来要做自适应合并。

实验在 8×H20 上进行，模型是 GPT-4o-mini 与 Qwen2.5-3B/7B；GVD 用 DeepSeek-R1 自动评分，LoCoMo 用 F1/BLEU-1。没有报告端到端延迟、吞吐、GPU 显存或成本。

记忆对象是文本/摘要/画像，不是 KV 张量；它优化的是“上下文里放什么”，不是“GPU 里缓存什么”。对第一章而言，它适合做 `ctx` 的语义层，但不能直接回答 KV 的存储/加载成本。

实验规模是 GVD 的 15 个虚拟用户、LoCoMo 的平均 300 轮；真实多租户、跨设备、隐私约束没有覆盖。

论文未给出 arXiv 编号；代码已开源。

## G 引用信息

Kang, Jiazheng, Mingming Ji, Zhe Zhao, and Ting Bai. “Memory OS of AI Agent.” In *Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing (EMNLP 2025)*, 25961–25970. 2025.

```bibtex
@inproceedings{kang2025memoryos,
  title     = {Memory OS of AI Agent},
  author    = {Kang, Jiazheng and Ji, Mingming and Zhao, Zhe and Bai, Ting},
  booktitle = {Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing (EMNLP 2025)},
  pages     = {25961--25970},
  year      = {2025}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 3–6 页方法；第 6–8 页实验；第 8 页限制与结论。
