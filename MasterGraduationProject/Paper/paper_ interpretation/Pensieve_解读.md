---
template: doc
theme: auto
lang: zh
title: Pensieve：按块计价的 KV 保留价值
subtitle: EuroSys 2025 · ctx
source: EuroSys '25, pp. 144–158；DOI 10.1145/3689031.3696086；arXiv:2312.05516v3 [cs.LG], 2024-10-07
outline: right
---

多轮会话的历史 KV 在无状态服务里被反复重算；Pensieve 把会话上下文切成 32 token 的块，放进 GPU/CPU 两级缓存，并用 `V = Cost(s,l) / T` 给每个块算保留价值。对第一章最有用的是，它把“重算成本”和“空闲时间”写成了一个可直接实现的驱逐优先级。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Stateful Large Language Model Serving with Pensieve |
| 作者 | Lingfan Yu, Jinkun Lin, Jinyang Li |
| 机构 | New York University |
| 发表 | Twentieth European Conference on Computer Systems（EuroSys '25），2025-03-30 至 04-03，Rotterdam；pp. 144–158 |
| 正式版本 | EuroSys '25，15 页；DOI 10.1145/3689031.3696086 |
| arXiv / DOI | arXiv:2312.05516v3 [cs.LG]，2024-10-07；DOI 10.1145/3689031.3696086 |
| 本地原文 | `paper_source/Pensieve_arXiv2312.05516.pdf` |
| 代码/数据 | 未发现代码仓库；实验使用 ShareGPT 与 UltraChat 两个公开多轮对话数据集 |
| 版本边界 | 本地 PDF 为 arXiv v3；EuroSys 正式版页码 144–158。论文注明早期草稿于 2023-12-09 上传 arXiv |

## B 问题与动机

现有 LLM 服务系统按请求处理，请求之间无状态。多轮对话中，每一轮都要把不断增长的历史拼进 prompt，从零预填充；同一段历史被反复计算。

一种直接办法是把已处理的上下文按 token embedding 保存下来，下一次请求复用并追加。论文认为这个思路可行，因为用户在聊天时，后续请求通常会在较短时间内到达，缓存有机会命中。

难点有三个。第一，放在哪里：GPU 最快但容量小，磁盘加载太慢；GPU+CPU 两级缓存需要处理两层容量限制和换入换出。第二，如何高效复用：缓存可能只覆盖部分上下文，缺失部分要重算。第三，换入换出会让 KV 在 GPU 中不连续，现有注意力内核要求连续内存，或只支持单 token 输入。

论文的观察是：同一会话的历史是连续的，且越靠前的 token 重算越便宜。原因是因果注意力：前部 token 的注意力上下文短，后部 token 要 attend 更长的历史。这个观察直接决定了“从头部驱逐”的策略。

## C 方法机制

**两级缓存。** Pensieve 在 GPU 和 CPU 内存中保存会话的 KV-token。GPU 缓存是主缓存，CPU 缓存是下一层；CPU 也满时，块被丢弃，下次通过重算恢复。论文没有使用磁盘，因为磁盘加载延迟会明显伤害交互体验。

**块级对象。** KV-token 按块管理，块大小可配置，实验取 32 token。驱逐决策以块为单位，而不是整个会话；因此一个会话的上下文可以跨 GPU、CPU 和“已丢弃”三种状态。

**保留价值。** 每个块的保留价值为：

`V = Cost(s, l) / T`

其中 `Cost(s,l)` 是块大小 `s`、上下文长度 `l` 时的重算成本，`T` 是会话最后一次活跃至今的时间。`V` 越小越先被驱逐。这个式子把“重算贵”与“最近活跃”放在同一个尺度上：重算越贵越应保留，空闲越久越应淘汰。

**重算成本估计。** 论文把成本拆成注意力部分和非注意力部分：

`Cost(s,l) = Cost_attention(s,l) + Cost_other(s)`

非注意力部分（线性层、LayerNorm、激活等）与上下文长度无关，可合并为常数 `c`；块大小固定为 32 后，成本简化为 `Cost(l) = Cost_attention(l) + c`。论文离线剖析 2 的幂次上下文长度，再用插值估计其他长度。

**驱逐位置。** 论文同时表达两种偏好：优先淘汰更久未活跃的会话；优先淘汰会话历史前部的块。前者来自 LRU 假设，后者来自“前部重算更便宜”的实测。块级 `V` 把两者合在一起。

**提前换出。** 请求结束后不立即释放 GPU 槽位；当 GPU 空闲槽位低于阈值（例如 25%）时，调度器让 worker 把选中的 KV-token 换到 CPU。GPU 内存是惰性回收：直到这些槽位真的分配给别的会话才释放。

**流水线换入。** 需要换回时，不等待所有层传完再开始执行；按层传输，每层的 KV 到齐后就开始该层的自注意力。论文用 GPU event 保证依赖。

**丢弃后的恢复。** 被 CPU 淘汰的块，从持久化会话历史中取回原始文本 token，拼到新请求的 prompt 前面重算。由于总是从头部淘汰，GPU 一般保存最近 token，CPU 保存中段，最早的部分可能已丢弃。

**非连续注意力内核。** 换入的 KV 与原有 KV 在 GPU 中不连续。Pensieve 扩展 PagedAttention 内核，支持一次输入多个 token，并让 Query 对应非连续的 KV 区域。丢弃头部后，Query 可能对应两段不连续上下文，论文把它们当成两个共享底层上下文的子请求处理。

**调度。** 请求按统一批处理调度；生成阶段 GPU 缓存不足时，按到达时间从晚到早挂起请求，换出 KV 后放回等待队列。为避免频繁挂起，系统保留 10% 的 GPU 缓存槽位给生成中的请求。

