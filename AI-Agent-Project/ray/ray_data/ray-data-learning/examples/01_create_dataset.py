"""01 - 创建 Dataset：多种数据源创建方式。

本示例展示：
- 从 Python list 创建
- 从 pandas DataFrame 创建
- 从 numpy array 创建
- 从 PyArrow Table 创建
- 从 CSV / JSON / Parquet 文件创建
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
    print("  创建 Dataset：多种数据源")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # ==================== 1. 从 Python list 创建 ====================
    print("\n[1] 从 Python list 创建")
    ds_list = ray.data.from_items([
        {"x": 1, "y": "a"},
        {"x": 2, "y": "b"},
        {"x": 3, "y": "c"},
    ])
    ds_list.show()

    # ==================== 2. 从 pandas DataFrame 创建 ====================
    print("\n[2] 从 pandas DataFrame 创建")
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "score": [95.5, 87.3, 92.1],
        "passed": [True, True, True],
    })
    ds_pandas = ray.data.from_pandas(df)
    ds_pandas.show()

    # ==================== 3. 从 numpy array 创建 ====================
    print("\n[3] 从 numpy array 创建")
    arr = np.random.randn(5, 3)  # 5 行 3 列
    ds_numpy = ray.data.from_numpy({"features": arr})
    ds_numpy.show()

    # ==================== 4. 从 PyArrow Table 创建 ====================
    print("\n[4] 从 PyArrow Table 创建")
    table = pa.table({
        "id": pa.array([1, 2, 3, 4]),
        "value": pa.array([10.0, 20.0, 30.0, 40.0]),
        "label": pa.array(["pos", "neg", "pos", "neg"]),
    })
    ds_arrow = ray.data.from_arrow(table)
    ds_arrow.show()

    # ==================== 5. 从 CSV 文件创建 ====================
    print("\n[5] 从 CSV 文件创建")
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "raw", "users.csv")
    if os.path.exists(csv_path):
        ds_csv = ray.data.read_csv(csv_path)
        print(f"  CSV 行数: {ds_csv.count()}")
        ds_csv.show(limit=3)
    else:
        print(f"  文件不存在: {csv_path}")
        print("  请先运行: python scripts/generate_data.py")

    # ==================== 6. 从 JSON 文件创建 ====================
    print("\n[6] 从 JSONL 文件创建")
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "data", "raw", "events.jsonl")
    if os.path.exists(json_path):
        ds_json = ray.data.read_json(json_path)
        print(f"  JSONL 行数: {ds_json.count()}")
        ds_json.show(limit=3)
    else:
        print(f"  文件不存在: {json_path}")

    # ==================== 7. 从 Parquet 文件创建 ====================
    print("\n[7] 从 Parquet 文件创建")
    parquet_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "data", "raw", "items.parquet")
    if os.path.exists(parquet_path):
        ds_parquet = ray.data.read_parquet(parquet_path)
        print(f"  Parquet 行数: {ds_parquet.count()}")
        ds_parquet.show(limit=3)
    else:
        print(f"  文件不存在: {parquet_path}")

    ray.shutdown()
    print("\n示例结束。")


if __name__ == "__main__":
    main()
