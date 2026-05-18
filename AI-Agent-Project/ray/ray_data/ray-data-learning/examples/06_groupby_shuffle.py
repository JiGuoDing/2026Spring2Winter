"""06 - groupby / sort / shuffle / repartition。

本示例展示：
- groupby 聚合操作
- sort 排序
- shuffle 洗牌
- repartition 重新分区
- shuffle 的性能成本说明
"""

import ray
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 50)
    print("  groupby / sort / shuffle / repartition")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # 创建示例订单数据
    ds = ray.data.from_items([
        {"order_id": i, "user_id": i % 10, "category": f"cat_{i % 5}",
         "amount": round(100 + i * 3.7, 2), "status": ["completed", "pending", "cancelled"][i % 3]}
        for i in range(200)
    ])
    print(f"原始数据: {ds.count()} 行")
    ds.show(limit=5)

    # ==================== groupby ====================
    print("\n--- groupby(): 分组聚合 ---")
    print("""
    groupby() 本身是惰性的，需要配合聚合函数使用：
    - map_groups(): 自定义聚合（最灵活）
    - count(): 计数
    - sum() / min() / max() / mean(): 常用聚合
    """)

    # 按 category 分组计数
    print("按 category 分组计数:")
    ds.groupby("category").count().show()

    # 按 category 分组求和
    print("按 category 分组求 amount 总和:")
    ds.groupby("category").sum("amount").show()

    # 按 category 分组求均值
    print("按 category 分组求 amount 均值:")
    ds.groupby("category").mean("amount").show()

    # 使用 map_groups 自定义聚合
    print("使用 map_groups 自定义聚合（每组取最大订单）:")
    def get_max_order(group: pd.DataFrame) -> pd.DataFrame:
        return group.loc[group["amount"].idxmax():group["amount"].idxmax()]

    ds.groupby("category").map_groups(get_max_order).show()

    # ==================== sort ====================
    print("\n--- sort(): 排序 ---")
    print("按 amount 降序排列（前 5 条）:")
    ds.sort("amount", descending=True).show(limit=5)

    print("多列排序（先按 category，再按 amount 降序）:")
    ds.sort(["category", "amount"], descending=[False, True]).show(limit=5)

    # ==================== repartition ====================
    print("\n--- repartition(): 重新分区 ---")
    print(f"  当前分区数: {ds.num_blocks()}")
    ds_repartitioned = ds.repartition(num_blocks=4)
    print(f"  重新分区后: {ds_repartitioned.num_blocks()} 个分区")

    # ==================== shuffle 成本说明 ====================
    print("\n" + "=" * 50)
    print("  Shuffle 成本说明")
    print("=" * 50)
    print("""
    以下操作会触发 shuffle（数据重新分布）：
    - groupby() + 聚合: 需要将相同 key 的数据移到同一分区
    - sort(): 需要全局排序，数据需要重新分布
    - repartition(): 改变分区数

    Shuffle 的成本：
    1. 网络 I/O: 数据需要在节点间传输
    2. 磁盘 I/O: 中间结果可能需要落盘
    3. 内存: 需要缓冲区存放中间数据
    4. 计算: 序列化/反序列化开销

    优化建议：
    1. 尽量在 shuffle 前过滤数据，减少传输量
    2. 使用适当的分区数（太多或太少都不好）
    3. 考虑使用 map_groups() 替代复杂 groupby
    4. 对于小数据集，to_pandas() 后用 pandas 操作可能更快
    """)

    ray.shutdown()
    print("示例结束。")


if __name__ == "__main__":
    main()
