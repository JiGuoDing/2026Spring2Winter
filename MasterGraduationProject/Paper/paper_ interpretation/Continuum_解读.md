---
template: doc
theme: auto
lang: zh
title: Continuum：用 TTL 给工具调用间隙定价
subtitle: arXiv 2025 · ctx
source: arXiv:2511.02230v7 [cs.OS], 2026-09-08；论文标注 PVLDB 20(1), 2027
outline: right
---

Agent 在两次 LLM 调用之间插入工具调用，现有引擎按“请求结束”立即淘汰 KV，导致下一次调用重算或排队。Continuum 给 KV 加一个按“重载成本 + 每轮排队延迟”算出的 TTL，在工具调用期间把缓存钉在 GPU 上，到期自动释放。对第一章最有用的是，它把 TTL 从固定常量变成了一个可优化的变量。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live（正文标题栏拼作 “Continnum”） |
| 作者 | Hanchen Li, Runyuan He, Qiuyang Mang, Qizheng Zhang, Huanzhi Mao, Xiaokun Chen, Hangrui Zhou, Huanchen Zhang, Alvin Cheung, Joseph Gonzalez, Ion Stoica |
| 机构 | UC Berkeley；Stanford University；Tsinghua University |
| 发表 | arXiv 2025；论文标注 PVLDB 20(1): XXX–XXX, 2027 |
| 正式版本 | arXiv v7，2026-09-08；PVLDB 卷期已标注，页码与 DOI 为占位符 |
| arXiv / DOI | arXiv:2511.02230v7 [cs.OS]；DOI 论文写作 `XX.XX/XXX.XX`，未给出 |
| 本地原文 | `paper_source/Continuum_arXiv2511.02230.pdf` |
| 代码/数据 | https://github.com/Hanchenli/vllm-continuum；SWE-Bench、BFCL V4、OpenHands 轨迹 |
| 版本边界 | 正文标题与正文均拼作 “Continnum”；任务说明确认正式名为 “Continuum”。本稿按正式名引用，正文事实取自 v7 |

## B 问题与动机

现有推理引擎把“解码结束”当作请求结束，立即释放 KV，把 GPU 让给排队的请求。这个策略适合多轮聊天，却不适合 Agent：Agent 在推理步骤之间插入工具调用，工具返回后会用同一段上下文继续推理。

工具调用通常比人类打字快。论文统计，SWE-Bench 的平均轮数为 10.9，工具时间均值 925ms；BFCL v4 平均 6.3 轮，工具时间均值 1,923ms。很多工具调用在 2 秒内返回，下一次请求很快就会到。

如果 KV 在工具调用期间被淘汰，回来时要么重算 prefill，要么从 CPU 重新加载；更严重的是“每轮排队延迟”：即使能立刻从 CPU 加载，请求仍要排在别的请求后面等 GPU 内存释放。这个延迟每轮都会出现，随轮数累积。

工具调用时长分布很不均匀。论文统计，最慢的 10% `fetch_url` 占该工具总延迟的 52.5%；最慢的 10% `cd` 占 94.1%。固定“保留到下一次请求”的策略，遇到长工具调用会长期占用 GPU，甚至死锁。

已有工作不够。InferCept 只按重载成本决定 preserve，不建模每轮排队延迟；Autellix 用 end-of-turn eviction；Pie 暴露接口但不提供保留策略；Ayo、Alto、Parrot 假设静态工作流，不适用于动态 Agent。

## C 方法机制

**TTL 钉住。** 当一个请求结束、并且后面跟着工具调用时，Continuum 不立即释放 KV，而是给它一个 TTL，在 TTL 内把 KV 保留在 GPU。下一次请求在 TTL 内到达，就直接复用；TTL 到期，自动释放。

**成本。** 钉住 KV 的机会成本是它占用的 GPU 内存本可以服务其他请求：

`Cost(τ, r) = MemUsage(r) / M × τ`

