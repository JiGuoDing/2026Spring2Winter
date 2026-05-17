"""
functools 与 itertools 模块

两个标准库模块提供了函数式编程的核心工具：

functools - 函数工具：
- lru_cache / cache：自动缓存函数结果（记忆化）
- partial：偏函数，固定部分参数
- reduce：累积计算
- total_ordering：自动生成比较方法
- wraps：保留被装饰函数的元信息

itertools - 迭代器工具：
- chain：连接多个迭代器
- product / combinations / permutations：笛卡尔积、组合、排列
- groupby：分组
- islice / takewhile / dropwhile：切片和条件过滤
- accumulate：累积运算

应用场景：
- 性能优化（缓存、惰性计算）
- 数据处理管道
- 数学和统计计算
"""

import functools
import itertools
import time
from collections import deque
from dataclasses import dataclass
from typing import Iterator


# ==================== functools 演示 ====================

# --- lru_cache 缓存 ---

@functools.lru_cache(maxsize=256)
def fibonacci(n: int) -> int:
    """带缓存的斐波那契计算（自动记忆化，避免重复计算）"""
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


@functools.cache  # Python 3.9+，无限缓存
def expensive_computation(x: int, y: int) -> int:
    """模拟耗时计算"""
    time.sleep(0.01)
    return x ** 2 + y ** 2


# --- partial 偏函数 ---

def power(base: int, exponent: int) -> int:
    return base ** exponent

square = functools.partial(power, exponent=2)   # 固定 exponent=2
cube = functools.partial(power, exponent=3)     # 固定 exponent=3


# --- total_ordering 自动比较 ---

@dataclass(order=True)
class Version:
    """版本号类：@dataclass(order=True) 自动生成所有比较方法"""
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"


# ==================== itertools 演示 ====================

def flatten_nested(nested: list) -> Iterator:
    """使用 chain.from_iterable 展平嵌套列表"""
    return itertools.chain.from_iterable(nested)


def sliding_window(iterable: Iterator, size: int) -> Iterator[tuple]:
    """使用 deque(maxlen) 实现滑动窗口，每步 O(1)"""
    it = iter(iterable)
    window: deque = deque(itertools.islice(it, size), maxlen=size)
    if len(window) == size:
        yield tuple(window)
    for item in it:
        window.append(item)  # maxlen 自动丢弃最左元素
        yield tuple(window)


# ---------- 真实场景示例：数据分析管道 ----------

@dataclass
class SaleRecord:
    product: str
    category: str
    amount: float
    region: str


def generate_reports(records: list[SaleRecord]) -> None:
    """使用 itertools 进行数据分析：分组、聚合、排列组合"""

    # 按类别分组统计
    sorted_records = sorted(records, key=lambda r: r.category)
    print("  按类别分组:")
    for category, group in itertools.groupby(sorted_records, key=lambda r: r.category):
        items = list(group)
        total = sum(r.amount for r in items)
        print(f"    {category}: {len(items)}笔, 合计¥{total:,.2f}")

    # 累积销售额
    print("\n  累积销售额:")
    amounts = [r.amount for r in records]
    for i, cumulative in enumerate(itertools.accumulate(amounts)):
        print(f"    第{i+1}笔后: ¥{cumulative:,.2f}")

    # 区域两两配对（用于联合促销分析）
    regions = sorted(set(r.region for r in records))
    print("\n  区域配对方案:")
    for r1, r2 in itertools.combinations(regions, 2):
        print(f"    {r1} <-> {r2}")


def data_pipeline_demo() -> None:
    """展示 functools 和 itertools 在数据管道中的协作"""
    # 偏函数创建数据过滤器
    is_high_value = functools.partial(
        lambda threshold, r: r.amount >= threshold, 500
    )

    records = [
        SaleRecord("笔记本", "电子产品", 5999.0, "华东"),
        SaleRecord("鼠标", "配件", 129.0, "华北"),
        SaleRecord("显示器", "电子产品", 2499.0, "华东"),
        SaleRecord("键盘", "配件", 399.0, "华南"),
        SaleRecord("耳机", "配件", 799.0, "华北"),
        SaleRecord("平板", "电子产品", 3299.0, "华南"),
    ]

    # 管道：过滤 -> 排序 -> 取前3
    high_value = filter(is_high_value, records)
    sorted_sales = sorted(high_value, key=lambda r: r.amount, reverse=True)
    top3 = itertools.islice(sorted_sales, 3)

    print("  高价值商品 Top 3:")
    for i, record in enumerate(top3, 1):
        print(f"    {i}. {record.product}: ¥{record.amount:,.2f} ({record.region})")

    # 完整报告
    print("\n  === 完整报告 ===")
    generate_reports(records)


if __name__ == "__main__":
    # functools: 缓存
    print("=== lru_cache 缓存 ===")
    start = time.perf_counter()
    result = fibonacci(100)
    elapsed = time.perf_counter() - start
    print(f"  fibonacci(100) = {result}")
    print(f"  耗时: {elapsed:.6f}秒")
    print(f"  缓存信息: {fibonacci.cache_info()}")

    # functools: 偏函数
    print("\n=== partial 偏函数 ===")
    print(f"  square(5) = {square(5)}")
    print(f"  cube(3) = {cube(3)}")

    # functools: total_ordering
    print("\n=== total_ordering 自动比较 ===")
    versions = [Version(2, 1, 0), Version(1, 9, 9), Version(2, 0, 0), Version(2, 1, 1)]
    for v in sorted(versions):
        print(f"  {v}")

    # itertools: 展平嵌套
    print("\n=== chain 展平嵌套列表 ===")
    nested = [[1, 2], [3, 4, 5], [6]]
    print(f"  原始: {nested}")
    print(f"  展平: {list(flatten_nested(nested))}")

    # itertools: 滑动窗口
    print("\n=== 滑动窗口 ===")
    data = [10, 20, 30, 40, 50, 60]
    for window in sliding_window(iter(data), 3):
        print(f"  {window} -> 平均: {sum(window)/len(window):.1f}")

    # 数据分析管道
    print("\n=== 数据分析管道 ===")
    data_pipeline_demo()
