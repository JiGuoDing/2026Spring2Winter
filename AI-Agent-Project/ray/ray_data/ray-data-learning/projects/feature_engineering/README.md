# Feature Engineering 项目

## 目标

读取用户行为数据（events.jsonl），按用户聚合，生成用户级特征表。

## 运行

```bash
# 先生成数据
python ../../scripts/generate_data.py

# 运行特征工程
python main.py
```

## 处理步骤

1. 读取 events.jsonl 用户行为数据
2. 按用户聚合行为统计
3. 生成用户级特征：
   - 行为次数统计
   - 活跃天数
   - 会话时长统计
   - 设备偏好
   - 最近活跃时间
4. 写出为 Parquet

## Shuffle 说明

groupby 操作会触发 shuffle，本项目展示了哪些步骤涉及 shuffle 以及如何优化。
