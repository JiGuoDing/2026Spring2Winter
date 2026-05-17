# 04 高级与优化

## 你会学到什么

- 如何对比 goroutine-per-conn 和事件驱动模型。
- `io.Copy` 为什么经常比手写循环更快，以及它的快路径是什么。
- Linux 上 `sendfile` / `splice` 这类零拷贝思路的基本用法。
- 如何用 `crypto/tls` 和超时、限流等手段提升网络程序的安全性。

## 核心要点

- 事件驱动框架适合连接数极多、IO 密集的场景。
- `io.Copy` 会优先使用 `WriterTo` 或 `ReadFrom` 快路径。
- Linux-only API 需要明确 build tag，不能假设所有平台都一样。

## 运行示例

```bash
go run ./net/04_optimization_security/examples/io_copy
go run ./net/04_optimization_security/examples/gnet_echo
```

Linux 上再运行：

```bash
go run ./net/04_optimization_security/examples/sendfile_linux.go
```

## 本章示例

- [examples/io_copy/main.go](examples/io_copy/main.go)
- [examples/gnet_echo/main.go](examples/gnet_echo/main.go)
- [examples/sendfile_linux.go](examples/sendfile_linux.go)
- [examples/sendfile_stub.go](examples/sendfile_stub.go)

`gnet_echo` 现在是一个纯标准库的 reactor 风格 fallback，用来演示事件驱动思路；如果后续能拉到外部模块，再替换成真正的 gnet 示例即可。

## 面试回答要点

- 你不需要背诵 epoll / kqueue 的细节实现，但要知道它们解决的是“少量线程处理大量连接”的问题。
- `io.Copy` 的优势来自接口快路径、缓冲复用和标准库优化。
- `sendfile` 适合文件到 socket 的零拷贝传输，`splice` 更偏 Linux 管道与 socket 之间的数据转移。

## 练习题

1. 为什么事件驱动模型在高连接数场景中更有优势。
2. `io.Copy` 为什么通常比手写 `Read` / `Write` 循环更推荐。
3. `sendfile` 和 `splice` 的适用场景有什么差异。
4. 为什么 Linux-only 代码需要用 build tag 区分。
5. 你会如何为一个 TCP 服务增加基础防护措施。
