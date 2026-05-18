"""03 - 数据转换：map / flat_map / filter / map_batches。

本示例展示：
- map: 逐行转换
- flat_map: 一行变多行
- filter: 过滤
- map_batches: 批量处理
- 缺失值处理
- 类型转换
"""

import ray
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ray_utils import get_data_path


def main():
    print("=" * 50)
    print("  数据转换操作")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # 创建示例数据
    ds = ray.data.from_items([
        {"name": "Alice", "age": 30, "score": 95.5, "tags": "python,rust"},
        {"name": "Bob", "age": 25, "score": None, "tags": "java"},
        {"name": "Charlie", "age": None, "score": 87.3, "tags": "python,go,javascript"},
        {"name": "Diana", "age": 28, "score": 92.1, "tags": ""},
        {"name": "Eve", "age": 32, "score": 78.9, "tags": "rust,c++"},
    ])

    print("\n原始数据:")
    ds.show()

    # ==================== map: 逐行转换 ====================
    print("\n--- map(): 逐行转换 ---")
    # 添加一个新列：年龄段
    ds_mapped = ds.map(lambda row: {
        **row,
        "age_group": "senior" if (row["age"] or 0) >= 30 else "junior",
    })
    ds_mapped.show()

    # ==================== filter: 过滤 ====================
    print("\n--- filter(): 过滤 ---")
    # 过滤出年龄大于等于 28 的记录
    ds_filtered = ds.filter(lambda row: row["age"] is not None and row["age"] >= 28)
    ds_filtered.show()

    # ==================== flat_map: 一行变多行 ====================
    print("\n--- flat_map(): 一行变多行 ---")
    # 将 tags 字符串拆分为多行
    ds_flat = ds.flat_map(lambda row: [
        {**row, "tag": tag.strip()}
        for tag in (row["tags"] or "").split(",")
        if tag.strip()
    ])
    ds_flat.show()

    # ==================== map_batches: 批量处理 ====================
    print("\n--- map_batches(): 批量处理（pandas 格式） ---")
    # 使用 pandas DataFrame 作为 batch 格式
    def process_batch(batch: pd.DataFrame) -> pd.DataFrame:
        # 填充缺失值
        batch["age"] = batch["age"].fillna(0).astype(int)
        batch["score"] = batch["score"].fillna(0.0)
        # 添加新列
        batch["name_upper"] = batch["name"].str.upper()
        return batch

    ds_batch = ds.map_batches(process_batch, batch_format="pandas")
    ds_batch.show()

    # ==================== 缺失值处理 ====================
    print("\n--- 缺失值处理 ---")
    def fill_missing(row):
        return {
            **row,
            "age": row["age"] if row["age"] is not None else 0,
            "score": row["score"] if row["score"] is not None else 0.0,
        }

    ds_filled = ds.map(fill_missing)
    print("填充缺失值后:")
    ds_filled.show()

    # ==================== 类型转换 ====================
    print("\n--- 类型转换 ---")
    def convert_types(row):
        return {
            **row,
            "age": int(row["age"]) if row["age"] is not None else 0,
            "score": float(row["score"]) if row["score"] is not None else 0.0,
        }

    ds_converted = ds.map(convert_types)
    print("类型转换后:")
    print(f"  Schema: {ds_converted.schema()}")
    ds_converted.show()

    ray.shutdown()
    print("\n示例结束。")


if __name__ == "__main__":
    main()
