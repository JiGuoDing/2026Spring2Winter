---
template: doc
theme: auto
lang: zh
title: LMCache：把 KV 缓存做成企业级一等存储对象
subtitle: arXiv 2025（MLSys 2026 invited talk）· ctx
source: arXiv:2510.09665v2 [cs.LG], 2025-12-05, 19 pp.
outline: right
---

问题是大模型 KV 缓存已远超 GPU 容量、又要在查询与推理引擎之间复用；论文用“分块批量搬运 + 连接器解耦 + 控制器 API”把 KV 缓存变成可定位、可固定、可迁移、可压缩的一等对象，对第一章最有用的是这套对象化与生命周期操作抽象。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference |
| 作者 | Yuhan Liu\*, Jiayi Yao\*, Yihua Cheng\*, Yuwei An, Xiaokun Chen, Shaoting Feng, Yuyang Huang, Samuel Shen, Rui Zhang, Kuntai Du, Junchen Jiang（\* 同等贡献） |
| 机构 | Tensormesh Inc.；University of Chicago |
| 发表 | arXiv 2025；任务清单标注 MLSys 2026 invited talk（论文正文未提及该信息） |
| 正式版本 | arXiv v2，2025-12-05；会议正式版页码与 DOI 论文未给出 |
| arXiv / DOI | arXiv:2510.09665v2 [cs.LG]；DOI 论文未给出 |
| 本地原文 | `paper_source/LMCache_arXiv2510.09665.pdf`（19 页） |
| 代码/数据 | https://github.com/LMCache/LMCache；LongBench、vLLM 官方 benchmark、合成多轮问答 |
| 版本边界 | 实测 LMCACHE v0.3.6；基线为 vLLM v0.10.2 与 v0.11.0；商业 API 只做黑盒对比 |

## B 问题与动机

传统 KV 缓存只服务于单次查询，查询结束即随 GPU 显存释放。论文把它称为“LLM 原生的知识表示”，并给出线上统计：用户存储的 KV 缓存总量持续增长并远超 GPU 容量，超出部分（图 3 蓝色区域）逐周上升。另一个统计是复用强度：超过 19% 的用户对已存 token 的复用次数超过 1.5 次。

因此出现两类“把 KV 缓存移出 GPU”的场景。其一是上下文缓存：把一次查询产生的 KV 段持久化，供后续共享同一前缀的查询复用。其二是 PD 分离：prefill 与 decode 放在不同 GPU，prefill 产生的 KV 必须传到 decode 端。

现有系统有三个缺口。分页显存把 KV 切成 16–64 KB 的小页，vLLM 在 Llama-3.1-8B-Instruct 上页大小为 62.5 KB，小页传输无法打满带宽。2025 年平均每 4 天就有一个重要 LLM 发布、每周 15–20 个开放权重模型，推理引擎必须跟着快速演进，KV 布局频繁变化。系统还缺少统一的定位、驱逐、固定、压缩接口，上层路由器无法做缓存感知决策。

## C 方法机制

LMCache 位于推理引擎与异构存储/网络之间，核心组件包括 KV connector、token processor、storage manager、event manager 和全局 cache controller。

搬运优化有四条。第一，按可配置 chunk 聚合多页多层，默认 256 token，先经 CUDA kernel 收进连续 GPU buffer，再用 DMA 整块下沉。第二，store/load 支持多源多目的并行，全双工链路上可同时读写。第三，decode 阶段延迟攒批，攒满一个 chunk 再写，避免逐 token 小写。第四，按层流水：第 1 层计算时预取第 2 层 KV，只占用单层大小的 GPU buffer。

数据拷贝用引用计数做零拷贝，多个目的端共享同一份数据；动态下沉只复制空闲页的一个窗口，用 start/current/end 三个指针控制复制比例与分配停顿的权衡。

