# `dataset-v0.1.0` $\rightarrow$ `dataset-v0.2.0` 完善与优化指南（面向执行 Agent）

> **文档定位**：本指南面向负责迭代完善实验数据集的执行 Agent。当前 `dataset-v0.1.0` 已具备极佳的工程基础（确定性复现、40 项断言校验、只读 SQLite 三层保护、300/300 谓词真值与清晰的构造/实测边界），足以跑通 1.1 节动机实验；但对照论文 **1.2–1.4 节（尤其是 C1–C4 正式实验与消融实验）** 的要求，仍存在若干 P0/P1 级缺口。
> **核心目标**：先对现版数据做一次快速量化“体检”，再按优先级完成结构补强与模型标定通道建设，升级并封版为 `dataset-v0.2.0`。

---

## 1. 版本升级铁律（执行前必读）

执行 Agent 在修改任何生成器或数据文件时，必须严格遵守 `HANDBOOK.md` 第 0、6、11 节的原有契约：

1. **契约先行**：凡涉及字段增补、规模或参数微调，必须严格按顺序执行：**先改 `schema/` 与 `config/params.json` $\rightarrow$ 更新 `contracts/CHANGELOG.md`（记录 `v0.2.0` 变更） $\rightarrow$ 修改生成器并重跑构建 $\rightarrow$ 同步更新 `HANDBOOK.md` 与 `DATASET_CARD.md`**。
2. **严守 `measured` 与 `mock` 隔离（铁律 3）**：绝不允许用随机数、经验常数或估算值去伪造 LLM 生成/改写毫秒耗时或 `token_cost`。若当前运行环境具备 LLM API / 本地 GPU，则跑真实模型并写入 `measured`；若当前环境暂无法调用 LLM，则只完成标定脚本建设与结构优化，模型耗时行继续保持 `mock=pending`。
3. **保留已有高价值设计**：严禁删除 6 条 `codebook_revision` 零影响负对照（用于测试误触发率），严禁破坏“块 ID 跨版本固定”不变量，严禁降低 `verify.py --all` 的断言严格度（升级后应只增不减）。

---

## 2. 第 0 步：先运行“数据集现状体检”（先诊断，后动刀）

在修改任何生成器前，先写并运行一个轻量诊断脚本 `dataset/tools/audit_v010.py`，输出 `dataset/audit_v010_report.json`，查明以下 5 项真实分布，避免盲目改动：

1. **时钟差诊断**：遍历 `update_events.jsonl`（40 条），对比每条事件的 `timestamp` 与 `docs_versioned.jsonl` 中对应 `(doc_id, new_ver)` 的 `updated_at`，统计时间差分布（如 `u0019` 的 `updated_at=06:00` vs `timestamp=08:14`）。
2. **`act` 与 `plan` 异质性诊断**：统计 `act_plan_pool.json` 中 100 个 `act` 的 `len(downstream_tools)` 分布（0、1、2、3+ 各占多少）及 `act_cost` 方差；统计 60 个 `plan` 的 `completion_rate` 与 `plan_cost` 分布。
3. **语义簇与改写密度诊断**：统计 `request_context.jsonl` 中 200 道题在各 `domain` 下的分布、每题实际出现频次与 3 种改写变体的分布，评估单题冷启动与跨题同簇借用的可行性。
4. **更新影响面诊断**：统计 40 次更新事件累计的文档级受影响请求数、主张级受影响请求数，以及在主张级受影响的请求中，“单主张/局部变更（受影响主张占比 $<50\%$）”与“多主张/大改（$\ge 50\%$）”的比例。
5. **负例相似度诊断**：用默认句向量模型（或 TF-IDF）计算 `labels/safe_reuse.jsonl`（300 对）中正例与 N1–N6 负例的余弦相似度分布，检查是否存在负例过易区分或正例相似度过低的问题。

---

## 3. 逐项完善与优化任务（按优先级排序）

### 【P0-1】统一并澄清“文档生效时刻 `updated_at`”与“更新事件时刻 `timestamp`”的时钟语义

* **现状与风险**：
  `HANDBOOK.md §2.2` 规定文档版本 1/2/3 固定于 `00:00` / `06:00` / `12:00` 生效，但 `update_events.jsonl` 的 40 条事件散布在 `06:13`–`17:45`（例如 `u0019` 指向 `wp_017` `v1→v2`，`timestamp` 为 `08:14:36Z`，但 `v2` 的 `updated_at` 是 `06:00:00Z`）。这会导致一个致命歧义：在 `06:00`–`08:14` 期间，`doc_at(ts)` 认为文档已变、`is_safe()` 判定旧缓存过期，但流式缓存系统直到 `08:14` 才收到更新事件，这会直接撞毁 1.4.1 节“越权与过期复用次数作为硬断言要求为零”的实验结论。
