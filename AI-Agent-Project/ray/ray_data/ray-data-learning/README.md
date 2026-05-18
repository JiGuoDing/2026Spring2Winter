# Ray Data 学习项目

一个从入门到精通的 Ray Data 学习项目，包含示例代码、综合项目和完整文档。

## Ray Data 是什么

Ray Data 是 Ray 生态中的分布式数据处理库，专为机器学习和数据工程设计。

**适合场景**:
- 大规模数据预处理（ETL）
- 特征工程
- 批量推理（Batch Inference）
- 与 ML 训练管道集成

## 与类似工具对比

| 特性 | Ray Data | pandas | Dask | Spark |
|------|----------|--------|------|-------|
| 分布式 | 内置 | 单机 | 可选 | 内置 |
| ML 集成 | 原生 | 需转换 | 一般 | MLlib |
| GPU 支持 | 原生 | 无 | 有限 | 有限 |
| 惰性执行 | 是 | 否 | 是 | 是 |
| 学习曲线 | 低 | 低 | 中 | 高 |
| 适合规模 | 中-大 | 小 | 中-大 | 大 |

## 项目结构

```
ray-data-learning/
├── README.md                    # 本文件
├── requirements.txt             # 依赖
├── pytest.ini                   # 测试配置
├── data/
│   ├── raw/                     # 原始数据（生成）
│   └── processed/               # 处理后数据
├── scripts/
│   └── generate_data.py         # 数据生成脚本
├── docs/                        # 文档
│   ├── learning_path.md         # 学习路线
│   ├── concepts.md              # 核心概念
│   ├── api_cheatsheet.md        # API 速查
│   ├── performance_tuning.md    # 性能优化
│   └── common_pitfalls.md       # 常见坑
├── examples/                    # 示例代码（由浅入深）
│   ├── 00_quick_start.py        # 快速入门
│   ├── 01_create_dataset.py     # 创建 Dataset
│   ├── 02_read_write.py         # 读写数据
│   ├── 03_transform.py          # 数据转换
│   ├── 04_map_batches.py        # 批量处理
│   ├── 05_lazy_execution.py     # 惰性执行
│   ├── 06_groupby_shuffle.py    # 聚合与 shuffle
│   ├── 07_parallelism.py        # 并行控制
│   ├── 08_interop.py            # 生态集成
│   ├── 09_batch_inference.py    # 批量推理
│   └── 10_debugging.py          # 调试技巧
├── projects/                    # 综合项目
│   ├── etl_pipeline/            # ETL 流程
│   ├── feature_engineering/     # 特征工程
│   └── batch_inference/         # 批量推理
├── tests/                       # 测试
└── utils/                       # 工具函数
```

## 安装

```bash
# 克隆或进入项目目录
cd ray-data-learning

# 安装依赖
pip install -r requirements.txt
```

## 生成数据

```bash
python scripts/generate_data.py
```

生成文件：
- `data/raw/users.csv` — 用户信息（1000 条）
- `data/raw/orders.csv` — 订单数据（5000 条）
- `data/raw/events.jsonl` — 行为事件（10000 条）
- `data/raw/items.parquet` — 商品信息（200 条）
- `data/raw/dirty_users.csv` — 脏数据（用于调试练习）

## 运行示例

```bash
# 快速入门
python examples/00_quick_start.py

# 按顺序运行所有示例
for f in examples/*.py; do echo "=== $f ==="; python "$f"; done
```

## 运行测试

```bash
pytest
```

## 推荐学习顺序

1. **入门**（1 天）：`00_quick_start.py` → `01_create_dataset.py`
2. **核心**（3 天）：`02` → `10` 按编号顺序
3. **实践**（1 周）：`projects/` 下的 3 个项目
4. **进阶**：阅读 `docs/` 文档，优化性能

详细学习路线见 `docs/learning_path.md`。

## 后续进阶方向

1. **Ray Train**: 分布式模型训练
2. **Ray Serve**: 模型服务部署
3. **Ray集群**: 多节点分布式处理
4. **流式处理**: 实时数据管道
5. **GPU推理**: 大规模深度学习推理
