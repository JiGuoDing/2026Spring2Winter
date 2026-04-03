# 05 Stream 与消费组

## 你会学到什么

- 如何创建 Stream 和消费组。
- 如何生产、消费并 ACK 消息。
- 为什么 Stream 更适合可靠消息场景。

## 运行

```bash
go run ./redis/tutorial/05_stream
```

## 面试要点

- Stream 和 List 做队列如何选型？
- 消费组中的 PEL 是什么？
- 消费者宕机后消息如何恢复处理？
