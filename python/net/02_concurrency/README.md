# 02 并发模型

## 你会学到什么

- 为什么网络程序里常见“每连接一个线程”的模型。
- 如何用 `ThreadPoolExecutor` 限制并发数，避免线程数量失控。
- 如何用 `asyncio` 写出一个异步 IO 版本的回显服务。
- `socket` 在并发读写上的边界应该怎么理解。

## 核心要点

- 线程很轻量，但不是免费资源，连接数很大时仍然需要控制。
- 线程池本质上是“固定数量的执行单元 + 任务队列”。
- 常见实践是“一条连接一个读循环 + 一条写循环”，而不是多个线程同时乱写同一个连接。

## 运行示例

```bash
python 02_concurrency/examples/threaded_echo.py
python 02_concurrency/examples/thread_pool_echo.py
python 02_concurrency/examples/asyncio_echo.py
```

## 本章示例

- [examples/threaded_echo.py](examples/threaded_echo.py)
- [examples/thread_pool_echo.py](examples/thread_pool_echo.py)
- [examples/asyncio_echo.py](examples/asyncio_echo.py)

## 面试回答要点

- 连接很多时，直接无限制启动线程可能会压垮内存和调度器。
- 线程池的关键不是“更快”，而是“更可控”。
- `asyncio` 的优势在于用单线程事件循环处理大量 IO 等待。

## 练习题

1. 为什么网络程序里常说“每连接一个线程”。
2. `ThreadPoolExecutor` 的典型使用场景是什么。
3. 线程池和无限制启动线程的差异是什么。
4. 为什么同一个 `socket` 上的并发写要小心。
5. 你会如何设计一个可取消的网络任务池。
