# FreeInference Agentic Trace 数据集评估记录

> 记录日期：2026-11-20
> 来源：本地核查 GitHub README、`release/schema.py`、论文 PDF（18 页）、HF 数据卡、OpenData 官网。
> 用途：第一章「数据与实验设置」的候选负载/外部效度层评估；不改变 ABCD-Cache v0.2 的主实验台定位。

---

## 0. 一句话定位

**目前公开数据中规模最大、字段最全的「人类驱动 Agent 服务 trace」**：16 周、1.2 万会话、120 万请求、121 万工具调用、209B 输入 token，带会话/请求/工具/16-token 前缀块/上下文变更，CC BY 4.0。
**但它只有元数据，没有 prompt/response 文本、没有工具返回内容、没有文档版本与权限、没有缓存正确性真值**——因此只能作为**到达/会话/工具/生命周期与外部效度层**，不能作为四类缓存对象的主实验台。

---

## 1. 基本信息

| 项 | 内容 |
|---|---|
| 名称 | FreeInference Agentic Trace |
| 论文 | *From Requests to Sessions: A Large-Scale Characterization of Human-Driven Agentic Workloads*（Nixon, Tian, Zheng, Gunawi, Yang；2026-10 版） |
| DOI | 10.5281/zenodo.23903440 |
| 代码/说明 | https://github.com/HarvardMadSys/freeinference_agentic_trace |
| 数据 | https://huggingface.co/datasets/harvardMadsys/freeinference_agentic_trace |
| 数据门户 | https://data.freeinference.org/ |
| 可视化 | https://agent-traces.freeinference.org/ |
| 许可 | **CC BY 4.0**（可商用、可再分发，需署名） |
| 时间跨度 | 2026-05-17 ~ 2026-09-05（16 周 / 3.7 个月） |
| 规模 | 12,002 会话 / 267 账户 / 1,186,582 请求 / 1,213,347 工具调用 / 209.2B 输入 token / 552.5M 输出 token / 197.1B 缓存 token |
| Harness | 13 个人类 harness（Hermes 3,953；OpenCode 1,733；Pi 1,499；SWE-Bench 1,035（回放对照）；Kilo 797；Codex 763；Oh-My-Pi 719；Claude Code 639；Copilot 295；Zcode 197；OpenClaw 189；Cline 86；Zoo 75；OpenHands 22） |
| 文件形态 | 原始 JSONL 约 108 GB（解压）；Parquet 三表（sessions/requests/tool_calls）约 9 GB；HF 按周切分（16 个 split） |
| 仓库组件 | `release/`（schema/reader/download/convert/trace_lines）、`simulation/`（前缀缓存重放 + 成本模拟）、`paper/`（图表复现）、`export/`（脱敏管线、隐私检查） |

---

## 2. 字段与 schema（公开匿名版）

来源：`release/schema.py`（文件头注明 "The anonymous release's files and columns"）。

### 2.1 sessions

`session_id`（32 hex 哈希）、`user_id`（16 hex 哈希）、`harness`、`parent_session_id`、`spawned_by_step`、`spawned_by_call_index`。

### 2.2 requests

`session_id`、`step`、`link_reason`、`start_ms`、`end_ms`、`ttft_ms`、`model`、`provider`（匿名字母）、`stream`、`step_trigger`（user/tool）、`waited_for`、`prompt_tokens`、`completion_tokens`、`cache_read_tokens`、`role_tokens`（system/user/assistant/tool/tool_definitions 分角色 token 数）、`n_messages`、`tool_definition_names`（小写/`other`）、`finish_reason`、`transition`（append/mutation/switch）、`cause`（compaction/tool_definitions/system_prompt/dropped_turns/injection/tool_result/other）、`block_ids`（16-token 块的周内等价 ID）。

### 2.3 tool_calls

