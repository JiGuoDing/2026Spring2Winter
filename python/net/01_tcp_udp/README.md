# 01 基础核心

## 你会学到什么

- 如何用 `socket.socket`、`bind`、`listen` 和 `accept` 写出一个 TCP 服务端。
- 如何用 `connect` 构建 TCP 客户端，并处理粘包与拆包。
- 如何使用 UDP 的 `sendto` 和 `recvfrom` 完成一次完整收发。

## 核心要点

- TCP 是面向连接的字节流协议，不保留消息边界。
- UDP 是无连接的数据报协议，一次读写通常对应一条消息。
- 粘包和拆包不是 Python 独有问题，而是 TCP 流式语义带来的结果。
- 关闭连接时应尽量做到超时可控、资源可释放、错误可观察。

## 运行示例

```bash
python 01_tcp_udp/examples/tcp_length_prefix.py
python 01_tcp_udp/examples/udp_echo.py
```

## 本章示例

- [examples/tcp_length_prefix.py](examples/tcp_length_prefix.py)
- [examples/udp_echo.py](examples/udp_echo.py)

## 面试回答要点

- 长度前缀和自定义分隔符是最常见的消息边界方案。
- `settimeout` 可以为读写提供兜底超时，避免连接长期卡死。
- TCP 更适合需要可靠传输的场景，UDP 更适合低延迟、可容忍丢包的场景。

## 练习题

1. 为什么 TCP 会出现粘包和拆包。
2. 长度前缀协议和分隔符协议各有什么优缺点。
3. UDP 和 TCP 在应用场景上如何取舍。
4. 为什么 `socket` 的同一方向并发写入需要谨慎。
5. 解释 `settimeout`、`setblocking`、`shutdown` 的区别。
