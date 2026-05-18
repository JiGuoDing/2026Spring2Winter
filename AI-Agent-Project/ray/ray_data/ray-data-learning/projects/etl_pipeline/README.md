# ETL Pipeline 项目

## 目标

读取原始数据，完成清洗、类型转换、异常过滤、特征列生成，并写出 Parquet。

## 运行

```bash
# 先生成数据
python ../../scripts/generate_data.py

# 运行 ETL 流程
python main.py
```

## 处理步骤

1. 读取 users.csv 和 orders.csv
2. 清洗：过滤无效数据、处理缺失值
3. 类型转换：确保数值类型正确
4. 特征生成：计算用户级统计特征
5. 合并：关联用户和订单数据
6. 写出：输出为 Parquet 格式

## 输出

- `data/processed/users_clean.parquet`
- `data/processed/user_order_features.parquet`
