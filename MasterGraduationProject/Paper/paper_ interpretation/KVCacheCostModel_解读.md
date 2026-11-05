---
template: doc
theme: auto
lang: zh
title: KV 缓存复用的成本模型：省延迟是否也省钱
subtitle: arXiv 2025 · value model / ctx
source: arXiv:2503.14647v1 [cs.NI], 2025-03-18, 2 pp. (poster)
outline: right
---

问题是从云端存储并复用 KV 缓存，除了降延迟，是否还能降低 compute、storage、network 三项费用；论文给出一个解析成本模型并用 Llama-7B 仿真验证，对第一章最有用的是“复用收益必须与存储/传输成本同量纲比较”的建模骨架。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | Towards More Economical Context-Augmented LLM Generation by Reusing Stored KV Cache |
| 作者 | Hanchen Li\*, Yuhan Liu\*, Yihua Cheng, Kuntai Du, Junchen Jiang（\* 同等贡献） |
| 机构 | The University of Chicago |
| 发表 | arXiv 2025；会议/期刊正式发表信息论文未给出 |
| 正式版本 | arXiv v1，2025-03-18；2 页 poster，无正式版页码与 DOI |
| arXiv / DOI | arXiv:2503.14647v1 [cs.NI]；DOI 论文未给出 |
| 本地原文 | `paper_source/KVCacheCostModel_arXiv2503.14647.pdf`（2 页） |
| 代码/数据 | 未发现公开代码；TriviaQA 的 200 个上下文 |
| 版本边界 | 解析模型 + 初步仿真；Llama-7B、4×V100；不是完整系统实现 |

## B–D 问题、方法与实验

**问题。** 长上下文应用常把同一份文档或财报作为前缀。把前缀算成 KV 缓存存起来，下次直接加载，可以省掉 prefill；但 KV 要占存储、要占网络，云上都要付费。论文问：在什么条件下，复用 KV 比“每次重新读文本并 prefill”更便宜。

**两个成本式。** 文本重算路径只付 GPU 推理费：

`C_text = C_GPU × N × [T_prefill(L_context + L_prompt) + T_decode(L_output)]`

其中 `C_GPU` 是 GPU 实例小时价，`N` 是同一上下文的请求数，`L_context`、`L_prompt`、`L_output` 分别是上下文、用户问题、输出 token 数。

KV 复用路径把成本拆成三块：GPU 推理、上下文存储、传输。GPU 部分只 prefill 用户问题、不再 prefill 上下文，但公式还额外加了一次 `T_prefill`（论文未注明是加载还是预填充）；存储按“单价 × KV 大小 × 服务时长”计；传输按“KV 大小与 TTFT SLO”计。

`C_KV = C_GPU × [N × (T_decode(L_output) + T_prefill(L_prompt)) + T_prefill] + Storage + Transmission`

**关键推演。** 两式相除可近似为：

`C_text / C_KV ≈ 1 + ((N−1)/N) × T_prefill(L_context) / (T_decode(L_output) + T_prefill(L_prompt))`

这说明上下文越长、问题与输出越短、复用次数越多，节省越显著。

**算例。** Llama-7B 的 10K token 上下文需要 5.2 GB 存储。AWS EBS io2 单价 0.125 美元/GB·月、吞吐 4 GB/s；一小时存储加传输约 8.8×10⁻⁴ 美元。同小时单次 prefill 的 GPU 成本约 6×10⁻³ 美元（脚注算例 0.0058），是前者的 7 倍以上。论文由此判断：只要同一上下文每小时被复用超过一次，KV 复用就可能更经济；存储通常只占总成本的很小一部分。

**实验。** Llama-7B 跑在 EC2 p3.8xlarge（4×V100），HuggingFace 模型并行；TriviaQA 200 个上下文，每个上下文使用 5 次；输入长度 1–10K、输出长度 1–100 token 两组扫描。

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 变输入长度 | 输入 1–10K token，输出固定 | 端到端延迟降 1.1–2.9×；云成本降约 1.3–3.6× | 输入越长，省掉的 prefill 越多；输入越短，节省越有限 |
| 变输出长度 | 输出 1–100 token | 延迟降 1.6–3.5×；成本降 1.7–4.5× | 输出越长，首 token 的节省被摊薄，收益下降 |
| 盈亏平衡 | 解析模型 + AWS 价格 | 同一上下文每小时复用超过 1 次即可考虑复用 | 复用频率是价值模型的第一阶变量 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | 面向 `ctx` 的“上下文 KV”，也适用于 `rag` 的文档块：只要同一段文本被多个请求作为前缀 |
| 价值建模 | 给出可计算的成本侧：`C_KV` 含 GPU、存储、传输三项；收益侧是省掉的 `T_prefill(L_context)`。可直接作为第一章价值函数的“成本项”，并用 `C_text/C_KV` 做是否复用的判据 |
| 生命周期 | 写入发生在上下文首次 prefill 后；保留需要持续付存储费；复用需要按 SLO 付传输费。论文没有 TTL、驱逐、刷新策略，只给出“每小时复用一次”的盈亏平衡 |
| Flink 映射 | 用 `ValueState<CostAccumulator>` 按 key 累计 prefill 次数、存储时长、传输字节；用 `TimerService` 按小时窗口结算；checkpoint 保存计费参数；指标流可直接接 Flink metrics |
| 可写缺口 | 模型只有钱，没有质量、风险、租户维度，且假设 KV 完全等价。第一章可把“每 token 复用收益”细化为对象级价值，加入质量约束与风险惩罚，并用 Flink 状态维护实时复用频率 |

## F 局限与边界

这是 2 页 poster，模型是解析近似，不是实测系统。实验只用一个模型（Llama-7B）、一个数据集（TriviaQA 200 个上下文）、固定“每个上下文用 5 次”的假设；没有多租户并发、没有缓存容量上限、没有驱逐。价格只用 AWS 一档（io2），未覆盖不同区域、spot、预留实例。质量维度完全缺席：默认复用 KV 与重新计算等价。原文成本公式有一处符号复用（`C_storage` 同时出现在存储单价与传输链路成本的位置），按上下文区分，不影响量级结论，但复现时需注意。

## G 引用信息

```bibtex
@misc{li2025kvcost,
  title  = {Towards More Economical Context-Augmented LLM Generation by Reusing Stored KV Cache},
  author = {Li, Hanchen and Liu, Yuhan and Cheng, Yihua and Du, Kuntai and Jiang, Junchen},
  year   = {2025},
  eprint = {2503.14647},
  archivePrefix = {arXiv},
  primaryClass  = {cs.NI},
  note   = {arXiv v1, 18 Mar 2025; poster}
}
```

来源页面：PDF 第 1 页标题、作者、摘要与成本模型；第 1–2 页算例与实验；第 2 页结论与参考文献。
