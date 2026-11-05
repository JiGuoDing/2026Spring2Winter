---
template: doc
theme: auto
lang: zh
title: PromptPeek：KV 缓存共享如何泄漏提示词
subtitle: NDSS 2025 · ctx（风险）
source: NDSS 2025, San Diego, 2025-02-24/28, pp. 1–15, DOI 10.14722/ndss.2025.241772
outline: right
---

问题是多租户推理框架按前缀共享 KV 缓存，命中与否会改变请求的服务顺序；论文把这一 1-bit 侧信道变成逐 token 还原提示词的攻击，对第一章最有用的是把“复用风险”写成生命周期中的硬约束，而不是事后补丁。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | I Know What You Asked: Prompt Leakage via KV-Cache Sharing in Multi-Tenant LLM Serving |
| 作者 | Guanlong Wu, Zheng Zhang, Yao Zhang, Weili Wang, Jianyu Niu, Ye Wu, Yinqian Zhang（通讯作者） |
| 机构 | SUSTech；ByteDance Inc. |
| 发表 | Network and Distributed System Security (NDSS) Symposium 2025，2025-02-24/28，San Diego |
| 正式版本 | NDSS 2025 会议论文，pp. 1–15；ISBN 979-8-9894372-8-3 |
| arXiv / DOI | DOI 10.14722/ndss.2025.241772；arXiv 编号论文未给出 |
| 本地原文 | `paper_source/PromptPeek_NDSS2025.pdf`（15 页） |
| 代码/数据 | 未发现公开代码；数据集为 UltraChat、PromptBase、awesome-chatgpt-prompts、alpaca-gpt4 |
| 版本边界 | 实验基于 SGLang，具体版本论文未给出；单张 A100 80G；目标模型 Llama2-13B |

## B 问题与动机

vLLM 与 SGLang 默认开启前缀 KV 共享：两个请求只要从第一个 token 起有连续相同前缀，后者就能直接复用前者的 KV，只重算不同部分。SGLang 用 radix tree 存 KV，显存满时按 LRU 驱逐；调度用 Longest Prefix Match（LPM），匹配前缀更长的请求先服务。

论文的关键观察是：LPM 把“是否命中”编码进了返回顺序。攻击者不需要读显存，只要观察自己请求的返回次序，就能判断某个候选 token 是否与受害者前缀相同。于是 KV 共享从性能机制变成了跨租户侧信道。

攻击成立需要三个条件，论文在第七节明确列出。第一，KV 缓存只要显存够就一直保留，给攻击者足够多的试探机会。第二，共享状态可被客户端观测，至少泄漏 1 bit。第三，客户端能自由控制请求参数并高频发送请求。

## C 方法机制

攻击以 token 为粒度循环执行。候选生成阶段，攻击者用同 tokenizer 的本地 LLM 生成 top-k 个可能的下一个 token，并额外生成一个“dummy token”（最不可能的词）构造 dummy 请求。token 选择阶段，攻击者把 dummy 请求放在候选前后，强制候选进入等待队列，再由 LPM 按匹配长度重排。

判定规则很直接。若某个候选命中，返回顺序是“前置 dummy → 命中候选 → 后置 dummy → 其余候选”；若没有命中，则是“前置 dummy → 后置 dummy → 全部候选”。候选批次大小不必等于本地 LLM 的 top-k；论文实测有的 token 要几千个候选，有的不到十个。

提示词重建阶段有两个技巧。其一是 prompt switching：攻击者重发此前的失败候选，并用等长 dummy 包裹；如果该候选已被驱逐，匹配长度会少一个 token，次序随之改变，从而推断目标提示词也已按 LRU 被清出。其二是主动清空：发送大量互不相同、输出长度拉满的 dummy 请求，把显存压满，触发“除当前 batch 外全部驱逐”，从干净状态开始下一次重建。

## D 关键实验

