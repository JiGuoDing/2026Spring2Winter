"""生成 Ray Data 学习项目的示例数据。

生成以下文件到 data/raw/ 目录：
- users.csv: 用户信息表
- orders.csv: 订单数据
- events.jsonl: 用户行为事件
- items.parquet: 商品信息
- dirty_users.csv: 含脏数据的用户表（用于调试练习）
"""

import csv
import json
import os
import random
from datetime import datetime, timedelta

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


# 配置随机种子以保证可复现
random.seed(42)
np.random.seed(42)

# 基础路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

# 常量
NUM_USERS = 1000
NUM_ORDERS = 5000
NUM_EVENTS = 10000
NUM_ITEMS = 200

CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "西安", "重庆"]
GENDERS = ["M", "F", ""]
CATEGORIES = ["电子产品", "服装", "食品", "家居", "图书", "运动", "美妆", "玩具"]
ACTIONS = ["view", "click", "add_to_cart", "purchase", "search", "share", "review"]
DEVICES = ["mobile", "desktop", "tablet", "app"]


def generate_users(num_users):
    """生成用户数据。"""
    users = []
    for i in range(1, num_users + 1):
        age = random.randint(18, 70)
        # 模拟少量缺失值
        city = random.choice(CITIES) if random.random() > 0.05 else ""
        gender = random.choice(GENDERS)
        # 模拟异常值：极少数用户年龄为负数或极大值
        if random.random() < 0.02:
            age = random.choice([-1, 0, 150, 200])
        # 模拟注册时间
        reg_date = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1500))
        users.append({
            "user_id": i,
            "name": f"user_{i:04d}",
            "age": age,
            "gender": gender,
            "city": city,
            "email": f"user_{i}@example.com",
            "registration_date": reg_date.strftime("%Y-%m-%d"),
            "vip_level": random.randint(0, 5),
            "balance": round(random.uniform(0, 10000), 2),
        })
    return users


def generate_orders(num_orders, num_users):
    """生成订单数据。"""
    orders = []
    for i in range(1, num_orders + 1):
        user_id = random.randint(1, num_users)
        num_items = random.randint(1, 5)
        amount = round(random.uniform(10, 5000) * num_items, 2)
        status = random.choice(["completed", "pending", "cancelled", "refunded"])
        order_date = datetime(2023, 1, 1) + timedelta(
            days=random.randint(0, 365),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        orders.append({
            "order_id": i,
            "user_id": user_id,
            "amount": amount,
            "status": status,
            "order_date": order_date.strftime("%Y-%m-%d %H:%M:%S"),
            "payment_method": random.choice(["alipay", "wechat", "credit_card", "bank"]),
            "num_items": num_items,
        })
    return orders


def generate_events(num_events, num_users):
    """生成用户行为事件（JSONL 格式）。"""
    events = []
    for i in range(1, num_events + 1):
        user_id = random.randint(1, num_users)
        event_time = datetime(2024, 1, 1) + timedelta(
            days=random.randint(0, 180),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        events.append({
            "event_id": i,
            "user_id": user_id,
            "action": random.choice(ACTIONS),
            "item_id": random.randint(1, NUM_ITEMS),
            "timestamp": event_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "device": random.choice(DEVICES),
            "session_duration": random.randint(1, 3600),
        })
    return events


def generate_items(num_items):
    """生成商品信息（返回 PyArrow Table 用于写 Parquet）。"""
    item_ids = list(range(1, num_items + 1))
    names = [f"item_{i:04d}" for i in item_ids]
    categories = [random.choice(CATEGORIES) for _ in item_ids]
    prices = [round(random.uniform(5, 2000), 2) for _ in item_ids]
    stocks = [random.randint(0, 10000) for _ in item_ids]
    ratings = [round(random.uniform(1, 5), 1) for _ in item_ids]
    created = [
        (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1500))).strftime("%Y-%m-%d")
        for _ in item_ids
    ]

    table = pa.table({
        "item_id": pa.array(item_ids, type=pa.int64()),
        "name": pa.array(names, type=pa.string()),
        "category": pa.array(categories, type=pa.string()),
        "price": pa.array(prices, type=pa.float64()),
        "stock": pa.array(stocks, type=pa.int64()),
        "rating": pa.array(ratings, type=pa.float64()),
        "created_date": pa.array(created, type=pa.string()),
    })
    return table


def generate_dirty_users(num_users):
    """生成含脏数据的用户表，用于调试练习。"""
    users = generate_users(num_users)
    dirty = []
    for i, u in enumerate(users):
        row = dict(u)
        # 注入各种脏数据
        if i % 50 == 0:
            row["age"] = "not_a_number"  # 类型错误
        if i % 30 == 0:
            row["user_id"] = ""  # 缺失 ID
        if i % 20 == 0:
            row["email"] = "invalid-email"  # 无效邮箱
        if i % 100 == 0:
            row["balance"] = -9999  # 异常余额
        if i % 70 == 0:
            row["name"] = None  # 空值
        dirty.append(row)
    return dirty


def write_csv(path, rows, fieldnames):
    """写入 CSV 文件。"""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  已生成: {os.path.basename(path)} ({len(rows)} 行)")


def write_jsonl(path, records):
    """写入 JSONL 文件。"""
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  已生成: {os.path.basename(path)} ({len(records)} 行)")


def write_parquet(path, table):
    """写入 Parquet 文件。"""
    pq.write_table(table, path)
    print(f"  已生成: {os.path.basename(path)} ({table.num_rows} 行)")


def main():
    """生成所有示例数据。"""
    print("=" * 50)
    print("  Ray Data 学习项目 - 示例数据生成器")
    print("=" * 50)

    os.makedirs(RAW_DIR, exist_ok=True)

    # 生成用户数据
    print("\n[1/5] 生成用户数据...")
    users = generate_users(NUM_USERS)
    write_csv(os.path.join(RAW_DIR, "users.csv"), users, users[0].keys())

    # 生成订单数据
    print("\n[2/5] 生成订单数据...")
    orders = generate_orders(NUM_ORDERS, NUM_USERS)
    write_csv(os.path.join(RAW_DIR, "orders.csv"), orders, orders[0].keys())

    # 生成行为事件
    print("\n[3/5] 生成行为事件...")
    events = generate_events(NUM_EVENTS, NUM_USERS)
    write_jsonl(os.path.join(RAW_DIR, "events.jsonl"), events)

    # 生成商品信息
    print("\n[4/5] 生成商品信息...")
    items_table = generate_items(NUM_ITEMS)
    write_parquet(os.path.join(RAW_DIR, "items.parquet"), items_table)

    # 生成脏数据
    print("\n[5/5] 生成脏数据用户表...")
    dirty_users = generate_dirty_users(NUM_USERS)
    write_csv(os.path.join(RAW_DIR, "dirty_users.csv"), dirty_users, dirty_users[0].keys())

    print("\n" + "=" * 50)
    print(f"  所有数据已生成到: {RAW_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