* **对应论文章节**：1.2.2 节（使用前核对依赖状态）、1.3.2 节（流式更新与修复）、1.4.1 节（硬断言）。
* **具体改造方案（推荐方案 A）**：
  * **方案 A（推荐：事件驱动时钟对齐）**：
    1. 对 `update_events.jsonl` 中涉及的 34 篇文档变更，将其在 `docs_versioned.jsonl`（及 `knowledge/docs.jsonl`）中对应 `new_ver` 的 `updated_at` **精确对齐**为该更新事件的 `timestamp`（即“文档在事件发生那一刻生效并同步发出更新事件”）。
    2. 其余未出现在 `update_events.jsonl` 中的批量快照文档变更，可继续保持 `06:00` / `12:00` 生效（或在 `request_stream` 中仅通过快照边界切换），并在 `verify.py` 中新增断言：*凡出现在 `update_events.jsonl` 中的 `(doc_id, new_ver)`，其 `docs_versioned.updated_at == update_event.timestamp`*。
  * **方案 B（备选：显式双时间戳）**：若刻意保留“底层先变、事件延迟到达”的真实延迟场景，则在 `update_events.jsonl` 中显式增加 `effective_at` 与 `notified_at` 两个字段，并同步修改 `HANDBOOK.md` 与 `is_safe()` 说明文档，区分“已知版本过期（硬断言必须为 0）”与“未通知窗口静默变更（不可避免的外部延迟）”。

---

### 【P0-2】固化 `query_emb` 句向量表示，并构建 300 条真实 LLM 耗时/成本一键标定脚本

* **现状与风险**：
  1. `request_stream.jsonl` 中 `query_emb` 恒为 `null`，导致 1.2.2、1.3.1、1.4.3 所有语义召回与聚类实验无法直接开跑。
  2. `real_calibration_300.template.csv` 仅 `t_act_ms` 有值，`costs/path_costs.csv` 中 4 行模型耗时为 `mock=pending`，`labels/branch_pairs.jsonl` 中 `t_model_*` 恒 `null`。没有这 300 条真实 LLM 耗时与 token 数据，**1.4 节 C1–C4 的 P95 端到端时延、推理成本、goodput 与 MAPE 标定全部无法产出**。
* **对应论文章节**：1.2.2 节、1.4.1 节（实测标定与 MAPE）、1.4.2–1.4.6 节（C1–C4 全部端到端指标）。
* **具体改造步骤**：
  1. **句向量固化（零体积膨胀方案）**：
     - 选用固定、轻量、可本地复现的中文句向量模型（首选 `BAAI/bge-small-zh-v1.5` 或 `BAAI/bge-base-zh-v1.5`），对 `request_stream.jsonl` 及 `streams/seed42–46.jsonl`、`long_01,02.jsonl` 中全部去重 `query_text` 批量编码；
     - 建议将向量存为二进制文件 `dataset/events/query_embeddings.npz`（含 `query_texts` 与 `embeddings` 矩阵，体积仅数 MB，避免把 512/768 维浮点数组直接写进 JSONL 导致文件暴涨），并在 `common/io.py` 中提供 `load_query_embeddings()` 辅助函数；在 `config/params.json` 记录模型名称、维度与归一化方式。
  2. **编写真实 LLM 标定脚本 `dataset/tools/run_model_calibration.py`**：
     - 兼容 OpenAI API / DeepSeek / 本地 vLLM / Ollama（通过环境变量 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 配置）；
     - 针对 `events/real_calibration_300.template.csv` 中的 300 条请求，依次真实执行 `plan`、`rag`、`act`（已有实测）、`resp` 生成，并抽样执行 `partial_repair/rewrite` 与 `full_regen/generate`，精确记录每步 wall-clock 毫秒数与 `prompt_tokens` / `completion_tokens`；
     - 运行完毕后自动输出：
       - `dataset/events/real_calibration_300.csv`（全部 7 列填满且 `measured=true`）；
       - 更新 `dataset/costs/path_costs.csv` 中原先 4 行 `pending` 模型成本行（改为 `measured=true, mock=""`）；
       - 更新 `dataset/labels/branch_pairs.jsonl` 中的 `t_model_full_ms`、`t_model_cache_ms` 与端到端净收益 `g_e2e_ms`；
       - 自动计算并打印建模时延相对实测时延的 **MAPE**。
     - *注意*：若当前执行 Agent 没有可用 LLM Key，须先将脚本写完并通过 `--dry-run` 语法与接口自测，待用户/作者填入 Key 后一键执行，**严禁伪造模型耗时**。

