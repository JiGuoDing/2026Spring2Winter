# Ray Data 学习项目生成 Prompt

你是一名资深 Python / Ray Data 工程师，也是一名擅长设计学习项目的技术导师。

请在当前目录下生成一个完整的 **Ray Data 学习项目**，用于帮助我快速入门并逐步精通 Ray Data。

项目要求：内容由浅入深、示例可运行、注释清晰、文档完整，适合本地单机学习，也要体现真实工程实践。

---

## 目标

生成一个 `ray-data-learning` 项目，要求覆盖：

- Ray Data 基础概念
- Dataset 创建、读取、写入
- map / filter / map_batches 等核心转换
- batch 处理与并行执行
- lazy execution 与 materialize
- groupby、sort、shuffle、repartition
- pandas / numpy / pyarrow / scikit-learn / PyTorch 简单集成
- 性能优化
- 调试与常见坑
- 真实小型项目实践

所有代码请使用 **中文注释**，示例尽量使用本地生成的小数据集，不依赖外部网络资源。

---

## 技术栈

使用：

- Python 3.10+
- ray[data]
- pandas
- numpy
- pyarrow
- pytest
- scikit-learn，可选
- torch，可选，仅用于简单批量推理示例

请生成 `requirements.txt`。

---

## 建议项目结构

请创建类似下面的结构，可根据实际情况微调：

```text
ray-data-learning/
├── README.md
├── requirements.txt
├── pytest.ini
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
├── scripts/
│   └── generate_data.py
├── docs/
│   ├── learning_path.md
│   ├── concepts.md
│   ├── api_cheatsheet.md
│   ├── performance_tuning.md
│   └── common_pitfalls.md
├── examples/
│   ├── 00_quick_start.py
│   ├── 01_create_dataset.py
│   ├── 02_read_write.py
│   ├── 03_transform.py
│   ├── 04_map_batches.py
│   ├── 05_lazy_execution.py
│   ├── 06_groupby_shuffle.py
│   ├── 07_parallelism.py
│   ├── 08_interop.py
│   ├── 09_batch_inference.py
│   └── 10_debugging.py
├── projects/
│   ├── etl_pipeline/
│   │   ├── README.md
│   │   └── main.py
│   ├── feature_engineering/
│   │   ├── README.md
│   │   └── main.py
│   └── batch_inference/
│       ├── README.md
│       └── main.py
├── tests/
│   ├── test_generate_data.py
│   ├── test_dataset_basic.py
│   └── test_etl_pipeline.py
└── utils/
    ├── __init__.py
    ├── ray_utils.py
    └── data_utils.py
```

---

## 数据生成

请编写 `scripts/generate_data.py`，生成本地示例数据到 `data/raw/`：

- `users.csv`
- `orders.csv`
- `events.jsonl`
- `items.parquet`
- `dirty_users.csv`

数据要能覆盖：

- 缺失值
- 异常值
- 类型转换
- 聚合统计
- 批处理
- 分区读写
- 简单特征工程

---

## 示例要求

`examples/` 中每个文件都要能单独运行，并展示一个明确主题。

建议包括：

1. 快速入门：初始化 Ray、创建 Dataset、show、take、count、schema、materialize。
2. 创建 Dataset：list、pandas、numpy、Arrow、CSV、JSON、Parquet。
3. 读写数据：CSV / JSON / Parquet 读写与格式选择。
4. 数据转换：map、flat_map、filter、map_batches、缺失值处理、类型转换。
5. map_batches：pandas / numpy / pyarrow batch format，batch size，并行度。
6. lazy execution：说明哪些操作是惰性的，如何触发执行。
7. groupby / sort / shuffle / repartition：说明 shuffle 成本。
8. 并行与性能：parallelism、concurrency、num_cpus、repartition。
9. 生态集成：pandas、numpy、pyarrow、sklearn。
10. 批量推理：用 Ray Data 做简单批量预测。
11. 调试：常见错误、脏数据处理、schema 问题。

---

## 综合项目

请生成 3 个小型完整项目：

### 1. ETL Pipeline

读取原始数据，完成清洗、类型转换、异常过滤、特征列生成，并写出 Parquet。

### 2. Feature Engineering

读取用户行为数据，按用户聚合，生成用户级特征表，并说明哪些步骤可能触发 shuffle。

### 3. Batch Inference

生成或加载简单模型，使用 `map_batches` 批量推理，输出预测结果，并说明如何扩展到 GPU。

---

## 文档要求

请在 `docs/` 中写中文文档，内容包括：

- 学习路线：1 天入门、3 天掌握核心 API、1 周工程实践。
- 核心概念：Dataset、Block、Task、Actor、lazy execution。
- API 速查：常用 Ray Data API、适用场景和简短示例。
- 性能优化：batch size、并行度、repartition、shuffle、materialize、数据格式选择、内存管理、Ray Dashboard。
- 常见坑：schema 不一致、batch 格式错误、用户函数异常、OOM、版本差异等。

---

## README 要求

`README.md` 要说明：

- Ray Data 是什么，适合什么场景。
- 与 pandas / Dask / Spark 的简单对比。
- 项目结构说明。
- 安装依赖。
- 生成数据。
- 运行示例。
- 运行测试。
- 推荐学习顺序。
- 后续进阶方向。

至少包含以下命令：

```bash
pip install -r requirements.txt
python scripts/generate_data.py
python examples/00_quick_start.py
pytest
```

---

## 测试要求

请使用 pytest 编写轻量测试，至少覆盖：

- 示例数据是否成功生成。
- Ray Dataset 是否能正常创建。
- ETL Pipeline 是否能生成输出。
- 关键转换逻辑是否正确。

---

## 代码质量要求

所有 Python 代码必须：

- 有清晰中文注释。
- 使用清楚的变量名。
- 每个示例可独立运行。
- 使用 `if __name__ == "__main__":`。
- 打印关键执行步骤，便于学习。
- 尽量避免外部网络依赖。
- 遇到 Ray 版本差异时，在注释中说明。

---

## 交付要求

请直接在当前目录创建完整项目。

完成后请输出：

1. 项目结构树。
2. 安装与运行命令。
3. 推荐学习顺序。
4. 每个示例的作用简介。
5. 测试运行方法。
