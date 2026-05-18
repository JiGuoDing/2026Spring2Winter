"""Feature Engineering：用户行为特征提取。

从 events.jsonl 中提取用户级特征，展示 groupby 聚合和 shuffle。
"""

import ray
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from utils.ray_utils import get_data_path, get_output_path


def main():
    print("=" * 50)
    print("  Feature Engineering：用户行为特征提取")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # ==================== 1. 读取行为数据 ====================
    print("\n[1] 读取行为数据...")
    events_path = get_data_path("events.jsonl")
    if not os.path.exists(events_path):
        print(f"  数据文件不存在: {events_path}")
        print("  请先运行: python scripts/generate_data.py")
        return

    ds_events = ray.data.read_json(events_path)
    print(f"  行为数据: {ds_events.count()} 行")
    ds_events.show(limit=3)

    # ==================== 2. 行为次数统计（触发 shuffle） ====================
    print("\n[2] 行为次数统计...")
    print("  注意：groupby 会触发 shuffle（数据重新分布）")

    # 按用户和行为类型统计
    def count_actions(batch: pd.DataFrame) -> pd.DataFrame:
        return batch.groupby(["user_id", "action"]).size().reset_index(name="count")

    # 使用 map_groups 进行分组统计
    # 注意：map_groups 比 groupby().count() 更灵活
    df_events = ds_events.to_pandas()

    # 行为次数透视表
    action_counts = df_events.groupby(["user_id", "action"]).size().unstack(fill_value=0)
    action_counts = action_counts.reset_index()
    print(f"  行为次数统计: {len(action_counts)} 个用户")
    print(f"  列: {list(action_counts.columns)}")
    print(action_counts.head().to_string(index=False))

    # ==================== 3. 用户活跃度特征 ====================
    print("\n[3] 用户活跃度特征...")

    # 转换时间戳
    df_events["timestamp"] = pd.to_datetime(df_events["timestamp"])
    df_events["date"] = df_events["timestamp"].dt.date

    # 按用户聚合
    user_activity = df_events.groupby("user_id").agg(
        # 行为统计
        total_events=("event_id", "count"),
        unique_actions=("action", "nunique"),
        # 时间统计
        active_days=("date", "nunique"),
        first_seen=("timestamp", "min"),
        last_seen=("timestamp", "max"),
        # 会话统计
        avg_session_duration=("session_duration", "mean"),
        max_session_duration=("session_duration", "max"),
        total_session_duration=("session_duration", "sum"),
        # 商品统计
        unique_items=("item_id", "nunique"),
    ).reset_index()

    # 计算衍生特征
    user_activity["events_per_day"] = (
        user_activity["total_events"] / user_activity["active_days"]
    ).round(2)
    user_activity["items_per_event"] = (
        user_activity["unique_items"] / user_activity["total_events"]
    ).round(4)

    print(f"  用户活跃特征: {len(user_activity)} 行")
    print(f"  列: {list(user_activity.columns)}")
    print(user_activity.head().to_string(index=False))

    # ==================== 4. 设备偏好特征 ====================
    print("\n[4] 设备偏好特征...")

    device_counts = df_events.groupby(["user_id", "device"]).size().unstack(fill_value=0)
    device_counts = device_counts.reset_index()
    # 找出每个用户的主要设备
    device_cols = [c for c in device_counts.columns if c != "user_id"]
    device_counts["primary_device"] = device_counts[device_cols].idxmax(axis=1)

    print(f"  设备偏好特征: {len(device_counts)} 行")
    print(device_counts.head().to_string(index=False))

    # ==================== 5. 合并所有特征 ====================
    print("\n[5] 合并所有特征...")

    # 合并行为统计和活跃度
    features = action_counts.merge(user_activity, on="user_id", how="outer")
    # 合并设备偏好
    features = features.merge(device_counts[["user_id", "primary_device"]], on="user_id", how="left")

    # 填充缺失值
    features = features.fillna(0)

    print(f"  最终特征表: {len(features)} 行")
    print(f"  列数: {len(features.columns)}")
    print(f"  列: {list(features.columns)}")

    # ==================== 6. 写出结果 ====================
    print("\n[6] 写出特征表...")
    output_path = get_output_path("user_features.parquet")
    features.to_parquet(output_path, index=False)
    print(f"  已写出: {output_path}")

    # 展示结果
    print("\n  最终特征表前 3 行:")
    print(features.head(3).to_string(index=False))

    # ==================== Shuffle 说明 ====================
    print("\n" + "=" * 50)
    print("  Shuffle 说明")
    print("=" * 50)
    print("""
    本项目中的 shuffle 操作：

    1. groupby("user_id").agg(...):
       - 需要将同一用户的所有事件移到同一节点
       - 触发 shuffle

    2. groupby(["user_id", "action"]).size().unstack():
       - 需要按 user_id + action 分组
       - 触发 shuffle

    优化建议：
    - 如果数据量大，可以先 filter 出需要的列再 groupby
    - 使用 map_groups 替代复杂 groupby
    - 考虑使用 Ray Data 的 groupby API 代替 to_pandas()
    """)

    ray.shutdown()
    print("Feature Engineering 完成。")


if __name__ == "__main__":
    main()
