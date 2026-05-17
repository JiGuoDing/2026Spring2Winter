# 03 HTTP 与高级协议

## 你会学到什么

- 如何用 `net/http` 构建服务端、客户端和中间件链。
- 如何用 WebSocket 做一个最小聊天室广播示例。
- 如何用 Go 标准库 `net/rpc` 处理远程方法调用。
- 如何理解 gRPC 的 `.proto`、服务定义和生成代码结构。

## 核心要点

- `http.Client` 一定要设置超时，避免默认客户端无限等待。
- WebSocket 适合双向实时通信，但要注意连接上的并发写问题。
- `net/rpc` 是标准库方案，适合理解 RPC 原理；gRPC 更适合工程化落地。

## 运行示例

```bash
go run ./net/03_http_rpc_websocket/examples/http_stack
go run ./net/03_http_rpc_websocket/examples/websocket_chat
go run ./net/03_http_rpc_websocket/examples/rpc_demo
go run ./net/03_http_rpc_websocket/examples/grpc_demo
```

## 本章示例

- [examples/http_stack/main.go](examples/http_stack/main.go)
- [examples/websocket_chat/main.go](examples/websocket_chat/main.go)
- [examples/rpc_demo/main.go](examples/rpc_demo/main.go)
- [examples/grpc_demo/hello.proto](examples/grpc_demo/hello.proto)
- [examples/grpc_demo/main.go](examples/grpc_demo/main.go)

其中 `grpc_demo` 当前提供的是离线可运行的协议骨架示例，用来说明 proto 契约、服务名和调用形态；等外部依赖可用时，可以把它替换成真正的 grpc-go 生成代码版本。

## 面试回答要点

- `ServeMux` 负责路由分发，中间件负责横切逻辑。
- `Transport` 负责连接池与复用，`Client.Timeout` 负责整体请求超时。
- gRPC 的本质是“强类型的远程方法调用”，proto 文件只是接口契约。

## 练习题

1. 为什么 `http.DefaultClient` 不适合直接用于生产环境。
2. 中间件为什么通常是函数套函数的形式。
3. WebSocket 和普通 HTTP 请求的本质区别是什么。
4. `net/rpc` 和 gRPC 在接口描述能力上有什么不同。
5. 为什么 gRPC 需要 proto 文件来定义服务契约。
