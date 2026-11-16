# 第一章设计评审工作底稿（内部）
> 轮次：R1 证据收集后；后续会继续修订，不作为最终交付。

## 总判断
- 方案潜力：中上；当前初稿：尚未闭合。
- 核心洞察正确：缓存价值不是命中率/相似度，而是动作、请求、依赖、负载条件下的净价值；验证应是一等动作；刷新应带依赖级联。
- 最大问题：范围过宽、验证负担过重、数学与系统原子性未钉死、与最新预印本的新颖性碰撞被低估。

## 必须保留
1. 动作条件净价值（REUSE / VERIFY_THEN_REUSE / RECOMPUTE）。
2. 权限、模型、版本硬门；已知依赖范围内的失效不变量。
3. 刷新级联与共享后台预算这一可能的核心创新。
4. 决策后悔、风险预算兑现、净收益、尾部风险、负结果区间。
5. 最小 Flink 原型：keyed state、timer、checkpoint、rescale；不承诺生产级 exactly-once。

## 必须修复
### 数学
- 用完整路径成本 C_a(r)，而不是 W_i - C_l；明确共同成本、验证失败回退、假阳性/假阴性。
- N_i(H)S_i 必须改为逐请求边际安全覆盖；否则重叠条目/跨层路径重复计数。
- 刷新级联中的 rebuild 区分一次性重建与每请求重算，不能无条件乘 m_j(H)。
- 风险：拆成单次返回门 + 窗口/域预算；q_auth/q_model 不得同时当硬门和软概率。
- 版本比较使用依赖快照/版本域/摘要，不用通用 >=；区分 INVALID 与 UNAVAILABLE。
- 请求级动作、条目状态动作、后台任务动作拆成三类变量/时间尺度。
- 对偶价格只作为可解释资源信号；小规模 ILP Oracle 量化 greedy gap。
### 系统
- 读路径、版本失效、后台完成必须在同一序列化域或用 CAS/fencing；entry_generation + base_dependency_snapshot + auth_epoch。
- EVICT 仅删除 payload，不得自动逻辑失效下游；保留 dependency truth ledger/tombstone。
- 权限过滤和租户分区要在 ANN 前；避免候选存在性侧信道。
- version event 需 source_sequence、content_digest、event_id；watermark 不等于更新完整性。
- 全局预算不能只靠 tenant-keyed state；需配额/协调器或有界超支声明。
- 热门 key、backpressure、资源隔离、状态爆炸是 P0 风险。
### 实验
- P0 先测复用率、C_v/W、版本事件、级联乘数；不能先做复杂模型。
- 固定 matcher/retriever/verifier/candidate set；2x2 RP1/RP2；Oracle；人工/执行标签。
- 一个真实/半真实 end-to-end 场景优于五个拼接数据集。
- 总成本账本：签名/embedding/ANN/judge/回放/刷新/存储/恢复/探索。
- 报告漏复用与验证假阴性，不只报告错误复用。
- 冷启动、时间切分、cluster bootstrap、精确二项 CI、预注册阈值。
### 新颖性
- 2611.01077 已压缩 RP1 的“reuse risk + budgeted cache set”空间；必须区分跨层依赖与 lifecycle。
- FinCacheServe 已覆盖单对象依赖一致 + 效用管理；Krites 覆盖异步验证提升；Workflow-aware 覆盖依赖淘汰；ChurnBench 覆盖刷新调度重要性。
- 可能仅剩的强差异：刷新级联 + 共享验证/刷新预算 + 异步版本一致性；或跨层路径的联合价值/预算分配。
- 不要把“四类对象统一接口”当主创新；把 act/plan 降为适配器/扩展验证。

## 评分草案
- 问题价值 4.5/5
- 洞察/定位 3.8/5
- 当前设计自洽 2.8/5
- 数学严谨 2.7/5（设计稿 3.5/5）
- 新颖性 2.6/5（不同定位区间 3.5/5）
- 系统完整 3.0/5
- 实验可信 2.6/5（设计稿 4/5）
- 4个月可行性 2.3/5（收缩后 4/5）
- 初稿可读性 1.4/5
- 总评：C+/B-，边界可过，需重构；方案而非当前文本有 B 潜力。

## 评估反思
- 不能因初稿写法粗糙就否定设计；20261111 设计稿本身更成熟。
- 不能把所有最新预印本视为已确立事实；它们主要压缩“首创”空间，不证明本方案无效。
- 不能要求硕士做生产级一致性；但必须给出可执行的最小不变量。
- 不能让“统一”变成四个 enum 共用一个接口；需要证明同一边界下共享预算产生交互。
- 不能过度追求端到端强化学习/全局最优；可解释、可测、可回退的预算化控制更适合硕士。
- 不能把当前 1.4 的未来时当成实验结果；但设计稿有实验协议，应评价其可执行性而非缺结果本身。

