"""测试数据生成脚本。"""

import os
import subprocess
import pytest


# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")


@pytest.fixture(scope="module", autouse=True)
def generate_data():
    """运行数据生成脚本。"""
    script = os.path.join(BASE_DIR, "scripts", "generate_data.py")
    result = subprocess.run(
        ["python", script],
        capture_output=True,
        text=True,
        cwd=BASE_DIR,
    )
    assert result.returncode == 0, f"数据生成失败: {result.stderr}"


def test_users_csv_exists():
    """测试 users.csv 是否生成。"""
    path = os.path.join(RAW_DIR, "users.csv")
    assert os.path.exists(path), f"文件不存在: {path}"


def test_orders_csv_exists():
    """测试 orders.csv 是否生成。"""
    path = os.path.join(RAW_DIR, "orders.csv")
    assert os.path.exists(path), f"文件不存在: {path}"


def test_events_jsonl_exists():
    """测试 events.jsonl 是否生成。"""
    path = os.path.join(RAW_DIR, "events.jsonl")
    assert os.path.exists(path), f"文件不存在: {path}"


def test_items_parquet_exists():
    """测试 items.parquet 是否生成。"""
    path = os.path.join(RAW_DIR, "items.parquet")
    assert os.path.exists(path), f"文件不存在: {path}"


def test_dirty_users_csv_exists():
    """测试 dirty_users.csv 是否生成。"""
    path = os.path.join(RAW_DIR, "dirty_users.csv")
    assert os.path.exists(path), f"文件不存在: {path}"


def test_users_csv_has_content():
    """测试 users.csv 有内容。"""
    path = os.path.join(RAW_DIR, "users.csv")
    with open(path, "r") as f:
        lines = f.readlines()
    assert len(lines) > 1, "users.csv 应该有多行数据"


def test_orders_csv_has_content():
    """测试 orders.csv 有内容。"""
    path = os.path.join(RAW_DIR, "orders.csv")
    with open(path, "r") as f:
        lines = f.readlines()
    assert len(lines) > 1, "orders.csv 应该有多行数据"


def test_events_jsonl_has_content():
    """测试 events.jsonl 有内容。"""
    path = os.path.join(RAW_DIR, "events.jsonl")
    with open(path, "r") as f:
        lines = f.readlines()
    assert len(lines) > 1, "events.jsonl 应该有多行数据"
