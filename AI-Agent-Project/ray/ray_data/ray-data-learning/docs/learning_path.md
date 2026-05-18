# Ray Data 学习路线

## 1 天入门（2-3 小时）

### 目标
理解 Ray Data 是什么，能跑通基本示例。

### 学习内容
1. 阅读 `README.md` 了解项目概况
2. 安装依赖并生成数据
3. 运行 `00_quick_start.py` 体验基础操作
4. 运行 `01_create_dataset.py` 了解数据源
5. 阅读 `docs/concepts.md` 理解核心概念

### 检查点
- [ ] 能成功运行 `python examples/00_quick_start.py`
- [ ] 理解 Dataset、lazy execution 的基本概念
- [ ] 知道如何从 list 和文件创建 Dataset

---

## 3 天掌握核心 API（每天 2-3 小时）

### Day 2: 数据读写与转换
1. `02_read_write.py` — CSV/JSON/Parquet 读写
2. `03_transform.py` — map/filter/flat_map
3. `04_map_batches.py` — 批量处理

### 检查点
- [ ] 能选择合适的文件格式
- [ ] 理解 map 与 map_batches 的区别
- [ ] 能处理缺失值和类型转换

### Day 3: 执行模型与聚合
1. `05_lazy_execution.py` — 惰性执行
2. `06_groupby_shuffle.py` — 分组聚合与 shuffle
3. `07_parallelism.py` — 并行控制

### 检查点
- [ ] 理解何时触发执行
- [ ] 知道 shuffle 的成本和优化方法
- [ ] 能控制并行度

### Day 4: 生态集成与推理
1. `08_interop.py` — pandas/numpy/sklearn 集成
2. `09_batch_inference.py` — 批量推理
3. `10_debugging.py` — 调试技巧

### 检查点
- [ ] 能在 Ray Data 中使用 pandas/numpy
- [ ] 能用 map_batches 做批量预测
- [ ] 知道常见错误的排查方法

---

## 1 周工程实践（每天 2-3 小时）

### Day 5-6: 综合项目
1. 完成 `projects/etl_pipeline/` — ETL 流程
2. 完成 `projects/feature_engineering/` — 特征工程

### Day 7: 批量推理与优化
1. 完成 `projects/batch_inference/` — 批量推理
2. 阅读 `docs/performance_tuning.md` — 性能优化
3. 阅读 `docs/common_pitfalls.md` — 常见坑

### 检查点
- [ ] 能独立完成一个完整的数据处理流程
- [ ] 理解性能优化的关键点
- [ ] 能处理真实数据中的各种问题

---

## 进阶方向

1. **分布式处理**: 多节点 Ray 集群
2. **GPU 推理**: 使用 GPU 进行深度学习批量推理
3. **流式处理**: Ray Data 与流式数据源集成
4. **与 Ray Train 集成**: 分布式训练
5. **生产部署**: 数据管道自动化
