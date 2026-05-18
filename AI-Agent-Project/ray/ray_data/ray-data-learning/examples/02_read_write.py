"""02 - 读写数据：CSV / JSON / Parquet 读写与格式选择。

本示例展示：
- 读取 CSV、JSON、Parquet 文件
- 写出到不同格式
- 格式选择建议
"""

import ray
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ray_utils import get_data_path


def main():
    print("=" * 50)
    print("  读写数据：格式选择与操作")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # 使用临时目录作为输出
    output_dir = tempfile.mkdtemp(prefix="ray_data_output_")
    print(f"输出目录: {output_dir}\n")

    # ==================== 读取 CSV ====================
    print("--- 读取 CSV ---")
    csv_path = get_data_path("users.csv")
    if os.path.exists(csv_path):
        ds_csv = ray.data.read_csv(csv_path)
        print(f"  行数: {ds_csv.count()}")
        print(f"  Schema: {ds_csv.schema()}")
        ds_csv.show(limit=2)

        # 写出为 Parquet（推荐格式，列式存储，压缩效率高）
        parquet_out = os.path.join(output_dir, "users_from_csv.parquet")
        ds_csv.write_parquet(output_dir)
        print(f"  已写出为 Parquet")

    # ==================== 读取 JSONL ====================
    print("\n--- 读取 JSONL ---")
    json_path = get_data_path("events.jsonl")
    if os.path.exists(json_path):
        ds_json = ray.data.read_json(json_path)
        print(f"  行数: {ds_json.count()}")
        ds_json.show(limit=2)

    # ==================== 读取 Parquet ====================
    print("\n--- 读取 Parquet ---")
    parquet_path = get_data_path("items.parquet")
    if os.path.exists(parquet_path):
        ds_parquet = ray.data.read_parquet(parquet_path)
        print(f"  行数: {ds_parquet.count()}")
        print(f"  Schema: {ds_parquet.schema()}")
        ds_parquet.show(limit=2)

        # 写出为 CSV
        csv_out = os.path.join(output_dir, "items.csv")
        ds_parquet.write_csv(output_dir)
        print(f"  已写出为 CSV")

    # ==================== 格式选择建议 ====================
    print("\n" + "=" * 50)
    print("  格式选择建议")
    print("=" * 50)
    print("""
    CSV:
      - 优点: 人类可读，通用性强
      - 缺点: 无类型信息，体积大，读取慢
      - 适合: 小数据、数据交换、调试

    JSON/JSONL:
      - 优点: 支持嵌套结构，半结构化
      - 缺点: 体积大，解析慢
      - 适合: 日志数据、API 数据

    Parquet（推荐）:
      - 优点: 列式存储，压缩率高，类型保留，读取快
      - 缺点: 不可直接编辑
      - 适合: 生产环境、大数据、分析场景
    """)

    ray.shutdown()
    print("示例结束。")


if __name__ == "__main__":
    main()
