# 01 String 与 Hash

## 你会学到什么

- String 适合缓存对象与计数器。
- Hash 适合对象字段存储与局部更新。
- Go 中 JSON 序列化后写入 String 的常见方式。

## 运行

```bash
go run ./redis/tutorial/01_string_hash
```

## 面试要点

- String 和 Hash 的选型区别是什么？
- Hash 为什么更适合字段级更新？
- 计数器为什么在 Redis 中是原子操作？
