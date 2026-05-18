"""Batch Inference：使用 Ray Data 进行批量推理。

展示 map_batches 批量预测流程，以及 GPU 扩展说明。
"""

import ray
import numpy as np
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from utils.ray_utils import get_data_path, get_output_path


class SimpleModel:
    """简单的线性模型，用于演示批量推理。"""

    def __init__(self, weights, bias=0.0):
        self.weights = np.array(weights)
        self.bias = bias

    def predict(self, features: np.ndarray) -> np.ndarray:
        """预测分数。"""
        return features @ self.weights + self.bias

    def predict_class(self, features: np.ndarray) -> np.ndarray:
        """预测类别（二分类）。"""
        scores = self.predict(features)
        return (scores > 0).astype(int)


def main():
    print("=" * 50)
    print("  Batch Inference：批量推理")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # ==================== 1. 准备数据 ====================
    print("\n[1] 准备推理数据...")
    # 读取用户数据作为推理输入
    users_path = get_data_path("users.csv")
    if not os.path.exists(users_path):
        print(f"  数据文件不存在: {users_path}")
        print("  请先运行: python scripts/generate_data.py")
        return

    ds_users = ray.data.read_csv(users_path)
    print(f"  推理数据: {ds_users.count()} 行")

    # ==================== 2. 加载模型 ====================
    print("\n[2] 加载模型...")
    # 模拟一个用户价值预测模型
    # 特征：age, vip_level, balance -> 预测用户价值
    model = SimpleModel(weights=[0.02, 1.5, 0.001], bias=-2.0)
    print(f"  模型权重: {model.weights}")
    print(f"  模型偏置: {model.bias}")
    print(f"  含义: 用户价值 = 0.02*age + 1.5*vip_level + 0.001*balance - 2.0")

    # ==================== 3. 批量推理 ====================
    print("\n[3] 批量推理...")

    def batch_predict(batch: pd.DataFrame) -> pd.DataFrame:
        """对一个 batch 进行预测。"""
        # 提取特征
        features = batch[["age", "vip_level", "balance"]].values.astype(float)
        # 预测
        batch["value_score"] = model.predict(features).round(4)
        batch["value_class"] = model.predict_class(features)
        # 分类标签
        batch["value_label"] = batch["value_class"].map({0: "低价值", 1: "高价值"})
        return batch

    ds_predicted = ds_users.map_batches(batch_predict, batch_format="pandas", batch_size=100)
    print("  预测完成，结果前 10 条:")
    ds_predicted.show(limit=10)

    # ==================== 4. 统计预测结果 ====================
    print("\n[4] 预测统计...")
    df = ds_predicted.to_pandas()
    print(f"  高价值用户: {(df['value_class'] == 1).sum()} ({(df['value_class'] == 1).mean():.1%})")
    print(f"  低价值用户: {(df['value_class'] == 0).sum()} ({(df['value_class'] == 0).mean():.1%})")
    print(f"  平均价值分数: {df['value_score'].mean():.4f}")
    print(f"  分数范围: [{df['value_score'].min():.4f}, {df['value_score'].max():.4f}]")

    # 按 VIP 等级统计
    print("\n  按 VIP 等级统计高价值用户比例:")
    vip_stats = df.groupby("vip_level").agg(
        total=("value_class", "count"),
        high_value=("value_class", "sum"),
    )
    vip_stats["high_value_rate"] = (vip_stats["high_value"] / vip_stats["total"]).round(4)
    print(vip_stats.to_string())

    # ==================== 5. 写出结果 ====================
    print("\n[5] 写出预测结果...")
    output_path = get_output_path("user_predictions.parquet")
    ds_predicted.write_parquet(os.path.dirname(output_path))
    print(f"  已写出: {output_path}")

    # ==================== 6. GPU 扩展说明 ====================
    print("\n" + "=" * 50)
    print("  GPU 扩展说明")
    print("=" * 50)
    print("""
    要使用 GPU 进行批量推理，只需修改 map_batches 调用：

    ds_predicted = ds_users.map_batches(
        batch_predict,
        batch_format="pandas",
        batch_size=256,     # GPU 通常用更大的 batch
        num_gpus=1,         # 每个任务使用 1 个 GPU
    )

    对于深度学习模型：
    1. 使用 PyTorch/TensorFlow 加载模型到 GPU
    2. 在 batch_predict 中将数据移到 GPU
    3. 使用 @ray.remote(num_gpus=1) 创建 Actor 保持模型状态

    多 GPU 并行：
    - Ray 自动将数据分发到多个 GPU
    - 通过 concurrency 参数控制并发数
    """)

    ray.shutdown()
    print("Batch Inference 完成。")


if __name__ == "__main__":
    main()
