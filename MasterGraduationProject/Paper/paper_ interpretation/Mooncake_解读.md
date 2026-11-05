---
template: doc
theme: auto
lang: zh
title: Mooncake：以全局 KVCache 池换取更少计算
subtitle: FAST 2025 · ctx
source: FAST '25, pp. 155–170；ISBN 978-1-939133-45-8；Best Paper
outline: right
---

Kimi 的长上下文请求把 KV 缓存变成跨节点复用的全局资源；Mooncake 把 CPU、DRAM、SSD 和 RDMA 汇成分布式 KVCache 池，由 Conductor 按前缀命中长度、传输时间和排队时间做调度。对第一章最有用的是，它把“缓存价值”直接变成了“路由信号”。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Mooncake: Trading More Storage for Less Computation — A KVCache-centric Architecture for Serving LLM Chatbot |
| 作者 | Ruoyu Qin, Zheming Li, Weiran He, Jialei Cui, Feng Ren, Mingxing Zhang, Yongwei Wu, Weimin Zheng, Xinran Xu |
| 机构 | Moonshot AI；Tsinghua University |
| 发表 | 23rd USENIX Conference on File and Storage Technologies（FAST '25），2025-02-25 至 02-27，Santa Clara；pp. 155–170；Best Paper |
| 正式版本 | FAST '25  proceedings 版，16 页；本地 PDF 为同一正式版 |
| arXiv / DOI | 论文未给出 arXiv 编号；DOI 论文未给出；ISBN 978-1-939133-45-8 |
| 本地原文 | `paper_source/Mooncake_FAST2025.pdf` |
| 代码/数据 | https://github.com/kvcache-ai/Mooncake；论文称开放 trace 与 KVCache 传输基础设施 |
| 版本边界 | 实验用模拟 LLaMA3-70B 架构的 dummy model 与 Kimi 真实 trace 回放；生产统计与回放实验分开报告 |

## B 问题与动机

Kimi 是面向公众的 LLM 聊天服务，负载在输入/输出长度、到达分布和 SLO 上高度多样。作为 MaaS 提供方，目标是在满足 TTFT 与 TBT 约束的前提下最大化有效吞吐。

GPU 服务器通常是高度集成的节点，但 CPU、DRAM、SSD 和 NIC 的利用率并不均衡。论文主张把这些资源解耦成独立资源池：prefill 池、decoding 池，以及一个分布式 KVCache 池。

只把 KV 缓存在本地 HBM/DRAM 不够。论文测算，本地 DRAM 最多只能支撑理论命中率的 50%；长上下文场景下，KV 需要跨节点共享。

论文给出一个带宽判据：当前缀长度为 `p`、模型维度为 `d`、GQA 比为 `gqa` 时，复用 KV 比重新计算更有利于 TTFT 的条件是

`B/G > 2ds / (gqa × (a·p·d + b·d²))`

其中 `B` 是 KV 加载带宽，`G` 是 GPU 计算吞吐。以 LLaMA3-70B、8×A800、前缀 8192 token 为例，最低 `B` 约为 6GB/s；8×H800 约为 19GB/s。论文认为 100Gbps NIC 足以满足。

## C 方法机制

**总体架构。** Conductor 是全局调度器；prefill 实例和 decoding 实例分开部署；MooncakeStore 把每个节点的 CPU、DRAM、SSD 和 RDMA 资源组织成分布式 KVCache 池。

**请求四步。** 第一，选中的 prefill 节点按前缀块键从远端 CPU 内存加载可复用 KV。第二，做增量 prefill，把新生成的 KV 写回本地 CPU 内存；未缓存 token 超过阈值（通常大于 1000）时，切成 chunk 流水执行。第三，按层把 KV 异步流式传到 decoding 节点的 CPU 内存。第四，decoding 节点把请求加入连续批处理。

**KVCache 存储。** KV 以 paged block 存储，块大小为 16–512 token，实验取 256。每个块带一个哈希键，键由“自身哈希 + 前缀哈希”决定，用于去重。同一个键可以在多个节点有副本，副本数量由缓存负载均衡策略控制。池满时按 LRU 淘汰，但正在被请求访问的块不淘汰。

**调度。** 对每个新请求，Conductor 把请求的块键与每个 prefill 实例的缓存键逐一比较，得到前缀匹配长度 `prefix_len`。它用离线拟合的多项式回归估计 prefill 执行时间，再加上排队时间，得到该实例上的 TTFT；选择 TTFT 最短的实例。若 TTFT 或 TBT 超过 SLO，直接返回 HTTP 429。

**缓存负载均衡。** 请求不一定总被送到前缀最长的实例，因为该实例可能过载。若“换一个实例多做一点 prefill”的时间小于“从远端搬 KV”的时间，Conductor 会把请求转到替代实例，由它主动拉取 KV 并本地保存。这个阈值目前手工调整，论文说未来可以自适应。

**热点复制。** 系统不预测未来访问，而是用启发式迁移：被频繁访问的块在多个实例上保留副本，冷块换出。这样既降低热点访问延迟，也把热点前缀自动扩散到更多 prefill 节点。

**长上下文 prefill。** 论文用 chunked pipeline parallelism（CPP）把一条长请求的多个 chunk 分到多个节点流水处理。与序列并行相比，CPP 只在流水段边界通信，减少跨节点 all-reduce 和网络争用。

