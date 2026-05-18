"""05 - 惰性执行（Lazy Execution）。

本示例展示：
- 哪些操作是惰性的（不立即执行）
- 哪些操作会触发执行
- materialize() 的作用
- 执行计划的概念
"""

import ray
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 50)
    print("  惰性执行（Lazy Execution）")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # 创建初始数据集
    ds = ray.data.from_items([
        {"x": i, "y": i * 2, "z": i ** 2}
        for i in range(50)
    ])

    # ==================== 惰性操作 ====================
    print("\n--- 惰性操作（不立即执行，只构建执行计划）---")
    print("""
    以下操作是惰性的：
    - map() / flat_map() / filter()
    - map_batches()
    - select_columns() / drop_columns()
    - sort() / repartition()
    - groupby().map_groups()

    这些操作返回新的 Dataset，但不会立即计算。
    Ray 会构建一个执行计划（execution plan），延迟到需要结果时才执行。
    """)

    # 构建一个链式惰性操作
    step1 = ds.filter(lambda row: row["x"] > 10)
    step2 = step1.map(lambda row: {**row, "w": row["x"] + row["y"]})
    step3 = step2.filter(lambda row: row["w"] < 100)
    print(f"  构建了 3 步惰性操作链（filter -> map -> filter）")
    print(f"  此时尚未执行任何计算\n")

    # ==================== 触发执行的操作 ====================
    print("--- 触发执行的操作 ---")
    print("""
    以下操作会触发执行：
    - show() / take() / count() / schema()
    - materialize()
    - iter_rows() / iter_batches()
    - to_pandas() / to_numpy() / to_arrow()
    - write_parquet() / write_csv()
    """)

    # 触发执行：show
    print("--- 触发执行：show() ---")
    step3.show(limit=5)

    # ==================== materialize ====================
    print("\n--- materialize(): 物化执行 ---")
    print("materialize() 强制执行所有待处理的操作，将结果缓存到内存中。")
    print("后续对 materialized 数据集的操作不会重复计算。\n")

    materialized = step3.materialize()
    print(f"  物化后行数: {materialized.count()}")
    print(f"  Schema: {materialized.schema()}")

    # 对物化数据集的操作不会重复计算
    print("\n  对物化数据集再次操作（不会重复计算）:")
    further = materialized.filter(lambda row: row["x"] > 20)
    further.show(limit=5)

    # ==================== 何时使用 materialize ====================
    print("\n--- 何时使用 materialize ---")
    print("""
    适合使用 materialize() 的场景：
    1. 一个数据集会被多次使用（避免重复计算）
    2. 调试时想立即看到中间结果
    3. 想要缓存耗时的转换结果

    不适合的场景：
    1. 数据集只使用一次
    2. 内存不足以容纳完整结果
    3. 链式操作中间不需要查看结果
    """)

    ray.shutdown()
    print("示例结束。")


if __name__ == "__main__":
    main()
