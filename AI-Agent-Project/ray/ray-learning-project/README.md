# Ray 学习项目 —— 从 Flink 到 Ray 的半天速通指南

## 项目概述

本学习项目专为**有 Flink 背景的开发者**设计，通过 5 个渐进式 Python 文件，在半天内系统掌握 Ray 的核心概念与用法。

**每个文件都是独立可运行的**，包含：
- 完整的可运行代码
- 详尽的中文注释（API 用途、运行机制、设计意图）
- Flink 类比说明（每个 Ray 概念都对应到熟悉的 Flink 概念）
- 面试问题 + 参考答案

## 快速开始

```bash
# 1. 安装 Ray
pip install ray

# 2. 按顺序运行
python 00_hello_ray.py      # ~3 分钟
python 01_remote_tasks.py    # ~5 分钟
python 02_actor_model.py     # ~8 分钟
python 03_resource_management.py  # ~5 分钟
python 04_data_pipeline.py   # ~10 分钟
```

## 课程结构

| 文件 | 主题 | Flink 类比核心 | 关键收获 |
|------|------|---------------|----------|
| `00_hello_ray.py` | Hello Ray | JobManager/TaskManager, MapFunction | 理解 Ray 运行模型 |
| `01_remote_tasks.py` | 远程任务与 DAG | Operator Chain, JobGraph | 掌握动态 DAG 构建 |
| `02_actor_model.py` | Actor 模型 | KeyedState, RichFunction | 有状态分布式计算 |
| `03_resource_management.py` | 资源管理 | TaskSlot, SlotSharingGroup | 资源精细化控制 |
| `04_data_pipeline.py` | 完整流水线 | 完整的 Flink Job | 综合实践 |

## 知识点覆盖

### 第零课：Hello Ray
- [x] `ray.init()` 启动/连接集群
- [x] `@ray.remote` 装饰器
- [x] `ray.get()` / `ray.put()` 与 ObjectRef
- [x] 并行执行模式（串行 vs 并行）
- [x] Object Store 基础
- [x] 任务间依赖（隐式 DAG）
- [x] `ray.wait()` 非阻塞等待

### 第一课：远程任务与分布式 DAG
- [x] 任务参数传递机制（传值 vs 传引用）
- [x] 动态 DAG（条件分支、循环展开）
- [x] 嵌套远程任务（递归并行/分治）
- [x] 任务粒度实验（最佳并行度分析）
- [x] 任务重试（`max_retries`）
- [x] 投机执行（`ray.wait` 高级用法）
- [x] Ray 调度 vs Flink 调度可视化对比

### 第二课：Actor 模型
- [x] 有状态计数器（Actor 基础）
- [x] `concurrency_groups` 并发控制
- [x] Actor 生命周期（创建/存活/销毁）
- [x] Actor 替代 KeyedState（按用户聚合）
- [x] Actor 间协作（Coordinator-Worker 模式）
- [x] max_concurrency vs Flink parallelism 对比

### 第三课：资源管理
- [x] `num_cpus` / `num_gpus` 资源请求
- [x] 自定义资源（`resources={"db_connections": 1}`）
- [x] Placement Group（资源预留与共置）
- [x] `PACK` / `SPREAD` / `STRICT_PACK` / `STRICT_SPREAD` 策略
- [x] Actor GPU 绑定（推理服务模拟）
- [x] Ray 资源模型 vs Flink Slot 模型深度对比

### 第四课：完整数据处理流水线
- [x] 模拟广告点击日志生成
- [x] 分布式日志清洗（过滤 + 标准化）
- [x] 按广告主维度聚合（类似 Window + KeyBy）
- [x] 异常检测 Actor（滑动窗口 + 基线对比）
- [x] 结果存储 Actor（JSONL 文件写入）
- [x] 监控面板 Actor（实时吞吐/延迟指标）
- [x] 全流程可视化（进度条 + 仪表盘）

## 面试问题清单（共 21 题）

| 编号 | 问题 | 所在文件 |
|------|------|----------|
| Q1 | @ray.remote 和 Flink DataStream.map() 的本质区别 | `00_hello_ray.py` |
| Q2 | ray.put() 和 ray.get() 的使用场景 | `00_hello_ray.py` |
| Q3 | Object Store 与 Flink State Backend 的区别 | `00_hello_ray.py` |
| Q4 | ray.wait() 的实际应用场景 | `00_hello_ray.py` |
| Q5 | Remote task 和 Flink 算子实例的本质区别 | `01_remote_tasks.py` |
| Q6 | Ray 中访问外部数据库的方式（vs Flink AsyncIO） | `01_remote_tasks.py` |
| Q7 | Ray 适合但 Flink 不适合的场景 | `01_remote_tasks.py` |
| Q8 | Ray 任务调度开销与粒度判断 | `01_remote_tasks.py` |
| Q9 | Actor 与 Flink KeyedState 的核心区别 | `02_actor_model.py` |
| Q10 | max_concurrency 和 Flink parallelism 的区别 | `02_actor_model.py` |
| Q11 | 什么场景用 Ray Actor 而非 Flink | `02_actor_model.py` |
| Q12 | Actor 间互相调用的风险 | `02_actor_model.py` |
| Q13 | num_cpus 和 Flink TaskSlot 的本质区别 | `03_resource_management.py` |
| Q14 | Placement Group 的使用场景 | `03_resource_management.py` |
| Q15 | 超额提交任务的后果 | `03_resource_management.py` |
| Q16 | Flink Slot 与 Ray PG 资源利用率差异 | `03_resource_management.py` |
| Q17 | 设计系统时选 Ray 还是 Flink 的判断标准 | `04_data_pipeline.py` |
| Q18 | 异常检测为何用 Actor 而非 remote task | `04_data_pipeline.py` |
| Q19 | Ray 中如何实现 Flink Watermark 效果 | `04_data_pipeline.py` |
| Q20 | Ray 故障恢复 vs Flink Checkpoint | `04_data_pipeline.py` |
| Q21 | Object Store 内存溢出处理 | `04_data_pipeline.py` |

## Ray vs Flink 速查表

```
选 Ray 时：
  ✓ 灵活批处理、ML 训练推理、动态 DAG
  ✓ Python 生态深度集成
  ✓ 交互式开发 / 探索性分析
  ✓ 秒级延迟可接受

选 Flink 时：
  ✓ 毫秒级实时流处理
  ✓ Exactly-Once 语义必须保证
  ✓ 复杂 Event Time / Window / Watermark
  ✓ SQL 驱动的流分析
  ✓ 已有 JVM 基础设施

两者协作：
  Flink(实时ETL) → Kafka → Ray(ML推理)
  Ray(模型训练) → 模型文件 → Flink(在线预测)
```

## 学习建议

1. **不要在 IDE 里"读"代码** —— 直接 `python 00_hello_ray.py` 运行，观察输出
2. **修改参数实验** —— 改 `num_batches`、`batch_size`、`parallel_cleaners` 看效果
3. **打断点调试** —— 在 `ray.get()` 前后加断点，理解异步调用模型
4. **主动回答面试题** —— 看题 → 自己回答 → 对比参考答案
5. **画对比图** —— 把你理解的 Flink 架构画出来，对照画出 Ray 的架构

## 输出文件

运行 `04_data_pipeline.py` 后，会在 `./ray_pipeline_output/` 目录生成：
- `stats.jsonl` —— 按广告主的聚合统计结果
- `alerts.jsonl` —— 异常点击告警记录
