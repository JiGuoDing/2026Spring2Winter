# 模型标定：把 `mock=pending` 变成 `measured`

这一步补的是**作者自己的实验测量**，不是数据构造。凭据只在本机读取，不进入任何数据集产物。

## 一、准备（你来做）

1. 复制模板：`dataset/.env.example` → `dataset/.env`
2. 填四行（值只有你知道，不要贴到聊天窗口）：

```ini
LLM_BASE_URL=http://127.0.0.1:11434/v1      # Ollama；vLLM 用 :8000/v1；云服务填厂商地址
LLM_API_KEY=sk-...                           # 目标为 localhost 时可留空
LLM_MODEL_SMALL=qwen2.5-7b-instruct          # 对齐成本表 local-small-7b 行
LLM_MODEL_LARGE=                             # 对齐 api-large-placeholder 行，没有就留空
```

只填一个模型也可以：另一个档案的两行会**保持 `mock=pending`**，这是如实记录，不是缺陷。

## 二、运行（我来做，或你自己跑）

```bash
# 1. 校验（不联网、不写任何 measured 值）
python dataset/tools/run_calibration_from_env.py --dry-run

# 2. 试跑 5 条（不写回，只看量级与接口是否通）
python dataset/tools/run_calibration_from_env.py --limit 5

# 3. 全量（两个档案各一轮，约 600–660 次调用/档案）
python dataset/tools/run_calibration_from_env.py

# 4. 中断后续跑（每完成一条已落盘，不会重跑）
python dataset/tools/run_calibration_from_env.py --alias small --resume
```

### 实测耗时（2026-11-25，单卡 27B，串行，**用户指定配置，禁止擅自修改**）

生成参数（由用户指定，未经同步不得改动）：

| 参数 | 值 |
|---|---|
| `LLM_MAX_TOKENS_RESP` / `_PLAN` / `_CACHE` | **32768** |
| `LLM_CONTEXT_WINDOW` | **65536** |
| `LLM_REASONING_EFFORT` | **xhigh** |
| `temperature` | 0 |
| `LLM_TIMEOUT_S` / `LLM_MAX_RETRIES` | 2700 / 2 |

后果（已实测）：约 1/6–1/3 的请求会"生成到上限"，单条约 **38 分钟**（32768 token @ ~15 tok/s）；
这类请求可能整段输出为空（思考占满预算）。全量预计 **45–75 小时**（2–3 天），可断点续跑。

> **规则**：任何生成参数（max_tokens / 上下文 / 推理强度 / 超时 / 重试）的调整，
> 必须先与作者同步并取得同意，不得由执行方自行下调。此前擅自把上限降到 4096 属违规操作，
> 相关数据已归档到 `embeddings/calibration/archive_config_4096/`，不参与统计。

**一个必须写进论文的发现**：旧配置把 resp 截断在 512 token，而模型实际需要约 3,000 token。
按旧配置标定会把端到端时延系统性低估约 5 倍。因此本轮标定采用无截断配置，
`token_cost` 包含思考 token（服务端 `usage.completion_tokens` 计入了 reasoning 部分）。

结论：这是**串行、单请求、无截断**口径，对应用户可见的端到端时延；不要用并发压测替代。
中途失败不影响已完成的请求——进度写在 `embeddings/calibration/requests_progress.jsonl`，
加 `--resume` 即从断点继续。旧配置下的 46 条测量已归档到
`embeddings/calibration/archive_config_v1/`，仅作对照，不参与本轮统计。

**模型命名**：当前把 27B 模型放在 `local-small-7b` 这个**槽位**里跑（单卡只能部署一个）。
跑完会把这批行的模型列改成真实模型名（如 `local-qwen3-8-27b`），并同步文档，避免"7b"这个错标签。
大模型到位后，用 `LLM_MODEL_LARGE` 填 `api-large-placeholder` 槽位再跑一轮即可补齐另外两行。

产物：

| 文件 | 变化 |
|---|---|
| `events/real_calibration_300.csv` | 7 列填满（`t_act_ms` 沿用模板实测） |
| `costs/path_costs.csv` | 对应档案 2 行 `mock=pending` → `measured` |
| `labels/branch_pairs.jsonl` | 30 对抽样回填 `t_model_full_ms` / `t_model_cache_ms` / `g_e2e_ms` |
| `embeddings/calibration/` | 过程明细（`requests.jsonl` / `run_meta.json` 等） |
| 控制台 | 建模时延 vs 实测时延的 MAPE |

## 三、跑完（我来做）

1. 校验列完整、`measured`/`mock` 不混填、行数 300；
2. 合并两次运行（如分两次跑），核对 `costs` 四行状态；
3. 更新 `DATASET_CARD.md` / `HANDBOOK.md` / `PAPER_MAP.md` 的实测口径；
4. 升版 `v0.3.0`，跑 `verify.py --all`（48 项）确认只增不减；
5. 输出“建模 vs 实测”对照表，可直接进论文 1.4.1。

## 四、安全

- `dataset/.env` 已加入 `.gitignore`，但**本仓库当前没有 `.git`**，仍请勿把该文件复制到别处。
- 跑完立即删除 `dataset/.env`；若曾以任何形式外泄（截图、聊天、临时文件），请轮换 key。
- 包装脚本只打印 scheme+host 与“已提供”，不打印 key；子脚本输出里也不含 key。

## 五、口径提醒（写论文时必须写清）

- `token_cost` 是 **token 数**（plan+resp 的 prompt+completion 合计），不是金额。论文报“推理成本”需另给单价假设与日期。
- 模型耗时是**单次实测**，`temperature=0` 也不保证逐字节复现；同参数重跑数值会变，属正常。要报均值请每个档案跑 3 次取中位数（`--out-csv` 分别输出后合并）。
- `t_model_cache_ms` 用短上下文 resp 近似（脚本 `note` 已记录该口径）。
- `--act-source template` 复用模板实测的 `t_act_ms`；要重测 SQL 执行段用 `--act-source local`。
