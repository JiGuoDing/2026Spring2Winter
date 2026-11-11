---
template: doc
theme: auto
lang: zh
title: AgenticCache：用异步缓存复用具身 Agent 的计划转移
subtitle: MLSys 2026 · plan cache · 2-gram 计划局部性 + 后台 LLM 校正
source: Hojoon Kim, Yuheng Wu, Thierry Tambe, "AgenticCache: Cache-Driven Asynchronous Planning for Embodied AI Agents," MLSys 2026, arXiv:2604.24039v1.
outline: right
mode: light
---

AgenticCache 缓存的不是回答，也不是 KV。它缓存具身 Agent 的高层计划转移 $\langle P_i\rightarrow P_j\rangle$，并在后台异步调用 LLM 校验缓存。

## A 论文卡片

| 项 | 内容 |
|:--|:--|
| 完整题名 | AgenticCache: Cache-Driven Asynchronous Planning for Embodied AI Agents |
| 作者 | Hojoon Kim、Yuheng Wu、Thierry Tambe |
| 机构 | Seoul National University；Stanford University |
| 发表 | MLSys 2026 Research Track Oral |
| 公开版本 | arXiv:2604.24039v1，2026-04-27 |
| 代码 | [hojoonleokim/MLSys26_AgenticCache](https://github.com/hojoonleokim/MLSys26_AgenticCache) |
| 缓存对象 | 高层计划之间的转换，例如 `GoGrasp → Transport` |
| 缓存键 | 前一个计划 $P_i$ + 当前状态元数据范围 |
| 更新机制 | 后台 LLM 异步确认、纠错和更新计数 |
| 实验对象 | 四个多 Agent 具身 benchmark × GPT-5、GPT-5-mini、GPT-5-nano |
| 主要结果 | 平均成功率约 +22 个百分点；时延 -65%；token -50% |
| 证据边界 | 主要集中在结构化操作与运输任务；无形式化保证 |

**一句话定位：** 它把计划局部性做成短周期程序性记忆，用异步 LLM 校正来避免纯缓存造成的陈旧执行。

## B 问题：每步都问 LLM

具身 Agent 的循环是：

```flow LR
(Observe) -> (Plan with LLM) -> (Act) -> (New observation)
```

同步规划要求 Agent 等 LLM 返回后再执行。论文报告：

- 超过 70% 的运行时间花在 LLM 规划查询。
- 长程任务的 LLM 成本随轨迹长度近似线性增长。
- 多 Agent 并发时，同步等待进一步扩大时延。

已有异步方案仍有问题：

| 方案 | 思路 | 主要问题 |
|:--|:--|:--|
| Parallel planning-acting | 执行当前计划时预取下一计划 | 环境变化会让预取计划失效 |
| Speculative planning | 小模型先提出动作，大模型验证 | 错动作的回滚成本高，仍需逐步调用 LLM |
| 纯 pattern cache | 直接复用历史计划 | 忽略状态，容易在动态环境出错 |

AgenticCache 的机会来自另一个观察：

> 具身任务的计划转移具有强局部性。下一步通常只由少数常见转换决定。

## C 计划局部性

论文对不同状态的下一计划做了 2-gram 分析。

代表性现象：

- `GoGrasp target` 之后，`Put into container` 出现约 59.7%。
- 许多计划只有少量常见后继。
- 长程任务中存在稳定的“抓取 → 运输 → 放置”模式。

但纯局部性不够：

```flow LR
(Plan Pi) -> [Frequent successor Pj]
[Frequent successor Pj] -> [Execute]
[Execute] -> {State still valid?}
{State still valid?} -> (Continue): yes
{State still valid?} -> [Rollback or replan]: no
```

失败例子：

- 另一 Agent 已经拿起目标物体。
- 目标物体被移出可及范围。
- 共享资源被占用。
- 多 Agent 会合点发生变化。

因此必须做混合规划：

```flow LR
(Current plan) -> (Cache lookup)
(Cache lookup) -> [Instant reuse]: hit
(Cache lookup) -> [LLM fallback]: miss
[Instant reuse] -> (Background LLM check)
(Background LLM check) -> [Confirm]: continue
(Background LLM check) -> [Correct]: replace plan
```

## D 缓存结构

每个具身 Agent 维护自己的缓存。缓存项是一个计划转换：

$$
\langle P_i\rightarrow P_j\rangle.
$$

每个转换还保存状态元数据范围，例如：

| 元数据 | 示例 |
|:--|:--|
| Steps | 当前 episode 步数 |
| Held items | 当前持有物体数 |
| Finished subgoals | 已完成子目标数 |
| Visited rooms | 已访问房间数 |

不同 benchmark 使用不同字段。论文主要采用物体计数和任务进度。

### D.1 缓存项

```tree
Plan transition Pi -> Pj
  Metadata ranges | observed min to max
  Count C | how often the transition occurred
  Candidate count Ncand | candidate appearances
  Confirmed count Nconf | LLM confirmations
  Importance I | Nconf / Ncand
  Score S | C × I
```

### D.2 候选过滤

给定上一计划 $P_i$ 和当前状态 $s_t,h_t$：

$$
\mathcal{F}(P_i)=\{P_j\mid s_t\in[s^{\min}_{ij},s^{\max}_{ij}],\ h_t\in[h^{\min}_{ij},h^{\max}_{ij}]\}.
$$

只有元数据范围与当前状态兼容的转换才进入候选。

### D.3 评分

下一计划选为：

$$
P^*=\arg\max_{P_j\in\mathcal{F}(P_i)}S(P_i\rightarrow P_j).
$$

评分为：

$$
S(P_i\rightarrow P_j)=C(P_i\rightarrow P_j)\cdot I(P_j).
$$

两个因子分工明确：

- $C$ 是局部信号：这个转换出现得多不多。
- $I$ 是全局信号：目标计划被 LLM 确认的可靠程度。

$$
I(P_j)=\frac{N^{\mathrm{conf}}(P_j)}{N^{\mathrm{cand}}(P_j)}.
$$

这类似分支预测：

- 只看局部频率会过度利用模式。
- 只看全局可靠性会忽略具体上下文。
- 乘积同时奖励“常见”和“可靠”。

## E 异步更新器

后台 Cache Updater 不阻塞执行。它负责校验缓存是否正确。

### E.1 确认与纠错

```flow LR
(Active plan Pi) -> [Background LLM query]
[Background LLM query] -> (Predicted plan Pj)
(Predicted plan Pj) -> {Seen in executed trajectory?}
{Seen in executed trajectory?} -> [Confirm and add counts]: yes
{Seen in executed trajectory?} -> [Correct active plan]: no
[Confirm and add counts] -> (Cache refined)
[Correct active plan] -> (Cache refined)
```

**确认：**

- LLM 返回的计划已在最近执行轨迹中出现。
- 增加该转换的 transition count。
- 增加目标计划的 confirmation count。
- 当前计划继续执行。

**纠错：**

- LLM 返回一个最近轨迹中没有的计划。
- 新增或更新 `P_t → P'_t+k`。
- 降低错误转换的计数。
- 若新计划可执行，立即替换当前计划。

### E.2 查询抑制

减少无效 LLM 查询：

| 抑制条件 | 行为 |
|:--|:--|
| Confirmation suppression | LLM 确认当前计划后，等该计划执行完再查询 |
| Correction suppression | 计划被纠正后，等替代计划执行完再查询 |

这样避免两个问题：

- 重复确认同一个正在执行的计划。
- 多条纠正相互冲突，导致策略抖动。

### E.3 缓存 miss

缓存 miss 包括：

- 当前状态没有匹配的 `P_i`。
- 所有后继都被状态元数据过滤掉。

miss 时：

1. 高层规划暂停。
2. Updater 请求 LLM 生成新计划。
3. 新计划插入缓存。
4. Agent 恢复执行。

### E.4 异步时序

```timeline v
t0 | 查询 LLM | 记录上下文与当前计划
t0+1..k | 继续执行 | 缓存链式提供计划
t0+k | LLM 返回 | 与已执行轨迹比较
确认 | 增加计数 | 继续当前计划
纠正 | 替换计划 | 更新缓存并抑制查询
```

其中，$k$ 表示 LLM 返回前经历的环境步数。它不是预先固定的 speculative depth。

### E.5 离线预热

可选预填充：

- 从 GPT-5 在 OOD 任务上的成功轨迹提取 plan transitions。
- 每个 benchmark 只用 1–4 个训练 episode。
- 预填充改善前几个决策。
- 空缓存也能在线启动，冷启动仍能获得大部分收益。

## F 主实验结果

实验覆盖四个多 Agent benchmark：

| Benchmark | 规划模态 | Agent 数 | 协调 | 环境 |
|:--|:--|--:|:--|:--|
| CoELA@TDW-MAT | LLM | 2 | 分散 | ThreeDWorld |
| COMBO@TDW-COOK | VLM | 2 | 分散 | ThreeDWorld |
| COMBO@TDW-GAME | VLM | 4 | 分散 | ThreeDWorld |
| COHERENT@BHV-1K | LLM | 5 | 集中 | 图结构 |

主结果：

- GPT-5 与 GPT-5-mini 的成功率为 84%–100%。
- GPT-5-nano 的成功率为 68%–100%。
- TDW-GAME 上 AgenticCache 对三种模型均为 100%。
- 同一 benchmark 上，parallel planning 为 0%–22%。
- speculative planning 为 11%–33%。
- 12 个配置平均：时延约 -65%，token 约 -50%，成功率平均约 +22 个百分点。

```chart bar horizontal unit=hours
| Baseline | AgenticCache
TDW-MAT | 41.34 | 22.27
TDW-COOK | 12.86 | 1.75
TDW-GAME | 7.88 | 1.11
BEHAVIOR-1K | 3.36 | 1.55
```

图表使用 GPT-5 结果。TDW-COOK 的时延从 12.86 h 降到 1.75 h，成本从 21.0 美元降到 4.4 美元。

### F.1 平均值要怎样读

“平均成功率 +22”指跨配置的平均绝对提升，约为 22 个百分点。它不是每个任务都提升。

实际表现有明显任务差异：

- TDW-MAT 上 GPT-5 从 90.23% 降到 88.64%。
- TDW-MAT 上 GPT-5-nano 从 71.59% 降到 67.95%。
- 强收益主要来自多 Agent 协调更困难的 TDW-GAME 和 TDW-COOK。

因此不能写成“所有环境都提升 22%”。

## G 冷启动、命中率与消融

### G.1 冷启动

不使用离线预填时：

- 标准任务：时延降低 1.4–1.9×，成本降低约 1.35×。
- 长程任务：时延降低 1.3–1.9×，成本降低 1.4–1.8×。
- GPT-5-nano 长程成功率 42.8% → 62.8%。
- GPT-5-mini 长程成功率 62.8% → 69.4%。
- GPT-5 长程成功率 82.2% → 80.6%。

冷 miss 主要造成早期停顿，不消除总体收益。GPT-5 的小幅下降来自陈旧转换和多 Agent 协调冲突。

### G.2 命中率

- TDW-GAME：大于 66%。
- BEHAVIOR-1K：至少 73%。
- TDW-COOK：39%–46%，计划多样性更高。
- TDW 环境 miss 回退需要 9–29 秒。
- BEHAVIOR-1K miss 回退需要 5.2–7.1 秒。

计划局部性越强，缓存收益越大。miss 回退很贵时，应优先提升缓存覆盖。

### G.3 缓存规模

- 每个 Agent 保存约 35 个转换。
- 内存占用约 0.1–1 KB。
- 转换数在约 1500 步后明显放缓。
- 缓存从频繁新增转向细化现有条目。

这说明缓存很小，但也说明论文未测试容量压力下的显式淘汰策略。

### G.4 消融

| 组件 | 影响 |
|:--|:--|
| Static cache | 平均成功率约 24% |
| Cache updates only | 成功率提升 12% |
| Plan replacement only | 平均提升 35% |
| Full system | 平均成功率 70.7% |

更新和替换解决不同问题：

- 更新修正 transition 统计和元数据。
- 替换及时中止错误的当前计划。

## H 评价、边界与第一章用法

### H.1 主要贡献

- 识别具身任务中的 2-gram 计划局部性。
- 把计划转换做成运行时缓存对象。
- 用状态元数据范围过滤不适配的转换。
- 用局部频率乘全局可靠性的评分选择计划。
- 用异步 LLM 更新实现低延迟纠错。
- 在四个多 Agent benchmark 和三种模型规模上评估。

### H.2 与其他缓存的关系

| 缓存类型 | 缓存对象 | 生命周期重点 |
|:--|:--|:--|
| vCache / MVR-cache | 查询回答 | 语义命中与错误率 |
| TVCACHE | 工具结果 | 执行历史与环境状态一致 |
| Agentic Plan Caching | 任务级计划模板 | 计划复用与模型适配 |
| AgenticCache | 计划转移 | 局部频率、状态过滤、异步纠错 |

AgenticCache 的独特处是：

> 它不是缓存一张全局任务计划，而是缓存执行过程中的短期 `Pi → Pj` 转移。

### H.3 关键风险

| 风险 | 影响 |
|:--|:--|
| 只建模 2-gram | 延迟依赖和长程计划结构可能丢失 |
| 状态用 min–max 范围 | 非凸状态区域可能被错误覆盖 |
| 计数无显式衰减 | 环境变化后旧频率可能长期占优 |
| 无容量和淘汰实验 | 真实长部署下的 stale population 未评估 |
| 每个 Agent 独立缓存 | 多 Agent 冲突只能靠 LLM 事后纠正 |
| 缺少版本与资源预留 | 共享资源争用可能出现死锁或重复劳动 |
| 依赖计划局部性 | 开放式探索和创造性任务可能失效 |
| 没有形式化保证 | 成功依赖经验评估和 benchmark 结构 |
| 主实验使用 OpenAI API 成本 | 成本结果与 2025 年 10 月价格绑定 |
| 离线预填来自同 benchmark 轨迹 | 跨域冷启动收益仍有限 |

### H.4 多 Agent 失效模式

论文明确承认协调点问题：

- 一个 Agent 按本地高频转换行动。
- 另一个 Agent 因不同观察偏离计划。
- 会合点错配，出现重复劳动或 handoff 丢失。
- 共享区域被多个 Agent 同时占用。
- Updater 可能在数步后才纠正。

这说明局部缓存价值不等于全局任务价值。多 Agent 调度需要资源预留和全局协调。

### H.5 对第一章的价值

AgenticCache 可以直接作为 `ctx/act` 之间的计划缓存基线。

1. **缓存键设计**：`previous_plan + state_ranges` 是结构化依赖键。
2. **异步刷新**：后台 LLM 校正可映射为 REFRESH 动作。
3. **陈旧纠错**：确认/纠正机制对应 `q_stale` 与 `C_refresh`。
4. **评分函数**：`C × I` 是“局部频率 × 全局可靠性”的价值近似。
5. **冷启动**：离线轨迹预填与在线学习可以形成混合缓存。
6. **多 Agent 冲突**：可作为缓存价值中加入全局协调成本的案例。

### H.6 适合扩展的研究问题

- 用版本向量和资源占用状态替代 min–max 范围。
- 加入 transition count 的时间衰减和容量淘汰。
- 从 2-gram 扩展到 3-gram、层级子程序或依赖图。
- 把多 Agent 资源预留纳入缓存选择。
- 用学习模型替代 `C × I` 手工评分。
- 在跨域任务上评估离线预填的可迁移性。
- 把全局任务成功率与缓存局部收益联合建模。

```callout tip 第一章建议
把 AgenticCache 放在“计划/工作流复用”层。它提供了异步刷新和 stale correction 的工程模板，但还没有解决容量、版本、陈旧分布和多 Agent 全局价值。第一章可以把这些缺口纳入依赖感知缓存生命周期。
```

### H.7 最终判断

AgenticCache 的核心不是“缓存答案”，而是“缓存计划的短期转移”。

它证明了：

- 具身任务存在可利用的计划局部性。
- 计划缓存必须有状态过滤和异步校正。
- 缓存更新与计划替换可以共同提升成功率。

它也暴露了新的研究问题：

- 局部高频并不等于全局最优。
- 计划局部性依赖任务结构。
- 多 Agent 共享资源需要全局协调。

**原始材料：** [arXiv:2604.24039](https://arxiv.org/abs/2604.24039) · [代码与 artifact](https://github.com/hojoonleokim/MLSys26_AgenticCache) · [MLSys 2026](https://mlsys.org/virtual/2026/poster/3583)