---

### 【P1-1】补强 `act_plan_pool.json` 中的 `downstream_tools` 梯度与 `plan` 完成率方差

* **现状与风险**：
  `HANDBOOK.md §3.5` 给出的 `act` 示例为 `"downstream_tools": []`。如果第 0 步体检发现 100 个 `act` 中绝大多数的 `downstream_tools` 均为空列表，那么论文 **1.2.1 节** 的 `act` 专属价值修正项 $\Delta S_{\mathrm{act}} = w_{\mathrm{act}}\min(d_i / D_{\mathrm{ref}}, 1)$ 将退化为 0，直接导致 **1.4.6 节 C4**“去掉 `act`/`plan` 价值项”的消融实验失去区分度。
* **对应论文章节**：1.2.1 节（类型专属价值）、1.4.6 节（C4 消融实验）。
* **具体改造步骤**：
  1. 利用仓库已构建的 **`contracts/lineage.json`**（包含 84 条 `fk/aggregate/derive` 血缘边及 `three_hop_chain`），把每个 `act` 关联的底层表映射到血缘图中：
     - 处于上游基础表/维度表或中间聚合表的 `act`，将其下游依赖表对应的 `act_key` 填入 `downstream_tools`；
     - 确保 100 个 `act` 的 `d_i = len(downstream_tools)` 呈现清晰梯度（例如约 30% 为 `0`，30% 为 `1`，25% 为 `2`，15% 为 `3–4`）。
  2. 同步核查 60 个 `plan` 的 `completion_rate`：确保不同难度（`single_table` / `join` / `nested_agg`）对应的模板在完成率上呈现合理分化（例如简单模板 `0.90–0.98`，复杂嵌套聚合模板 `0.70–0.85`），避免所有模板都是 `0.92` 导致 $w_{\mathrm{plan}} q_i$ 无区分度。

---

### 【P1-2】显式构建语义簇标签 `cluster_id` 并强化同簇多条目结构（支撑簇内反馈借用）

* **现状与风险**：
  当前题库为 200 道题、每题 3 种中文改写。论文 **1.2.2 节** 与 **1.4.3 节 C1** 的核心亮点之一是“**新版本反馈不足时，利用 LLM 请求簇从同簇其他条目借用同相似度区间、权限相容、版本一致的标注**”，并在 1.4.3 节单列了“更新后的 500 条请求”来检验簇内借用是否加速命中恢复。如果一个簇里只有 1 道题，缺乏“同簇内多个可互相借用反馈的条目”，簇内借用机制很难显形。
* **对应论文章节**：1.2.1 节（`resp` 的 LLM 辅助分簇）、1.2.2 节（版本感知的簇内反馈借用）、1.4.3 节（C1 消融）。
* **具体改造步骤**：
  1. 在 `tasks/tasks.jsonl` 与 `events/request_context.jsonl` 中新增 **`cluster_id`** 字段（如 `cls_sales_01`），按 `(domain, 业务意图/指标类型)` 将 200 道题划分为约 **35–50 个语义簇**，确保每个高频语义簇包含 **3–6 道意图相近、共享部分底层指标/白皮书文档但参数或提问角度略异的题目**。
  2. 核查更新后时间窗口（尤其是 06:00 与 12:00 之后的请求）中，处于同一 `cluster_id` 且权限相容、版本一致的请求密度，确保新版本条目冷启动时能够真正从同簇其他条目借用到有效样本（$m > 0$）。

---

### 【P1-3】校准 40 次更新的主张级受影响规模与“局部修复 vs. 全量重生成”比例

* **现状与风险**：
  论文 **1.4.5 节（C3 更新与修复）** 写道：“共 40 个事件、**约 1,600 条受影响回答**”。但根据 `HANDBOOK.md §3.4 & §5.5`，当前 40 次更新中 6 条是 `codebook_revision` 零影响负对照，34 条真实更新中 24 条命中主张，且主张级最强事件 `u0019` 仅命中 68 条请求、5 条主张（而 `u0023` 是文档级 602 条、主张级 0 条）。若第 0 步体检显示 40 次更新累计的**主张级**受影响回答总数偏小（如不足 300 条），或缺乏“多主张大改需要回退到全量重生成”的样本，C3 实验中的成本分解与回退率统计会不够饱满。
