---
template: doc
theme: auto
lang: zh
title: CachedAttention：会话级 KV 缓存的分层复用
subtitle: USENIX ATC 2024 · ctx
source: USENIX ATC '24, pp. 111–126；arXiv:2403.19708v3 [cs.CL], 2024-06-30
outline: right
---

多轮对话里历史 token 的 KV 被反复重算，CachedAttention 把整个会话的 KV 存进 HBM/DRAM/SSD 分层缓存，再用调度器提示做预取和淘汰，并用位置编码解耦避免截断导致缓存失效。对第一章最有用的是它给出了“会话级缓存对象 + 分层生命周期”的完整系统样本。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Cost-Efficient Large Language Model Serving for Multi-turn Conversations with CachedAttention |
| 作者 | Bin Gao, Zhuomin He, Puru Sharma, Qingxuan Kang, Djordje Jevdjic, Junbo Deng, Xingkun Yang, Zhou Yu, Pengfei Zuo |
| 机构 | National University of Singapore；Shanghai Jiaotong University；Huawei Cloud |
| 发表 | 2024 USENIX Annual Technical Conference（USENIX ATC '24），pp. 111–126 |
| 正式版本 | USENIX ATC '24  proceedings 版；本地 PDF 为 arXiv v3 |
| arXiv / DOI | arXiv:2403.19708v3 [cs.CL]，2024-06-30；DOI 论文未给出 |
| 本地原文 | `paper_source/CachedAttention_ATC2024.pdf` |
| 代码/数据 | 未发现代码链接；实验使用 ShareGPT 公开数据 |
| 版本边界 | 正式版与 arXiv v3 的题名一致；本地 PDF 为 arXiv v3，正式版页码据 ATC '24  proceedings |

## B 问题与动机

多轮会话是 LLM 的常见负载。论文统计 ShareGPT 的 9 万多条会话，73% 是多轮，30% 的会话超过 4K token。

现有服务引擎在会话空闲后丢弃 KV，下一次用户发言时重算全部历史。论文测算，新会话轮次中历史 token 占比可超过 99%，重复预填充时间占预填充时间的 99%。

KV 体积是根本约束。GPT-3 每个 token 产生 4.5MB KV；LLaMA-65B 每个 token 需要 2.5MB。2K token 的会话产生约 5GB KV。4 张 A100 80GB 上，模型占 130GB，剩余 190GB 空闲 HBM 会在 14 秒内被 KV 填满；改放 512GB 主机内存，也会在 1 分钟内填满。

把 KV 放到更慢的介质会引入访问开销。论文实测，LLaMA-65B 预填充 2K token 约 360ms；把 2K token 的 5GB KV 从主机内存加载到 GPU 约 192ms，PCIe Gen4 的有效带宽约 26GB/s；磁盘带宽低于 5GB/s。

还有一个容易忽略的失效条件：上下文窗口溢出后的截断会改变 token 位置，使已保存的 KV 全部失效。ShareGPT 中 47% 的会话超过 2K token，30% 超过 4K token；用 LLaMA-2 的 4K 窗口时，30% 的会话会触发溢出。

## C 方法机制

**会话是缓存对象。** 一个会话的所有 KV 作为一个整体保存到 AttentionStore，也作为一个整体取回。论文明确把“一个 item”定义为“一个会话关联的全部 KV”，因为同一会话的 KV “要么全用、要么全不用”。这决定了淘汰和预取的最小粒度。

**分层存储。** AttentionStore 使用主机 DRAM 和 SSD 扩展容量。DRAM 是数十 GB/s，SSD 是数 GB/s；论文把大多数 KV 放在 SSD，靠调度把即将访问的会话提前搬到 DRAM。

**层内预取。** 加载 KV 时按 Transformer 层流水：GPU 计算第 l 层时，读流加载第 l+1 层。论文还预留 HBM 读缓冲区，使预取不必等待上一个 job 释放执行缓冲区。若单层加载时间大于单层计算时间，就用更大的缓冲区覆盖缺口。缓冲区大小的形式化条件为 `S_buf = B(T_load·L_hist − T_pref·L_new)`。

