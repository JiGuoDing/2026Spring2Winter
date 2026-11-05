---
template: doc
theme: auto
lang: zh
title: KVFlow：用 Agent Step Graph 预判 KV 复用
subtitle: NeurIPS 2025 · ctx
source: NeurIPS 2025（第 39 届 Conference on Neural Information Processing Systems）
outline: right
---

Agent 工作流的固定 prompt 会被反复调用，LRU 却常在 Agent 即将再次执行前把它的 KV 淘汰。KVFlow 把工作流抽象成 Agent Step Graph，用 `steps-to-execution` 给每个 KV 节点排优先级，并提前预取下一批 Agent 的缓存。对第一章最有用的是，它把“未来复用概率”变成了一个可计算的图上的量。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows |
| 作者 | Zaifeng Pan, Ajjkumar Patel, Yipeng Shen, Zhengding Hu, Yue Guan, Wan-Lu Li, Lianhui Qin, Yida Wang, Yufei Ding |
| 机构 | University of California, San Diego；AWS |
| 发表 | 39th Conference on Neural Information Processing Systems（NeurIPS 2025） |
| 正式版本 | NeurIPS 2025；页码论文未给出 |
| arXiv / DOI | 论文未给出 arXiv 编号；DOI 论文未给出 |
| 本地原文 | `paper_source/KVFlow_NeurIPS2025.pdf` |
| 代码/数据 | 论文承诺开源 `https://github.com/PanZaifeng/KVFlow`；实验用合成 10 阶段工作流与 PEER 风格工作流 |
| 版本边界 | 本地 PDF 为 NeurIPS 2025 排版版；无 arXiv 版本可对照 |

## B 问题与动机

LLM Agent 工作流由多个专用 Agent 组成，每个 Agent 有固定 prompt（角色、职责、行为约束、few-shot 示例）和动态任务输入。固定 prompt 在每次调用中重复，适合用前缀缓存复用 KV。

现有系统用 LRU 淘汰。Agent 工作流的执行顺序不是请求到达顺序：一个即将执行的 Agent 可能已经空闲很久，而刚执行完的 Agent 可能很久不会再跑。LRU 会把“马上要用”的缓存误判为冷数据。

论文给出一个四 Agent 的例子：Planner、Executor、Expresser、Reviewer 顺序循环。时间戳 13 时 Executor 活跃并更新 KV，LRU 认为 Expresser 最久未用而将其淘汰；时间戳 14 Expresser 再次执行，发生 cache miss，预填充延迟上升。

固定 prompt 可能很大。论文举例，TestBench Agent 和 RTL Generator Agent 的固定 prompt 分别超过 3000 和 1000 token。缓存命中与否对延迟影响显著。

GPU 容量有限时，单纯做前缀缓存不够。论文要同时解决两个问题：淘汰时不要误伤即将复用的 Agent；缓存未命中时不要阻塞生成。

## C 方法机制

**Agent Step Graph（ASG）。** 每个节点是一次 Agent 调用，边表示依赖关系。节点带一个 `steps-to-execution` 值，表示它距离当前执行点还有多少步。聚合函数沿边传播：

- 若一个 Agent 依赖多个前驱全部完成，取 `max(E1, E2) + 1`。
- 若任一前驱完成即可触发，取 `min(E1, E2) + 1`。
- 同步屏障按所有前驱的最大步数加一。

这样，条件分支、并行汇合、循环都能用同一套图表达。

**节点级淘汰优先级。** 优先级只分配给 Agent 固定 prompt 的最后一个 KV 节点，然后沿树向上传播。动态后缀（本轮任务输入、生成内容）一律给最高淘汰优先级，尽早清掉。

当一个节点被多个 Agent 共享时，取子节点中最小（最不易淘汰）的优先级。这样共享前缀会尽量保留，只要它对任一近期 Agent 还有用。

淘汰时从叶节点开始，用最大堆按优先级取出；释放一个节点后，如果父节点变成叶子，再把父节点入堆。这保证“先删动态后缀，再删固定前缀”，且不会删掉仍被更近 Agent 需要的共享节点。

**主动预取。** 当 CPU 内存作为二级缓存时，系统可以在当前 Agent 执行期间，根据 ASG 预取下一批可能执行的 Agent 的 KV。分支处保守地预取所有可能分支，但限制并发预取数量。

**状态感知调度。** 每个 KV 节点有四种状态：在 GPU、在 CPU、正在加载、正在换出。调度器跳过仍在加载的请求，先执行其他就绪请求；正在换出的节点不参与淘汰，避免竞争条件。预取与计算使用不同硬件资源（PCIe 全双工），可以重叠。

**固定/动态切分。** 用户可以用原语显式标记固定部分的结束位置；也可以启发式地把“持续命中的前缀”视为固定部分。为避免陈旧条目，KVFlow 支持自适应机制：固定 prompt 节点超过阈值时间未被复用就自动移除。

