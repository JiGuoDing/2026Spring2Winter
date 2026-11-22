# D 数据集与 Trace 选型：两次讨论的整理稿

> 整理对象：
> 1. `Design/20261118_第一章数据集选型与实验映射分析.md`（2026-11-18 调研，2026-11-20 追加"补充记录"）
> 2. `Design/20261120_FreeInference_Agentic_Trace_数据集评估.md`（2026-11-20 新建）
>
> 说明：本文只做提炼与对照，不引入两文之外的新数据；凡两文标注"未核实/部分核实/查无此物"的，本文照原样保留该状态，不升级为事实。

---

## 0. 一页结论

1. **22 个候选里只有 3 个能当实验主干**：ABCD（客服政策主场景，覆盖 resp/rag/act/plan 四类对象 + 逐轮动作真值）、ToolBench + StableToolBench（act 主数据，工具名/参数/返回齐全、可本地回放）、Chutes 一年生产 trace（真实到达、容量、TTL、热点漂移）。
2. **三个必须补的缺口**：vCache SemCache（resp 语义缓存的"错误率—命中率"标准口径，可与 vCache/Krites 对齐）、ChurnBench（文档/数据版本 + append-only ledger 真值，E5 受控平台）、FiscalQA Pro（真实"条文—版本—生效区间"事件，E5 外部效度）。
3. **没有任何公开数据集同时具备"真实到达 + 重复分布 + 四类对象结构 + 版本事件 + 可验证真值"**。所以数据方案是**三层拼装**：到达层借 trace、内容/重复层借任务数据集、版本层借版本基准或受控注入；每层"哪些字段是构造的、偏差多大"必须写进论文。
4. **FreeInference Agentic Trace 被明确降级**：16 周 / 120 万请求 / 121 万工具调用，规模与字段在公开 trace 里最好，但只有元数据——无 prompt/response 文本、无工具返回、无参数值、无文档版本与权限、无缓存正确性真值。定位从"候选主数据"改为 **T5 到达-会话-工具层 + 外部效度层**，不改变 ABCD-Cache v0.2 的主实验台定位。
5. **它只能支撑"缓存价值/失效/依赖"的统计层，不能支撑语义层**：块级前缀复用、上下文变更诱因、空闲/TTL 先验可算；语义等价、正确命中、真依赖图与版本闭包都算不出来。
6. **对第一章 1.1 最有价值的不是"选了哪个数据集"，而是几条可直接引用的现象量级**：缓存读占 token 97%/成本 73%、15 分钟保留捕获大部分复用但近全复用需约一天且存储 25.6×、56% 会话发生过上下文 mutation、静态 RAG 2.7% vs 版本化语料 99.1%、是刷新调度而非缓存年龄决定陈旧性。这些是"问题存在且值得做"的证据，不是本文方法的证据。

---

## 1. 两次讨论谈了什么（时间线）

| 时间 | 动作 | 产出 |
|---|---|---|
| 2026-11-18 | 对第一章初稿 1.4 节列出的**22 个数据集**做 5 路并行核对（resp/服务流、act/工具轨迹、rag/版本化语料、新兴业务 trace、workload 方法学），逐条查论文、官方仓库、HF 数据卡、许可证 | 22 项判定表；Tier A/B/C/D 分级；6 条身份纠正；四类对象×数据源映射；A–F 实验映射；三层拼装协议与效度威胁；开工复核清单 |
| 2026-11-20 | 对 **FreeInference Agentic Trace** 做专项深评（GitHub README、`release/schema.py`、18 页论文 PDF、HF 数据卡、OpenData 官网） | 独立评估文档：字段级清单、"明确没有的字段"、论文 7 条关键发现、6 类用途及边界、5 类明确不能支撑的部分、prompt 可得性状态 |
| 2026-11-20 晚 | 把 FreeInference 结论回写进 11-18 文档（追"补充记录"），并把定位收敛为 T5/到达-会话-工具层 | 两份文档结论一致：FreeInference 是补充轨，不是主实验台 |

**讨论的实质**：不是"挑一个最好的数据集"，而是**在公开数据现状下设计一套可辩护的拼装方案，并给每个数据集划死"能借什么、不能借什么"**。

---

## 2. 评估维度：先定标准，再评数据

六条筛选标准（S1–S6），每条都绑定到具体实验，避免"看着有用"式选型：

| 标准 | 含义 | 对应实验 |
|---|---|---|
| S1 能否形成请求流 | 有到达时间戳，或可按会话/事件顺序重放并赋逻辑时间 | E2 / E3 / F |
| S2 是否有可统计的重复 | 精确重复、等价类、模板重复、同工具同参数重复，且非自造 | E1 / A |
| S3 是否覆盖四类对象 | `resp` 问答、`rag` 证据、`act` 工具结果、`plan` 计划片段 | E1–E3 |
| S4 是否有可验证真值 | 程序化 reward / 动作级标签 / qrels / 人类偏好 / ledger | A / B / D / E |
| S5 是否有时间演化与版本 | 来源更新时间、版本区间、TTL/新鲜度标签，或可受控注入 | E2 / E5 |
| S6 许可与成本 | 公开可下载、许可清晰、单机/小集群可容纳 | 全程 |

**结论：没有数据集能全满足 S1–S6。** 所以选型原则变成"一个叙事主场景 + 一条真实流 + 一条语义缓存标准线 + 一个版本实验平台"，各自承担不同实验层，最后在 F 拼装。

