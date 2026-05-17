# 00 入门篇

## 你会学到什么

- Python 网络编程在 OSI 模型和 TCP/IP 分层中的位置。
- `socket`、`http.client`、`socket.create_connection` 这些概念分别解决什么问题。
- 如何用标准库写出第一个最小 HTTP 请求。

## 核心概念

- OSI 模型更偏理论分层，常见的网络编程主要落在传输层和应用层。
- TCP/IP 更贴近工程实现，Python 的 `socket` 模块就是围绕这些协议栈抽象出来的。
- `socket` 是操作系统提供的通信端点，Python 只是把它封装成了更易用的接口。

## 运行示例

```bash
python 00_intro/examples/http_request.py
```

## 本章示例

- [examples/http_request.py](examples/http_request.py)

## 面试回答要点

- `socket` 是“通信端点”，`socket.socket()` 只是对系统调用的封装。
- `http.client` 适合帮助你理解请求行、请求头和响应体这些协议细节。
- `socket.create_connection` 会把地址解析、超时和连接建立这些细节封装起来。

## 练习题

1. 解释 OSI 七层模型和 TCP/IP 四层模型的差异。
2. `socket.socket` 和 `http.client.HTTPConnection` 的区别是什么。
3. 为什么手写 HTTP 请求时需要 `Host` 头。
4. `socket`、`conn` 和 `listener` 在概念上分别代表什么。
5. 你如何判断一个请求是由客户端主动建立还是服务端被动接受。
