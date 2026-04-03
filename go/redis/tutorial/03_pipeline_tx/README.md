# 03 Pipeline 与事务

## 你会学到什么

- Pipeline 用于减少 RTT，提升吞吐。
- `WATCH + TxPipelined` 实现乐观锁。
- Redis 事务不回滚这一核心认知。

## 运行

```bash
go run ./redis/tutorial/03_pipeline_tx
```

## 面试要点

- Pipeline 和事务的本质差异是什么？
- Redis 为什么没有关系型数据库那种回滚？
- 高并发扣减库存如何避免超卖？