`session_id`、`step`、`call_index`、`name`、`category`（Read/Edit/Write/Browser/MCP/Ask User/Subagent/*Interpreter/*Search/*File Ops/*Git-VCS/*Network/*Wait-Poll/*Build-Test/*Packages/Other）、`programs`、`parse_status`、**`arguments_skeleton`（参数值只保留类型）**、`outcome`（ok/error/denied/timeout）、`result_tokens`、`latency_ms`。

### 2.4 明确没有的字段

- ❌ message/prompt/response 文本
- ❌ 工具返回内容（只有 `result_tokens`）
- ❌ 工具参数具体值（只有类型骨架）
- ❌ 原始标识符（session/user 均哈希）
- ❌ 文档、文档版本、权限/角色、答案真值

> 公开 README 原文：**"No message text, prompt text, tool results, or raw identifiers are released."**

---

## 3. 论文关键发现（可直接用于第一章动机与数据设置）

1. **缓存读主导 token 与成本**：报告了缓存用量的请求中，cached input 占 token 量 **97%**、API 成本 **73%**（按 1:10:50 的缓存/非缓存/输出单价假设）。
2. **工具执行主导活跃会话时延**：工具时延减半带来 **1.38×** 加速；prefill 减半 1.09×，decode 减半 1.16×。
3. **15 分钟保留规则**：15 分钟 KV 保留捕获大部分复用；接近全部复用需约一天，存储开销 **25.6×**；15 分钟时新 prefill 仍比无限保留下限高 **60.9%**，30 分钟降至 35%。
4. **上下文变更**：仅 4.00% 请求修改 prior context，但 **56% 会话**发生过 mutation；即使无限缓存，mutation 仍占新 prefill 的 **62.5%**；mutation 原因含 injection、system prompt、tool definitions、dropped turns、compaction 等。
5. **会话形态**：中位 **4 个 user step**、**36 个 tool step**、**42 个 LLM step**；中位会话 30 分钟；84.5% 请求只发 1 个工具调用；子 agent 占 10.4% 会话；67% 会话出现批处理。
6. **基准回放≠真实负载**：SWE-Bench 回放会话比人类会话短 **9.4×**、上下文小 **5.1×**，约 **5 分钟**保留即接近理想复用，而生产需要约 **一天**。
7. **会话重建**：harness 大多不发 session id，作者用重放输出重建；在提供显式 id 的 harness 上 **95%** 一对一对齐；不完整/切分会存在。

---

## 4. 对第一章的用途

| 用途 | 怎么用 | 边界 |
|---|---|---|
| **T5 / 到达层** | 取 1–2 周窗口，拟合会话到达、turn 间隔、user idle、tool gap；校准自建测试台的请求生成器 | 只借形状，不借语义 |
| **E2 生命周期** | 用 15 分钟保留、user idle、mutation 分布做 TTL/刷新先验；对比“空闲后失效”策略 | 这是 KV/前缀缓存结论，不是语义缓存结论，引用时区分 |
| **E3 / Flink 回放** | 9 GB Parquet 按周回放，测吞吐/P95/积压/恢复；过滤 SWE-Bench 回放会话 | 只报系统层指标，不报语义正确性 |
| **act 成本标定** | 用 tool `category`、`latency_ms`、`outcome`、`result_tokens` 标定只读工具时延/失败率分布 | 无工具返回内容，不能做 act 正确性/内容复用 |
| **外部效度** | 将自造请求流与会话统计与 trace 对比，报告偏差（KS/相对误差） | 只能对齐系统层统计 |
| **论文动机** | 引用 cached token 97%/73%、tool 1.38×、15 min/25.6×、mutation 56%/62.5% | 只作动机与参数先验，不作语义缓存证据 |

---

## 5. 明确不能支撑的部分

- `resp` 语义缓存的等价性/正确性（无 prompt/response 文本、无等价标签）；
- `rag` 证据复用与文档版本（无文档、无版本、无权限）；
- `plan` 模板与金标序列（无计划文本/模板）；
- `act` 结果内容复用（无工具返回、无参数值）；
- 权限/租户（`user_id` 是匿名账户，不是租户/角色）；
- 任何“缓存命中是否正确”的真值（只有 provider 报告的 cached token）。

---

## 6. Prompt 状态（重要）

| 版本 | 是否含 prompt/response | 状态 |
|---|---|---|
| 公开 Agentic Trace（HF/GitHub 当前版） | ❌ 无 | 已发布，可直接下载 |
| 内部完整 trace（论文分析用） | ✅ `messages`（论文 Table 3） | 不公开 |
| **FreeInference raw prompt dataset** | ✅ 计划含 `messages/response/tool_calls/tool_results` | **Planned，pending IRB approval**，未发布 |

- 论文脚注：完整 trace 含 prompt 版本“upon approval”，否则发布匿名版；
- OpenData 官网 Roadmap：raw prompt dataset 标注 **Planned**，发布说明“pending IRB approval”；
- 联系方式：`data@freeinference.org`；
- **不建议从公开 trace 反推 prompt**：`block_ids` 是周内等价 ID（不是哈希值），`role_tokens` 只有计数，`arguments_skeleton` 只有类型；用户输入/模型输出/工具结果均不可反演。能做的是 harness 指纹识别（公开系统提示的 token 数匹配）与结构重建，不能还原文本，也不能当真实 prompt 使用。

---

## 7. 使用方案（建议）

1. **只下 Parquet（约 9 GB）**：`hf download harvardMadsys/freeinference_agentic_trace --repo-type dataset --local-dir ...`；按周 split 读取；过滤 `harness == "SWE-Bench"` 的回放会话。
2. **抽三组统计**：会话（user turn/step/时长/idle）、请求（inter-arrival、token、TTFT）、工具（类别、时延、失败率、单请求工具数）。
3. **做三件事**：校准自建请求生成器；用工具时延/类别标定 act 成本；按周回放做 E3 系统层实验；把 15 min/mutation 作为 TTL/刷新先验并在论文中标注“KV 缓存结论，非语义缓存”。

---

## 8. 风险与限制

| 风险 | 说明 |
|---|---|
| 域不匹配 | 编码/助手 agent（Claude Code、Codex、OpenCode 等），不是客服政策场景 |
| 无文本 | 不能做 resp/rag/plan 的语义与正确性实验 |
| Session 重建 | 95% 一对一对齐；存在切分/不完整；时间跨度内 harness 版本演化 |
| 账户≠租户 | 267 个匿名账户，无组织/角色/ACL |
| 包含基准回放 | SWE-Bench 1,035 会话；做人类负载分析时要过滤 |
| 规模 | 原始 108 GB；Parquet 9 GB；本机 16 GB 内存需用 DuckDB/按周读取 |
| Prompt 不可得 | 公开版无文本；raw prompt dataset 待 IRB；不要反推当真实数据 |
| 引用边界 | 论文结论是 KV/前缀缓存与 serving 负载，不是语义缓存 |

---

## 9. 引用

```bibtex
@misc{nixon2026requests,
  title        = {From Requests to Sessions: A Large-Scale Characterization
                  of Human-Driven Agentic Workloads},
  author       = {Nixon, William and Tian, Muxin and Zheng, Yunjia
                  and Gunawi, Haryadi S. and Yang, Juncheng},
  year         = {2026},
  month        = {nov},
  publisher    = {Zenodo},
  note         = {Preprint},
  doi          = {10.5281/zenodo.23903440},
  url          = {https://doi.org/10.5281/zenodo.23903440}
}
```

## 10. 链接

- 仓库：https://github.com/HarvardMadSys/freeinference_agentic_trace
- 数据：https://huggingface.co/datasets/harvardMadsys/freeinference_agentic_trace
- 论文：https://data.freeinference.org/pdf/paper/from-requests-to-sessions
- 门户：https://data.freeinference.org/
- 可视化：https://agent-traces.freeinference.org/
- schema：https://github.com/HarvardMadSys/freeinference_agentic_trace/blob/main/release/schema.py
- 联系：data@freeinference.org
