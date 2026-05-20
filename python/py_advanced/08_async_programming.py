"""
异步编程 (Async Programming)

Python 3.5+ 引入的 asyncio 模块提供了基于协程的异步编程模型。
协程是一种可以暂停和恢复的函数，通过 await 关键字让出控制权，实现单线程并发。

核心概念：
- async def：定义协程函数
- await：暂停协程执行，等待异步操作完成
- asyncio.gather()：并发运行多个协程
- asyncio.create_task()：创建任务
- async with / async for：异步上下文管理器和异步迭代器

应用场景：
- 高并发网络请求（爬虫、API调用）
- 数据库异步操作
- WebSocket服务
- IO密集型任务的性能优化
"""

import asyncio
import time
from dataclasses import dataclass
from typing import AsyncIterator


# ---------- 基础协程 ----------

async def fetch_data(url: str, delay: float) -> dict:
    """模拟异步HTTP请求（用 sleep 模拟网络延迟）"""
    print(f"  开始请求: {url}")
    await asyncio.sleep(delay)  # 模拟IO等待，让出控制权
    return {"url": url, "status": 200, "data": f"{url}的响应数据"}


async def process_response(response: dict) -> str:
    """模拟异步处理响应数据"""
    await asyncio.sleep(0.1)  # 模拟处理耗时
    return f"[{response['status']}] {response['url']}: {response['data']}"


# ---------- 异步上下文管理器 ----------

class AsyncDatabasePool:
    """模拟异步数据库连接池"""

    def __init__(self, pool_size: int = 5) -> None:
        self.pool_size = pool_size
        self._available = pool_size
        self._name = "DBPool"

    # * "AsyncDatabasePool" 是类型注解，表示 __aenter__ 方法返回的是 AsyncDatabasePool 类型的实例
    # * "" 语法是前向引用，用于在类定义时引用类本身，Python 会将其当作 字符串 延迟解析，等到类定义完成后才去查找这个类型
    # * 该方法配合 async with 语句使用，用于在异步上下文管理器中初始化资源并返回资源实例
    async def __aenter__(self) -> "AsyncDatabasePool":
        print(f"  [{self._name}] 初始化连接池({self.pool_size}个连接)")
        await asyncio.sleep(0.2)  # 模拟连接建立
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        print(f"  [{self._name}] 关闭连接池")
        await asyncio.sleep(0.1)

    async def execute(self, query: str) -> list[dict]:
        if self._available <= 0:
            raise RuntimeError("连接池已满")
        self._available -= 1
        try:
            await asyncio.sleep(0.05)  # 模拟查询耗时
            return [{"query": query, "rows": 42}]
        finally:
            self._available += 1


# ---------- 异步迭代器 ----------

class AsyncRange:
    """异步迭代器：模拟逐批获取数据"""

    def __init__(self, start: int, stop: int, batch_size: int = 3) -> None:
        self.start = start
        self.stop = stop
        self.batch_size = batch_size
        self._current = start

    def __aiter__(self) -> "AsyncRange":
        return self

    async def __anext__(self) -> list[int]:
        if self._current >= self.stop:
            raise StopAsyncIteration
        await asyncio.sleep(0.05)  # 模拟网络延迟
        batch = list(range(self._current, min(self._current + self.batch_size, self.stop)))
        self._current += self.batch_size
        return batch


# ---------- 真实场景示例：并发数据采集 ----------

@dataclass
class FetchResult:
    url: str
    data: str
    elapsed: float

async def fetch_with_timing(url: str, delay: float) -> FetchResult:
    """带计时的数据获取"""
    start = time.monotonic()
    result = await fetch_data(url, delay)
    elapsed = time.monotonic() - start
    return FetchResult(url=url, data=result["data"], elapsed=elapsed)


async def sequential_fetch(urls: list[str]) -> list[FetchResult]:
    """串行获取：一个接一个"""
    results = []
    # * 以下为异步串行获取，效果与同步串行获取相同
    # for url in urls:
    #     result = await fetch_with_timing(url, 0.3)
    #     results.append(result)
    # return results
    
    # * 以下为并行获取，效果与下面的 concurrent_fetch 相同
    for url in urls:
        # ! 直接调用 fetch_with_timing 并不会执行函数体，而是返回一个协程对象，需要使用 await 关键字等待其完成
        # * 循环只是把协程对象收集到列表中，最后用 gather 同时执行
        result = fetch_with_timing(url, 0.3)
        results.append(result)
    return await asyncio.gather(*results)

async def concurrent_fetch(urls: list[str]) -> list[FetchResult]:
    """并发获取：同时发起所有请求"""
    tasks = [fetch_with_timing(url, 0.3) for url in urls]
    # * *tasks 表示将 tasks 列表展开，作为参数传递，等价于 asyncio.gather(task1, task2, task3)
    return await asyncio.gather(*tasks)


async def limited_concurrent_fetch(
    urls: list[str], max_concurrent: int = 3
) -> list[FetchResult]:
    """限流并发：使用信号量控制并发数"""
    semaphore = asyncio.Semaphore(value=max_concurrent)

    async def limited_fetch(url: str) -> FetchResult:
        async with semaphore:
            return await fetch_with_timing(url, 0.3)

    tasks = [limited_fetch(url) for url in urls]
    return await asyncio.gather(*tasks)


async def async_pipeline_demo() -> None:
    """异步数据管道：展示异步迭代器和上下文管理器的组合使用"""
    print("=== 异步数据管道 ===")

    async with AsyncDatabasePool(pool_size=3) as pool:
        # 异步迭代器逐批获取数据
        async for batch in AsyncRange(0, 10, batch_size=3):
            # 并发处理每批数据
            tasks = [pool.execute(f"SELECT * FROM users WHERE id = {i}") for i in batch]
            results = await asyncio.gather(*tasks)
            ids = ", ".join(str(i) for i in batch)
            print(f"  批次 [{ids}]: 处理完成，共 {len(results)} 条查询")


async def main() -> None:
    urls = [f"https://api.example.com/users/{i}" for i in range(1, 7)]

    # 串行 vs 并发对比
    print("=== 串行获取 ===")
    start = time.monotonic()
    seq_results = await sequential_fetch(urls)
    seq_time = time.monotonic() - start
    print(f"  耗时: {seq_time:.2f}秒")

    print("\n=== 并发获取 ===")
    start = time.monotonic()
    con_results = await concurrent_fetch(urls)
    con_time = time.monotonic() - start
    print(f"  耗时: {con_time:.2f}秒")
    print(f"  加速比: {seq_time / con_time:.1f}x")

    print("\n=== 限流并发(最多2个) ===")
    start = time.monotonic()
    lim_results = await limited_concurrent_fetch(urls, max_concurrent=2)
    lim_time = time.monotonic() - start
    print(f"  耗时: {lim_time:.2f}秒")

    # 异步管道
    print()
    await async_pipeline_demo()


if __name__ == "__main__":
    asyncio.run(main())
