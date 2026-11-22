---
template: doc
theme: auto
title: 流式智能体落地案例调研
subtitle: Flink Agents 与事件驱动 Agent 的生产案例、示例与研究证据
file: streaming-agent-cases
---

公开的具体案例存在。它们分三种性质：可复现示例、生产落地、研究原型。开源的 Apache Flink Agents 仍是 0.x 预览版，规模化生产案例出现在阿里云与 Confluent 的产品线上。

## A 先分清三种案例

| 层次 | 是什么 | 代表 | 可核对性 |
| --- | --- | --- | --- |
| 官方示例 | 仓库内可运行的 quickstart | 评论分析、RAG、多模态、决策模型 | ok 可复现 |
| 生产落地 | 云厂商产品 + 客户真实业务 | 阿里云 Streaming Agent、Confluent | warn 厂商自报 |
| 研究原型 | 论文系统与评测集 | StreamAgent、StreamingClaw | warn 需甄别 |

:::callout info 引用口径
版本节奏：0.1（2025-10-15）、0.2（2026-02-06）、0.3（2026-06-19）、0.4（2026-10-30）。[0.4 公告](https://flink.apache.org/2026/10/30/apache-flink-agents-0.4.0-release-announcement/)称其由早期生产用户反馈塑造，是 1.0 前最后一步。论文写明“开源版未规模化、商业版已落地”，论点更稳。
:::

## B 生产落地：六个可核对的场景

| 场景 | 实施方 | 关键做法 | 公开结果 |
| --- | --- | --- | --- |
| [赛事 AI 解说](http://m.blog.itpub.net/70004426/viewspace-3186654/) | 央视体育 × 阿里云 Flink | 直播流 + 官方赛程 + Flink 状态维护比赛上下文 | 高光片段 1 分钟内合成上传 |
| [短剧投流素材](http://m.blog.itpub.net/70004426/viewspace-3186654/) | 短剧营销公司 | OSS CDC → 抽帧打标 → Embedding → Paimon → StarRocks | 上传到可检索 < 30 分钟 |
| [AI 巡店](http://m.blog.itpub.net/70004426/viewspace-3186654/) | 连锁门店 | 周期抽帧 + 关键帧证据 + 多模态模型 | 单路 25fps 约 216 万帧/天，成本 1 元级/天 |
| [淘宝闪购](http://m.blog.itpub.net/70004426/viewspace-3186654/) | 淘天 | Flink + Fluss 湖流一体 | 点查 P99 800ms→5ms，IO 成本 −67%，1.4 PB |
| [淘宝反作弊](https://juejin.cn/post/7702841455874064438) | 淘天 | Fluss 作实时上下文 + 增量图计算 + Agent 编排 | 端到端 P95 < 3s，+5pt 召回 |
| [客服 L1 自动化](https://www.ibm.com/new/product-blog/how-thunai-automates-customer-support-with-ai-agents-and-ibm-confluent) | Thunai × IBM Confluent | Kafka 事件流 + 向量库 + 多 Agent | 70–80% 工单自动解决 |

## C 三条最值得引用的细节

- **央视解说**：名次与奖牌以官方确认为准，证据不足时不出结论。Flink 状态记录比赛阶段、逐枪成绩与领先关系。
- **淘宝反作弊**：同一份数据会在流链路、批链路与故障恢复中重复推理。计划用 Fluss KV 缓存结果，Token 降幅超过 60%。
- **AI 巡店**：先筛证据，再调模型。一路 25fps 每天约 216 万帧，多数静止或重复。

## D 官方示例与 SQL 化入口

| 入口 | 形态 | 说明 |
| --- | --- | --- |
| [Flink Agents 示例](https://github.com/apache/flink-agents/tree/main/python/flink_agents/examples) | Python 代码 | quickstart 评论分析、rag、多模态、decision_models |
| [AGENT_RUN](https://help.aliyun.com/zh/flink/realtime-flink/flink-sql-calls-agent) | Flink SQL 表值函数 | 阿里云 VVR 11.8+，PARTITION BY 让同 key 落同一实例 |
| [CREATE AGENT](https://docs.confluent.io/cloud/current/ai/streaming-agents/streaming-agents-examples.html) | Flink SQL | Confluent 侧，AI_RUN_AGENT 逐行调用 |
| 官方 Quickstart | 文档 | 单 Agent、多 Agent、ReAct、YAML |

## E 两种典型架构形态

```flow LR
(事件流) -> [CEP / 窗口门控]: 只放行约 1%
[CEP / 窗口门控] -> (Agent 算子): 命中上下文
[(Flink Keyed State)] --> (Agent 算子): 历史与状态
(Agent 算子) -> [LLM 推理]
(Agent 算子) -> [工具调用]
(Agent 算子) -> (动作: 拦截 / 工单 / 告警)
```

核心原则：不是每条事件都调 LLM。Flink 处理确定性的 99%，Agent 只推理需要判断的 1%。三种模式见 [AWS Builder Center](https://builder.aws.com/content/39iEDP7GmLo1PuIed1DJ7CGarXi/when-your-stream-processing-pipeline-can-think-apache-flink-agents-aws)。

## F 案例到缓存对象的映射

| 缓存对象 | 案例中的对应物 | 暴露的问题 |
| --- | --- | --- |
| act 工具结果 | 淘宝图查询与模型打分 Tool；巡店证据帧 | 同一 Tool 被多链路重复调用，帧大量重复 |
| rag 检索证据 | 短剧切片与 Embedding；文档 CDC | 全量重算代价高，缺少价值判断 |
| resp 最终回答 | 淘宝 Fluss LLM 缓存；Thunai 重复问题 | 只有按 Key 缓存与哈希去重 |
| plan 计划模板 | 反作弊的运行时编排 | 复用后能否执行缺少验证 |

:::callout warn 研究缺口
工业界现有做法是 KV 缓存、哈希去重、前置过滤。缺少统一的价值判断：该不该复用、复用前是否验证、何时淘汰。
:::

## G 研究侧证据

| 工作 | 关注点 |
| --- | --- |
| [StreamAgent](https://www.emergentmind.com/topics/streamagent) | 流原生 agent 架构，扩展到感知与执行 |
| StreamingClaw | 面向具身与自动驾驶的实时感知、决策与行动，缺长期多模态记忆 |
| IPIBench / IPI-Agent | 连续流下的主动交互，触发不稳定 |
| [分层记忆与事件图（IEEE 2026）](https://ieeexplore.ieee.org/document/11476389) | 分层记忆 + 事件图，LLM 决定存储与检索 |
| [AgileLog（SOSP '26）](https://dl.acm.org/doi/abs/10.1145/3830418.3843875) | 数据流上 Agent 的共享日志 |
| AOI / 两朵云 | 观测改为事件触发，截图循环需 3–5 秒 |

## H 建议的引用写法

:::callout ok 三步
先用央视解说、淘宝反作弊、Thunai 客服三条例证说明场景真实。再指出重复处理普遍存在。最后落到价值建模与生命周期控制的缺口。
:::