配套的还有三层**重复/版本注入梯度**，用来控制"自造数据"的偏置：

- 重复注入：R0 有机重复（只留数据集天然存在的）→ R1 簇内重采样（只改次数不改相似度结构）→ R2 受控注入（λ∈{0,10,25,50}%，须报告"注入对相似度不高于 R0 中位数"，换改写模型重跑，λ=0 臂作下界）。
- 版本注入：U0 无更新（对照）→ U1 真实快照 → U2 合成 churn（区分 content-change 与 answer-affecting change）→ U3 近似碰撞探针。

---

## 3. 候选数据集全清单

### 3.1 22 个原始候选（逐项）

"版本/状态/依赖"列是本章最关心的一列：**它决定该数据集能不能碰第 3 章的失效与依赖实验**。

| # | 数据集 | 真实类型 / 来源 | 规模 | 结构（流/工具/文本） | 版本/状态/依赖信息 | 判定 |
|---|---|---|---|---|---|---|
| 1 | WebShop | 交互式环境 | 环境，未记录规模 | 无时间流；search/click 动作；reward 0–100 | 无版本、无状态快照 | 仅受控环境 |
| 2 | ShoppingBench + SN15 traces | AAAI'26 电商沙箱（250 万商品）+ Bittensor Subnet 15 竞技场 + 18K winners-only 轨迹 | 250 万商品 / 18K 轨迹 | 无时间戳；有工具 schema；ASR/CAR/judge | 无版本 | 备选（重复系赛题任务库构造性重复） |
| 3 | AgentSim ATC | SIGIR'26 Agent-Trace Corpus，静态轨迹 | 103,567 条 step 级轨迹；固定 199,968 篇文档 | step 时间（非用户到达）；search/synthesize；`tool_input/output`、`evidence_retrieved`、`execution_time_ms`、`error` | 固定语料可做 v0/v1 注入；grounding 真值 100% | 推荐（rag） |
| 4 | UserSim | **模拟器工具**，不是数据集 | — | 生成时可赋时间；mock 工具 | 可控 | 工具，非数据 |
| 5 | TicToc | ACL 2026 Findings《Your LLM Agents are Temporally Blind》标注集 | 5.6k | 静态标注，可注入时间 | 时间敏感决策标签；人类偏好 | 备选（verify 标签源） |
| 6 | PasarBench | **查无此物** | — | — | — | 删除 / 向导师确认 |
| 7 | FreeInference Agentic Trace | Harvard MadSys 等，Zenodo DOI 10.5281/zenodo.23903440，真实 agent 网关 trace | 12,002 会话 / 267 账户 / 1,186,582 请求 / 1,213,347 工具调用 / 209.2B 输入 token / 197.1B 缓存 token；16 周 | 墙钟毫秒时间戳；13 个人类 harness（+1 SWE-Bench 回放）；工具名/类别/参数类型骨架/时延/结果 token；16-token 块 ID | **无文档版本、无权限、无状态真值**；有 `transition`/`cause` 上下文变更类型 | 推荐（E3 / 到达层 / act 成本） |
| 8 | AitW | 静态 GUI 演示 | — | GUI 坐标动作，无 API 语义 | 无 | 不建议 |
| 9 | WorkArena++ | 交互环境 | 未记录 | 无时间流；浏览器动作；oracle 0/1 | KB 可改（弱版本能力） | 备选（E2 概念验证） |
| 10 | ToolBench | OpenBMB 静态标注/SFT，Apache-2.0 | 126,486 实例 / 469,585 次调用 | 无时间戳；工具名+参数+返回齐全，`toolenv/*/api.py` 可本地起服务 | **无工具版本**，需自建 schema 哈希/快照日期 | **核心（act）** |
| 11 | Mooncake trace | FAST'25 官方 `toolagent_trace.jsonl`，真实 trace | 23,608 请求 / 1 小时 / 毫秒时间戳 + 512-token 块 hash | 短窗真实流；无文本 | 无版本 | 推荐（E3 小规模回放） |
| 12 | Ko-Agent-Trajectories-1.0 | 韩语 SFT，模拟工具 | 未记录 | 结构重复；有模拟工具 | 无 | 备选（压测） |
| 13 | AgentBank | 2013–2023 时代 SFT 文本轨迹 | 未记录 | 文本内工具描述 | 无 | 不建议 |
| 14 | DeepResearchGym Search Logs | 真实 agent 搜索日志（已打散） | 14.44M 请求 / 3.97M 会话 | **仅会话内相对时间**，不能当全局流；仅检索 k | 无文档/答案/版本 | 推荐（query 重复与突发） |
| 15 | AReaL-tau2 / τ²-bench | 合成 SFT/RL | 未记录 | 无时间流；含 DB 快照；动作级可验证 reward | DB 可改造（可造状态/版本） | 推荐（E1 act/plan 真值） |
| 16 | ASQ | Agentic Search Queryset，静态轨迹 | 未记录 | 无时间戳；检索调用 | 无 | 推荐（rag 离线验证） |
| 17 | ABCD | ASAPP + Columbia，NAACL 2021，MIT | 10,042 条真人 role-play 对话 / 55 子流程 / 30 动作 / 125 槽值 / 政策库约 95 KB | 无时间戳（可重放）；动作序列 + 政策约束 | **政策库可拆文档并注入版本**；逐轮动作真值 | **核心（主场景）** |
| 18 | Nemotron-SFT-Agentic-v2 | 合成 SFT | 99 万条 | 模拟工具，结构重复 | 无 | 样本池 |
| 19 | MiroVerse-v0.1 | SFT，gated | 未记录 | 文本内工具 | 无 | 备选偏弱（许可混合 NC） |
| 20 | Chutes（A Year in LLM Serving） | 真实一年生产 trace，CC BY 4.0 | 6.12B 请求 / 314,970 用户 / 9,174 模型 / 875,921 实例 / 91 GB parquet | 1 年、秒/毫秒级；字段 `started_at/completed_at/it/ot/ct/ttft`；**无文本** | 无版本事件；有缓存命中 token `ct` | **核心（E2/E3）** |
| 21 | Search Arena 24K | 真实用户标注 | 24,069 多轮对话 / 12,652 张人类偏好票 | **有时间戳**；web search trace；2 个月窗 | 无版本 | 推荐（E1 resp/rag 质量） |
| 22 | ShareChat | Indiana University 五平台聊天语料（arXiv:2512.17843），CC BY-NC 4.0 | 未记录 | **是聊天语料，不是 trace**；无工具 | 无 | 备选（非商用，不可作主数据） |

