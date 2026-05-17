# Golang 网络编程学习指南

这是一个面向初学者和面试复习场景的 Go 网络编程学习项目。内容按“入门 -> TCP/UDP -> 并发模型 -> HTTP / WebSocket / RPC / gRPC -> 高级与优化 -> 实战项目 -> 附录”的顺序组织，兼顾原理、可运行示例和工程化习惯。

## 学习目标

- 系统理解 Go 网络编程的基础概念和常用标准库 API。
- 通过可运行示例掌握 TCP、UDP、HTTP、WebSocket、RPC 和 gRPC 的基本用法。
- 了解并发模型、worker pool、超时、优雅关闭和常见调试问题。
- 对 IO 多路复用、零拷贝、TLS 和 gnet 这类进阶话题形成整体认识。

## 目录结构

```text
net/
├── README.md
├── build.md
├── 00_intro/
├── 01_tcp_udp/
├── 02_concurrency/
├── 03_http_rpc_websocket/
├── 04_optimization_security/
├── 05_port_scanner/
└── 06_appendix/
```

## 推荐阅读顺序

1. [00_intro/README.md](00_intro/README.md)
2. [01_tcp_udp/README.md](01_tcp_udp/README.md)
3. [02_concurrency/README.md](02_concurrency/README.md)
4. [03_http_rpc_websocket/README.md](03_http_rpc_websocket/README.md)
5. [04_optimization_security/README.md](04_optimization_security/README.md)
6. [05_port_scanner/README.md](05_port_scanner/README.md)
7. [06_appendix/README.md](06_appendix/README.md)

## 运行前准备

在 go 目录下执行一次依赖整理：

```bash
go mod tidy
```

然后分别运行各章节示例，例如：

```bash
go run ./net/00_intro/examples/net_dial_http
go run ./net/01_tcp_udp/examples/tcp_length_prefix
go run ./net/01_tcp_udp/examples/udp_echo
go run ./net/02_concurrency/examples/worker_pool
go run ./net/03_http_rpc_websocket/examples/http_stack
go run ./net/03_http_rpc_websocket/examples/websocket_chat
go run ./net/03_http_rpc_websocket/examples/rpc_demo
go run ./net/03_http_rpc_websocket/examples/grpc_demo
go run ./net/04_optimization_security/examples/io_copy
go run ./net/04_optimization_security/examples/gnet_echo
go run ./net/05_port_scanner/examples/port_scanner
```

Linux 专项内容请查看 [04_optimization_security/README.md](04_optimization_security/README.md)，其中包含 sendfile / splice 的平台说明与替代方案。

## 章节风格说明

- 每章都尽量以“概念 -> 代码 -> 输出 -> 练习题”的顺序展开。
- 示例以本地回环地址和临时端口为主，避免依赖外网。
- 面试回答侧重三部分：问题背景、API 行为、实践中的边界和坑。

## 需求来源

本项目的原始需求说明保存在 [build.md](build.md)。