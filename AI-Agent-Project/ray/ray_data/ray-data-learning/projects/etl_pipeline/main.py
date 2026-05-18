"""ETL Pipeline：数据清洗、转换、特征生成。

处理流程：
1. 读取原始数据（users.csv, orders.csv）
2. 清洗：过滤无效数据、处理缺失值
3. 类型转换
4. 特征生成：用户级统计
5. 合并输出为 Parquet
"""

import ray
import pandas as pd
import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from utils.ray_utils import get_data_path, get_output_path


def clean_users(batch: pd.DataFrame) -> pd.DataFrame:
    """清洗用户数据。"""
    # 过滤无效 user_id
    batch = batch[batch["user_id"].notna() & (batch["user_id"] != "")].copy()
    # 转换 age 为数值
    batch["age"] = pd.to_numeric(batch["age"], errors="coerce")
    # 过滤异常年龄
    batch = batch[(batch["age"] >= 0) & (batch["age"] <= 120)]
    # 填充缺失值
    batch["city"] = batch["city"].fillna("未知")
    batch["gender"] = batch["gender"].fillna("U")
    # 转换类型
    batch["user_id"] = batch["user_id"].astype(int)
    batch["age"] = batch["age"].astype(int)
    batch["vip_level"] = pd.to_numeric(batch["vip_level"], errors="coerce").fillna(0).astype(int)
    batch["balance"] = pd.to_numeric(batch["balance"], errors="coerce").fillna(0.0)
    return batch


def clean_orders(batch: pd.DataFrame) -> pd.DataFrame:
    """清洗订单数据。"""
    batch = batch.copy()
    # 确保类型正确
    batch["order_id"] = batch["order_id"].astype(int)
    batch["user_id"] = batch["user_id"].astype(int)
    batch["amount"] = pd.to_numeric(batch["amount"], errors="coerce").fillna(0.0)
    batch["num_items"] = pd.to_numeric(batch["num_items"], errors="coerce").fillna(1).astype(int)
    # 过滤无效金额
    batch = batch[batch["amount"] > 0]
    return batch


def main():
    print("=" * 50)
    print("  ETL Pipeline")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # ==================== 1. 读取数据 ====================
    print("\n[1] 读取原始数据...")
    users_path = get_data_path("users.csv")
    orders_path = get_data_path("orders.csv")

    if not os.path.exists(users_path):
        print(f"  数据文件不存在: {users_path}")
        print("  请先运行: python scripts/generate_data.py")
        return

    ds_users = ray.data.read_csv(users_path)
    ds_orders = ray.data.read_csv(orders_path)
    print(f"  用户数据: {ds_users.count()} 行")
    print(f"  订单数据: {ds_orders.count()} 行")

    # ==================== 2. 清洗 ====================
    print("\n[2] 清洗数据...")
    ds_users_clean = ds_users.map_batches(clean_users, batch_format="pandas")
    ds_orders_clean = ds_orders.map_batches(clean_orders, batch_format="pandas")

    # 物化以获取实际行数
    ds_users_clean = ds_users_clean.materialize()
    ds_orders_clean = ds_orders_clean.materialize()
    print(f"  清洗后用户: {ds_users_clean.count()} 行")
    print(f"  清洗后订单: {ds_orders_clean.count()} 行")

    # ==================== 3. 写出清洗后的用户数据 ====================
    print("\n[3] 写出清洗后的用户数据...")
    users_output = get_output_path("users_clean.parquet")
    ds_users_clean.write_parquet(os.path.dirname(users_output))
    print(f"  已写出: {users_output}")

    # ==================== 4. 计算用户级订单特征 ====================
    print("\n[4] 计算用户级订单特征...")

    # 转为 pandas 进行聚合（小数据集适用）
    df_orders = ds_orders_clean.to_pandas()

    # 按用户聚合
    user_features = df_orders.groupby("user_id").agg(
        order_count=("order_id", "count"),
        total_amount=("amount", "sum"),
        avg_amount=("amount", "mean"),
        max_amount=("amount", "max"),
        completed_count=("status", lambda x: (x == "completed").sum()),
    ).reset_index()

    # 计算完成率
    user_features["completion_rate"] = (
        user_features["completed_count"] / user_features["order_count"]
    ).round(4)

    print(f"  用户特征表: {len(user_features)} 行")
    print(f"  列: {list(user_features.columns)}")
    print("\n  前 5 行:")
    print(user_features.head().to_string(index=False))

    # ==================== 5. 合并用户信息和订单特征 ====================
    print("\n[5] 合并用户信息和订单特征...")
    df_users = ds_users_clean.to_pandas()
    df_merged = df_users.merge(user_features, on="user_id", how="left")
    # 没有订单的用户填充 0
    df_merged = df_merged.fillna({
        "order_count": 0, "total_amount": 0, "avg_amount": 0,
        "max_amount": 0, "completed_count": 0, "completion_rate": 0,
    })
    df_merged["order_count"] = df_merged["order_count"].astype(int)
    df_merged["completed_count"] = df_merged["completed_count"].astype(int)

    print(f"  合并后: {len(df_merged)} 行")
    print(f"  列: {list(df_merged.columns)}")

    # ==================== 6. 写出最终结果 ====================
    print("\n[6] 写出最终结果...")
    output_path = get_output_path("user_order_features.parquet")
    df_merged.to_parquet(output_path, index=False)
    print(f"  已写出: {output_path}")

    # 展示结果
    print("\n  最终结果前 5 行:")
    print(df_merged.head().to_string(index=False))

    ray.shutdown()
    print("\nETL Pipeline 完成。")


if __name__ == "__main__":
    main()
