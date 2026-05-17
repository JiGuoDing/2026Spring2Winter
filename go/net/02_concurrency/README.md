# 02 并发模型

## 你会学到什么

- 为什么 Go 网络程序常用“每连接一个 goroutine”的模型。
- 如何用 `sync.WaitGroup` 管理一批连接或任务的生命周期。
- 如何用 worker pool 限制并发数，避免 goroutine 数量失控。
- `net.Conn` 在并发读写上的边界应该怎么理解。

## 核心要点

- `goroutine` 很轻量，但不是免费资源，连接数量非常大时仍然需要控制。
- worker pool 本质上是“固定数量的执行单元 + 任务队列”。
- 常见实践是“一条连接一个读循环 + 一条写循环”，而不是多个 goroutine 同时乱写同一个连接。

## 运行示例

```bash
go run ./net/02_concurrency/examples/worker_pool
```

## 本章示例

- [examples/worker_pool/main.go](examples/worker_pool/main.go)

## 面试回答要点

- 连接很多时，直接无限制启动 goroutine 可能会压垮内存和调度器。
- worker pool 的关键不是“更快”，而是“更可控”。
- `WaitGroup` 适合等待一组固定任务结束，不适合动态计数错误地复用。

## 练习题

1. 为什么网络程序里常说“每连接一个 goroutine”。
2. `sync.WaitGroup` 的典型使用场景是什么。
3. worker pool 和无限制启动 goroutine 的差异是什么。
4. 为什么同一个 `net.Conn` 上的并发写要小心。
5. 你会如何设计一个可取消的网络任务池。