* **对应论文章节**：1.1 节 M3 动机实验、1.3.2 节（选择性局部修复与回退）、1.4.5 节（C3 实验）。
* **具体改造步骤**：
  1. **保留 6 条 `codebook_revision` 负对照**以及 6–10 条“文档级引用但主张级 0 变更”的事件（如 `u0023`），确保“误触发率”和“粗粒度失效浪费”的论证依然犀利。
  2. **检查并适度增强主张级覆盖与分层**：若累计主张级受影响回答总数 $< 400$ 条，可在不改变 40 事件总数的前提下，微调部分 `metric_revision` / `lineage_switch` / `data_row_change` 事件所指向的热点文档块，使其覆盖更多高频热点题目的 `gold_fact_spans`；同时确保受影响回答中：
     - 约 **65%–75%** 仅涉及单条或少数主张变更（$\rho < 50\%$，适合 **局部修复**）；
     - 约 **25%–35%** 涉及多条主张或核心口径/推理链大改（适合检验 **回退至全量重生成**）。
  3. 在 `DATASET_CARD.md` 中明确给出最终实测的“文档级受影响总条数”与“主张级受影响总条数”，方便作者同步更新论文 1.4.5 节中的预期数字，做到全文口径 100% 一致。

---

### 【P2-1】补齐 60 条人工复核工具链与边界文档校准（答辩防质疑）

1. **人工复核辅助脚本（支撑 1.4.1 节一致率报告）**：
   - `labels/to_review.csv`（60 行）目前尚未人工标注。编写一个极简脚本 `dataset/tools/score_human_review.py`，读取作者填完人工判定列（`human_safe`）后的 CSV，自动计算规则/判官与人工标注的**一致率（Agreement %）**与 **Cohen's Kappa**，直接供论文 1.4.1 节引用。
2. **检索难度与权限口径说明核对**：
   - 若跑 M1/1.2.2 时发现由于模板文档措辞过于规整，导致 `rag` 向量检索 Top-$K$ 召回率接近 100%（测不出部分缺失与补检逻辑），可考虑在 `knowledge/build.py` 中为每个业务域增加少量同域近似干扰块（distractor chunks），使 Top-$K$ 检索具备真实的区分度。
   - 在 `DATASET_CARD.md` 中清晰写明 `N2_permission` 的语义（防止高密级缓存条目泄露给低密级请求，与 §5.4 谓词一致；同时如实说明底库检索侧不含硬拒绝样本），避免论文行文表述反了。

---

## 4. `dataset-v0.2.0` 交付验收清单（Release Checklist）

执行 Agent 完成优化后，须逐条确认以下 8 项全部 PASS，再向作者交付：

- [ ] **体检先行**：已生成并保留 `dataset/audit_v010_report.json`，所有优化均基于实测分布而非拍脑袋猜测。
- [ ] **契约同步**：已依次更新 `schema/`、`config/params.json`、`contracts/CHANGELOG.md`（记录 `v0.2.0` 全部变更）、`HANDBOOK.md` 与 `DATASET_CARD.md`。
- [ ] **时钟无歧义**：`docs_versioned.updated_at` 与 `update_events.timestamp` 的关系已按方案 A（或方案 B）彻底对齐，并写入 `verify.py` 新断言。
- [ ] **句向量与标定就绪**：已生成确定性句向量缓存 `dataset/events/query_embeddings.npz`；已写好 `dataset/tools/run_model_calibration.py` 并通过 `--dry-run` 测试（若已接真实 LLM，则确认 300 条实测与 MAPE 已回填；若未接 LLM，确认 `measured` 与 `mock=pending` 严格隔离、零伪造）。
- [ ] **`act`/`plan` 有梯度**：100 个 `act` 的 `downstream_tools` 非空占比 $\ge 50\%$ 且 $d_i$ 有清晰梯度；60 个 `plan` 的 `completion_rate` 有合理方差。
- [ ] **语义簇与更新面达标**：`tasks.jsonl` 与 `request_context.jsonl` 已补齐 `cluster_id`；40 次更新保留 6 条 `codebook_revision` 负对照，且主张级受影响回答总数与“局部改 vs. 大改”比例分布合理。
- [ ] **全量校验通过**：`python dataset/verify/verify.py --all` 全部断言 PASS（含本次新增断言），核心确定性文件连续两次构建哈希一致。
- [ ] **清单刷新**：已运行 `python dataset/tools/gen_manifest.py` 与 `python dataset/tools/stats.py`，并将 `v0.1.0` vs. `v0.2.0` 的关键统计对比汇总写入交付说明。
