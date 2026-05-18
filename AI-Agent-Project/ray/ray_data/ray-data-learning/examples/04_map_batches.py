"""04 - map_batches 深入：batch 格式与并行度。

本示例展示：
- pandas batch format
- numpy batch format
- pyarrow batch format
- batch_size 控制
- 并行度（concurrency）控制
"""

import ray
import pandas as pd
import numpy as np
import pyarrow as pa
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 50)
    print("  map_batches 深入：batch 格式与并行度")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # 创建较大规模数据
    ds = ray.data.from_items([
        {"id": i, "value": i * 1.5, "label": f"cat_{i % 5}"}
        for i in range(100)
    ])
    print(f"原始数据: {ds.count()} 行\n")

    # ==================== 1. pandas batch format ====================
    print("--- [1] pandas batch format ---")
    def pandas_transform(batch: pd.DataFrame) -> pd.DataFrame:
        # pandas DataFrame 操作
        batch["value_squared"] = batch["value"] ** 2
        batch["value_log"] = np.log1p(batch["value"])
        return batch

    ds_pandas = ds.map_batches(pandas_transform, batch_format="pandas", batch_size=20)
    print(f"  结果行数: {ds_pandas.count()}")
    ds_pandas.show(limit=5)

    # ==================== 2. numpy batch format ====================
    print("\n--- [2] numpy batch format ---")
    def numpy_transform(batch: dict) -> dict:
        # numpy 格式下，batch 是 {列名: np.ndarray} 的字典
        values = batch["value"]
        batch["value_normalized"] = (values - values.mean()) / (values.std() + 1e-8)
        return batch

    ds_numpy = ds.map_batches(numpy_transform, batch_format="numpy", batch_size=25)
    print(f"  结果行数: {ds_numpy.count()}")
    ds_numpy.show(limit=5)

    # ==================== 3. pyarrow batch format ====================
    print("\n--- [3] pyarrow batch format ---")
    def arrow_transform(batch: pa.Table) -> pa.Table:
        # PyArrow Table 操作
        values = batch.column("value").to_pylist()
        new_col = pa.array([v * 2 for v in values], type=pa.float64())
        return batch.append_column("value_doubled", new_col)

    ds_arrow = ds.map_batches(arrow_transform, batch_format="pyarrow", batch_size=30)
    print(f"  结果行数: {ds_arrow.count()}")
    ds_arrow.show(limit=5)

    # ==================== 4. batch_size 控制 ====================
    print("\n--- [4] batch_size 控制 ---")
    def count_batch(batch: pd.DataFrame) -> pd.DataFrame:
        # 记录每个 batch 的大小
        print(f"    batch 大小: {len(batch)} 行")
        return batch

    print("  batch_size=10:")
    ds.map_batches(count_batch, batch_format="pandas", batch_size=10).materialize()

    print("\n  batch_size=50:")
    ds.map_batches(count_batch, batch_format="pandas", batch_size=50).materialize()

    # ==================== 5. 并行度控制 ====================
    print("\n--- [5] 并行度（concurrency）控制 ---")
    print("  通过 num_cpus 参数控制每个任务的资源占用")
    # 设置每个 map_batches 任务使用 1 个 CPU
    ds_parallel = ds.map_batches(
        pandas_transform,
        batch_format="pandas",
        batch_size=20,
        num_cpus=1,
    )
    print(f"  并行处理完成，结果行数: {ds_parallel.count()}")

    ray.shutdown()
    print("\n示例结束。")


if __name__ == "__main__":
    main()
