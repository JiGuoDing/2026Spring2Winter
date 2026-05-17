# 00 入门篇

## 你会学到什么

- Go 网络编程在 OSI 模型和 TCP/IP 分层中的位置。
- `socket`、`net.Dial`、`net.Listen` 这些概念分别解决什么问题。
- 如何用 `net.Dial` 手写一个最小 HTTP 请求。

## 核心概念

- OSI 模型更偏理论分层，常见的网络编程主要落在传输层和应用层。
- TCP/IP 更贴近工程实现，Go 的 `net` 包就是围绕这些协议栈抽象出来的。
- `socket` 是操作系统提供的通信端点，Go 只是把它封装成了更易用的接口。

## 运行示例

```bash
go run ./net/00_intro/examples/net_dial_http
```

## 本章示例

- [examples/net_dial_http/main.go](examples/net_dial_http/main.go)

## 面试回答要点

- `net.Dial` 是“主动发起连接”的入口，适合客户端场景。
- 手写 HTTP 请求有助于理解协议本身，而 `http.Client` 负责把这些细节封装起来。
- `net.Conn` 表示一个已经建立完成的连接，后续读写都围绕它展开。

## 练习题

1. 解释 OSI 七层模型和 TCP/IP 四层模型的差异。
2. `net.Dial` 和 `http.Get` 的区别是什么。
3. 为什么手写 HTTP 请求时需要 `Host` 头。
4. `net.Conn` 和 `net.Listener` 分别代表什么。
5. 你如何判断一个请求是由客户端主动建立还是服务端被动接受。
