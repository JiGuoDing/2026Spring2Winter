"""00 - 快速入门：Ray Data 基础操作。

本示例展示：
- Ray 初始化
- 从 Python list 创建 Dataset
- show / take / count / schema 等基础操作
- materialize 物化执行
"""

import ray
import sys
import os

# 将项目根目录加入 path，便于导入 utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    # ==================== 1. 初始化 Ray ====================
    print("=" * 50)
    print("  快速入门：Ray Data 基础操作")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)
    print("Ray 初始化完成\n")

    # ==================== 2. 从 list 创建 Dataset ====================
    print("--- 从 list 创建 Dataset ---")
    ds = ray.data.from_items([
        {"name": "Alice", "age": 30, "city": "北京"},
        {"name": "Bob", "age": 25, "city": "上海"},
        {"name": "Charlie", "age": 35, "city": "广州"},
        {"name": "Diana", "age": 28, "city": "深圳"},
        {"name": "Eve", "age": 32, "city": "杭州"},
    ])

    # ==================== 3. 基础查看操作 ====================
    print("\n--- show(): 打印前几行 ---")
    ds.show(limit=3)

    print("\n--- take(2): 取前 2 行 ---")
    rows = ds.take(2)
    for row in rows:
        print(f"  {row}")

    print("\n--- count(): 统计行数 ---")
    print(f"  总行数: {ds.count()}")

    print("\n--- schema(): 查看 Schema ---")
    print(f"  Schema: {ds.schema()}")

    print("\n--- columns(): 查看列名 ---")
    print(f"  列名: {ds.columns()}")

    # ==================== 4. materialize 物化执行 ====================
    # Ray Data 默认使用惰性执行（lazy execution）
    # materialize() 会强制执行所有待处理的操作并将结果缓存
    print("\n--- materialize(): 物化执行 ---")
    materialized = ds.materialize()
    print(f"  物化后行数: {materialized.count()}")

    # ==================== 5. 简单转换 ====================
    print("\n--- filter(): 过滤 ---")
    filtered = ds.filter(lambda row: row["age"] > 28)
    filtered.show()

    print("\n--- map(): 转换 ---")
    mapped = ds.map(lambda row: {**row, "age_group": "senior" if row["age"] >= 30 else "junior"})
    mapped.show()

    # ==================== 6. 清理 ====================
    ray.shutdown()
    print("\nRay 已关闭，示例结束。")


if __name__ == "__main__":
    main()
