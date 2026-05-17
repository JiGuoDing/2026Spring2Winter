# 04 高级与优化

## 你会学到什么

- 如何用 `selectors` 对比阻塞 socket 和事件循环式的 IO 处理。
- 如何理解 `memoryview` 的零拷贝数据共享，以及 `os.sendfile` 的适用场景。
- 如何用 `ssl.SSLContext` 包装 socket，构建一个最小 TLS 连接。
- 如何通过超时、并发限制和资源回收做基础安全防护。

## 核心要点

- 事件驱动框架适合连接数极多、IO 密集的场景。
- `memoryview` 适合在不额外复制数据的情况下切片和共享缓冲区。
- `sendfile` 适合文件到 socket 的零拷贝传输，但不是所有平台都支持。
- `ssl.SSLContext` 应该作为配置中心，而不是到处散落的临时包装。

## 运行示例

```bash
python 04_optimization_security/examples/selectors_echo.py
python 04_optimization_security/examples/zero_copy_demo.py
python 04_optimization_security/examples/tls_demo.py
```

`tls_demo.py` 会尝试调用系统里的 `openssl` 命令生成临时证书；如果本机没有安装 OpenSSL，它会打印提示并退出。

## 本章示例

- [examples/selectors_echo.py](examples/selectors_echo.py)
- [examples/zero_copy_demo.py](examples/zero_copy_demo.py)
- [examples/tls_demo.py](examples/tls_demo.py)

## 面试回答要点

- 你不需要背诵 epoll / kqueue 的细节实现，但要知道它们解决的是“少量线程处理大量连接”的问题。
- `io` 和 `selectors` 都是围绕文件描述符和事件通知做抽象。
- `sendfile` 适合文件到 socket 的零拷贝传输，`memoryview` 适合缓冲区共享。
- 基础安全手段包括超时、并发上限、合理 backlog、输入校验和 TLS。

## 练习题

1. 为什么事件驱动模型在高连接数场景中更有优势。
2. `memoryview` 为什么可以减少数据复制。
3. `sendfile` 和普通 `read` / `write` 的区别是什么。
4. 为什么 Windows 上的 `sendfile` 示例需要做 fallback。
5. 你会如何为一个 TCP 服务增加基础防护措施。