**传输引擎。** 支持多 RDMA NIC、拓扑感知路径选择、零拷贝和故障切换；按内存地址选择 preferred/secondary NIC，避免 UPI/PCIe 瓶颈。实验使用 4×200Gbps 或 8×400Gbps 网络。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 有效请求容量 | 16 个 8×A800 节点；Kimi 对话 trace；TBT 100/200/300ms | 相比基线提升 59%–498% | 长上下文越重，全局池的相对收益越大 |
| 工具/Agent 负载 | 同上；前缀缓存比例 59% | 200ms 阈值下比 vLLM 前缀缓存高 42% | 高前缀复用负载适合全局池；vLLM 的 chunked prefill 反而干扰解码 |
| 合成负载 | 平均输入 15,325 token，缓存比例 66% | 200ms 阈值下比 vLLM 高 40% | 热点分散时，本地缓存不够，需要全局容量 |
| Prefill GPU 时间 | 三种负载 | 比 vLLM 降低 36%、53%、64%；vLLM 前缀缓存是 Mooncake 的 1.43×、1.40×、2.59×；chunked prefill 是 1.90×、2.68×、3.33× | 全局命中直接转化为 GPU 时间，而不只是 TTFT |
| 全局 vs 本地缓存 | 10 个 prefill 节点；每节点 3M token 容量；输出限制为 1 token | 全局缓存命中率最高提升 136%，prefill 计算时间最多降低 48% | 容量不是唯一变量，跨节点可访问性才是 |
| 调度 | 16 个 8×A800 节点；真实对话 trace | 全局缓存感知 3.07s，本地缓存感知 3.58s，负载均衡 5.27s，随机 19.65s；全局缓存负载均衡再降 14% | 缓存命中与负载均衡需要一起优化 |
| 容量需求 | LLaMA3-70B；每 token 320KB | 3M token 本地容量在多数场景达不到理论最大命中率的 50%；50M token 接近 100%，至少需要 20 个节点的 DRAM | 全局池的容量门槛很高，适合大规模部署 |
| 传输 | 40GB 数据，对应 LLaMA3-70B 128k token | 4×200Gbps 下 87GB/s，8×400Gbps 下 190GB/s；比 TCP 快 2.4×/4.6×，比 Gloo 快 7.5×/16.2× | 传输引擎是全局池成立的前提 |
| 128k 前缀 | prefix cache 比例 0% vs 95% | 前缀缓存降低 prefill 时间 92%，降低 TTFT 86% | 长上下文下，缓存收益远大于调度开销 |

## E 对第一章的用法

下表把论文事实映射到第一章；其中 Flink 映射与可写缺口是我们的推断。

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `ctx`，兼及 `rag`/工具结果的前缀。对象是“全局可寻址的 KV block”，块大小 16–512 token，键含前缀哈希；同一键可多副本。 |
| 价值建模 | 论文没有逐块价值公式，但给出了可计算的收益链：前缀匹配长度→节省的 FLOPs→TTFT 改善；带宽判据决定“搬 KV 还是重算”；调度器用 `estimated TTFT = transfer + queue + prefill` 选实例。热点复制用访问频率做代理。 |
| 生命周期 | 写入增量 KV 到本地 CPU；按前缀哈希去重；热块复制到多节点；池满按 LRU 淘汰（访问中的块除外）；冷块换出；按层异步传输；没有 TTL。 |
| Flink 映射 | `MapState<blockHash, BlockMeta>` 存副本位置、最后访问、pin 状态；`BroadcastState` 广播 prefill 队列与 SLO 阈值；`TimerService` 触发热点迁移和预取；`checkpoint` 保存全局目录；按 `blockHash` 分区，KV 本体放外部池。 |
| 可写缺口 | LRU + 频率复制是启发式，没有把“块价值 = 前缀长度 × 单位 token 节省 − 传输/存储成本 − SLO 风险”写进准入与复制决策；也没有 TTL 和租户公平性。可写“价值感知的全局准入/复制 + 软 TTL”的增量。 |

## F 局限与边界

论文有强烈的生产背景，但可复现实验使用模拟 LLaMA3-70B 的 dummy model 和回放 trace；真实 Kimi 的模型结构、流量和故障模式没有完全公开。

实验集群是 16 个 8×A800 节点，网络为 4×200Gbps RDMA；结论依赖高带宽网络。论文建议最低 100Gbps，低于该值时 TTFT 会明显恶化。

P/D 比例固定，只在负载显著波动时切换节点角色；没有给出自动弹性伸缩策略。

淘汰是 LRU，热点复制是启发式；两者都没有显式价值模型，也没有 TTL。缓存池要接近理论最大命中率需要约 50M token 容量、至少 20 个节点的 DRAM，小规模部署不一定划算。

调度阈值 `kvcache_balancing_threshold` 目前手工调整；论文把自适应调整留给未来工作。

论文没有单独讨论多租户隔离、缓存隐私和跨用户前缀共享的安全风险。

## G 引用信息

Qin, Ruoyu, Zheming Li, Weiran He, Jialei Cui, Feng Ren, Mingxing Zhang, Yongwei Wu, Weimin Zheng, and Xinran Xu. “Mooncake: Trading More Storage for Less Computation — A KVCache-centric Architecture for Serving LLM Chatbot.” In *Proceedings of the 23rd USENIX Conference on File and Storage Technologies (FAST '25)*, 155–170. 2025.

```bibtex
@inproceedings{qin2025mooncake,
  title     = {Mooncake: Trading More Storage for Less Computation --- A KVCache-centric Architecture for Serving LLM Chatbot},
  author    = {Qin, Ruoyu and Li, Zheming and He, Weiran and Cui, Jialei and Ren, Feng and Zhang, Mingxing and Wu, Yongwei and Zheng, Weimin and Xu, Xinran},
  booktitle = {Proceedings of the 23rd USENIX Conference on File and Storage Technologies (FAST '25)},
  pages     = {155--170},
  year      = {2025},
  isbn      = {978-1-939133-45-8}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 2–7 页设计与调度；第 8–14 页实验；第 14 页结论。
