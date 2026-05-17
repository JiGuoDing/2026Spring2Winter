# 03 HTTP 与高级协议

## 你会学到什么

- 如何用标准库 `http.server` 构建最小 REST 风格服务。
- 如何用 `urllib.request` 和 `requests` 发起 HTTP 请求，并理解超时、会话和连接池。
- 如何用 Flask 表达路由、请求钩子和装饰器式中间件。
- 如何用 WebSocket 做一个最小聊天室广播示例。
- 如何理解 gRPC 的 `.proto` 契约、服务定义和生成代码流程。

## 核心要点

- `http.client` 和 `urllib.request` 更适合理解协议细节；`requests` 更适合工程实践。
- HTTP 服务端通常会把路由、鉴权、日志和错误恢复拆成不同层次。
- WebSocket 适合双向实时通信，但要注意连接上的并发写问题。
- gRPC 的本质是“强类型的远程方法调用”，proto 文件只是接口契约。

## 运行示例

```bash
python 03_http_rpc_websocket/examples/http_stack.py
python 03_http_rpc_websocket/examples/flask_app.py
python 03_http_rpc_websocket/examples/websocket_chat.py
python 03_http_rpc_websocket/examples/grpc_demo.py
```

## 本章示例

- [examples/http_stack.py](examples/http_stack.py)
- [examples/flask_app.py](examples/flask_app.py)
- [examples/websocket_chat.py](examples/websocket_chat.py)
- [examples/hello.proto](examples/hello.proto)
- [examples/grpc_demo.py](examples/grpc_demo.py)

其中 `grpc_demo.py` 会在运行时调用 `grpc_tools.protoc` 根据 [hello.proto](examples/hello.proto) 生成临时 Python stub，然后完成服务端与客户端的完整演示。

## 面试回答要点

- 路由负责请求分发，中间件负责日志、鉴权和统一处理。
- `requests.Session` 会复用底层连接，适合长生命周期的客户端。
- WebSocket 是一次 HTTP Upgrade 之后的长连接协议。
- proto 文件是接口契约，生成代码只是把契约映射成具体语言的类和方法。

## 练习题

1. 为什么 `http.DefaultClient` 不适合直接用于生产环境。
2. 中间件为什么通常是函数套函数的形式。
3. WebSocket 和普通 HTTP 请求的本质区别是什么。
4. `urllib.request` 和 `requests` 在可读性和控制力上有什么差别。
5. 为什么 gRPC 需要 proto 文件来定义服务契约。