## R2 更新：最新碰撞与推荐主线
- arXiv:2611.10418v1 SafeCache（2026-11-07）：已把 direct reuse / selective verification / regeneration 作为 safety-conditioned routing，并在 verifier-call budget 与 unsafe-reuse target 下校准。RP1 的动作条件价值 + 验证预算不能作为独立首创。
- arXiv:2605.27494 GroundedCache（2026-05-26）：query similarity、evidence overlap、source-version validity、answer support 四门联合判断，直接覆盖证据—回答安全复用的单对象版本。
- arXiv:2611.01077v2 Multi-Turn Semantic Caching：reuse risk + budgeted cache set + offline/online learning，进一步压缩 RP1 与单纯集合准入的新颖性。
- arXiv:2605.20630 Temporal Semantic Caching in Plan-Execute Pipelines：参数丰富查询、时间有效性、dependency-aware workflow，覆盖部分 agent/plan/tool 叙事。
- arXiv:2610.17544 Many Steps into One：简单成功率计数器是差的变化检测器，支持版本/证书重启而不是仅历史安全率。
- arXiv:2607.00394 SOLAR：在线 semantic cache replacement with switching costs, competitive/regret bounds；LRU/LFU 可能不如 FIFO，baseline 必须包含 FIFO/SOLAR 类。
- arXiv:2603.28795 StepCache：step-level reuse + lightweight verification + selective patching，说明部分复用/修复也不是完全空白。
- arXiv:2610.21394 Matoi：reusable consequence evidence、current authority、durable history 分离；支持权限/证据/重验证边界。
- arXiv:2611.17316 CoReMem：prospective valuation / cost-internalizing memory；说明未来价值估计是活跃方向。
- arXiv:2610.28577 Cache Engineering for Agents、2611.08638 MORTIS 等主要针对 KV，不是逻辑缓存；作为边界，不作为本文创新。

## R2 推荐主线
面向版本化 RAG 的证据—回答跨层可修复复用：风险校准与验证预算联合控制。
- 核心不是四类对象统一，而是文档→证据→回答两阶段动作对：证据 REUSE/VERIFY/REFRESH，回答 REUSE/REGENERATE。
- 研究现象：证据风险不能替代最终答案风险；部分证据可保留但回答必须重生成或修复。
- 核心机制：按最终答案边际风险/决策边界价值分配验证预算，允许跨层 salvage；固定容量/淘汰用简单基线。
- 主实验：版本变化下的 fresh-goodput、证据/答案正确性、无必要重生成比例、验证税、尾部延迟。
- 3 个核心 claim：C1 证据风险不等于最终答案风险；C2 联合动作优于两层独立门控；C3 按最终答案边际风险分配验证优于按层平均或不确定性排序。
- 可保留 resp/rag 完整，act/plan 仅适配器/负结果，Flink 仅事件状态 microbenchmark。
- 这样与 FinCacheServe（全有或全无依赖门）、FreshCache（独立层预算）、vCache/SafeCache（单层答案路由）、GroundedCache（每次重检索证据门）、Krites（异步验证）有可陈述差异。

## R2 反思
- 魔鬼评审的 2.08/5 按 CCF-A 口径有参考价值，但对硕士论文过于严苛；应按方案潜力 + 当前可执行性分开评分。
- Dewey 的 B 方案比共享验证/刷新预算更适合四个月：它把跨层动作和最终答案风险作为主线，而不是要求完整八动作控制器。
- 但 B 仍需解决：证据风险传播、部分证据的动作定义、验证器误判、版本事件真实性、FinCacheServe/FreshCache 基线公平性。
- 不能把跨层写成四个 enum；必须用两阶段动作对与路径成本/最终答案风险证明交互。
- 不能把 Flink 作为核心创新；用现有 flink-jobs 的 CustomerSupportAgentJob/PlanActSupportJob 作为试验台，降低工程量。

## R3 更新：Planck 最新碰撞审计与最终取舍
- 新增必引预印本：SafeCache(2611.10418)、GroundedCache(2605.27494)、MT(2611.01077)、TemporalSC(2605.20630)、CoReMem(2611.17316)、Matoi(2610.21394)、GenCache(2511.17565)、Many Steps(2610.17544)、SOLAR(2607.00394)、StepCache(2603.28795)。
- RP1 的多轮 reuse risk + budgeted cache set 已被 MT 覆盖；一般 selective revalidation 已被 Matoi/GenCache 覆盖；prospective valuation 已被 CoReMem 覆盖；SafeCache 直接覆盖 direct reuse/verify/regenerate + verifier budget。RP1 单独只能评中弱。
- 真正尚未直接覆盖的清晰空位：跨对象 refresh cascade、下游命中损失、共享刷新/验证预算下的合并刷新；其次是 David 推荐的证据—回答可修复复用与最终答案级风险预算。
- 推荐合并：主线不是四类对象全量，而是版本化 RAG 的“证据—回答可修复复用 + 级联感知刷新/预算控制”。这既保留可选 refresh cascade（Planck）又保留高可行性的两阶段动作对（Dewey）。
- 最小范围：rag→resp 强制；act→resp/plan 或 plan→act 选一条；四类接口保留，act/plan 仅扩展验证。
- 关键判定：若级联乘数 M(i) 中位数 <1.2、联合动作翻转 <5%、或去除级联后净收益无显著差异，则 refresh cascade 降级为负结果；若部分证据 salvage 区域 <15% 或联合动作不优于独立层，则跨层主线降级。
- 论文主 claim 只保留 3 条：C1 证据风险不等于最终答案风险；C2 联合可修复复用优于独立层门控；C3 在同预算下，级联感知的刷新/验证分配优于 TTL/独立预算/不确定性排序。
- 现有 flink-jobs 工程可作平台：CustomerSupportAgentJob 已有 user-keyed state、exact-match cache、TTL、short-term memory、checkpoint；PlanActSupportJob 有 plan/tool 执行但无缓存。用它们降低工程量，不要从零搭建完整 Flink 平台。
- 反思：Planck 更偏“系统/新颖性最大”，Dewey 更偏“硕士可完成/证据闭环”。最终推荐 Dewey 的 B 作为主线，嵌入一个 Planck 式 refresh-cascade 判定实验；不推荐继续当前四类对象 + 八动作 + 全闭环。