### 3.2 需纠正的六个身份问题（影响引用，必须先改）

| 初稿写法 | 核实结果 | 处理 |
|---|---|---|
| ABCD（未写机构） | ASAPP Research + Columbia，NAACL 2021，仓库 `asappresearch/abcd`，MIT；Salesforce DialogStudio 只是再分发 | 引 Chen et al., 2021；不要写"Salesforce 数据集" |
| AgentSim ATC | 真实对象是 SIGIR'26《AgentSim: A Platform for Verifiable Agent-Trace Simulation》的 **Agent-Trace Corpus（ATC）**，与空管无关 | 引 arXiv:2604.26653，说明 ATC 全称 |
| TicToc | 与 SIGMOD'16 同名工作无关；要引 ACL 2026 Findings《Your LLM Agents are Temporally Blind》 | 写清版本，不要写成"语义缓存系统" |
| ShareChat | 不是印度社交平台服务 trace，是 IU 的五平台聊天语料，CC BY-NC | 改描述，明确"非 trace、非商用" |
| Mooncake tool-agent trace | FAST'25 `toolagent_trace.jsonl`（23,608 请求 / 1 小时 / 512-token 块 hash）与 2026 vLLM×Mooncake Codex/SWE-bench Pro 610 条轨迹是两个东西，后者许可冲突 | 分开写，优先用 FAST'25 官方 trace |
| ShoppingBench SN15 | ShoppingBench（AAAI'26 沙箱）+ Bittensor Subnet 15 竞技场 + 18K winners-only 轨迹，三样东西 | 拆开引用；"首轮请求重复度高"是赛题任务库导致的构造性重复 |

### 3.3 清单没写但必须补的（9 项）

| 数据集 | 补齐的缺口 | 规模/结构 | 版本/状态 | 优先级 |
|---|---|---|---|---|
| vCache SemCache（LMArena / SearchQueries / Classification / Combo） | resp 语义缓存"错误率—命中率"标准口径，与 vCache/Krites 直接可比 | LMArena 约 6 万（3,500 语义类，每类 1–23 变体，类 ID 即等价真值）；SearchQueries 约 15 万；Classification 45K、Combo 27.5K（**部分核实**） | 无时间戳、无版本、无权限 | ★★★ |
| ChurnBench | 版本更新 + append-only ledger 真值 + 刷新调度结论 | 合成企业数据织物（Postgres/MongoDB/限流 SaaS API/文档库），`--days 180 --seed 42` 可复现，MIT | **每变更写 ledger，任意时刻 T 的金标可重算** | ★★★ |
| FiscalQA Pro | 真实版本事件的外部效度 | 32,436 个"条文—版本"（法国税法 1938–2031，93 年）/ 69,208 条判决→条文版本链接 / 209 道专家题 / nugget 确定性评分 | **真实版本区间 + 生效时间** | ★★☆ |
| StableToolBench | ToolBench 的虚拟 API/缓存基础设施 | 工具，非数据 | 可固定工具快照 | ★★★ |
| AgentBench DBBench | 低成本执行环境；只读 SQL → act 精确键、状态版本 | 未记录 | 可造状态/版本 | ★★☆ |
| RAGTruth | 证据支持/幻觉的词级标签 | 未记录 | 无 | ★★☆ |
| StreamingQA | 带 `question_ts/evidence_ts` 的 14 年新闻语料 | 14 年 | **时间切片 `index(T)`** | ★★☆ |
| τ²-bench 原始环境 | AReaL-tau2 的来源，可验证动作奖励 | 未记录 | DB 快照可改造 | ★★☆ |
| Azure LLM trace / BurstGPT | 真实到达与会话结构（Chutes 不够时的备选） | 未记录 | 无 | ★☆☆ |

---

## 4. 选型结论：主数据集与角色分工

### 4.1 五个核心 + 三缺口

