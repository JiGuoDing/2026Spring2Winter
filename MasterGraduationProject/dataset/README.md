# 实验数据系统（dataset/）

面向"流式智能体缓存价值建模与生命周期控制"的实验数据系统。交付物不是一份静态数据集，
而是**可复现的生成器 + 已生成的 v0.3.0 实例（含 300 条真机标定）+ 单一口径的配置 + 分阶段验收器**。

文档入口：`REPORT.md`（数据集与实验全貌）、`HANDBOOK.md`（字段手册）、`AGENT_PLAYBOOK.md`（后续 Agent 工作规范）、`PAPER_MAP.md`（论文↔文件映射）。

## 当前状态

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 契约冻结 | schema、表目录、血缘、ID/随机规则、fixtures | 8 项断言通过 |
| P1 取数库 | 60 表、3 快照、只读执行器、结果比对器、36 项单测 | 6 项断言通过 |
| P2 知识层 | 2,000 文档 × 3 版本、13,770 块、1,360 条变更 | 6 项断言通过 |
| P3 题库 | 200 题、600 条主张、40 个语义簇 | 6 项断言通过 |
| P4 事件层 | 3,000 请求、40 更新（双时间戳）、5 种子流、2 长流 | 14 项断言通过 |
| P5 剖面与标签 | 6 路径成本表、300 双视角标签、120 配对 | 5 项断言通过 |
| P6 交付 | 数据集卡片、论文映射表、全量 MANIFEST、句向量状态 | 3 项断言通过 |

全量验收：`python dataset/verify/verify.py --all` → 48 项全 PASS。

**v0.3.0 状态**：模型阶段成本已用单卡 27B 实测回填（300 条请求 + 30 对分支），动机实验 M1/M2 已完成，报告见 `exp_motivation/RESULTS.md`。

## 快速开始

```bash
# 1. 契约（已固化，重跑幂等）
python dataset/tools/gen_catalog.py
python dataset/tools/gen_fixtures.py

# 2. 数据
python dataset/db/gen_schema.py && python dataset/db/build.py
python dataset/knowledge/build.py
python dataset/tasks/build.py
python dataset/events/build.py
python dataset/costs/runner.py
python dataset/labels/build.py
python dataset/tools/build_embeddings.py        # 句向量（需要模型缓存，可跳过）

# 3. 验收与清单
python dataset/verify/verify.py --all
python dataset/tools/gen_manifest.py
python dataset/tools/stats.py
python dataset/tools/audit_v010.py               # 体检报告

# 4. 投影到动机实验目录
python dataset/tools/stage_motivation.py
```

## 目录

| 目录 | 内容 | 写者 |
|---|---|---|
| `schema/` | 四类产出文件的 JSON Schema，字段唯一真源 | lead |
| `contracts/` | 表目录、血缘、协作规则、契约变更记录 | lead |
| `config/params.json` | 规模、阈值、种子、时间轴，全局唯一来源 | lead |
| `common/` | ID、随机数、读写哈希的唯一入口 | lead |
| `fixtures/` | 各文件样例，供上游未就绪时解耦开发 | lead |
| `db/` | 60 表库、v0/v1/v2 快照、只读执行器、结果比对器 | agent-db |
| `knowledge/` | 2,000 篇版本化知识文档与变更映射 | agent-knowledge |
| `tasks/` | 200 道取数题、gold SQL、三层真值 | agent-tasks |
| `events/` | 动机实验 5 个输入文件、请求流、更新事件、种子副本 | agent-events |
| `costs/` | 六条执行路径的成本表与测量脚本 | agent-cost |
| `labels/` | 双视角安全复用标签、分支配对、待复核清单 | agent-label |
| `embeddings/` | 真实句向量（600×512）与模型缓存 | agent-embed |
| `verify/` | 分阶段验收器，48 项断言 | lead |
| `tools/` | 目录生成、清单、统计、动机实验投影 | lead |

## 验收哲学

每阶段末跑 `verify.py --stage Pn`，不绿不许进下一阶段。断言覆盖：契约合规、规模达标、
同种子可复现、只读约束真实生效、引用完整性、无测试期泄漏、measured 与 mock 不混填。

## 研究诚信

- 凡由脚本构造的字段，在 `DATASET_CARD.md` 第三节标注 `constructed`；凡实测标注 `measured`。
- 模型相关的实测成本（`t_plan`、`t_rag`、`t_resp`、`token_cost`、生成与改写耗时）**不由本系统代造**，
  只提供模板、runner 与回填说明；未回填前，价值模型只有本地分量。
- 人工标注不代做，只提供 60 条待复核清单（`labels/to_review.csv`）。
- 详细边界见 `DATASET_CARD.md` 第八节"已知局限"。