| 实验 | 设置 | 结果 | 读法 |
|:--|:--|:--|:--|
| 整体效果 | A100 80G、Llama2-13B、SGLang；batch 16；每请求输出上限 128；温度 0 | 输入重建平均成功率 99%、还原率 99%；模板重建 98%、91%；无背景知识整段提示词 95%、81% | 即使没有模板知识，也能还原大部分提示词 |
| 成本 | 统计候选请求数，不计 dummy | 知道模板时，还原性别、年龄、体重、身高共需 60 个请求 | 攻击成本可以低到几十次请求 |
| 难 token | 同一提示词中的 “Frank” | 无背景需 4093 个请求；有背景只需 24 个 | 成本分布长尾，少数 token 决定整段能否还原 |
| 请求分布 | 三个数据集、三种场景 | 超过 90% 的 token 用少于 10 个候选请求即可还原 | 方法在多数 token 上很高效 |
| GQA 缓存 | Llama3-8B-GQA，role-based 数据 | 三种场景成功率均 100%；整段 5505 请求/输入、306 请求/token | KV 越小，目标在显存中活得越久，攻击反而更容易 |
| 影响因素 | 并发用户、显存、候选/ dummy 批量 | 用户少于 200 时效果稳定；显存低于 70GB 开始下降；候选批量 40 时效果峰值 | 攻击空间由剩余显存、并发请求与攻击请求共同决定 |

## E 对第一章的用法

| 维度 | 可用点 |
|:--|:--|
| 缓存对象 | 直接对应 `ctx`：系统提示、模板、用户输入、历史对话都以 KV 前缀形式被共享；共享粒度是 token 前缀，不是语义块 |
| 价值建模 | 复用收益必须减去“暴露概率 × 泄漏损失”。论文给出三个可观测因子：缓存驻留时间、共享是否可观测、客户端请求控制自由度；可写成风险惩罚项 `risk = P(observe) × sensitivity` |
| 生命周期 | 驻留越久，攻击窗口越大；LRU 驱逐与“显存满才清”都是风险放大器。TTL、强制失效、按租户隔离、限制共享可见性都是生命周期层的防御点 |
| Flink 映射 | 以 `tenantId` 做 keyBy，`MapState<prefixHash, CacheMeta>` 只在本租户内可见；State TTL 加随机抖动，避免“同一时刻集体过期/集体保留”；用 timer 记录最长驻留并触发审计 |
| 可写缺口 | 论文只证明风险存在，没有把风险量化进缓存价值，也没有评估防御。第一章可写“风险感知的准入/保留策略”：在 Flink 状态后端按租户隔离前缀、给 TTL 加抖动，并用可观测性开关切断侧信道 |

## F 局限与边界

实验在单张 A100 的本地 SGLang 上完成，公网云的多租户 colocation 未实测；论文把 colocation 列为未来工作。攻击只针对 LPM，FCFS/随机调度未覆盖；作者认为其他缓存感知策略也可能有类似问题，但未验证。防御只给出方向（如要求至少 M 个 token 同时匹配、引入随机性），没有实现与评测。SGLang 版本、代码与超参细节未给出，复现边界不完整。威胁模型假设攻击者知道调度与驱逐策略，属于较强假设。

## G 引用信息

```bibtex
@inproceedings{wu2025promptpeek,
  title     = {I Know What You Asked: Prompt Leakage via KV-Cache Sharing in Multi-Tenant LLM Serving},
  author    = {Wu, Guanlong and Zhang, Zheng and Zhang, Yao and Wang, Weili and Niu, Jianyu and Wu, Ye and Zhang, Yinqian},
  booktitle = {Network and Distributed System Security Symposium (NDSS)},
  year      = {2025},
  pages     = {1--15},
  doi       = {10.14722/ndss.2025.241772},
  publisher = {Internet Society}
}
```

来源页面：PDF 第 1 页标题、作者、摘要与 NDSS 版权页；第 3–6 页系统模型与攻击；第 9–12 页实验；第 12–14 页攻击条件、讨论与结论。
