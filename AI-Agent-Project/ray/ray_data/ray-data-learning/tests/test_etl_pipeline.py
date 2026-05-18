"""测试 ETL Pipeline。"""

import os
import subprocess
import ray
import pandas as pd
import pytest


# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")


@pytest.fixture(scope="module", autouse=True)
def run_etl():
    """运行 ETL Pipeline。"""
    # 先确保数据已生成
    gen_script = os.path.join(BASE_DIR, "scripts", "generate_data.py")
    subprocess.run(["python", gen_script], capture_output=True, cwd=BASE_DIR)

    # 运行 ETL
    etl_script = os.path.join(BASE_DIR, "projects", "etl_pipeline", "main.py")
    result = subprocess.run(
        ["python", etl_script],
        capture_output=True,
        text=True,
        cwd=BASE_DIR,
    )
    assert result.returncode == 0, f"ETL 运行失败: {result.stderr}"


def test_users_clean_exists():
    """测试清洗后的用户数据是否生成。"""
    path = os.path.join(PROCESSED_DIR, "users_clean.parquet")
    assert os.path.exists(path), f"文件不存在: {path}"


def test_user_order_features_exists():
    """测试用户订单特征是否生成。"""
    path = os.path.join(PROCESSED_DIR, "user_order_features.parquet")
    assert os.path.exists(path), f"文件不存在: {path}"


def test_users_clean_readable():
    """测试清洗后的用户数据可读取。"""
    path = os.path.join(PROCESSED_DIR, "users_clean.parquet")
    if os.path.exists(path):
        df = pd.read_parquet(path)
        assert len(df) > 0
        assert "user_id" in df.columns
        assert "age" in df.columns


def test_user_order_features_readable():
    """测试用户订单特征可读取。"""
    path = os.path.join(PROCESSED_DIR, "user_order_features.parquet")
    if os.path.exists(path):
        df = pd.read_parquet(path)
        assert len(df) > 0
        assert "user_id" in df.columns
        assert "order_count" in df.columns


def test_etl_with_ray():
    """测试使用 Ray Data 运行 ETL 关键步骤。"""
    ray.init(ignore_reinit_error=True, log_to_driver=False)
    try:
        users_path = os.path.join(RAW_DIR, "users.csv")
        if not os.path.exists(users_path):
            pytest.skip("数据未生成")

        # 测试读取
        ds = ray.data.read_csv(users_path)
        assert ds.count() > 0

        # 测试 filter
        filtered = ds.filter(lambda row: row.get("age", 0) > 0)
        assert filtered.count() > 0

        # 测试 map_batches
        def clean_batch(batch: pd.DataFrame) -> pd.DataFrame:
            batch["age"] = pd.to_numeric(batch["age"], errors="coerce").fillna(0).astype(int)
            return batch

        cleaned = ds.map_batches(clean_batch, batch_format="pandas")
        assert cleaned.count() > 0
    finally:
        ray.shutdown()