接口分两层。连接器接口把调度器与 model runner 分开：`get_num_new_matched_tokens` 报告命中 token 数，`start_load_kv`/`wait_load_kv` 与 `start_store_kv`/`wait_store_kv` 控制逐层加载与写回。控制器接口提供 `lookup`、`move`、`clear`、`pin/unpin`、`compress/decompress`，实例通过 `batched_admit`、`batched_evict`、`batched_p2p_lookup` 上报与查询全局元数据。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 单节点 CPU 卸载 | 多轮文档问答，每查询约 10K token；Llama-3.1-8B 输入 20K；CPU 上限 500 GB；5 个模型 | TTFT 小 1.9–8.1×；同 TTFT 下吞吐高 2.3–14×；QPS=1 时 ITL 小 7%–92% | 收益主要来自 CPU 比 GPU 能存更多 KV，命中率更高 |
| 真实 trace | 公司 F/G 的输入输出分布，拉伸到 1 小时内跑完；500 GB CPU DRAM | TTFT 小 3.7–6.8×；ITL 小 19%–58% | 跨 5 个模型一致，说明不是单一负载偶然 |
| 中心化远端存储 | 远端带宽 15 Gbps；LongBench TriviaQA；Poisson 到达 | 同 TTFT 下吞吐高 1.3–3× | 远端容量更大但加载更慢，需要“加载还是重算”的自适应判断 |
| PD 分离 | 8K 输入、200 输出；对比 vLLM 原生 PD | 平均 TTFT 缩小 1.53–1.84×；平均 ITL 缩小 1.12–1.66× | 收益来自 chunk 级传输，而非页级 NIXL 拷贝 |
| 组件消融 | CPU 加载带宽；异步计算 | 400 Gbps 对 88 Gbps；异步把端到端延迟降 1.46× | 传输粒度与计算/IO 重叠是两项独立增益 |

敏感度实验给出一个对第一章很有用的阈值：网络 32 Gbps 时，只有输入超过 256K token，加载 KV 才比重新 prefill 更快；64 或 128 Gbps 时，所有长度都更快。论文还报告，把上下文截断到只留最近 token，会让前缀命中率从约 85% 降到 45%。

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | 把 KV 缓存定义为可提取、可加载、可定位、可固定、可压缩的一等对象；可作为第一章 `ctx` 的底层物理表示，而 `ctx` 是其在 Agent 会话层的语义封装 |
| 价值建模 | 论文的可测变量是命中率、复用次数、TTFT/ITL、加载带宽；阈值实验说明“复用收益”不是常量，而是上下文长度与网络带宽的函数，可写成 `benefit = f(hit, L_context, BW) − load_delay` |
| 生命周期 | 写入（store）、准入/驱逐（admit/evict 接口）、保留（pin/unpin）、迁移（move）、清除（clear）、压缩（compress）、预取（async prefetch）都已对象化；但具体驱逐策略论文未给出 |
| Flink 映射 | 全局 token pool 可映射为 `MapState<prefixHash, CacheMeta>`；`pin` 映射为元数据布尔位；预取用 `TimerService` 在排队窗口触发；跨节点迁移走 checkpoint 外的控制流；chunk 合并可借 RocksDB compaction |
| 可写缺口 | 论文的判据是系统性能而非“价值”：没有把复用风险、未来复用概率、存储/加载成本、质量约束合成一个可计算效用，也没有 TTL 与租户隔离。第一章可补“价值感知的准入/驱逐 + Flink 状态后端实现” |

## F 局限与边界

论文假设 KV 复用是精确等价的，因此不测生成质量下降；它优化的是搬运，不是“该不该复用”。安全维度未覆盖：多租户共享前缀可能带来 PromptPeek 一类侧信道，论文没有讨论。驱逐策略只暴露接口，未给出默认算法与 TTL 语义。实验以 vLLM 为主，SGLang 只做一组 CPU 卸载对比；商业基线是黑盒，作者对商业方案内部机制的判断属于推测。真实 trace 被拉伸到 1 小时，长期漂移未覆盖。

## G 引用信息

```bibtex
@misc{liu2025lmcache,
  title  = {LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference},
  author = {Liu, Yuhan and Yao, Jiayi and Cheng, Yihua and An, Yuwei and Chen, Xiaokun and
            Feng, Shaoting and Huang, Yuyang and Shen, Samuel and Zhang, Rui and Du, Kuntai and
            Jiang, Junchen},
  year   = {2025},
  eprint = {2510.09665},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  note   = {arXiv v2, 5 Dec 2025}
}
```

来源页面：PDF 第 1 页标题、作者与摘要；第 4–6 节架构与优化；第 8 节实验；第 9 节真实部署经验；第 10 节结论。
