# 06 附录

## 常见错误与调试

- `ioutil.ReadAll` 或 `io.ReadAll` 读不到结束条件时，往往会一直阻塞。
- `http.DefaultClient` 默认没有请求超时，生产环境通常要显式设置。
- TCP 长连接要关注读写 deadline、连接关闭、半关闭和资源回收。
- WebSocket 和一些事件驱动框架里，连接的并发写必须小心处理。

## 性能测试工具

- `wrk`：更适合压测 HTTP 服务。
- `ab`：上手简单，适合快速看吞吐和延迟。
- `go test -bench`：适合测标准库和本地实现的微基准。

## 推荐阅读

- Go 官方文档：`net`、`net/http`、`crypto/tls`、`net/rpc`
- Go blog 上关于网络、并发和性能优化的文章
- gnet 项目源码和示例
- `gorilla/websocket` 官方仓库

## 本章示例

- [examples/bench_copy/bench_test.go](examples/bench_copy/bench_test.go)

## 练习题

1. 为什么 `ReadAll` 在网络程序里要慎用。
2. 为什么 HTTP 客户端要设置超时。
3. 你会如何为 TCP 服务增加可观测性。
4. `wrk`、`ab` 和 `go test -bench` 分别适合什么场景。
5. 当网络程序出现大量 TIME_WAIT 时，你会先看哪些问题。