**实现。** 原型约 7K 行 C++/CUDA，基于 PyTorch 2.0.0、CUDA 11.8，使用 NVIDIA Cutlass 实现多 token 注意力内核。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 单卡端到端 | Azure NC A100 v4，单张 A100-80GB；OPT-13B、Llama 2-13B；每 GPU 40GB KV；ShareGPT | OPT-13B 在 120ms/token 延迟下吞吐为 vLLM 的 1.36×、TensorRT-LLM 的 1.14×；Llama 2-13B 在 180ms/token 下为 1.70×、1.58× | 有状态缓存对真实多轮数据有效；Llama 2-13B 用了 GQA，KV 更小，收益更大 |
| UltraChat | 同上；UltraChat | OPT-13B 在 120ms/token 下为 vLLM 1.17×、TensorRT-LLM 1.14×；Llama 2-13B 在 100ms/token 下为 1.58×、1.47× | ShareGPT 轮数更多，收益更大；合成数据轮数少，复用机会少 |
| 四卡大模型 | 4×A100-80GB；OPT-66B、Llama 2-70B；ShareGPT | OPT-66B 在 200ms/token 下为 vLLM 2.04×、TensorRT-LLM 1.64×；Llama 2-70B 在 400ms/token 下为 3.0×、2.47× | 模型越大，计算增长快于 KV 增长，缓存收益更明显 |
| 驱逐策略 | OPT-13B；Pensieve 策略 vs LRU；ShareGPT | 3 req/s 以下两者接近，超过后 Pensieve 更好；两者命中率都低于 80%，Pensieve 的 CPU 命中率高最多 4.4 个百分点；平均减少重算 KV-token 最多 14.6% | 收益来自“从头部驱逐 + 按重算成本排序”，不是单纯提高命中率 |
| 用户思考时间 | Llama 2-13B；平均思考时间 30/60/120/300/600 秒 | 思考时间越长，吞吐越低；600 秒时仍优于 vLLM，但差距缩小 | 缓存价值随空闲时间衰减；TTL 式的时间维度不可省略 |
| 仅 GPU 缓存 | Pensieve（GPU cache） vs Pensieve（all） | GPU-only 在低负载下也能降延迟，但高请求率下 GPU 很快耗尽，退化为重算 | CPU 层是容量缓冲，不是可有可无的优化 |

## E 对第一章的用法

下表把论文事实映射到第一章；其中 Flink 映射与可写缺口是我们的推断。

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `ctx`。对象是“会话上下文按 32 token 切分后的 KV 块”，可跨 GPU/CPU/丢弃三态；比 CachedAttention 的整会话对象细，适合做“块级价值”的基线。 |
| 价值建模 | 直接给出可计算的价值密度：`V = Cost(s,l) / T`。`Cost` 由离线剖析的注意力成本加常数得到，`T` 是空闲时间。它把“复用收益”与“未来复用概率”的代理（越久未用越不可能用）合在一起，是第一章最接近“可落地公式”的参考。 |
| 生命周期 | 请求结束后保留；GPU 空闲低于 25% 时提前换出到 CPU；CPU 满时按 `V` 丢弃；下次请求按层流水换入；被丢弃的头部块重算。没有 TTL，`T` 承担时间衰减；没有准入过滤，所有块先留在 GPU。 |
| Flink 映射 | `MapState<chunkId, ChunkMeta>` 存 `Cost`、`lastActive`、所在层；`ValueState<Long>` 存会话当前上下文长度；`TimerService` 推进 `T` 并触发换出；`checkpoint` 保存块索引；`compaction` 合并相邻块，减少元数据。KV 张量放外部 GPU/CPU 缓存服务。 |
| 可写缺口 | `V` 的分母是“已空闲时间”，不是“未来复用概率”；没有质量风险、验证成本和跨会话语义复用。可把 `T` 换成生存分析/预测模型的输出，把 `Cost` 扩展为“重算 + 传输 + 验证”，并加入租户/会话优先级。 |

## F 局限与边界

论文没有单独的 Limitations 小节。实验在 Azure NC A100 v4 上进行，最多 4 张 A100-80GB，每 GPU 40GB KV、220GB CPU 内存；只覆盖 GPU+CPU 两级，没有磁盘或远端存储。

缓存键是精确 token 前缀，不做语义近似；同一会话内复用是安全的，但跨会话共享没有覆盖。

`Cost` 依赖离线 profiler 和插值。模型、GPU、batch 大小变化后需要重新标定；论文没有给出在线校准方法。

驱逐策略只用“空闲时间”作为未来复用的代理，遇到周期性回访或外部事件触发的回访会误判。论文没有 TTL，也没有“刷新/续期”操作。

实验数据是 ShareGPT 与 UltraChat，请求到达用 Poisson 模拟，用户思考时间用指数分布模拟；没有真实生产 trace、多租户隔离和隐私约束。

论文未给出代码仓库链接；复现需要按论文描述重写内核与调度器。

## G 引用信息

Yu, Lingfan, Jinkun Lin, and Jinyang Li. “Stateful Large Language Model Serving with Pensieve.” In *Proceedings of the 20th European Conference on Computer Systems (EuroSys '25)*, 144–158. 2025. https://doi.org/10.1145/3689031.3696086. arXiv:2312.05516v3.

```bibtex
@inproceedings{yu2025pensieve,
  title     = {Stateful Large Language Model Serving with Pensieve},
  author    = {Yu, Lingfan and Lin, Jinkun and Li, Jinyang},
  booktitle = {Proceedings of the 20th European Conference on Computer Systems (EuroSys '25)},
  pages     = {144--158},
  year      = {2025},
  doi       = {10.1145/3689031.3696086},
  note      = {arXiv:2312.05516v3}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 3–8 页设计；第 8–11 页实验；第 11 页结论。
