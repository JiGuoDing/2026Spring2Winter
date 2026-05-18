"""数据处理工具函数。"""

import os
import json


def ensure_dir(path):
    """确保目录存在，不存在则创建。"""
    os.makedirs(path, exist_ok=True)
    return path


def read_jsonl(path):
    """读取 JSONL 文件，返回字典列表。"""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(path, records):
    """将字典列表写入 JSONL 文件。"""
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_separator(title, char="=", width=60):
    """打印分隔线，便于阅读输出。"""
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def print_dataset_info(ds, name="Dataset"):
    """打印 Dataset 基本信息。"""
    print(f"\n--- {name} 信息 ---")
    print(f"  行数: {ds.count()}")
    print(f"  Schema: {ds.schema()}")
    print(f"  列: {ds.columns()}")