**异步保存。** 预填充阶段产生的 KV 量大，论文按层写回，并与后续解码重叠；解码阶段逐 token 产生 KV，也按层写回。若解码结束时还没写完，就暂存到 HBM 写缓冲区，避免阻塞下一个 job。

**调度器感知的预取与淘汰。** 作业调度器维护 job queue，因而知道等待作业的顺序。预取窗口长度为 `L_pw = C_mem / S_kv`，即主机内存能容纳的会话数；淘汰窗口长度为 `(C_mem + C_disk) / S_kv`。淘汰时从窗口尾部向前扫描，优先淘汰离当前较远的会话；若待淘汰项仍在窗口内，则豁免。论文把这种策略与 LRU/FIFO 对比，强调它利用了“未来访问信息”。

**位置编码解耦。** 保存 KV 时不嵌入位置编码，加载时再按新位置重新嵌入。这样截断可以直接作用于 KV，而不必重算。该方法要求模型使用相对位置编码（RPE），LLaMA、T5、Falcon、Mistral、Mixtral 都属于这一类；绝对位置编码（APE）模型不在覆盖范围内。论文还允许按 token 丢弃列表（TDL）选择性保留重要 token 的 KV。

**TTL 的位置。** 论文在容量实验中提到每个会话的 KV 有 TTL，表示“最后一次访问后的最大保存时间”，实验把 TTL 设为 1 小时。这不是完整的 TTL 策略，只是容量估算的一个参数。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 端到端 | 4×A100 80GB、128GB DRAM、10TB SSD；ShareGPT 9K 会话，平均 5.75 轮，约 52K 轮；前 10K 轮预热，后 42K 轮评测 | 命中率 86%、71%、89%、90%（LLaMA-13B/65B/70B、Falcon-40B）；TTFT 降低 85%、61%、87%、86%；预填充吞吐提升 6.8×、2.6×、7.8×、7.2×；GPU 时间加速 4.0×、1.9×、3.3×、3.4×；成本降低 70%、43%、66%、68% | 命中率与模型 KV 体积强相关；LLaMA-65B 的 2.5MB/token 使其命中率最低 |
| 层内预取 | LLaMA-13B、单 GPU、batch=16；历史 1K token、新输入 100 token | 无预取（NO-PL）为基线；无读缓冲（PL-B0）降低预填充时间 35%；15 层读缓冲（PL-B15）降低 61% | 预取把加载藏到计算后面；缓冲区越大，越能覆盖“加载慢于计算”的区间 |
| 异步保存 | LLaMA-13B、单 GPU、batch=16；prompt 1K–1.6K、解码 20 步 | 端到端执行时间降低 13%–15% | 写回不再位于关键路径 |
| 淘汰策略 | 128GB DRAM + 2TB/5TB/10TB SSD；对比 LRU/FIFO | 128G/2T 时命中率比 LRU 高 27%、比 FIFO 高 31%；128G/10T 时 CA 86%，LRU 58%，FIFO 48%；GPU 时间最多加速 2.7×；CA 超过 99.6% 的命中发生在 DRAM | 收益来自“预取到 DRAM”，而不是单纯扩大 SSD |
| 截断 | 对比 OF（位置编码嵌入 KV，溢出即重算）与 CA | 命中率分别下降 17.6%、41.5%、18.1%、18.4%（四模型，OF 相对 CA）；CA 的 PPL 与 token 截断（TT）差距小于 0.02；朴素 KV 截断（NKVT）的 PPL 升到 10³ 量级 | 位置编码解耦把“溢出即失效”变成“截断后仍可复用” |
| 容量 | 改变 `RCC/CCpUT`；TTL=1 小时 | 比值 0.1 时命中率 51%；0.25 时 98% | 不需要按峰值会话数配置满容量；热点集中度高 |
| 存储介质 | HBM-only、HBM+DRAM、CA（HBM+DRAM+SSD） | HBM-only 命中率接近 0%；HBM+DRAM 为 3.4%、1.7%、7.7%、19.1%；CA 为 86%、71%、89%、90% | 仅靠 HBM 或 HBM+DRAM 无法承载多轮会话的 KV 总量 |

