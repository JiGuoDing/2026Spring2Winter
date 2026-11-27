# 后续 Agent 工作手册（Playbook）

> 读者：接下来要在本数据集上写实验脚本、实现缓存策略、跑 A–F 实验的 Agent。
> 本文不重复数据字段说明（看 `HANDBOOK.md`），只讲**怎么干、别干什么、干完怎么交**。
> 版本：dataset-v0.3.0 · 2026-11-26

---

## 0. 开工前 20 分钟

按顺序读，不要跳：

| 顺序 | 文档 | 重点 |
|---|---|---|
| 1 | `dataset/REPORT.md` §4、§7、§8 | 数据模型、已完成实验、未完成清单 |
| 2 | `dataset/HANDBOOK.md` §2、§3、§6 | 字段、双时间戳、不变量 |
| 3 | `dataset/PAPER_MAP.md` | 每个实验读哪些文件、哪些列 |
| 4 | `dataset/contracts/CHANGELOG.md` | 最近改了什么、为什么 |
| 5 | 本文 §2、§3 | 铁律与分工 |

**先跑一遍**：`python dataset/verify/verify.py --all`，确认 48 项全绿再动手。基线不绿时写任何实验都没有意义。

---

## 1. 三条铁律

### 铁律一：数据集只读

`dataset/` 下除 `embeddings/calibration/`（标定过程产物）外，一律**只读**。
实验代码写 `exp_*/`，结果写 `exp_*/results/`，不要把中间产物写回 `dataset/`。

确实发现数据缺陷时，走契约流程（见 §8），不要直接改文件。

### 铁律二：测量口径不可混

- `measured`（真机测量）与 `mock=pending` / `assumed`（假设）**永远分列**，不混进同一个表格单元格；
- TTL、命中率等指标必须注明样本量 n、种子、是否含模型段；
- 一个 CSV 里只放同一口径的数，不同口径分文件。

### 铁律三：复用判定只用一个实现

判定"能否安全复用"必须 `import` 数据集自带的谓词：

```python
import sys; sys.path.insert(0, "dataset/labels")
import build as labels_build
ds = labels_build.Dataset()
safe = labels_build.view_judge(ds, cached_req, req, "truth")["safe"]      # 真值视角
safe_sys = labels_build.view_judge(ds, cached_req, req, "system")["safe"]  # 系统视角
```

不要自己重写一套版本比较逻辑。重写即口径分裂，两组实验的数字将不可比。

---

## 2. 文件所有权与并行分工

多个 Agent 并行时按下表分目录，一个目录只有一个写者：

| 目录 | 写者 | 内容 |
|---|---|---|
| `dataset/`（除 calibration） | lead 独占 | schema / config / common / 数据文件 |
| `dataset/embeddings/calibration/` | 标定执行者 | 标定进度与元数据 |
| `exp_motivation/` | 动机实验 agent | M1/M2/M3 脚本与结果 |
| `exp_cache/replay/` | 回放器 agent | 请求流回放、缓存模拟器 |
| `exp_cache/policies/` | 策略 agent | LRU / TTL / 值驱动 策略实现 |
| `exp_cache/results/` | 分析 agent | 实验结果 CSV、图、摘要 |
| `exp_cache/README.md` | lead 汇总 | 实验总览 |

**接口先定、再并行**：回放器向策略暴露的接口应在写策略之前确定，例如
`policy.on_request(req, ctx) -> Decision(use_cached: bool, key: str)`、
`policy.on_insert(obj) -> None`、`policy.evict(capacity)`。
接口变更要通知所有使用方。

---

## 3. 实验实现的推荐顺序与最小验收

依赖关系：**A–B（回放器 + 基线）→ C（值驱动策略）→ D（双层提升）→ E（更新与修复）→ F（长流原型）**。
D 依赖 A–B 的回放器；E 依赖 B 的有效性检查；F 只做规模化，不改变方法。

### A 缓存机会与管理税

| 项 | 要求 |
|---|---|
| 输入 | `tasks/tasks.jsonl`、`events/request_stream.jsonl`、`db/snapshots/*.sqlite` |
| 产出 | `hits / misses / management_cost_ms / hit_rate` |
| 最小验收 | `hits + misses == 3000`；管理税单列统计，不与收益混算 |
| 常见坑 | 把"命中"当"有效命中"；管理税只算查找不算版本校验 |

### B 候选检索与有效性检查

