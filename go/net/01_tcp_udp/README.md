# 01 基础核心

## 你会学到什么

- 如何用 `net.Listen` 和 `net.Accept` 写出一个 TCP 服务端。
- 如何用 `net.DialTCP` 写出一个 TCP 客户端。
- 如何处理粘包与拆包、优雅关闭连接，以及 UDP 的基本收发。
- 为什么高并发网络程序常用“每连接一个 goroutine + worker pool”的组合。

## 核心要点

- TCP 是面向连接的字节流协议，不保留消息边界。
- UDP 是无连接的数据报协议，一次读写通常对应一条消息。
- `net.Conn` 的读写边界和并发安全性需要分清楚：通常允许一读一写并发，但同一方向的并发写要谨慎。

## 运行示例

```bash
go run ./net/01_tcp_udp/examples/tcp_length_prefix
go run ./net/01_tcp_udp/examples/udp_echo
```

## 本章示例

- [examples/tcp_length_prefix/main.go](examples/tcp_length_prefix/main.go)
- [examples/udp_echo/main.go](examples/udp_echo/main.go)

## 面试回答要点

- 粘包与拆包不是 Go 独有问题，而是 TCP 流式语义带来的结果。
- 长度前缀和自定义分隔符是最常见的消息边界方案。
- `SetDeadline` 可以为读写提供兜底超时，避免连接长期卡死。
- `CloseWrite` / `CloseRead` 适合在 TCP 半关闭场景里表达“我这边写完了”或“我这边不再读了”。

## 练习题

1. 为什么 TCP 会出现粘包和拆包。
2. 长度前缀协议和分隔符协议各有什么优缺点。
3. UDP 和 TCP 在应用场景上如何取舍。
4. 为什么 `net.Conn` 的同一方向并发写入需要谨慎。
5. 解释 `SetDeadline`、`SetReadDeadline`、`SetWriteDeadline` 的区别。