## E 对第一章的用法

下表把论文事实映射到第一章；其中 Flink 映射与可写缺口是我们的推断。

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | 以会话为最小粒度的 KV 缓存，对应第一章 `ctx` 的物理层。对象是“整个 session 的 KV”，不是单条消息或单个块；这提供了一个“粗粒度对象”的对照基线。 |
| 价值建模 | 论文没有显式价值公式，但给出了可计算的量：收益≈被避免的历史 token 预填充时间；成本≈KV 加载时间 + 分层存储成本；未来复用概率≈调度器队列中的 look-ahead 命中。可写成 `value(session) ≈ saved_prefill − load_time − storage_cost`，再用队列位置修正。 |
| 生命周期 | 覆盖写入（会话空闲时异步保存）、分层保留（DRAM/SSD）、预取（调度器 look-ahead）、淘汰（窗口尾部优先、整会话原子）、失效/刷新（位置编码解耦后截断）。TTL 只出现在容量实验，未形成完整策略。 |
| Flink 映射 | `sessionId` 作 key，`MapState<sessionId, SessionMeta>` 存块地址、所在层、最近访问、TTL；`ValueState<Long>` 存过期时间；`TimerService` 按 job queue 的 look-ahead 窗口触发预取；`checkpoint` 保存目录；KV 张量放外部存储，Flink 只做元数据与决策；`compaction` 可合并同一会话的版本。 |
| 可写缺口 | 会话原子淘汰无法表达“同一会话内不同片段价值不同”；价值模型缺未来复用概率、质量风险和验证成本；Flink State TTL 是固定值且按 key 最近访问刷新，不能直接实现论文的会话级 TTL 与窗口淘汰。可写“分块价值 + 动态 TTL + 全局调度提示”的增量。 |

## F 局限与边界

论文没有单独的 Limitations 小节。实验集中在 4×A100 80GB、128GB DRAM、10TB SSD 的单机环境，负载是 ShareGPT 加 Poisson 到达（λ=1.0），没有覆盖多租户隔离、跨节点共享和真实生产 trace。

缓存对象是精确 KV，命中即复用，不改变生成结果；论文没有评估语义近似复用，也没有“复用风险/质量约束”这一维。

位置编码解耦依赖 RPE。对使用 APE 的模型，截断后仍需重算，论文的失效修复不适用。

TTL 只在 4.3.6 节的容量实验中出现，设为 1 小时；论文没有给出 TTL 的在线选择方法，也没有把 TTL 与调度器窗口结合成统一策略。

成本按 AWS 按需价格计算（A100 5 美元/小时、DRAM 0.0088 美元/小时/GB、SSD 0.000082 美元/小时/GB），未覆盖预留实例、电价波动和跨区网络成本。

## G 引用信息

Gao, Bin, Zhuomin He, Puru Sharma, Qingxuan Kang, Djordje Jevdjic, Junbo Deng, Xingkun Yang, Zhou Yu, and Pengfei Zuo. “Cost-Efficient Large Language Model Serving for Multi-turn Conversations with CachedAttention.” In *2024 USENIX Annual Technical Conference (USENIX ATC 24)*, 111–126. 2024. arXiv:2403.19708v3.

```bibtex
@inproceedings{gao2024cachedattention,
  title     = {Cost-Efficient Large Language Model Serving for Multi-turn Conversations with CachedAttention},
  author    = {Gao, Bin and He, Zhuomin and Sharma, Puru and Kang, Qingxuan and Jevdjic, Djordje and Deng, Junbo and Yang, Xingkun and Yu, Zhou and Zuo, Pengfei},
  booktitle = {2024 USENIX Annual Technical Conference (USENIX ATC 24)},
  pages     = {111--126},
  year      = {2024},
  note      = {arXiv:2403.19708v3}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 1–4 节问题与设计；第 4 节实验；第 6 节结论。正式版页码据 USENIX ATC '24  proceedings 与后续论文引用（KVFlow 参考文献第 16 条）。
