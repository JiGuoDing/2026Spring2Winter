---
template: doc
theme: auto
lang: zh
title: FinCacheServe：依赖一致的答案复用
subtitle: arXiv 2026 · resp
outline: right
source: arXiv:2607.26076v1
---

FinCacheServe 把生成答案当作“有依赖的 serving 对象”，只有财务意图、证据指纹、工具输出、模型配置和文档版本全部一致才允许复用。对第一章最有用的，是它给出了一个把“复用收益、存储成本、更新风险”写在同一式子里的价值模型。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | FinCacheServe: Dependency-Consistent Answer Reuse for Cost-Efficient RAG Serving over Mutable Enterprise Documents |
| 作者 | Lingteng Zeng, Yifan Jin |
| 机构 | The Chinese University of Hong Kong（1）；Beijing Institute of Technology（2） |
| 发表 | arXiv 预印本，2026 |
| 正式版本 | 未见会议/期刊正式版；抽取文本为 arXiv v1 |
| arXiv / DOI | arXiv:2607.26076v1 [cs.IR]，14 Jul 2026；DOI 论文未给出 |
| 本地原文 | `paper_source/FinCacheServe_arXiv2607.26076.pdf` |
| 代码/数据 | 论文声明本 arXiv 版不附代码/数据 artifact；源文件为公开 SEC EDGAR 文档 |
| 版本边界 | 所有数字来自 arXiv v1；单机 vLLM 与归档 trace 回放 |

## B 问题与动机

企业 RAG 服务反复执行语义等价的分析请求，但文档会变：财报修订、证据块刷新、比率计算口径变化、模型或解码配置切换。基于文本相似度或固定 TTL 的缓存命中，可能返回过期证据。

现有 KV/前缀缓存优化的是“请求到达模型之后”的执行；答案复用则直接跳过模型调用。两者互补，但答案层需要更强的依赖契约。

金融文档把问题具体化：每个答案绑定公司、期间、 filing 范围、证据集、工具输出和 filing 版本。重复意图很多，但可复用性取决于细粒度依赖是否仍然一致。

论文把答案缓存定义为 serving 对象，而不是一段文本：条目记录归一化请求签名、源文档版本、证据指纹、工具指纹、模型身份、解码配置，以及从文档到答案的反向索引。

## C 方法机制

**请求签名。** 包含公司、报告期、查询族（流动性、收入变化、债务、利润率、风险因子变化、现金流）、文档范围（年报/季报/当前报告/XBRL 事实）、工具需求、模型身份、解码配置。查询族捕获分析意图，期间防止跨季度/跨年复用。

**复用门。** 候选答案要同时通过四组检查：

| 门 | 检查内容 |
|:--|:--|
| 签名门 | 公司、查询族、期间、文档范围、工具需求、模型、解码配置 |
| 证据门 | 检索支撑的指纹是否一致 |
| 版本门 | 条目记录的源文档版本是否等于当前版本库 |
| 工具/模型门 | 工具指纹、模型配置是否一致 |

只有全部通过才命中；否则走检索、工具执行、生成，再提升为新的答案条目。

**依赖失效。** 元数据面维护 document→answer 反向索引。filing 更新时先更新版本库，再通过反向索引使依赖该文档的答案条目失效，之后才允许读路径看到新版本。失效复杂度 O(k)，k 为依赖该文档的答案数。

**准入与驱逐。** 正确性门与缓存管理分离。对条目 c 定义效用：

`U(c) = Ĥ(s(c)) × C(c) − λ_m × M(c) − λ_f × F(c) − λ_u × R(c)`

`Ĥ` 是归一化签名的复用需求估计，`C` 是避免的生成成本，`M` 是条目大小，`F` 是文档扇出，`R` 是依赖文档的更新风险。U>0 才准入；容量满时驱逐 `U/M` 最低的条目。

**离线与在线策略。** 离线 CacheOpt 从回放 trace 估计 `Ĥ、F、R`，作为接近 Belady 的离线上界；在线 CacheOpt 用最近请求与 filing 更新的滑动窗口估计，得到可部署曲线。