| 项 | 要求 |
|---|---|
| 输入 | `knowledge/docs.jsonl`、`events/update_events.jsonl`、`labels/safe_reuse.jsonl` |
| 产出 | 有效命中率、过期误用率、误拒率 |
| 最小验收 | 随机抽 30 对判定结果与 `view_judge` **100% 一致**；误用率与有效命中率同时报 |
| 常见坑 | 只报命中率不报误用率；用语义相似度替代版本校验 |

### C 值驱动准入/保留

| 项 | 要求 |
|---|---|
| 输入 | `costs/path_costs.csv`（实测段）+ `events/streams/seed*.jsonl` |
| 产出 | 容量档位（`params.json: 0.25/0.5/0.75`）× 命中率 / 有效命中率 / 累计收益 |
| 最小验收 | 每档至少跑 **5 个种子**（seed42–46），报均值 ± 标准差；基线（LRU/TTL）同表对照 |
| 常见坑 | 单种子结论；用 token 数当金额；忽略管理税 |

### D `resp` 双层提升

| 项 | 要求 |
|---|---|
| 输入 | `labels/branch_pairs.jsonl`（注意只有 30/120 回填）、`labels/safe_reuse.jsonl` |
| 产出 | 只复用 rag/act 再重算 resp 的净收益（分别报省时与省 token） |
| 最小验收 | 分支数据只用已回填的 30 对，其余标 `unavailable`，不得补造 |
| 常见坑 | 把"省 token"说成"省时"；用未回填的配对算平均 |

### E 更新与依赖修复

| 项 | 要求 |
|---|---|
| 输入 | `events/update_events.jsonl`（双时间戳）、`tasks/tasks.jsonl` 的主张证据 |
| 产出 | 局部修复 vs 全量再生 的分层收益（按 ρ 分层：<0.5 局部 / ≥0.5 全量） |
| 最小验收 | 用 `effective_at` 判真值、`timestamp` 判系统可见性，两者不混；40 条事件全部纳入或说明排除理由 |
| 常见坑 | 用 `updated_at` 当"系统知道"的时刻 |

### F 组合长流 / 原型

| 项 | 要求 |
|---|---|
| 输入 | `events/streams/long_01,long_02.jsonl`（各 5,000） |
| 产出 | 规模化后的稳定性（命中率漂移、内存增长） |
| 最小验收 | 与 seed42 的结果对比，说明规模效应方向 |
| 常见坑 | 用 long 流的绝对数直接与 seed 流比较而不说明长度差异 |

---

## 4. 实验脚本骨架

