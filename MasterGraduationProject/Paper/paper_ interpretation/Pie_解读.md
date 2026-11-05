---
template: doc
theme: auto
lang: zh
title: Pie：把 KV 缓存生命周期下放给可编程 inferlet
subtitle: SOSP 2025 · ctx
source: SOSP '25, pp. 415–430；DOI 10.1145/3731569.3764814；arXiv:2510.24051v1 [cs.CL], 2025-10-28
outline: right
---

Pie 把单体式 prefill-decode 循环拆成细粒度 handler，让用户程序（inferlet）通过 API 自己分配、导出、屏蔽和复用 KV 页。对第一章最有用的是，它把“缓存策略”从系统内置启发式变成了应用可编程对象。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Pie: A Programmable Serving System for Emerging LLM Applications |
| 作者 | In Gim, Zhiyao Ma, Seung-seob Lee, Lin Zhong |
| 机构 | Yale University |
| 发表 | ACM SIGOPS 31st Symposium on Operating Systems Principles（SOSP '25），2025-10-13 至 10-16，Seoul；pp. 415–430，16 页 |
| 正式版本 | SOSP '25；DOI 10.1145/3731569.3764814 |
| arXiv / DOI | arXiv:2510.24051v1 [cs.CL]，2025-10-28；DOI 10.1145/3731569.3764814 |
| 本地原文 | `paper_source/Pie_arXiv2510.24051.pdf` |
| 代码/数据 | https://github.com/pie-project/pie；实验用 Llama 3 1B/3B/8B、GCP L4 |
| 版本边界 | 本地 PDF 为 arXiv v1；SOSP 正式版页码 415–430；两者技术内容一致 |

## B 问题与动机

现有 LLM 服务系统围绕“一个 prompt 进、一段 token 出”的单体循环设计。调度器统一管理 batch、KV 缓存和采样，应用只能通过文本 prompt 表达意图。

新兴应用不满足于这个模型。思维树、map-reduce 摘要、多步生成需要细粒度控制 KV 的分配、驱逐和复用；辅助解码、MCTS、状态化采样需要改写 token 预测循环；Agent 工作流需要把 LLM 调用与外部工具、代码执行、API 调用交织在一起。

论文把这些需求归为三条：

- R1：应用特定的 KV 缓存控制，包括分配、驱逐、复用策略。
- R2：可定制的生成过程，能按请求甚至按步骤修改采样循环。
- R3：计算与 I/O 的紧密集成，避免客户端与服务端来回协调。

现有系统（vLLM、TGI）用全局策略管理 KV，生成循环封闭，工具调用被隔离在服务系统之外。SGLang、Parrot 提供了一些编程抽象，但仍受单体设计限制。

## C 方法机制

**Handler 拆分。** Pie 把前向过程拆成三个阶段：`embed`（文本/图像→embedding）、`forward`（embedding→输出 embedding，可读写 KV）、`sample`（输出 embedding→token 分布）。每个阶段是一组细粒度 handler，通过 API 暴露。

**Inferlet。** 用户程序叫 inferlet，用任何能编译到 WebAssembly 的语言编写（C++、Rust、Python 等），通过 API 调用 handler。Pie 用 wasmtime 执行 inferlet，利用 Wasm 的轻量沙箱隔离多租户。一个 inferlet 可以管理自己的 KV 页、定义生成逻辑、直接发起 HTTP 请求或执行代码。

**资源对象。** `Embed` 是按 token 分配的 embedding 序列；`KvPage` 是一段连续的 KV 缓存，粒度为 8–32 token，沿用 PagedAttention 的分页思想。两者都由 inferlet 显式分配和释放。

**KV 相关 API。** 表 1 列出 42 个 API，其中 18 个是核心执行/资源管理 API。与缓存直接相关的包括：

- `alloc_kvpage(q, size)` / `dealloc_kvpage(q, kv)`：分配/释放 KV 页。
- `export_kvpage(kv, name)` / `import_kvpage(name)`：把 KV 页导出/导入，供其他 inferlet 共享。
- `copy_kvpage(q, src, dst)`：按 token 复制 KV。
- `mask_kvpage(q, tgt, mask)`：按 token 屏蔽 KV，用于丢弃不再需要的上下文。
- `forward(q, ikv, iemb, okv, oemb, mask)`：显式指定输入/输出 KV 与注意力掩码。

**命令队列与批处理。** 每个 inferlet 的 API 调用进入命令队列，队列标明依赖关系和优先级。控制层做垂直批处理（同一队列内无冲突的调用合并）和水平批处理（不同队列的同类型调用合并），再把批处理后的调用送到推理层执行。

**三层架构。** 应用层跑 inferlet；控制层做资源虚拟化、批处理和调度；推理层用 PyTorch/FlashInfer 执行 GPU 算子，并通过 ZeroMQ 与控制层通信。KV 页的物理内存由推理层持有，控制层只管理虚拟地址映射。

**应用示例。** 论文给出一个 Agent 工作流：频繁使用的 API 文档 KV 用 `export_kvpage` 长期保留；只调用一次的 API 规格用 `mask_kvpage` 从上下文中丢弃；检测到可调用签名时立即并发调用外部 API。三个优化叠加后，比 vLLM 上的 Python 基线吞吐高 3.5×。

**资源竞争。** 当 KvPage 需求超过容量时，Pie 目前按 FCFS 终止最近启动的 inferlet 来释放资源。论文把更丰富的配额、SLO/优先级准入、CPU-GPU 交换留给未来工作。

