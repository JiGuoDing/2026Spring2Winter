# Python 网络编程学习指南

这是一个面向初学者和面试复习场景的 Python 网络编程学习项目。内容按“入门 -> TCP/UDP -> 并发模型 -> HTTP / WebSocket / RPC / gRPC -> 高级与优化 -> 实战项目 -> 附录”的顺序组织，兼顾原理、可运行示例和工程化习惯。

原始需求来源于 [build.md](build.md)。

## 学习目标

- 系统理解 Python 网络编程的基础概念和常用标准库 API。
- 通过可运行示例掌握 TCP、UDP、HTTP、WebSocket、RPC 和 gRPC 的基本用法。
- 了解并发模型、线程池、异步 IO、超时、优雅关闭和常见调试问题。
- 对 IO 多路复用、零拷贝、TLS 和基础安全防护形成整体认识。

## 目录结构

```text
net/
├── README.md
├── build.md
├── requirements.txt
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

在 `python/net` 目录下建议先创建虚拟环境并安装依赖：

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

之后可以直接运行各章示例，例如：

```bash
python 00_intro/examples/http_request.py
python 01_tcp_udp/examples/tcp_length_prefix.py
python 01_tcp_udp/examples/udp_echo.py
python 02_concurrency/examples/threaded_echo.py
python 02_concurrency/examples/thread_pool_echo.py
python 02_concurrency/examples/asyncio_echo.py
python 03_http_rpc_websocket/examples/http_stack.py
python 03_http_rpc_websocket/examples/flask_app.py
python 03_http_rpc_websocket/examples/websocket_chat.py
python 03_http_rpc_websocket/examples/grpc_demo.py
python 04_optimization_security/examples/selectors_echo.py
python 04_optimization_security/examples/zero_copy_demo.py
python 04_optimization_security/examples/tls_demo.py
python 05_port_scanner/examples/port_scanner.py
```

## 章节风格说明

- 每章都尽量以“概念 -> 代码 -> 输出 -> 练习题”的顺序展开。
- 示例以本地回环地址和临时端口为主，避免依赖外网。
- 第三方库只出现在需要它们的章节中；如果环境里暂时没有安装，相关脚本会给出提示。