`MemUsage(r)` 是请求 `r` 的 KV 占用，`M` 是已见请求的平均内存占用，`τ` 是 TTL。比值表示“钉住 r 会挡住多少个平均请求”。

**收益。** 收益由两部分组成：

`Benefit(r) = CacheMissCost(r) + OutOfOrderCost(r)`

`CacheMissCost(r) = MemUsage(r) × Prefill-Reload(r) / M`，即避免的重算/加载时间按内存比例放大到被挡住的请求数。

`OutOfOrderCost(r) = T/M × MemUsage(r) × η`，其中 `T` 是历史平均排队延迟，`η` 是负载的“记忆度”因子：程序越接近完成、剩余步数越少，`η` 越接近 1；完全无记忆的负载 `η=0`。这一项是 InferCept 缺失的关键：即使 CPU 加载很快，排队延迟仍然存在。

**TTL 选择。** 给定工具 `f` 的时长分布，选择

`τ* = argmax_τ P(τ, f) × Benefit(r) − Cost(τ, r)`

其中 `P(τ,f)` 是工具在 `τ` 内完成的概率。消去公共的 `MemUsage/M` 后，等价于

`argmax_τ P(τ,f) × (T·η + Prefill-Reload(r)) − τ`

论文用历史工具调用记录的经验 CDF 估计 `P`，枚举记录中出现过的时长（包括 0），取期望收益最大的值。

**冷启动。** 历史记录少于阈值（论文取 100）时，先用全局工具统计；连全局统计也不足时，用固定默认 TTL。默认值由“工具时长服从 Exp(1)、负载完全记忆化（η=1）”的假设推出。

**调度优先级。** 请求按多键排序：被抢占的请求优先；TTL 内保留的请求优先于未钉住的请求；同类内按程序级到达时间（program-level FCFS）排序。这样既保护多轮连续性，又避免后来的单请求插队。

**实现。** 在 vLLM 上约 1k 行 Python。客户端给每个请求带 `program_id`；Tool-Call Handler 在请求进入/离开时识别工具、记录开始/结束时间、计算 TTL；调度器在 TTL 到期且程序不在等待队列时释放 KV。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 端到端 | Llama-3.1-8B/70B、Gemma-3-12B；A100/H100/B200；SWE-Bench、BFCL v4、OpenHands | 平均任务完成时间降低 1.12×–3.66×，吞吐提升 1.10×–3.22×；摘要给“超过 8×”的总体改进 | 多轮 Agent 的收益随轮数累积；TTL 减少了每轮重算和排队 |
| 生产 SWE-Agent | Company A 内部 H100 集群；500 个 SWE-Bench-Verified 任务；Poisson 分发 | 平均延迟最多降低 8.18×；通过率不低于基线（基线超 15 分钟会被判失败） | 真实分布式环境下，减少排队还能避免超时失败 |
| 消融 | Program FCFS、Static TTL、完整 Continuum | 逐项加入后性能逐步提升 | 程序级排序与动态 TTL 都有独立贡献 |
| 轮数扩展 | SWE-Bench trace 重复 1×–5×，反比缩放 token 长度 | 轮数越多，基线退化越明显；Continuum 延迟保持稳定；5× 时提升 3.7× | 每轮排队延迟会累积，固定策略随轮数恶化 |
| 批/块配置 | max batch 16–256；chunk 256–4096 | 各配置下都保持 1.3×–2.0× 提升 | 不依赖特定引擎参数 |
| 调度开销 | 无 CPU offload / 有 CPU offload | vLLM 0.95/2.33ms，Continuum 0.96/2.30ms | 开销在毫秒级，相对 GPU 执行可忽略 |
| OpenHands | Llama-8B，单张 H100；与 SGLang、Dynamo 对比 | 平均与 P95 延迟更优；吞吐 144.9 steps/min，对比 ThunderAgent 114.8、vLLM 93.4 | 真实 Agent rollout 也成立 |

