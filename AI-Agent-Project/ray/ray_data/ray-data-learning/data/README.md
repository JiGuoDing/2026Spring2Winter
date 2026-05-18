# 数据目录说明

## data/raw/

存放由 `scripts/generate_data.py` 生成的原始示例数据：

- `users.csv` — 用户信息表
- `orders.csv` — 订单数据
- `events.jsonl` — 用户行为事件（JSONL 格式）
- `items.parquet` — 商品信息（Parquet 格式）
- `dirty_users.csv` — 含脏数据的用户表（用于调试练习）

## data/processed/

存放示例和项目处理后的输出数据。

生成数据命令：
```bash
python scripts/generate_data.py
```
