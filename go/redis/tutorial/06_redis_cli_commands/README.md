# 06 Redis 命令行教程 (与 Go 无关)

本教程专注 redis-cli，目标是让你在后端面试中不仅会写命令，还能说清楚命令背后的原理和适用场景。

## 学习目标

- 掌握 redis-cli 连接、认证、切库、常用诊断命令。
- 覆盖 String、Hash、List、Set、ZSet、Stream、Bitmap、HyperLogLog、GEO 常见操作。
- 理解事务、Lua、过期与淘汰、持久化、主从和集群的关键命令和原理。
- 能把命令操作和面试回答连接起来（场景 -> 命令 -> 原理 -> 风险）。

## 1. 连接与基础操作

### 1.1 连接 Redis

```bash
# 本地连接
redis-cli -h 127.0.0.1 -p 6379

# 远程 + 密码
redis-cli -h 10.0.0.8 -p 6379 -a your_password

# TLS 连接（云服务常见）
redis-cli --tls -h redis.example.com -p 6380 -a your_password
```

### 1.2 基础检查命令

```bash
PING
AUTH your_password
SELECT 0
DBSIZE
INFO server
INFO memory
```

原理要点：
- `PING` 用于连通性探测。
- `INFO` 是线上排障入口，面试常问如何定位 Redis 问题。

## 2. Key 管理与过期机制

### 2.1 Key 生命周期

```bash
SET user:1 alice
EXPIRE user:1 60
TTL user:1
PERSIST user:1
DEL user:1
```

### 2.2 批量查看

```bash
# 生产环境优先 SCAN，避免 KEYS 阻塞
SCAN 0 MATCH user:* COUNT 100

# 仅用于开发环境快速查看
KEYS user:*
```

原理要点：
- Redis 过期删除采用惰性删除 + 定期删除。
- `KEYS *` 是 O(N) 且阻塞，线上风险高。

## 3. 常见数据类型命令

### 3.1 String

```bash
SET page:view 100
INCR page:view
MSET k1 v1 k2 v2
MGET k1 k2
```

适用场景：计数器、缓存对象、分布式锁值。

### 3.2 Hash

```bash
HSET user:1001 name alice age 28 city shanghai
HGET user:1001 name
HMGET user:1001 name city
HINCRBY user:1001 login_count 1
HGETALL user:1001
```

适用场景：对象字段存储，减少整对象反序列化。

### 3.3 List

```bash
LPUSH queue:mail job1 job2
RPOP queue:mail
BLPOP queue:mail 5
LRANGE queue:mail 0 -1
```

适用场景：简单队列、时间线。

### 3.4 Set

```bash
SADD tag:a redis go cache
SADD tag:b redis interview
SINTER tag:a tag:b
SUNION tag:a tag:b
SDIFF tag:a tag:b
```

适用场景：去重、共同好友、标签系统。

### 3.5 ZSet

```bash
ZADD rank:game 1200 user1 980 user2 1350 user3
ZREVRANGE rank:game 0 2 WITHSCORES
ZREVRANK rank:game user1
ZSCORE rank:game user2
```

适用场景：排行榜、延迟任务。

### 3.6 Stream

```bash
XADD stream:order * order_id 9001 status created
XGROUP CREATE stream:order g1 0 MKSTREAM
XREADGROUP GROUP g1 c1 COUNT 10 STREAMS stream:order >
XACK stream:order g1 1712200000000-0
XPENDING stream:order g1
```

适用场景：可靠消息队列，支持消费组和待确认追踪。

### 3.7 Bitmap / HyperLogLog / GEO

```bash
# Bitmap
SETBIT sign:2026-04:1001 3 1
BITCOUNT sign:2026-04:1001

# HyperLogLog
PFADD uv:2026-04-03 u1 u2 u3
PFCOUNT uv:2026-04-03

# GEO
GEOADD store:city 121.4737 31.2304 shanghai_store
GEOSEARCH store:city FROMLONLAT 121.47 31.23 BYRADIUS 10 km WITHDIST
```

## 4. 事务与 Lua

### 4.1 事务

```bash
MULTI
INCR counter:a
INCR counter:b
EXEC
```

原理要点：
- Redis 事务是命令队列批量执行，不是关系型事务。
- 运行时错误不会回滚已执行命令。

### 4.2 Lua 原子脚本

```bash
EVAL "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) else return 0 end" 1 lock:order req-001
```

原理要点：
- Lua 在 Redis 内部单线程执行，天然原子。
- 常用于分布式锁安全解锁、库存扣减。

## 5. 性能与排障命令

```bash
INFO stats
INFO commandstats
SLOWLOG GET 10
LATENCY DOCTOR
MEMORY STATS
MEMORY USAGE user:1001
```

谨慎命令：
- `MONITOR`：调试方便，但开销高。
- `FLUSHDB` / `FLUSHALL`：危险命令，需严格权限控制。

## 6. 持久化与高可用检查

```bash
INFO persistence
BGSAVE
BGREWRITEAOF

INFO replication
ROLE
```

原理要点：
- RDB：快照，恢复快。
- AOF：数据更完整，体积更大。
- 主从复制与哨兵、集群是高可用基础。

## 7. 面试回答模板

回答 Redis 命令题建议四步：
1. 业务场景。
2. 核心命令。
3. 原理解释（复杂度、数据结构、原子性）。
4. 风险与优化（阻塞、并发、容量、监控）。

示例：如何做排行榜？
- 场景：实时积分排名。
- 命令：`ZADD`、`ZREVRANGE WITHSCORES`、`ZREVRANK`。
- 原理：ZSet 底层跳表 + 哈希表，范围查询高效。
- 风险：大 key、频繁更新；优化可分榜单、定时归档。

## 8. 下一步练习

请继续阅读同目录下的 [hands_on_lab.md](hands_on_lab.md) 完成实操题，再用 [interview_drills.md](interview_drills.md) 进行面试演练。
