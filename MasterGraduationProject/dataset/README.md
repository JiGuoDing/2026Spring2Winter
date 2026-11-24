# 实验数据系统（dataset/）

面向"流式智能体缓存价值建模与生命周期控制"的实验数据系统。目标不是交付一份静态数据集，
而是交付**可复现的生成器 + 可验收的实例 + 单一口径的配置**。

## 快速开始

```bash
python dataset/tools/gen_catalog.py      # 生成 60 表目录与血缘（已固化在 contracts/）
python dataset/tools/gen_fixtures.py     # 生成脱耦开发用的样例
python dataset/db/gen_schema.py          # 由目录生成 DDL
python dataset/db/build.py               # 构建 v0/v1/v2 三个快照
python dataset/knowledge/build.py        # 生成 2000 文档 × 3 版本
python dataset/tasks/build.py            # 生成 200 题与 gold 结果
python dataset/events/build.py           # 生成 5 个动机实验输入文件
python dataset/verify/verify.py --all    # 全量验收
```

## 目录

| 目录 | 内容 | 写者 |
|---|---|---|
| `schema/` | 四类产出文件的 JSON Schema，字段唯一真源 | lead |
| `contracts/` | 表目录、血缘、协作规则、变更记录 | lead |
| `config/params.json` | 规模、阈值、种子、时间轴，全局唯一来源 | lead |
| `common/` | ID、随机数、读写哈希的唯一入口 | lead |
| `fixtures/` | 各文件 3 条样例，供上游未就绪时开发 | lead |
| `db/` | 60 表库、v0/v1/v2 快照、只读执行器、结果比对器 | agent-db |
| `knowledge/` | 2000 篇版本化知识文档与变更映射 | agent-knowledge |
| `tasks/` | 200 道取数题、gold SQL、三层真值 | agent-tasks |
| `events/` | 动机实验 5 个输入文件、请求流、更新事件 | agent-events |
| `costs/` | 六条执行路径的成本表与测量脚本 | agent-cost |
| `labels/` | 安全复用标签与分支配对 | agent-label |
| `verify/` | 分阶段验收器 | lead |

## 验收哲学

每阶段末跑 `verify.py --stage Pn`，不绿不许进下一阶段。断言覆盖：契约合规、规模达标、
同种子可复现、只读约束真实生效、覆盖矩阵无空格、无测试期泄漏、measured 与 mock 不混填。

## 研究诚信

- 凡由脚本构造的字段，在 `DATASET_CARD.md` 中标注 `constructed`；凡实测量测的标注 `measured`。
- 模型相关的实测成本（`t_rag`、`t_resp`、`token_cost`）不由本系统代造，只提供模板与 runner。
- 人工标注不代做，只提供待复核清单与模板。
