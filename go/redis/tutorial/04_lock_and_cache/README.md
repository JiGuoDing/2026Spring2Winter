# 04 分布式锁与缓存模式

## 你会学到什么

- 用 `SETNX + EX` 获取锁。
- 用 Lua 安全释放锁（校验 request_id）。
- Cache Aside 的基本流程（先查缓存，miss 再查库并回填）。

## 运行

```bash
go run ./redis/tutorial/04_lock_and_cache
```

## 面试要点

- 分布式锁为什么不能直接 `DEL`？
- 锁过期时间如何设置？
- 缓存穿透、击穿、雪崩如何应对？
