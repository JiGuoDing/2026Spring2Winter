# 角色与任务
你是一名资深 Golang 工程师和教育内容创作者。请为我生成一份 **《Golang 网络编程学习指南》** 项目。

## 项目目标
- 帮助初学者系统掌握 Go 语言网络编程核心知识。
- 兼顾实战与原理，提供可运行的代码示例和解释。
- 形成一份结构清晰、可直接作为学习或教学参考的文档。

## 输出要求
- 以 **Markdown** 格式输出整个项目。
- 项目应包含多个文件/章节，按目录组织（如果支持多文件输出，请输出一个主索引文件及子章节文件；若只能输出单文件，请使用 `<details>` 或 `<!-- 分节 -->` 模拟多文件结构）。
- 所有代码示例必须是 **可运行的 Go 代码**（除极简片段外），并附带注释和预期输出。
- 每章末尾提供 **练习题**（~5 个），难度循序渐进。

## 项目内容要求（必须包含以下模块）

### 1. 入门篇
- Go 网络编程概述：OSI 模型、TCP/IP 基础、socket 概念。
- 环境准备：Go 安装、工作区、常用工具（`go run`、`go mod`）。
- 第一个网络程序：使用 `net.Dial` 发起简单 HTTP 请求，分析流程。

### 2. 基础核心
- **TCP Socket 编程**：
  - `net.Listen` / `net.Accept` 构建 TCP 服务端。
  - `net.DialTCP` 构建 TCP 客户端。
  - 处理粘包与拆包（使用自定义分隔符或长度前缀）。
  - 优雅关闭连接（`SetDeadline`、`CloseRead`/`CloseWrite`）。
- **UDP Socket 编程**：
  - `net.ListenUDP` / `ReadFromUDP` / `WriteToUDP`。
  - 对比 TCP 的无连接特性及适用场景。
- **并发模型**：
  - 每个连接一个 goroutine 的经典模式。
  - 使用 `sync.WaitGroup` 管理连接。
  - 使用 worker pool 限制并发数。
  - `net.Conn` 的并发读写安全性说明。

### 3. HTTP 与高级协议
- **标准库 `net/http`**：
  - 服务端：`http.HandleFunc`、自定义 Handler、`ServeMux`。
  - 客户端：`http.Client` 超时设置、`Transport` 连接池。
  - 中间件模式（日志、鉴权、恢复 panic）。
- **WebSocket**：
  - 使用 `gorilla/websocket` 或 `nhooyr.io/websocket`。
  - 实现简单聊天室示例（广播消息）。
- **RPC**：
  - Go 内置 `net/rpc`（JSON-RPC 或 Gob）。
  - gRPC 基础（生成 `.proto`、服务端/客户端代码）。

### 4. 高级与优化
- **IO 多路复用**：
  - 对比标准库的 goroutine-per-conn 与 `epoll`/`kqueue` 模型。
  - 介绍 `gnet` 或 `evio` 事件驱动框架（简单示例）。
- **零拷贝与性能**：
  - `io.Copy` 内部原理。
  - `splice`、`sendfile` 在 Go 中的使用。
- **安全编程**：
  - TLS/SSL 配置（`crypto/tls`）。
  - 防止 TCP 端口耗尽、SYN Flood 等简单措施。

### 5. 实战项目
- **项目一：并发端口扫描器**
  - 使用 TCP 连接探测端口开放状态。
  - 控制并发数、超时、结果输出。

### 6. 附录
- 常见错误与调试（`ioutil.ReadAll` 阻塞、`http.DefaultClient` 无超时）。
- 性能测试工具（`wrk`、`ab`、`go test -bench`）。
- 推荐阅读：官方文档、经典书籍、优质开源项目。

## 文档组织建议（目录结构）