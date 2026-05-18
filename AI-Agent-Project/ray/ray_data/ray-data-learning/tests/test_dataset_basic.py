"""测试 Ray Dataset 基本操作。"""

import ray
import pandas as pd
import numpy as np
import pytest


@pytest.fixture(scope="module")
def ray_init():
    """初始化 Ray。"""
    ray.init(ignore_reinit_error=True, log_to_driver=False)
    yield
    ray.shutdown()


def test_from_items(ray_init):
    """测试从 list 创建 Dataset。"""
    ds = ray.data.from_items([{"x": 1}, {"x": 2}, {"x": 3}])
    assert ds.count() == 3


def test_from_pandas(ray_init):
    """测试从 pandas DataFrame 创建 Dataset。"""
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    ds = ray.data.from_pandas(df)
    assert ds.count() == 3
    assert "a" in ds.columns()
    assert "b" in ds.columns()


def test_from_numpy(ray_init):
    """测试从 numpy 创建 Dataset。"""
    arr = np.array([[1, 2], [3, 4], [5, 6]])
    ds = ray.data.from_numpy({"data": arr})
    assert ds.count() == 3


def test_filter(ray_init):
    """测试 filter 操作。"""
    ds = ray.data.from_items([{"x": i} for i in range(10)])
    filtered = ds.filter(lambda row: row["x"] > 5)
    assert filtered.count() == 4


def test_map(ray_init):
    """测试 map 操作。"""
    ds = ray.data.from_items([{"x": i} for i in range(5)])
    mapped = ds.map(lambda row: {"x": row["x"], "y": row["x"] * 2})
    result = mapped.take(1)
    assert result[0]["y"] == 0


def test_map_batches(ray_init):
    """测试 map_batches 操作。"""
    ds = ray.data.from_items([{"x": i} for i in range(20)])

    def double_batch(batch: pd.DataFrame) -> pd.DataFrame:
        batch["x"] = batch["x"] * 2
        return batch

    result = ds.map_batches(double_batch, batch_format="pandas")
    assert result.count() == 20


def test_schema(ray_init):
    """测试 schema 查看。"""
    ds = ray.data.from_items([{"name": "test", "value": 42}])
    schema = ds.schema()
    assert schema is not None


def test_take(ray_init):
    """测试 take 操作。"""
    ds = ray.data.from_items([{"x": i} for i in range(10)])
    rows = ds.take(3)
    assert len(rows) == 3
    assert rows[0]["x"] == 0


def test_materialize(ray_init):
    """测试 materialize 操作。"""
    ds = ray.data.from_items([{"x": i} for i in range(10)])
    filtered = ds.filter(lambda row: row["x"] > 5)
    materialized = filtered.materialize()
    assert materialized.count() == 4