## E 对第一章的用法

下表把论文事实映射到第一章；其中 Flink 映射与可写缺口是我们的推断。

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `ctx`。对象是“一次请求/一个程序在工具调用期间需要保留的 KV”，键是 `program_id`；它不是整个会话，而是会话中跨工具间隙的那一段。 |
| 价值建模 | 这是本批论文里最完整的 TTL 价值模型：`Benefit = 重载成本 + 排队延迟`，`Cost = 内存占用 × 时间`，`τ* = argmax P(τ,f)·Benefit − Cost`。`η` 把“程序越接近完成越值得保留”写成了一个可估参数。 |
| 生命周期 | 写入：请求结束时若后面有工具调用，则 pin；保留：TTL 内留在 GPU；驱逐：TTL 到期自动释放；没有预取；调度上用 program-level FCFS 保护连续性。 |
| Flink 映射 | `MapState<programId, ProgramMeta>` 存 TTL、pin 状态、下一个工具名；`ValueState` 存该工具的历史时长分布；`TimerService` 在 TTL 到期时触发释放；`BroadcastState` 可放全局工具统计。注意 Flink 的 `State TTL` 是 StateDescriptor 级固定值，不能按 entry 动态设 TTL，需自定义 timer + 优先队列。 |
| 可写缺口 | TTL 只针对 ReAct 式“推理→工具→推理”的线性节奏；非线性的分支、异步多 Agent、上下文折叠没有覆盖。`M` 用平均内存、`η` 用相关性近似，缺少对工具时长分布漂移的在线更新。可写“动态 per-entry TTL + 不确定性感知 + Flink timer 实现”的增量。 |

## F 局限与边界

论文第 7 节说明：当前设计针对 ReAct 式、工具交错的 Agent，每个 LLM 步骤返回明确的工具调用，然后有一个间隙。并行工具调用仍可按“推理→工具→推理”的节奏处理；但推测分支、异步多 Agent 协调、上下文折叠等非线性控制流可能违反这个节奏，论文留作未来工作。

TTL 模型使用平均内存 `M` 和历史排队时间 `T`；负载突变时，这两个量会滞后。工具时长用经验 CDF，假设历史分布对未来有代表性；冷启动阶段用默认 TTL，可能不是最优。

实验覆盖 Llama-3.1-8B/70B、Gemma-3-12B 和 A100/H100/B200，但主要是单机/单集群；跨地域、跨租户的公平性没有展开。

论文标注 PVLDB 20(1), 2027，但页码与 DOI 仍是占位符；本稿数字全部来自 arXiv v7（2026-09-08），正式版可能变化。

标题拼写不一致（Continnum/Continuum）是排版问题，不影响技术内容，但引用时需统一。

## G 引用信息

Li, Hanchen, Runyuan He, Qiuyang Mang, Qizheng Zhang, Huanzhi Mao, Xiaokun Chen, Hangrui Zhou, Huanchen Zhang, Alvin Cheung, Joseph Gonzalez, and Ion Stoica. “Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live.” arXiv:2511.02230v7, 2026. Forthcoming in *PVLDB* 20, no. 1 (2027).

```bibtex
@article{li2026continuum,
  title   = {Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live},
  author  = {Li, Hanchen and He, Runyuan and Mang, Qiuyang and Zhang, Qizheng and Mao, Huanzhi and Chen, Xiaokun and Zhou, Hangrui and Zhang, Huanchen and Cheung, Alvin and Gonzalez, Joseph and Stoica, Ion},
  journal = {Proceedings of the VLDB Endowment},
  volume  = {20},
  number  = {1},
  year    = {2027},
  note    = {arXiv:2511.02230v7; pages and DOI pending}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 4–6 页动机；第 5–8 页 TTL 模型；第 8–12 页实现与实验；第 12 页结论与数据可用性。