| 角色 | 数据集 | 覆盖 | 真值来源 | 许可 | 成本 |
|---|---|---|---|---|---|
| 叙事主场景 | ABCD | resp/rag/act/plan 全 | 逐轮动作真值（30 动作） | MIT | 低（静态 JSON） |
| act 主数据 | ToolBench + StableToolBench | act（+plan 轨迹） | ToolEval / 可回放 | Apache-2.0 | 中（虚拟 API 服务器） |
| 真实流与生命周期 | Chutes 一年 trace | E2/E3/F 系统层 | 无（仅系统指标） | CC BY 4.0 | 中高（91 GB，DuckDB） |
| resp 语义标准线 | vCache SemCache | resp（E1/A/B/D） | 等价类 + 错误率口径 | 数据公开；代码仓库偏 NC | 低 |
| 版本受控平台 | ChurnBench | rag/resp（E5） | append-only ledger | MIT | 低（docker compose） |
| 版本外部效度 | FiscalQA Pro | rag/resp（E5） | 金标条文 + 版本区间 | MIT + CC-BY-4.0 | 低（209 题，法语法律域） |
| 到达/会话/工具层 + 外部效度 | FreeInference Agentic Trace | 到达、会话、工具、成本校准 | 无 | CC BY 4.0 | 中（9 GB parquet；原始 108 GB） |

### 4.2 为什么是这几个（理由 + 对应第一章论证/实验）

- **ABCD**：公开数据中唯一同时具备"动作序列 + 政策约束 + 逐动作真值"的客服数据，天然对应 1.2 的四类对象。限制：众包 role-play 不是生产 trace，无时间戳/版本/ACL，政策库仅约 95 KB 做 RAG 会检索饱和（需展开成自然段 + 加干扰文档）。
- **ToolBench / StableToolBench**：可直接统计"工具名 + 规范化参数"的精确重复率，并把只读工具（列表/详情查询）与写操作分开——这是 1.2 对 `act` 的限定条件；StableToolBench 的虚拟 API 绕开 2023 年 API 大规模失效问题。
- **Chutes**：报告 prefix-cache 命中呈双峰、复用高度集中在短间隔（约 50% 在 0.1 s、80% 在 10 s、99% 在 15 min 内），**直接支撑"缓存年龄/保留窗口"建模**；但无 prompt/response 文本，只能做系统层与成本层。
- **vCache SemCache**：Krites 正是用 LMArena + SearchQueries 做 trace-driven 模拟（前 20% 历史前缀、后 80% 在线流、等价类 oracle、100 对人工审计），复用这套口径可与 vCache/Krites 可比。
- **ChurnBench**：能区分 **freshness error（取回时对、评测时错）** 与 reasoning error，并给出"**是刷新调度而不是缓存年龄决定陈旧性**"（TTL 1/14/28 天错误 7/4/4；禁用分层刷新后 28 天从 4 涨到 45）。
- **FiscalQA Pro**：静态 RAG 严格准确率 2.7%，版本化语料 + 金标条文 99.1%——把"版本选择"的危害量级说清楚。
- **FreeInference**：见第 5 节。

### 4.3 三层拼装协议

| 层 | 取什么 | 候选 | 纪律 |
|---|---|---|---|
| 到达层 | inter-arrival 形状与规模 | Chutes（1 年、秒/毫秒）> FreeInference（16 周、agent 会话 + 工具间隔）> Mooncake（1 小时、agent 形态） | **只取形状，不取语义** |
| 内容/重复层 | 请求内容、对象结构、天然重复 | ABCD / ToolBench / SemCache / AgentSim | 按目标 QPS 绑定到到达点；天然重复记 R0 |
| 版本层 | 真实版本区间或可编程 UPDATE/SUPERSEDE/EXPIRE | FiscalQA Pro（真实区间）、ChurnBench（可编程 + ledger）、ABCD 政策编辑、StreamingQA（`index(T)`） | 二维网格 `TTL × 每实体更新率`，并保留"固定刷新调度"臂 |

**最小可行组合（时间紧时）**：`ABCD + ToolBench + Chutes + SemCache + ChurnBench` 五个，版本实验用 ABCD 政策注入，外部效度后补 FiscalQA。

**权限/租户维度公开数据基本为空**（只有 FreeInference 的匿名 `user_id` 与 SSC 不公开的 InternalQA）。方案：把权限作为模型设定 + 合成 ACL 实验，limitations 引 SSC 专有结论（标准缓存 3.4–9.8% 违规复用、TTL 0.3–8.2%）作量级参照。

---

## 5. FreeInference / Agentic Trace 专项评估

### 5.1 身份与规模

| 项 | 内容 |
|---|---|
| 论文 | *From Requests to Sessions: A Large-Scale Characterization of Human-Driven Agentic Workloads*（Nixon, Tian, Zheng, Gunawi, Yang） |
| DOI / 许可 | 10.5281/zenodo.23903440 / **CC BY 4.0**（可商用、可再分发，需署名） |
| 时间跨度 | 2026-05-17 ~ 2026-09-05，16 周 |
| 规模 | 12,002 会话 / 267 账户 / 1,186,582 请求 / 1,213,347 工具调用 / 209.2B 输入 token / 552.5M 输出 token / 197.1B 缓存 token |
| Harness | 13 个人类 harness（Hermes 3,953；OpenCode 1,733；Pi 1,499；SWE-Bench 回放 1,035；Kilo 797；Codex 763；Oh-My-Pi 719；Claude Code 639；Copilot 295；Zcode 197；OpenClaw 189；Cline 86；Zoo 75；OpenHands 22） |
| 文件形态 | 原始 JSONL 约 108 GB（解压）；Parquet 三表（sessions/requests/tool_calls）约 9 GB；HF 按周 16 个 split |

### 5.2 字段结构（三层）

