# Redis CLI 实操题 (面试训练)

每题都要求你自己在 redis-cli 执行一遍，形成肌肉记忆。

## 题目 1：用户会话缓存

目标：
- 写入 `session:1001`，值为 JSON。
- 设置 30 分钟过期。
- 查看剩余 TTL。

参考命令：
```bash
SET session:1001 '{"uid":1001,"token":"abc"}' EX 1800
TTL session:1001
GET session:1001
```

## 题目 2：登录计数器

目标：
- `login:count:1001` 从 0 增加到 3。

参考命令：
```bash
SET login:count:1001 0
INCR login:count:1001
INCR login:count:1001
INCR login:count:1001
GET login:count:1001
```

## 题目 3：对象字段更新

目标：
- 创建用户 Hash。
- 仅更新 `city` 字段。

参考命令：
```bash
HSET user:1001 name alice age 28 city shanghai
HSET user:1001 city beijing
HGETALL user:1001
```

## 题目 4：共同标签

目标：
- 构造两个集合并求交集。

参考命令：
```bash
SADD tags:article:1 redis go cache
SADD tags:article:2 redis interview go
SINTER tags:article:1 tags:article:2
```

## 题目 5：积分排行榜

目标：
- 写入 3 个用户积分。
- 查询 Top2 和指定用户排名。

参考命令：
```bash
ZADD rank:score 100 u1 150 u2 120 u3
ZREVRANGE rank:score 0 1 WITHSCORES
ZREVRANK rank:score u1
```

## 题目 6：事务与 Lua

目标：
- 用 `MULTI/EXEC` 执行批量计数。
- 用 Lua 做安全解锁。

参考命令：
```bash
MULTI
INCR order:count
INCR pay:count
EXEC

EVAL "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) else return 0 end" 1 lock:demo req-001
```

## 题目 7：Stream 消费组

目标：
- 写入消息。
- 创建消费组。
- 拉取消息并 ACK。

参考命令：
```bash
XADD stream:order * order_id 9001 status created
XGROUP CREATE stream:order g1 0 MKSTREAM
XREADGROUP GROUP g1 c1 COUNT 10 STREAMS stream:order >
XACK stream:order g1 <message-id>
```

## 复盘检查

- 你能否不用看文档写出每题核心命令？
- 你能否解释每条命令对应的底层数据结构？
- 你能否说出线上风险命令及替代方案？
