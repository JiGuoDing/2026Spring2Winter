# 06 附录

## 常见错误与调试

- `socket.setdefaulttimeout` 只影响之后创建的新 socket，不会修改已经存在的连接。
- `http.client` 发起请求后如果忘了 `response.read()`，可能会导致连接复用行为不符合预期。
- `requests` 默认没有总体超时，生产环境里应始终显式设置 `timeout`。
- UDP 不保证送达顺序，也不保证重复包不会出现。

## 性能测试工具

- `locust`：适合做 HTTP 压测和场景化负载测试。
- `wrk`：适合做高并发 HTTP 压测。
- `ab`：简单直接，适合快速看吞吐和延迟。
- `pytest-benchmark`：适合对 Python 函数做基准测试。

## 推荐阅读

- Python 官方文档：`socket`、`asyncio`、`http.server`、`ssl`
- 经典书籍：《Python网络编程》
- 优质开源项目：`requests`、`Flask`、`websockets`、`grpcio`

## 学习收口

- 如果你已经能解释 TCP、UDP、HTTP、WebSocket、RPC 和 gRPC 的边界，就可以把这份指南当成一条完整的学习主线。
- 如果你还没完全熟悉并发和超时，建议先回到前四章，把每个示例都手动跑一遍。
