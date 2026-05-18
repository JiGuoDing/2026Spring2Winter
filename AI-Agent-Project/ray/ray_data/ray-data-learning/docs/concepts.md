# Ray Data 核心概念

## Dataset（数据集）

Ray Data 的核心抽象，表示一个分布式数据集。

```python
import ray
ds = ray.data.from_items([{"x": 1}, {"x": 2}])
```

特点：
- 分布式：数据分布在多个节点上
- 惰性：转换操作不会立即执行
- 类型感知：保留数据的 schema 信息

## Block（数据块）

Dataset 内部的数据分区单元。每个 Block 是一个独立的数据片段，可以并行处理。

```
Dataset
├── Block 0: [row0, row1, row2]
├── Block 1: [row3, row4, row5]
└── Block 2: [row6, row7, row8]
```

- Block 数量决定了并行度
- 可通过 `repartition()` 调整
- 查看：`ds.num_blocks()`

## Task（任务）

Ray 的基本调度单元。每个 map/filter 等操作会生成多个 Task，每个 Task 处理一个 Block。

```python
# 这会生成 N 个 Task（N = Block 数量）
ds.map(lambda row: {**row, "y": row["x"] * 2})
```

## Actor（参与者）

有状态的 Ray 实体。在 Ray Data 中，可用于：
- 保持模型状态（批量推理）
- 管理连接池
- 缓存计算结果

```python
@ray.remote
class ModelActor:
    def __init__(self):
        self.model = load_model()

    def predict(self, batch):
        return self.model(batch)
```

## Lazy Execution（惰性执行）

Ray Data 默认使用惰性执行模式：
- 转换操作（map/filter/groupby 等）只构建执行计划
- 需要结果时（show/take/count 等）才触发执行
- materialize() 可强制执行并缓存结果

```python
# 惰性操作 - 不执行
step1 = ds.filter(lambda row: row["x"] > 0)
step2 = step1.map(lambda row: {**row, "y": row["x"] * 2})

# 触发执行
step2.show()  # 此时才真正计算
step2.materialize()  # 强制执行并缓存
```

## Shuffle（数据重分布）

某些操作需要数据重新分布：
- groupby: 相同 key 的数据移到同一节点
- sort: 全局排序需要数据重分布
- repartition: 改变分区数

成本：网络 I/O、磁盘 I/O、内存、序列化开销

## Batch Processing（批处理）

map_batches 将数据按 batch 处理，而非逐行处理：
- 更高效的向量化操作
- 支持 pandas/numpy/pyarrow 格式
- 可控制 batch_size

```python
ds.map_batches(
    lambda batch: batch * 2,
    batch_format="pandas",
    batch_size=1000,
)
```