**并发。** 元数据面用服务级锁包住版本库更新与答案条目变更；托管 LLM 调用在临界区外执行，保证读与更新有单一线性化顺序。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 7B 全量 trace | 2,230 请求，Qwen2.5-7B，RTX 5090 | 跳过 1,188 次 LLM 调用（53.27%），0 条依赖过期输出 | 答案复用可去掉一半以上模型调用 |
| 7B 复述/更新压力 | 208 请求 | 跳过 52.88%，0 过期；TTL/语义/签名无失效各 46 条过期 | 省调用与保新鲜是两个轴 |
| 32B 强基线 | 544 请求，3 个 seed，Qwen2.5-32B | 53.31%（CI [49.11, 57.46]）；versioned semantic 38.97%、grounded 22.43%、entity-period 10.48%、exact 2.57% | 财务签名 + 失效联合贡献 14.34 个百分点 |
| 容量回放 | 64 条目，5 条归档 trace | LRU 1.01%、LFU 1.45%、CacheOpt 36.66%（距 oracle 0.56 个百分点）、Online 19.44% | 小容量下淘汰策略比命中率更重要 |
| 近似碰撞 | 2,376 个探针 | FinCacheServe 0% 不安全接受；global semantic 100%、versioned 87.18%、entity-period 61.54%、grounded 35.90% | 单字段契约都不够，必须联合 |
| SLO/能耗 | 2s SLO，450 W | 53.31% fresh goodput；2.80 Wh/千次，比 versioned semantic 的 5.03 Wh 低 44.30% | 不安全的高跳过率不是有效收益 |
| 元数据后端 | 100k 条目，fan-out 16 | 内存 lookup p95 2.13 μs、invalidation 27.00 μs；SQLite/WAL 84.42 μs、63.44 ms | 内存路径够快，持久化失效是瓶颈 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `resp`。对象是“最终答案 + 依赖契约”：答案文本、证据指纹、工具指纹、模型/解码配置、源文档版本、反向索引边。它不是普通回答缓存，而是可审计的 serving 对象。 |
| 价值建模 | 本批次中最完整的价值式之一：`U = 需求 × 避免成本 − 存储 − 扇出 − 更新风险`。`Ĥ` 对应未来复用概率，`C` 对应复用收益，`M` 对应存储成本，`F/R` 对应验证/失效成本；质量约束由四道依赖门承担。可直接借到第一章。 |
| 生命周期 | 准入（U>0）、驱逐（最低 U/M）、更新失效（反向索引）、未命中重生成；没有 TTL，也不依赖相似度单独放行。 |
| Flink 映射 | `MapState<signature, AnswerEntry>` 存答案与依赖；`MapState<docId, Set<answerId>>` 做反向索引；`ValueState<version>` 存文档版本；filing 更新走 broadcast/co-process 触发失效；`timer` 做效用衰减；`checkpoint` 保证元数据一致。 |
| 可写缺口 | 分布式多副本失效、跨区域一致性未验证；论文未给出 λ 权重的在线学习机制。可把 λ 做成按 SLO 和负载调整的参数，并把反向索引分片到 Flink keyed state，验证跨节点 exactly-once 失效；这是第一章可写的系统缺口。 |

## F 局限与边界

证据范围是公开 SEC 衍生负载、托管 vLLM、Qwen2.5 模型、单机内存元数据面加 SQLite/WAL 验证。生产流量在查询多样性、更新节奏、访问倾斜、工具组合、SLO 分布上可能不同。

一致性承诺是“相对于已记录依赖的新鲜度”，不是事实正确性。答案本身的财务正确性仍需 source review、answer audit 和领域治理。

能耗是“GPU 秒估计 + 板卡功率假设”，不是整机功率计读数；容量与策略回放基于归档 trace。

元数据压力验证到 100k 条目、64 个查询 worker；分布式缓存、多副本失效、跨区域一致性需要额外工程验证。

论文未给出代码/数据 artifact，也未给出正式版 DOI。

## G 引用信息

Zeng, Lingteng, and Yifan Jin. “FinCacheServe: Dependency-Consistent Answer Reuse for Cost-Efficient RAG Serving over Mutable Enterprise Documents.” arXiv:2607.26076v1, 2026.

```bibtex
@article{zeng2026fincacheserve,
  title   = {FinCacheServe: Dependency-Consistent Answer Reuse for Cost-Efficient RAG Serving over Mutable Enterprise Documents},
  author  = {Zeng, Lingteng and Jin, Yifan},
  journal = {arXiv preprint arXiv:2607.26076},
  year    = {2026},
  note    = {v1, 14 Jul 2026}
}
```

来源页面：arXiv 摘要页 `arXiv:2607.26076`；本地抽取文本第 1–14 页。
