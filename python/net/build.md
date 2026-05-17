# 角色与任务
你是一名资深 Python 工程师和教育内容创作者。请为我生成一份 **《Python 网络编程学习指南》** 项目。

## 项目目标
- 帮助初学者系统掌握 Python 网络编程核心知识。
- 兼顾实战与原理，提供可运行的代码示例和解释。
- 形成一份结构清晰、可直接作为学习或教学参考的文档。

## 输出要求
- 以 **Markdown** 格式输出整个项目。
- 项目应包含多个文件/章节，按目录组织（如果支持多文件输出，请输出一个主索引文件及子章节文件；若只能输出单文件，请使用 `<details>` 或 `<!-- 分节 -->` 模拟多文件结构）。
- 所有代码示例必须是 **可运行的 Python 代码**（除极简片段外），并附带注释和预期输出。
- 每章末尾提供 **练习题**（~5 个），难度循序渐进。

## 项目内容要求（必须包含以下模块）

### 1. 入门篇
- Python 网络编程概述：OSI 模型、TCP/IP 基础、socket 概念。
- 环境准备：Python 安装、`pip` 与虚拟环境（`venv`）、常用工具（`python`、`pip`、`ipython`）。
- 第一个网络程序：使用标准库 `socket` 或 `http.client` 发起简单 HTTP 请求，分析流程。

### 2. 基础核心
- **TCP Socket 编程**：
  - `socket.socket`、`bind`、`listen`、`accept` 构建 TCP 服务端。
  - `connect` 构建 TCP 客户端。
  - 处理粘包与拆包（使用自定义分隔符或长度前缀）。
  - 优雅关闭连接（`shutdown`、设置 `SO_REUSEADDR` 等）。
- **UDP Socket 编程**：
  - `socket.SOCK_DGRAM`、`sendto`、`recvfrom`。
  - 对比 TCP 的无连接特性及适用场景。
- **并发模型**：
  - 每个连接一个线程（`threading.Thread`）的经典模式。
  - 使用 `ThreadPoolExecutor` 限制并发数。
  - 使用 `asyncio` 实现异步 IO 处理（事件循环、协程）。
  - 提及 socket 的线程安全性（通常需要为每个连接创建独立 socket 或加锁）。

### 3. HTTP 与高级协议
- **HTTP 客户端与服务端**：
  - 服务端：使用 `http.server` 基础类、`Flask` 或 `FastAPI` 构建 REST API，自定义路由、中间件模式（装饰器、请求钩子）。
  - 客户端：使用 `urllib.request`、`requests` 库（超时、会话、连接池）。
- **WebSocket**：
  - 使用 `websockets` 库（或 `FastAPI` 的 WebSocket 支持）。
  - 实现简单聊天室示例（广播消息）。
- **RPC**：
  - 使用 `json-rpc`（如 `jsonrpcserver`、`jsonrpcclient`）或 `gRPC`（`grpcio`、`protobuf`）。
  - 演示生成 `.proto` 文件、编写服务端和客户端代码。

### 4. 高级与优化
- **IO 多路复用**：
  - 对比阻塞 socket + 线程模型与 `select`、`poll`、`epoll`（`selectors` 模块）。
  - 介绍 `asyncio` 事件循环底层原理（`SelectorEventLoop`）。
- **零拷贝与性能**：
  - `os.sendfile` 系统调用的使用场景。
  - 内存视图（`memoryview`）与零拷贝数据共享。
- **安全编程**：
  - 使用 `ssl` 模块包装 socket（`ssl.wrap_socket`、`SSLContext`）。
  - 防止 TCP 端口耗尽、SYN Flood 等简单措施。

### 5. 实战项目
- **项目一：并发端口扫描器**
  - 使用 TCP 连接探测端口开放状态。
  - 控制并发数（线程池或 asyncio）、超时、结果输出。

### 6. 附录
- 常见错误与调试（`socket.setdefaulttimeout` 无效、`http.client` 未正确处理响应体、`requests` 未设置超时）。
- 性能测试工具（`locust`、`wrk`、`ab`、`pytest-benchmark`）。
- 推荐阅读：官方文档（`socket`、`asyncio`）、经典书籍（《Python网络编程》）、优质开源项目（`requests`、`FastAPI`、`websockets`）。