"""08 - 生态集成：pandas / numpy / pyarrow / scikit-learn。

本示例展示：
- Ray Data 与 pandas 互转
- Ray Data 与 numpy 互转
- Ray Data 与 PyArrow 互转
- 使用 scikit-learn 进行简单特征工程
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
    print("  生态集成：pandas / numpy / pyarrow / sklearn")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # 创建示例数据
    ds = ray.data.from_items([
        {"feature1": i * 0.1, "feature2": i * 0.2 + 1, "label": i % 2}
        for i in range(100)
    ])

    # ==================== 1. pandas 互转 ====================
    print("\n--- [1] pandas 互转 ---")
    # Ray Data -> pandas
    df = ds.to_pandas(limit=50)
    print(f"  转为 pandas DataFrame: {df.shape}")
    print(f"  列类型:\n{df.dtypes}")

    # pandas -> Ray Data
    ds_from_pandas = ray.data.from_pandas(df)
    print(f"  从 pandas 创建: {ds_from_pandas.count()} 行")

    # 在 map_batches 中使用 pandas
    def pandas_feature_eng(batch: pd.DataFrame) -> pd.DataFrame:
        batch["feature_ratio"] = batch["feature1"] / (batch["feature2"] + 1e-8)
        batch["feature_sum"] = batch["feature1"] + batch["feature2"]
        return batch

    ds_pandas_eng = ds.map_batches(pandas_feature_eng, batch_format="pandas")
    print(f"  pandas 特征工程后: {ds_pandas_eng.columns()}")
    ds_pandas_eng.show(limit=3)

    # ==================== 2. numpy 互转 ====================
    print("\n--- [2] numpy 互转 ---")
    # Ray Data -> numpy
    numpy_dict = ds.to_numpy()
    print(f"  转为 numpy dict: {list(numpy_dict.keys())}")
    for k, v in numpy_dict.items():
        print(f"    {k}: shape={v.shape}, dtype={v.dtype}")

    # numpy -> Ray Data
    ds_from_numpy = ray.data.from_numpy({
        "a": np.array([1.0, 2.0, 3.0]),
        "b": np.array([4.0, 5.0, 6.0]),
    })
    print(f"  从 numpy 创建:")
    ds_from_numpy.show()

    # ==================== 3. PyArrow 互转 ====================
    print("\n--- [3] PyArrow 互转 ---")
    # Ray Data -> PyArrow
    arrow_table = ds.to_arrow(limit=50)
    print(f"  转为 Arrow Table: {arrow_table.shape}")
    print(f"  Schema: {arrow_table.schema}")

    # PyArrow -> Ray Data
    ds_from_arrow = ray.data.from_arrow(arrow_table)
    print(f"  从 Arrow 创建: {ds_from_arrow.count()} 行")

    # ==================== 4. scikit-learn 集成 ====================
    print("\n--- [4] scikit-learn 集成 ---")
    try:
        from sklearn.preprocessing import StandardScaler

        # 使用 map_batches 进行 sklearn 特征缩放
        def sklearn_scale(batch: pd.DataFrame) -> pd.DataFrame:
            scaler = StandardScaler()
            features = batch[["feature1", "feature2"]]
            scaled = scaler.fit_transform(features)
            batch["feature1_scaled"] = scaled[:, 0]
            batch["feature2_scaled"] = scaled[:, 1]
            return batch

        ds_scaled = ds.map_batches(sklearn_scale, batch_format="pandas")
        print("  StandardScaler 缩放后:")
        ds_scaled.show(limit=3)
    except ImportError:
        print("  scikit-learn 未安装，跳过此示例")
        print("  安装命令: pip install scikit-learn")

    # ==================== 5. 综合示例：特征工程流水线 ====================
    print("\n--- [5] 综合：特征工程流水线 ---")

    def feature_pipeline(batch: pd.DataFrame) -> pd.DataFrame:
        """完整的特征工程流水线。"""
        # 1. 基础特征
        batch["feature_ratio"] = batch["feature1"] / (batch["feature2"] + 1e-8)
        batch["feature_sum"] = batch["feature1"] + batch["feature2"]
        batch["feature_diff"] = batch["feature2"] - batch["feature1"]

        # 2. 非线性特征
        batch["feature1_sq"] = batch["feature1"] ** 2
        batch["feature_log"] = np.log1p(np.abs(batch["feature1"]))

        # 3. 分桶
        batch["feature1_bin"] = pd.cut(batch["feature1"], bins=5, labels=False)

        return batch

    ds_pipeline = ds.map_batches(feature_pipeline, batch_format="pandas")
    print(f"  流水线输出列: {ds_pipeline.columns()}")
    ds_pipeline.show(limit=3)

    ray.shutdown()
    print("\n示例结束。")


if __name__ == "__main__":
    main()