**实现。** 13,650 行代码，其中 11,640 行是 Rust 核心与支持库，其余是 Python GPU handler；支持库提供 `Context` 抽象、采样、停止条件和 fork-join。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 标准任务 | GCP g2-standard-32，单张 L4 24GB；Llama 3 1B/3B/8B，BF16 | 文本补全相对 vLLM/SGLang 有 3%–12% 延迟开销；吞吐与 SOTA 相当 | 可编程性有代价，但在标准任务上可接受 |
| Agent 工作流 | ReACT、CodeACT、Swarm；1B 模型；每 Agent 8/8/32 次外部 I/O | 延迟 4.27s、3.18s、6.14s；吞吐 29.94、40.18、5.21 agents/s；ReACT 延迟最多降 15%，吞吐最多升 30% | 小模型上主要收益来自消除客户端往返；大模型上主要来自保留 KV、避免重 prefill |
| 应用特定优化 | 频繁 API 文档保留 + 调用并发化 + 一次性规格丢弃 | 叠加后相对 vLLM Python 基线吞吐 3.5× | 三个优化分别对应“保留/并发/丢弃”，说明生命周期操作可组合 |
| 推理策略 | ToT、RoT、GoT、SkoT 作为 inferlet | 延迟最多降 28%，吞吐最多升 34% | 程序控制的 KV 复用比隐式前缀缓存更精确 |
| 注意力变体 | attention sink、windowed attention、hierarchical attention | 相对 StreamingLLM 原实现，延迟低 1.5×，吞吐高 30× 以上 | 同一套 `mask_kvpage` 能表达多种注意力模式；比较受底层 kernel 差异影响 |
| 启动开销 | 最多 896 个 inferlet 同时启动 | 热启动 10–50ms，冷启动 35–81ms | 相对 10–60ms/token 的生成延迟可忽略 |
| API 开销 | 控制层 vs 推理层；最多 896 并发 | 控制层每次 <30µs；推理层 10–300µs | 主要开销来自 Python 反序列化与 IPC，可用原生实现缓解 |
| 机会成本 | 32 并发；文本补全 TPOT | vLLM 64.06ms → Pie 65.59ms；总开销 1.53ms，其中缺少流水采样 +1.320ms | 8B 模型上开销约占 2.4%；摘要的 3%–12% 是另一组标准任务口径 |

## E 对第一章的用法

下表把论文事实映射到第一章；其中 Flink 映射与可写缺口是我们的推断。

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | `ctx`。对象是 `KvPage`（8–32 token）加上管理它的 inferlet；缓存不再由系统统一命名，而是由应用显式持有、导出、导入、屏蔽。 |
| 价值建模 | 论文不提供系统级价值公式，价值由应用逻辑编码。示例中“频繁使用的 API 文档”价值高，“只用一次的 API 规格”价值低；这提示第一章可以把“复用概率”拆成应用可声明的策略参数。 |
| 生命周期 | 覆盖分配、释放、导出/导入、复制、屏蔽；没有内建 TTL、LRU 或驱逐策略。资源不足时用 FCFS 终止最近启动的 inferlet。生命周期是“应用驱动”，不是“系统自动”。 |
| Flink 映射 | inferlet 可对应 Flink 的 UDF/operator；`KvPage` 句柄对应 operator 内的本地缓存句柄；`export/import` 对应 `BroadcastState` 或外部共享目录；`alloc/dealloc` 对应 `ValueState` 生命周期。Flink 不适合直接持有 GPU 页，需把 KV 放外部缓存服务，Flink 只做策略与元数据。 |
| 可写缺口 | 可编程性没有附带默认价值模型：应用必须自己写策略，系统不保证公平、隔离或回收。第一章可以补“策略库 + 默认价值函数 + 资源上限”，并研究 Flink UDF 如何安全地表达 per-request TTL/优先级。 |

## F 局限与边界

论文第 8 节列出限制。安全面扩大：用户 inferlet 可发起网络 I/O、读取 token 分布，带来侧信道、资源耗尽、模型抽取等风险；论文只给出方向，没有完整方案。

控制层是集中式批调度器，只接一个推理后端；多 GPU 节点部署需要额外的负载均衡、KvPage 局部性、全局调度和容错。

资源竞争目前用 FCFS 终止最近启动的 inferlet，缺少配额、SLO/优先级准入和 CPU-GPU 交换。

API 细粒度带来编程复杂度；论文用支持库缓解，但没有给出策略正确性的验证方法。

实验模型是 Llama 3 1B/3B/8B，单张 L4 24GB；没有覆盖 70B 级模型、多节点和生产多租户。

“3%–12% 延迟开销”来自摘要的标准任务口径；表 3 的 8B TPOT 开销是 1.53ms（2.4%），两组数字的口径不同，引用时需注明。

## G 引用信息

Gim, In, Zhiyao Ma, Seung-seob Lee, and Lin Zhong. “Pie: A Programmable Serving System for Emerging LLM Applications.” In *Proceedings of the ACM SIGOPS 31st Symposium on Operating Systems Principles (SOSP '25)*, 415–430. 2025. https://doi.org/10.1145/3731569.3764814. arXiv:2510.24051v1.

```bibtex
@inproceedings{gim2025pie,
  title     = {Pie: A Programmable Serving System for Emerging LLM Applications},
  author    = {Gim, In and Ma, Zhiyao and Lee, Seung-seob and Zhong, Lin},
  booktitle = {Proceedings of the ACM SIGOPS 31st Symposium on Operating Systems Principles (SOSP '25)},
  pages     = {415--430},
  year      = {2025},
  doi       = {10.1145/3731569.3764814},
  note      = {arXiv:2510.24051v1}
}
```

来源页面：PDF 第 1 页标题、作者、摘要；第 3–7 页编程模型与架构；第 8–12 页实验；第 12–13 页讨论与限制。