- **sessions**：`session_id`（32 hex 哈希）、`user_id`（16 hex 哈希）、`harness`、`parent_session_id`、`spawned_by_step`、`spawned_by_call_index`。
- **requests**：`session_id`、`step`、`link_reason`、`start_ms`、`end_ms`、`ttft_ms`、`model`、`provider`（匿名字母）、`stream`、`step_trigger`（user/tool）、`waited_for`、`prompt_tokens`、`completion_tokens`、`cache_read_tokens`、`role_tokens`（system/user/assistant/tool/tool_definitions 分角色）、`n_messages`、`tool_definition_names`、`finish_reason`、`transition`（append/mutation/switch）、`cause`（compaction/tool_definitions/system_prompt/dropped_turns/injection/tool_result/other）、`block_ids`（16-token 块的**周内等价 ID**）。
- **tool_calls**：`session_id`、`step`、`call_index`、`name`、`category`（Read/Edit/Write/Browser/MCP/Ask User/Subagent/*Interpreter/*Search/*File Ops/*Git-VCS/*Network/*Wait-Poll/*Build-Test/*Packages/Other）、`programs`、`parse_status`、`arguments_skeleton`（**参数值只保留类型**）、`outcome`（ok/error/denied/timeout）、`result_tokens`、`latency_ms`。

**明确没有**：message/prompt/response 文本；工具返回内容（只有 `result_tokens`）；参数具体值；原始标识符；文档、文档版本、权限/角色、答案真值。README 原文："No message text, prompt text, tool results, or raw identifiers are released."

### 5.3 能否支撑「缓存价值 / 失效 / 依赖」建模（关键判断）

| 层 | 能力 | 依据字段 | 支持程度 |
|---|---|---|---|
| L1 到达/会话/工具 | ✅ 完整 | 三层时间戳、`step_trigger`、`waited_for`、`latency_ms`、`category` | 可直接拟合到达率、turn 间隔、user idle、tool gap |
| L2 前缀/块级复用 | ✅ 统计层可用 | `block_ids`（周内等价 ID）、`cache_read_tokens`、`role_tokens`、`n_messages` | 可算块级复用率/命中年龄/复用距离；**受"周内等价"限制，跨周不可比** |
| L2' 失效诱因 | ⚠️ 部分 | `transition`（append/mutation/switch）+ `cause`（6 类） | 能观测"上下文何时、因何被改"，可做 TTL/刷新先验；**无陈旧性真值，无法判定失效是否正确** |
| L3 语义价值/正确命中 | ❌ | 无 prompt/response、无等价标签 | 算不出语义等价、答案正确性、错误复用代价 |
| L4 依赖图/版本闭包/权限 | ❌ | 无文档版本、无参数值、无对象 ID、`user_id` 是匿名账户非租户 | 只能做"请求—工具—上下文块"的时序共现，不能建"缓存对象→依赖节点→版本向量"的真依赖，也无法验证依赖闭包 |

**一句话**：它是**前缀/KV 层的负载与生命周期证据源**，不是**语义缓存的价值与正确性证据源**。

具体缺口（对应论文四类对象）：

- `resp` 语义缓存：无文本、无等价标签 → 等价性/正确性不可做；
- `rag`：无文档、无版本、无权限 → 证据复用与文档版本不可做；
- `plan`：无计划文本/模板/金标序列 → 不可做；
- `act`：无工具返回、无参数值 → 只能标定时延/失败率/单请求工具数，做不了结果内容复用与 act 正确性；
- 任何"缓存命中是否正确"的真值：只有 provider 报告的 cached token。

### 5.4 论文里可直接引用的 7 条发现（第一章动机层）

1. 缓存读主导 token 与成本：有缓存用量的请求中，cached input 占 token **97%**、API 成本 **73%**（按 1:10:50 单价假设）。
2. 工具执行主导活跃会话时延：工具时延减半 **1.38×** 加速；prefill 减半 1.09×、decode 减半 1.16×。
3. 15 分钟保留规则：15 分钟 KV 保留捕获大部分复用；接近全部复用需约 **一天**，存储开销 **25.6×**；15 分钟时新 prefill 仍比无限保留下限高 **60.9%**，30 分钟降至 35%。
4. 上下文变更：仅 **4.00% 请求**修改 prior context，但 **56% 会话**发生过 mutation；即使无限缓存，mutation 仍占新 prefill 的 **62.5%**。
5. 会话形态：中位 4 个 user step、36 个 tool step、42 个 LLM step；中位会话 30 分钟；84.5% 请求只发 1 个工具调用；子 agent 占 10.4% 会话；67% 会话出现批处理。
6. 基准回放 ≠ 真实负载：SWE-Bench 回放会话比人类会话短 **9.4×**、上下文小 **5.1×**，约 **5 分钟**保留即接近理想复用，而生产需要约 **一天**。
7. 会话重建：harness 大多不发 session id，作者用重放输出重建；在提供显式 id 的 harness 上 **95%** 一对一对齐，存在切分/不完整。

### 5.5 使用方案与引用纪律

1. 只下 Parquet（约 9 GB），按周 split 读取，过滤 `harness == "SWE-Bench"` 的回放会话；本机 16 GB 内存用 DuckDB 按列/按周读。
2. 抽三组统计：会话（user turn/step/时长/idle）、请求（inter-arrival、token、TTFT）、工具（类别/时延/失败率/单请求工具数）。
3. 做四件事：校准自建请求生成器；用工具时延/类别标定 act 成本；按周回放做 E3 系统层实验；把 15 min/mutation 作为 TTL/刷新先验。
4. **引用纪律**：以上全是 **KV/前缀缓存与 serving 负载** 结论，不是语义缓存结论，论文中必须标注区分；只作动机与参数先验，不作语义缓存证据。

### 5.6 Prompt 可得性（决定这条线还有没有上限）

| 版本 | 含 prompt/response | 状态 |
|---|---|---|
| 公开 Agentic Trace（HF/GitHub 当前版） | ❌ | 已发布，可直接下载 |
| 内部完整 trace（论文分析用） | ✅ `messages`（论文 Table 3） | 不公开 |
| FreeInference raw prompt dataset | ✅ 计划含 `messages/response/tool_calls/tool_results` | **Planned，pending IRB approval，未发布** |

**不建议从公开 trace 反推 prompt**：`block_ids` 是周内等价 ID（非哈希）、`role_tokens` 只有计数、`arguments_skeleton` 只有类型，用户输入/模型输出/工具结果均不可反演。能做的只有 harness 指纹识别（公开系统提示的 token 数匹配）与结构重建。

---

## 6. 实验映射：主张/RQ → 数据集 → 实验 → 指标

> 编号说明：两文混用 A–F 与 E1–E6 两套标签。本表以 11-18 文档第 5 节的 **A–F** 为准；E# 仅在该文档原文出现处保留（A↔E1、C↔E2、D↔E4、E↔E5、F↔E6 为按语义推断，**需与 lead 确认**）。

### 6.1 主张层（进 1.1 的动机证据）

| 编号 | 主张 / 研究问题 | 证据类型 | 数据集 | 实验 | 关键指标 | 章节归属 |
|---|---|---|---|---|---|---|
| C1 | 流式负载中存在真实且高度集中的缓存复用机会 | 现象统计 | Chutes（1 年 trace）、FreeInference | A（机会） | 精确重复率、潜在命中率@τ、命中年龄 p50/p95 | 1.1（动机）+ 第3章 A |
| C2 | 命中 ≠ 有用：错误复用与"变更≠危害"真实存在 | 已有工作量级 | SemCache、FreshCache（396 对变更仅 34.3% 影响答案）、SSC 专有结论（3.4–9.8% 违规复用） | A / B | 安全命中率、错误命中率、质量损失 | 1.1（动机）+ 第3章 B |
| C3 | 版本/失效真实发生且代价巨大 | 真实版本事件 | FiscalQA Pro（静态 2.7% vs 版本化 99.1%）、ChurnBench | E（E5） | 事实正确率、陈旧暴露率 | 1.1（动机）+ 第3章 E |
| C4 | 生命周期（TTL/保留）存在明确收益区间与饱和点 | 生产统计 | Chutes（50%/80%/99% 分位）、FreeInference（15 min / 25.6× / 60.9%） | C（E2） | 累计安全收益、churn、单位空间收益 | 1.1（动机）+ 第3章 C |
| C5 | 依赖/级联失效不可避免 | 上下文变更统计 | FreeInference（56% 会话 mutation、62.5% fresh prefill、cause 6 类） | C（E2） | 失效精确率/召回率、fan-out | 1.1（动机，仅结构层）+ 第3章 C |
| C6 | 基准回放不能代表真实负载（方法学辩护） | 对照统计 | FreeInference（SWE-Bench 9.4×/5.1×，5 min vs 1 day） | 外部效度 | KS / 相对误差 | **1.1 强证据** + 第3章效度节 |
| C7 | act 成本不可忽略，工具时延主导活跃会话 | 时延分解 | FreeInference（1.38× vs 1.09×/1.16×、`latency_ms`/`outcome`/`category`） | A + act 成本标定 | 工具时延分布、失败率、单请求工具数 | 1.1（动机）+ 第3章成本标定 |

### 6.2 实验层（第 3 章）

| 实验 | 主数据 | 补充 | 观察指标 |
|---|---|---|---|
| **A 机会与管理税** | SemCache（resp）、ToolBench（act）、AgentSim（rag）、ABCD（plan） | FreeInference（真实工具调用重复） | 精确重复率、语义潜在命中率@τ、安全命中率、管理税（检索/验证/适配）分布 |
| **B 候选检索与有效性** | SemCache + Search Arena（resp）、RAGTruth（证据支持）、ABCD（政策/动作有效性） | TicToc（时间敏感 verify 标签） | 候选召回、有效性判别 P/R、错误复用率与质量损失 |
| **C 生命周期（准入/保留/淘汰）** | Chutes（一年流、容量/TTL/热点）、ABCD（对象级价值） | ToolBench（act 容量）、Mooncake（短回放） | 累计安全收益、churn、重建成本、单位空间收益 |
| **D resp 静态层异步验证提升** | SemCacheLMArena + SearchQueries（Krites 口径：20% 历史 / 80% 在线 / 灰区 / 等价类 oracle） | Search Arena（真实偏好做质量差） | 静态来源服务比例、新增安全覆盖、质量差、后台预算敏感性 |
| **E 流式证据更新与修复** | ChurnBench（受控、ledger 真值）、ABCD 政策版本（场景内） | FiscalQA Pro（真实版本外部效度）、StreamingQA（时间切片）、RAGTruth（主张核验） | 事实正确率、证据支持率、陈旧暴露率与时长、局部修复成功率、总成本 |
| **F 组合与 Flink** | Chutes 到达 × 内容层（ABCD/ToolBench/AgentSim）× 版本层（ChurnBench） | FreeInference / Mooncake 做小规模 agentic 回放 | P95/P99、吞吐、队列、checkpoint 恢复、重复/遗漏任务 |
| **外部效度（贯穿）** | FreeInference 统计 vs 自建 T1 请求流 | Chutes 到达分布 | 会话/turn/工具间隔/burst 的 KS 与相对误差 |

### 6.3 四类对象 × 数据源（谁提供结构、谁提供真值、什么要自建）

| 对象 | 主数据源 | 真值/标签 | 需要自建 |
|---|---|---|---|
| `resp` | vCache SemCache、Search Arena 24K、（ABCD 客服回复） | 等价类、人类偏好、动作级正确性 | 近重复聚类、复用质量差、静态库切分 |
| `rag` | AgentSim ATC、RAGCache 公开 QA（MMLU/NQ/HotpotQA）、ABCD 政策库、ChurnBench 文档 | grounding、qrels、政策适用性、ledger | 文档版本/生效时间/权限、证据覆盖判断 |
| `act` | ToolBench/StableToolBench、ABCD 30 动作、AgentBench DBBench、FreeInference（真实调用） | ToolEval、逐轮动作标签、SQL 结果 | 只读性分类、工具版本、参数规范化、状态检查成本 |
| `plan` | ABCD 55 子流程、ToolBench DFSDT 树、τ²-bench 任务族、APC 五个任务集 | CDS/AST、pass/win、可验证 reward、任务成功率 | 模板抽取、槽位/前置条件、适配与回退标签 |

---

## 7. 分界：哪些归 1.1「问题背景与分析」，哪些归第 3 章

判断规则：**1.1 只用"现象存在且量级可观"的外部证据，且必须写清证据口径与边界；凡是"我们怎么构造数据、怎么设对照、怎么算指标"的，一律归第 3 章（或 1.4 数据与实验设置）。**

### 7.1 归 1.1（问题背景与分析）

| 证据 | 支撑的论点 | 引用边界 |
|---|---|---|
| Chutes：prefix-cache 命中双峰、约 50% 在 0.1 s / 80% 在 10 s / 99% 在 15 min 内 | 复用高度集中在短间隔 → 缓存年龄是有效变量 | 生产 serving 负载，非 agent 语义负载 |
| FreeInference：cached input 占 token 97%、成本 73% | 缓存复用已是主导项，价值建模有现实意义 | 按 1:10:50 单价假设 |
| FreeInference：15 min 保留捕获大部分复用；近全复用需约一天、存储 25.6×；15 min 仍比无限保留下限高 60.9% | 保留窗口存在"收益—存储"硬权衡 → 生命周期控制必要 | KV/前缀缓存结论，**不是语义缓存结论** |
| FreeInference：4.00% 请求 / 56% 会话发生 mutation；无限缓存下 mutation 仍占新 prefill 62.5% | 失效不是边缘情况，纯"扩大缓存"不能消解 | 同上的层级别混淆风险 |
| FreeInference：工具时延减半 1.38×，prefill 1.09×、decode 1.16× | act 对象与工具成本必须进价值模型 | 活跃会话时延口径 |
| FreeInference：SWE-Bench 回放比人类会话短 9.4×、上下文小 5.1×，5 min vs 1 day | 现有 agent 基准不能代表真实负载 → 自建/拼装数据的正当性 | 方法学辩护，最有力的一条 |
| FiscalQA Pro：静态 RAG 2.7% vs 版本化语料 + 金标 99.1% | 版本选择错误的危害量级 | 法语法律域、209 题、oracle 检索条件 |
| ChurnBench：TTL 1/14/28 天错误 7/4/4；禁用分层刷新后 28 天 4→45 | 陈旧性由刷新调度而非缓存年龄决定 → 生命周期要管"依赖与刷新" | 合成企业数据织物 |
| FreshCache：396 对确认变更中仅 34.3% 影响答案正确性 | change ≠ harm，不能把"变更"直接当"失效收益" | 作为反例量级引用 |
| SSC：标准缓存 3.4–9.8% 违规复用、TTL 0.3–8.2% | 权限维度缺失是真实风险 | SSC 内部数据不公开，只作量级参照 |
| ABCD 30 动作 / 55 子流程 / 逐轮真值；ToolBench 126,486 实例 / 469,585 调用 | 四类对象与动作级真值在公开数据中可得（研究可行性） | 属"可行性事实"，放 1.1 末或 1.4 |

**1.1 不该出现的**：SemCache 的 20%/80% 切分口径、R0/R1/R2 注入梯度、U0–U3 版本注入、三命中分离指标、≥3 seeds/bootstrap、T1 构造字段清单、Flink 失败注入用例——这些是方法与实验设计，放第 3 章。

### 7.2 归第 3 章（实验设计）

| 内容 | 为什么不能进 1.1 |
|---|---|
| 三层拼装的具体绑定方式（到达层 QPS 缩放、内容层绑定、版本层注入比例） | 这是本文的数据构造方法，不是背景事实 |
| 重复注入 R0/R1/R2 与 λ 档位、相似度对齐检验 | 属实验控制变量 |
| 版本注入 U0–U3 与 `TTL × 更新率` 二维网格 | 属实验设计 |
| 指标纪律：相似命中/正确命中/新鲜命中三分离、错误命中率、陈旧命中率、失效 P/R、成本分账、warm-up 丢弃 | 属评价方法 |
| Krites 口径复现（20% 历史 / 80% 在线 / 灰区 / 等价类 oracle / 100 对人工审计） | 属对比实验设置 |
| FreeInference 的 9 GB Parquet 回放、SWE-Bench 会话过滤、DuckDB 按周读取 | 属实现细节 |
| 外部效度映射（自建 T1 vs FreeInference/Chutes 的 KS 与相对误差阈值） | 属效度检验 |
| 构造字段标注（到达时间、热点、版本、成本参数、后台预算） | 属论文边界声明，放第 3 章或 limitations |

### 7.3 三条引用纪律（贯穿两章）

1. **层级别混淆**：FreeInference/Chutes 的结论是 KV/前缀缓存与 serving 负载结论，引用时必须写明"非语义缓存证据"。
2. **只借形状不借语义**：到达层只取 inter-arrival 与规模，不取语义分布；语义真值只能来自 SemCache/ABCD/ToolBench 这类有标签的数据。
3. **构造即标注**：任何注入/合成字段（到达时间、热点、版本、成本、预算）在论文中显式标注为实验构造，并给出偏差量化口径（KS/相对误差）。

---

## 8. 未决问题

| # | 未决问题 | 现状 / 冲突点 | 影响 | 建议动作 |
|---|---|---|---|---|
| Q1 | Chutes 与 FreeInference 是"二选一"还是"分工" | 11-18 文档 §3.3 写"若只能留一个：FreeInference……Chutes 已覆盖系统层，两者选一即可"；但 Tier A 把 Chutes 定为核心、FreeInference 为 Tier B，11-20 补充记录又把 FreeInference 定位为 T5 到达-会话-工具层 + 外部效度，**并未删 Chutes** | 决定第 3 章 C/F 实验的数据源与工作量 | 定稿为分工：Chutes 管 1 年到达/容量/TTL 系统层；FreeInference 管 agent 会话结构、工具成本标定、外部效度。若时间不足，砍 FreeInference 保留 Chutes |
| Q2 | T5 到底指谁 | 冻结版方案 T5 = Chutes；FreeInference 评估文档也用 T5 指"到达-会话-工具层" | 术语不一致会写乱 | 统一为"T5 到达层（Chutes 主 + FreeInference 补）"，或改称 T6 |
| Q3 | A–F 与 E1–E6 编号不统一 | 两文混用，且无对照表 | 映射表易错位 | 出一张 A–F ↔ E# ↔ 研究点一/二/集成 的对照表并冻结 |
| Q4 | raw prompt dataset 要不要等 | Planned，pending IRB，未发布 | 若发布可补语义层，但论文不能押在未发布数据上 | 不等待；可发信 data@freeinference.org 询问时间线，作为 limitations 一句话 |
| Q5 | 10 条开工前复核项 | PasarBench 是否存在、ABCD 10,042 与 8,034/2,008 划分、SemCache 各子集规模与代码许可、Chutes 分位数回原文、Mooncake 许可冲突、ChurnBench 7/4/4 与 4→45、FiscalQA canary 与 209 题 | 引用级错误风险 | 第 0 周逐条核对并留档；未核实项在论文中降级表述 |
| Q6 | 三层拼装的偏差量化阈值 | 只写了"报告偏差（KS/相对误差）"，没定阈值 | 外部效度无法判定通过与否 | 在第 3 章效度节先定阈值（如会话时长/工具间隔 KS < 0.1）再跑 |
| Q7 | 权限维度的实验地位 | 公开数据基本为空，只能合成 ACL；SSC 数据不公开 | 可能成为审稿人攻击点 | 明确写成"模型设定 + 合成 ACL + SSC 量级参照"，不宣称有真实权限数据 |
| Q8 | R2 注入的"相似度不高于 R0 中位数"如何操作化 | 只给了原则 | 自造重复偏置无法证伪 | 先定相似度度量（embedding 余弦 / 编辑距离）与 R0 中位数计算口径 |
| Q9 | FreeInference 域不匹配能否用 | 编码/助手 agent（Claude Code、Codex、OpenCode），主场景是客服政策（ABCD） | 外部效度只能对齐系统层统计，对不齐意图/语义分布 | 论文中限定"仅对齐系统层（到达、会话、工具、token）统计" |
| Q10 | 91 GB / 108 GB 与 16 GB 内存的抽取计划 | 尚未定抽哪几周、存哪 | 阻塞 C/F 实验启动 | 先定 2 周窗口 + DuckDB 按列查询，产出物落 T1 schema |

---

## 9. 附：本次整理确认的"事实边界"

以下条目两文明确标注为**未核实/部分核实/查无此物**，整理稿不升级为事实：

- PasarBench：**未找到任何公开证据**（形近 ParsBench/PawBench 均无关），建议删除或向导师确认来源。
- ABCD：10,042 条与 8,034/2,008 划分为二手交叉引用，"over 10K"是 README 说法。
- vCache SemCache：LMArena 约 6 万已核实；Classification 45K / SearchQueries 150K / Combo 27.5K **部分核实**；代码仓库许可徽章偏严（非商用/禁演绎）。
- Chutes：91 GB 版本、`ct` 字段口径、50%/80%/99% 分位数**需回原文核对**。
- Mooncake：23,608 条与字段需核；2026 Codex trace 许可冲突（CC-BY-NC vs MIT）。
- ChurnBench：7/4/4 与"28 天 4→45"**需回原文核对**。
- FiscalQA Pro：209 题、金标条文、canary 串、法语法律域适用性需核。
- FreeInference：108 GB 原始 vs 9 GB parquet 的差异与 HF 可下载性需实测确认。
