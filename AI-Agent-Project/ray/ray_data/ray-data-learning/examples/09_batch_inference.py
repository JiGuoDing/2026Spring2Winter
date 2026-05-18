"""09 - 批量推理：使用 Ray Data 做批量预测。

本示例展示：
- 使用 map_batches 进行批量推理
- 模拟一个简单的分类模型
- 批量预测的流程
- GPU 扩展说明
"""

import ray
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SimpleClassifier:
    """简单的线性分类器（不依赖外部模型框架）。"""

    def __init__(self, weights=None, bias=0.0):
        self.weights = weights or np.array([0.5, -0.3, 0.8])
        self.bias = bias

    def predict(self, features: np.ndarray) -> np.ndarray:
        """预测类别（0 或 1）。"""
        scores = features @ self.weights + self.bias
        return (scores > 0).astype(int)

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """预测概率（sigmoid）。"""
        scores = features @ self.weights + self.bias
        return 1 / (1 + np.exp(-scores))


def main():
    print("=" * 50)
    print("  批量推理：map_batches 批量预测")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # ==================== 1. 准备数据 ====================
    print("\n--- [1] 准备推理数据 ---")
    ds = ray.data.from_items([
        {"f1": np.random.randn(), "f2": np.random.randn(), "f3": np.random.randn(), "id": i}
        for i in range(200)
    ])
    print(f"  推理数据: {ds.count()} 行")

    # ==================== 2. 加载模型 ====================
    print("\n--- [2] 加载模型 ---")
    model = SimpleClassifier(weights=np.array([0.5, -0.3, 0.8]), bias=0.1)
    print(f"  模型权重: {model.weights}")
    print(f"  模型偏置: {model.bias}")

    # ==================== 3. 批量推理 ====================
    print("\n--- [3] 批量推理 ---")

    def batch_predict(batch: pd.DataFrame) -> pd.DataFrame:
        """对一个 batch 进行预测。"""
        features = batch[["f1", "f2", "f3"]].values
        batch["prediction"] = model.predict(features)
        batch["probability"] = model.predict_proba(features)
        return batch

    ds_predicted = ds.map_batches(batch_predict, batch_format="pandas", batch_size=50)
    print("  预测结果（前 10 条）:")
    ds_predicted.show(limit=10)

    # ==================== 4. 统计预测结果 ====================
    print("\n--- [4] 预测统计 ---")
    df = ds_predicted.to_pandas()
    print(f"  预测为 1 的比例: {df['prediction'].mean():.2%}")
    print(f"  平均预测概率: {df['probability'].mean():.4f}")
    print(f"  概率分布:")
    print(f"    0.0-0.2: {((df['probability'] >= 0) & (df['probability'] < 0.2)).sum()}")
    print(f"    0.2-0.4: {((df['probability'] >= 0.2) & (df['probability'] < 0.4)).sum()}")
    print(f"    0.4-0.6: {((df['probability'] >= 0.4) & (df['probability'] < 0.6)).sum()}")
    print(f"    0.6-0.8: {((df['probability'] >= 0.6) & (df['probability'] < 0.8)).sum()}")
    print(f"    0.8-1.0: {((df['probability'] >= 0.8) & (df['probability'] <= 1.0)).sum()}")

    # ==================== 5. GPU 扩展说明 ====================
    print("\n" + "=" * 50)
    print("  GPU 扩展说明")
    print("=" * 50)
    print("""
    使用 GPU 进行批量推理：

    1. 在 map_batches 中指定 num_gpus=1:
       ds.map_batches(
           predict_fn,
           batch_format="pandas",
           num_gpus=1,        # 每个任务使用 1 个 GPU
           batch_size=256,    # GPU 通常用更大的 batch
       )

    2. 模型加载到 GPU:
       import torch
       model = model.to("cuda")

    3. 使用 Actor 模型保持 GPU 上的模型:
       @ray.remote(num_gpus=1)
       class GPUModel:
           def __init__(self):
               self.model = load_model().to("cuda")

           def predict(self, batch):
               with torch.no_grad():
                   return self.model(batch)

    4. 多 GPU 并行:
       - Ray 会自动将数据分发到多个 GPU
       - 通过 concurrency 参数控制 GPU 并发数
    """)

    ray.shutdown()
    print("示例结束。")


if __name__ == "__main__":
    main()