**实现。** 基于 SGLang v0.4.4，扩展其 radix tree 缓存；前后端都做了修改，通过 HTTP 请求携带 Agent 身份和 ASG 步数信息。论文指出方法不限于 SGLang，vLLM 的 block 级 LRU 也可以加优先级。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 单工作流 | Qwen2.5-32B，单张 H100 80GB，PCIe Gen5 64GB/s；10 阶段顺序工作流；fixed/dynamic/output = 4096/32/32 等四组 | 4096/32/32、branches=1 时，比 SGLang+HiCache 快 1.24×，比纯 GPU SGLang 快 1.42× | 固定前缀越长，缓存 miss 的代价越大，KVFlow 的相对收益越明显 |
| 前缀长度 | fixed=4096 vs 8192 | 8192 时平均加速 1.30×，4096 时 1.22× | 收益随固定 prompt 增长 |
| 组件消融 | 在 HiCache 上逐项加 | 只加工作流感知淘汰：平均 1.11×；再加预取：1.29× | 淘汰与预取是两项独立增益 |
| 高并发 | Qwen2.5-32B、Llama-3.1-8B；四组配置：512/20、1024/10、512/128、1024/64（固定 token/并发工作流数） | 最高 1.25× 加速；相对 HiCache 最高 2.19×；HiCache 在 1024/64 时只有纯 GPU SGLang 的 0.57× | 高并发下 reactive loading 会打乱调度，主动预取更重要 |
| PEER 风格 | 4 Agent，真实模板生成 prompt；Financial QA | 相对 SGLang 最高 1.12×，相对 HiCache 最高 1.08× | prompt 只有几十到几百 token 时收益变小，但仍为正 |
| 正确性 | 只改缓存管理，不改模型/提示/解码 | 输出语义不变 | 评估只看延迟，不测质量；这是“精确复用”的安全边界 |

## E 对第一章的用法

下表把论文事实映射到第一章；其中 Flink 映射与可写缺口是我们的推断。

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `ctx`/`plan`。对象是 Agent 固定 prompt 对应的 KV 节点，多个 Agent 可共享前缀；动态后缀是与任务实例绑定的临时状态。 |
| 价值建模 | `steps-to-execution` 是“未来复用概率”的离散代理：步数越小，越可能马上复用，价值越高；动态后缀价值近似为零；共享节点取最小步数，价值按“最需要的 Agent”计。这个量比 LRU 的时间戳更接近 Agent 语义。 |
| 生命周期 | 准入：所有固定 prompt 先缓存；保留：按节点优先级；驱逐：叶到根、按优先级最大堆；预取：下一批 Agent；失效：固定 prompt 超时未复用则移除；回退：不可预测工作流退化为等优先级 + 关闭预取。没有 TTL，超时移除是唯一的时效机制。 |
| Flink 映射 | `MapState<nodeId, NodeMeta>` 存优先级、状态、父指针、固定/动态标记；`ValueState<Integer>` 存当前步；`BroadcastState` 广播 ASG；`TimerService` 按步推进并触发预取/超时移除；`checkpoint` 保存 radix 树；优先队列可用 `MapState` + 堆实现。 |
| 可写缺口 | 优先级只表达“时间邻近”，没有计“重算成本/存储字节/质量风险”；跨工作流共享节点只取最小优先级，缺少公平性与租户隔离；高度动态的 DAG 无收益。可写“步数 × 成本 × 风险”的复合价值，以及 Flink 中跨 key 的全局优先级协调。 |

## F 局限与边界

论文第 3.4 节明确限制：只适用于未来 Agent 调用可估计的结构化工作流。若执行顺序在某个未来窗口内可预测，KVFlow 可用；高度不可预测时没有性能收益，会退化为 SGLang 默认行为（等优先级、关闭预取），不引入额外开销或正确性问题。

高并发实验假设多个工作流“不交互、不共享”；真实多租户环境中，共享前缀、跨工作流依赖和公平性没有覆盖。

价值模型只有步数，没有缓存大小、重算成本、SLO 或质量约束。固定 prompt 的切分依赖用户标记或“持续命中”启发式；切错会把动态内容当固定内容缓存。

评估集中在 Qwen2.5-32B 与 Llama-3.1-8B、单张 H100；合成工作流的 prompt 长度可控，PEER 风格的真实 prompt 只有几十到几百 token，收益明显变小。

论文没有给出代码仓库的最终地址（只承诺开源）；复现需要按描述改 SGLang 前后端。

## G 引用信息

Pan, Zaifeng, Ajjkumar Patel, Yipeng Shen, Zhengding Hu, Yue Guan, Wan-Lu Li, Lianhui Qin, Yida Wang, and Yufei Ding. “KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows.” In *Advances in Neural Information Processing Systems (NeurIPS 2025)*. 2025.

```bibtex
@inproceedings{pan2025kvflow,
  title     = {KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows},
  author    = {Pan, Zaifeng and Patel, Ajjkumar and Shen, Yipeng and Hu, Zhengding and Guan, Yue and Li, Wan-Lu and Qin, Lianhui and Wang, Yida and Ding, Yufei},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS 2025)},
  year      = {2025}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 3–6 页设计；第 7–9 页实验；第 9 页限制；第 10 页结论。
