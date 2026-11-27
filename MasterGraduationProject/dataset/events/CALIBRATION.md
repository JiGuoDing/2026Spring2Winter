# 校准模板说明（real_calibration_300.template.csv）

这个文件只做一件事：把**能实测的那一段**测出来，把**必须由作者跑模型才能得到的列**留空。
列顺序固定为

```
req_id,t_plan_ms,t_rag_ms,t_act_ms,t_resp_ms,t_total_ms,token_cost
```

300 行，`req_id` 全部取自主请求流 `request_stream.jsonl`。

## 一、哪一列是实测，哪几列必须回填

| 列 | 归属 | 现状 | 依据 |
|---|---|---|---|
| `t_act_ms` | **measured** | 已逐条真实执行并计时 | 只依赖一次只读 SQL 在固定快照上的执行，本机可测 |
| `t_plan_ms` | 模型相关 | **留空** | 取决于规划模型与提示词，本系统不跑模型 |
| `t_rag_ms` | 模型相关 | **留空** | 取决于 embedding / 检索 / 重排模型 |
| `t_resp_ms` | 模型相关 | **留空** | 取决于回答模型、上下文长度、解码参数 |
| `t_total_ms` | 端到端 | **留空** | 由上面三段与调度开销共同决定，不可由分段相加替代 |
| `token_cost` | 模型相关 | **留空** | 取决于分词器与计量口径（prompt / completion / cached） |

留空的五列一律不写 0、不写占位均值、不写推算值：mock 与 measured 混填会直接毁掉
E4/E5 的服务时间-成本曲线。

## 二、样本是怎么抽的

- 抽样清单：`calibration_sample.jsonl`（300 行，字段 `req_id / timestamp / snapshot / task_id`）。
- 规则：先在主请求流里让 200 道题各出现一次，再从剩余请求里补 100 条，覆盖不同快照与不同改写。
  抽样只经 `common/seeds.py::rng("events", "calib_sample")`，同参数可复现。
- 每条记录都带上该请求自己的快照号：同一个题的 gold_sql 会分别在 v0 / v1 / v2 上执行，
  因此 `t_act_ms` 反映的是**该请求发生时**的数据规模，而不是固定用 v0。

## 三、`t_act_ms` 的测量口径

```
python dataset/events/calibrate.py            # 默认每个请求重复 3 次取中位数
python dataset/events/calibrate.py --reps 5   # 更稳，但更慢
python dataset/events/build.py --calibrate    # 先重建再校准
```

1. 用 `dataset/db/executor.py::execute(snapshot, gold_sql)` 执行该请求对应题目的 gold SQL；
2. 计时包含只读连接建立与 `PRAGMA query_only` 设置，即「一次 act 调用」的端到端耗时，
   不含 Python 侧结果序列化；
3. 单机、单进程、无并发；重复 `reps` 次取中位数，保留 3 位小数，单位毫秒；
4. 执行失败直接抛错并中止，不写任何兜底值（三个快照的 `execute` 均已被 P1 验收覆盖）。

`t_act_ms` 是**机器相关**的：换机器、换负载会得到不同数值，重跑 `calibrate.py` 会改变
CSV 的 sha256。`MANIFEST.json` 里该文件带 `"measured": true` 标记，与构造产物区分。

## 四、作者如何回填其余五列

对每一行 `req_id`：

1. 在 `request_stream.jsonl` 里取出该请求（`query_text`、`plan_id`、`act_key`、
   `gold_doc_ids`、`snapshot`），在 `request_context.jsonl` 里取出源题 `task_id`、租户、改写序号；
2. 用你选定的模型与配置跑**同一条请求**的四段：
   - `t_plan_ms`：规划段（选 plan / 展开步骤）耗时；
   - `t_rag_ms`：检索段（query 编码 + 召回 + 重排）耗时；
   - `t_act_ms`：直接用本文件已有实测值，**不要再测一遍**，否则同一列出现两套计时口径；
   - `t_resp_ms`：回答生成段（含工具结果回填后的续写）耗时；
3. `t_total_ms` 用端到端墙钟时间单独测，不要用四段相加冒充（并发、排队、缓存命中都会偏离）；
4. `token_cost` 记录计量口径：至少注明是 prompt+completion 合计还是仅 completion，
   是否含缓存命中 token，计价单位（token 数或折算金额）；
5. 回填时保持 `req_id` 原样、行序不变、只改空格子；回填完成的文件另存为
   `real_calibration_300.csv`（去掉 `.template`），不要覆盖模板。

## 五、回填后的自检

- 五列不得出现 `NA` / `-1` / 空以外的占位；未测就继续留空，并在实验记录里写明缺失条数；
- `t_total_ms ≥ max(t_plan_ms, t_rag_ms, t_act_ms, t_resp_ms)`；
- `token_cost` 与 `t_resp_ms` 的相关系数应在合理范围；若为 0，多半是计量口径写错；
- 分段之和与 `t_total_ms` 的差值（调度开销）应稳定，突增说明有并发干扰。

## 六、v0.2.0 重建时的处理

v0.2.0 重建请求流后，`calibration_sample.jsonl` 的 300 个 `req_id` 序列与旧版**逐条相同**
（抽样只依赖题号与到达次序，不依赖主张文本）。因此本模板**原样保留**，`t_act_ms` 仍是上一轮在本机
用 `db/executor.py` 真实执行 gold_sql 的实测中位数，没有重测、也没有改动：

- `build.py` 重建时只校验“模板 req_id 序列 == 抽样清单”，不一致会直接报错并提示跑 `calibrate.py`，
  绝不静默沿用旧值或编造新值；
- 若将来题号/到达次序变化导致 req_id 集合变化，必须运行
  `python dataset/events/calibrate.py` 真实重测（会改变 CSV 哈希），再更新 `MANIFEST.json` 记录；
- `MANIFEST.json` 中该文件的记录带 `"measured": true` 与「重测会改变哈希」的容差说明。