```python
"""<实验名>：<一句话目的>。只读 dataset/，输出写 exp_x/results/。"""
import csv, json, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "dataset"
sys.path.insert(0, str(DATASET))
sys.path.insert(0, str(DATASET / "labels"))
import build as labels_build          # 唯一复用判定实现
from common import io                 # 唯一 IO 实现

def main() -> int:
    ds = labels_build.Dataset()
    reqs = sorted(ds.reqs, key=lambda r: (r["timestamp"], r["req_id"]))
    # ... 实验逻辑 ...
    # 输出必须自带口径：样本量、种子、是否含模型段
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

硬性要求：

1. 时间只用 `req["timestamp"]`（ISO8601 Z），不要自己 `datetime.now()`；
2. 随机只用固定种子（`common/seeds.py::rng` 或显式 `random.Random(42)`），并在输出里记下种子；
3. 结果 CSV 第一行是列名，列名自解释（`hit_rate_pct` 而不是 `hr`）；
4. 每个结果旁边写一份同名 `.md` 摘要：口径、样本量、结论、有效性威胁、复现命令。

---

## 5. 指标口径规范

| 指标 | 定义 | 必须附带 |
|---|---|---|
| 命中率 | 复用次数 / 请求数 | n、策略、容量 |
| **有效命中率** | 安全复用次数 / 请求数 | 判定视角（truth / system） |
| **过期误用率** | 不安全复用次数 / 请求数 | 同上；与有效命中率必须同时报 |
| 管理税 | 查找 + 版本校验耗时 | 单列，不与收益合并 |
| 时延 | p50 与 p95 同时报 | 是否含模型段、是否 warmup |
| 收益 | 省时（ms）与省 token 分开 | 单价假设（若要换算金额） |

**不要只报均值。** 本数据集的 resp 时延 p50=98.6 s、p95=443.2 s，均值 147.1 s，三者差异巨大。

---

## 6. 常见错误 Top 12

| 错误 | 后果 | 正确做法 |
|---|---|---|
| 把 `mock=pending` 当实测 | 结论建立在空值上 | 先查 `measured` / `mock` 两列 |
| `safe` 与 `safe_system` 混报 | 过期误用被算成 0 | 明确标注视角 |
| 自己重写复用谓词 | 与标签口径分裂 | `import labels/build.py::view_judge` |
| 用 `task_id` 当缓存键 | 忽略快照/版本/权限/时间窗 | 键 = 题 + 口径 + 时间窗 + 快照 + 权限 + 时刻 |
| 读 `request_stream["query_emb"]` | 恒为 null | `io.embedding_lookup(query_text)` |
| 用 `updated_at` 判"系统是否知道" | 把通知延迟算成策略缺陷 | 系统视角用 `timestamp` |
| `token_cost` 当金额 | 成本结论错 | 它是 token 数；换算需单价 |
| 单种子 / 单流下结论 | 偶然性无法排除 | seed42–46 均值±std |
| 无 warmup 测首条 | 冷启动污染 p95 | 预热 2–3 次并排除 |
| 认为 120 对分支都已回填 | 用空值算出错误均值 | 只有 30 对可用 |
| 改 params/seed 让结果好看 | 数据失真且不可复现 | 禁止；契约流程变更 |
| 把 verify 全绿当实验正确 | 混淆一致性校验与结论正确性 | 校验只保证数据自洽 |

---

## 7. 遇到数据集缺陷怎么办

发现缺口（例如需要工具失败事件）时，走五步，不要先改数据：

1. **写清缺口**：缺什么字段、阻断哪个实验、影响多大；
2. **提案**：改 `schema/` 还是新增文件？是否需要 `params.json` 新键？
3. **同步 lead**：由 lead 改 `schema/`、`config/`、`common/`；
4. **登记**：`contracts/CHANGELOG.md` 写原因、影响范围、需要重跑哪些产物；
5. **验证**：断言只增不减，重跑 `verify.py --all`，更新 `MANIFEST.json`。

版本号规则：只改文档/补说明 → PATCH；加字段/加文件 → MINOR（如 v0.4.0）；改语义/破坏兼容 → MAJOR。

---

## 8. 交付与交接清单

每次交结果前逐项确认：

- [ ] 结果 CSV 与 `.md` 摘要都写了口径（n、种子、是否含模型段、measured/assumed）；
- [ ] 复现命令能从空环境一次跑通；
- [ ] 没有把实验中间产物写进 `dataset/`；
- [ ] 与 `view_judge` 的一致性抽检通过（若涉及复用判定）；
- [ ] `verify.py --all` 仍 48 项全绿；
- [ ] 若改了数据集，`CHANGELOG.md`、`MANIFEST.json`、`REPORT.md` §8 状态已同步。

交接给 lead 时说明三件事：**做了什么、数字是什么、还有什么没做**。

---

## 9. 禁忌清单

1. 不得把假设值（`assumed`）写成实测（`measured`）；
2. 不得修改 `config/params.json` 的种子、规模、目标区间来让结果好看；
3. 不得删除或覆盖 `embeddings/calibration/archive_*/` 下的作废归档（它们是审计证据）；
4. 不得在未通知的情况下改 `schema/`、`common/`、`labels/build.py`；
5. 不得在论文或报告里给出**未跑过**的实验结论；
6. 不得把 `fixtures/` 的小样本结果当作数据集结论。

---

## 10. 实验 A–F 的状态（接手时先看这里）

| 编号 | 状态 | 下一步 |
|---|---|---|
| M1 异质开销与重复率 | **已完成** | 多种子复跑后定稿 |
| M2 静态基线两难 | **已完成** | 同上 |
| M3 工具成本敏感性 | **已完成**（假设参数） | 补工具失败事件后升级为可回放 |
| A 缓存机会与管理税 | 未开始 | 先写回放器 |
| B 候选检索与有效性检查 | 未开始 | 依赖 A 的回放器 |
| C 值驱动准入/保留 | 未开始 | 依赖 A–B，需 5 种子 |
| D `resp` 双层提升 | 未开始 | 分支数据仅 30 对可用 |
| E 更新与依赖修复 | 未开始 | 需按 ρ 分层 |
| F 组合长流 | 未开始 | 可选 |

结果统一放 `exp_*/results/`，汇报格式见 §8。
