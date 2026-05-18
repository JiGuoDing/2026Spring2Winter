# Ray Data 2 天速学计划

> 本计划对应 `ray-data-learning/` 项目，按模块逐步推进，每天约 4-5 小时。

---

## Day 1：基础与核心 API（上午 + 下午）

### 上午（2.5h）：环境搭建 + 基础操作

| 时间 | 内容 | 对应文件 | 要点 |
|------|------|---------|------|
| 30min | 环境搭建 | `requirements.txt`, `scripts/generate_data.py` | 安装依赖、生成示例数据 |
| 30min | 快速入门 | `examples/00_quick_start.py` | Ray 初始化、Dataset 创建、show/take/count/schema |
| 30min | 创建 Dataset | `examples/01_create_dataset.py` | 从 list/pandas/numpy/Arrow/CSV/JSON/Parquet 创建 |
| 30min | 读写数据 | `examples/02_read_write.py` | CSV/JSON/Parquet 读写，格式选择建议 |
| 30min | 核心概念 | `docs/concepts.md` | Dataset、Block、Task、Lazy Execution |

**Day 1 上午检查点**：
- [ ] 能独立创建 Dataset（至少 3 种方式）
- [ ] 能读写 CSV/Parquet 文件
- [ ] 理解 Block 和 Lazy Execution 概念

---

### 下午（2.5h）：转换操作 + 批量处理

| 时间 | 内容 | 对应文件 | 要点 |
|------|------|---------|------|
| 40min | 数据转换 | `examples/03_transform.py` | map/flat_map/filter、缺失值处理、类型转换 |
| 40min | map_batches | `examples/04_map_batches.py` | pandas/numpy/pyarrow batch format、batch_size |
| 30min | 惰性执行 | `examples/05_lazy_execution.py` | 惰性 vs 触发执行、materialize |
| 40min | 练习：ETL | `projects/etl_pipeline/main.py` | 完整 ETL 流程：读取→清洗→转换→输出 |

**Day 1 下午检查点**：
- [ ] 理解 map 与 map_batches 的区别
- [ ] 能处理缺失值和类型转换
- [ ] 知道何时触发执行、何时使用 materialize
- [ ] 完成 ETL Pipeline 项目

---

## Day 2：高级特性 + 综合实践（上午 + 下午）

### 上午（2.5h）：聚合、并行、生态集成

| 时间 | 内容 | 对应文件 | 要点 |
|------|------|---------|------|
| 40min | groupby/shuffle | `examples/06_groupby_shuffle.py` | 分组聚合、sort、repartition、shuffle 成本 |
| 40min | 并行控制 | `examples/07_parallelism.py` | parallelism、concurrency、num_cpus |
| 40min | 生态集成 | `examples/08_interop.py` | pandas/numpy/pyarrow/sklearn 互转与集成 |
| 30min | API 速查 | `docs/api_cheatsheet.md` | 熟悉常用 API，建立速查习惯 |

**Day 2 上午检查点**：
- [ ] 能使用 groupby 进行聚合统计
- [ ] 理解 shuffle 成本和优化方法
- [ ] 能在 Ray Data 中使用 pandas/numpy

---

### 下午（2.5h）：批量推理 + 调试 + 综合项目

| 时间 | 内容 | 对应文件 | 要点 |
|------|------|---------|------|
| 30min | 批量推理 | `examples/09_batch_inference.py` | map_batches 批量预测、GPU 扩展说明 |
| 30min | 调试技巧 | `examples/10_debugging.py` | Schema 问题、脏数据、OOM、版本差异 |
| 30min | 性能优化 | `docs/performance_tuning.md` | batch_size、并行度、物化策略、格式选择 |
| 30min | 常见坑 | `docs/common_pitfalls.md` | 总结高频踩坑点 |
| 30min | 练习：特征工程 | `projects/feature_engineering/main.py` | 用户行为特征提取、shuffle 实践 |

**Day 2 下午检查点**：
- [ ] 能用 map_batches 做批量预测
- [ ] 知道常见错误的排查方法
- [ ] 完成特征工程项目
- [ ] 能说出 3 个性能优化要点

---

## 快速参考

### 运行命令

```bash
# 环境准备
cd ray-data-learning
pip install -r requirements.txt

# 生成数据
python scripts/generate_data.py

# 运行示例（按顺序）
python examples/00_quick_start.py
python examples/01_create_dataset.py
# ... 依次运行

# 运行项目
python projects/etl_pipeline/main.py
python projects/feature_engineering/main.py
python projects/batch_inference/main.py

# 运行测试
pytest
```

### 核心 API 速记

```
创建:  from_items / from_pandas / read_csv / read_parquet
查看:  show / take / count / schema / columns
转换:  map / flat_map / filter / map_batches
聚合:  groupby().count() / sum() / mean() / map_groups()
排序:  sort / repartition / random_shuffle
输出:  write_parquet / write_csv / to_pandas / to_arrow
控制:  materialize / iter_batches / num_blocks
```

### 学完后的能力

完成 2 天学习后，你将能够：
1. 使用 Ray Data 处理中等规模数据集
2. 编写 ETL 流程和特征工程管道
3. 使用 map_batches 进行批量推理
4. 识别和解决常见性能问题
5. 将 Ray Data 集成到 ML 工作流中
