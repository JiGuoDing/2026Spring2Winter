# Go + Redis 面试高频问答

## 1. 为什么 Go 中常用 go-redis/v9？

- API 完整，支持 Cluster、Sentinel、Pipeline、事务、Lua、Stream。
- 对 Context 友好，便于控制超时和取消。
- 社区成熟，生产使用广。

## 2. Go 里如何设置 Redis 超时？

- 客户端侧：`DialTimeout`、`ReadTimeout`、`WriteTimeout`。
- 请求侧：`context.WithTimeout`。
- 建议双层超时，避免长尾阻塞。

## 3. Pipeline 和事务有什么区别？

- Pipeline：减少网络往返，不保证原子性。
- 事务：命令批量执行，但不回滚。
- Lua：复杂逻辑原子执行，常用于扣减库存、解锁校验。

## 4. 如何实现安全分布式锁？

- 加锁：`SET key value NX PX ttl`。
- 解锁：Lua 比对 value 后删除，防误删。
- 续期：业务耗时不确定时需 watchdog 或手动续期。

## 5. Redis 事务为什么不支持回滚？

- Redis 设计目标是高性能，事务模型偏轻量。
- `EXEC` 后逐条执行，运行期错误不会回滚之前命令。

## 6. 如何处理缓存穿透、击穿、雪崩？

- 穿透：布隆过滤器 + 空值短期缓存。
- 击穿：热点 key 互斥重建。
- 雪崩：过期时间打散 + 限流降级 + 多级缓存。

## 7. Stream 和 List 做队列怎么选？

- List：轻量简单，但消费确认和重放能力弱。
- Stream：支持消费组、ACK、待处理消息追踪，适合可靠队列。

## 8. Go 中如何避免 Redis 连接泄漏？

- 复用全局客户端，不要每次请求 `NewClient`。
- 程序退出前 `Close()`。
- 结合指标监控连接池使用率。

## 9. 面试回答模板

- 先给结论。
- 再讲适用场景与关键命令。
- 最后说明边界问题与优化策略。
