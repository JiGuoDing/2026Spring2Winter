"""
生成器与迭代器 (Generators & Iterators)

迭代器是实现了 __iter__ 和 __next__ 方法的对象，用于逐个访问集合元素。
生成器是创建迭代器的简洁方式，使用 yield 关键字暂停和恢复函数执行。

核心优势：
- 惰性求值：按需生成值，不一次性占用内存
- 适合处理大规模数据流
- 支持无限序列的表示

应用场景：
- 逐行读取大文件
- 数据流管道处理
- 无限序列生成（斐波那契、素数等）
- 自定义可迭代数据结构
"""

import csv
import io
from typing import Iterator, Generator, TypeVar, Generic

T = TypeVar("T")


# ---------- 基础生成器 ----------

def fibonacci(limit: int | None = None) -> Generator[int, None, None]:
    """斐波那契数列生成器

    Args:
        limit: 返回值上限，None 表示无限生成
    """
    a, b = 0, 1
    while limit is None or a <= limit:
        # print(f"生成斐波那契数: {a}")  # 调试输出，展示生成过程
        yield a  # 暂停执行，返回当前值
        a, b = b, a + b


def chunked(iterable: Iterator[T], size: int) -> Generator[list[T], None, None]:
    """将可迭代对象按指定大小分块

    常用于批量处理数据库查询结果或API分页。
    """
    chunk: list[T] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:  # 处理最后不足一块的元素
        yield chunk


# ---------- 生成器管道 ----------

def read_csv_data(csv_text: str) -> Generator[dict[str, str], None, None]:
    """生成器：逐行解析CSV数据为字典"""
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        yield row


def filter_by_field(
    records: Iterator[dict[str, str]],
    field: str,
    min_value: float
) -> Generator[dict[str, str], None, None]:
    """生成器：过滤字段值大于指定阈值的记录"""
    for record in records:
        try:
            if float(record.get(field, "0")) >= min_value:
                yield record
        except ValueError:
            continue


def transform_fields(
    records: Iterator[dict[str, str]],
    field_types: dict[str, type]
) -> Generator[dict[str, object], None, None]:
    """生成器：将指定字段转换为目标类型"""
    for record in records:
        transformed: dict[str, object] = {}
        for key, value in record.items():
            target_type = field_types.get(key, str)
            try:
                transformed[key] = target_type(value)
            except (ValueError, TypeError):
                transformed[key] = value
        yield transformed


# ---------- 自定义迭代器类 ----------

class SlidingWindow(Generic[T]):
    """滑动窗口迭代器

    在序列上生成固定大小的滑动窗口，常用于时间序列分析、移动平均等。
    """

    def __init__(self, data: list[T], window_size: int) -> None:
        if window_size < 1:
            raise ValueError("窗口大小必须 >= 1")
        self.data = data
        self.window_size = window_size
        self._index = 0

    def __iter__(self) -> "SlidingWindow[T]":
        return self

    def __next__(self) -> list[T]:
        if self._index + self.window_size > len(self.data):
            raise StopIteration
        window = self.data[self._index : self._index + self.window_size]
        self._index += 1
        return window


# ---------- 真实场景示例：销售数据流式分析 ----------

SAMPLE_CSV = """\
date,product,quantity,price
2024-01-15,机械键盘,3,399.0
2024-01-15,无线鼠标,10,129.0
2024-01-16,显示器,1,2499.0
2024-01-16,USB集线器,20,79.0
2024-01-17,机械键盘,5,399.0
2024-01-17,无线鼠标,8,129.0
2024-01-18,显示器,3,2499.0
2024-01-18,耳机,15,299.0
"""


def analyze_sales() -> None:
    """使用生成器管道分析销售数据，全程惰性求值，不产生中间列表"""
    # 构建管道：读取 -> 过滤单价 >= 200 -> 类型转换
    records = read_csv_data(SAMPLE_CSV)
    high_value = filter_by_field(records, "price", 200.0)
    typed_records = transform_fields(high_value, {"quantity": int, "price": float})

    # 统计高价值商品的总销售额
    total_revenue: float = 0
    product_count: dict[str, int] = {}

    for record in typed_records:
        product = str(record["product"])
        revenue = int(record["quantity"]) * float(record["price"])  # type: ignore
        total_revenue += revenue
        product_count[product] = product_count.get(product, 0) + int(record["quantity"])  # type: ignore

    print(f"高价值商品(单价>=200)总销售额: ¥{total_revenue:,.2f}")
    print("各商品销量:")
    for product, count in product_count.items():
        print(f"  {product}: {count}件")


if __name__ == "__main__":
    # 斐波那契数列（惰性生成，不存全部到内存）
    print("=== 斐波那契数列(前100个) ===")
    fib = fibonacci()
    first_100 = [next(fib) for _ in range(100)]
    print(first_100)

    # 分块处理
    print("\n=== 分块处理 ===")
    data = list(range(1, 11))
    for i, chunk in enumerate(chunked(iter(data), 3)):
        print(f"  第{i+1}批: {chunk}")

    # 滑动窗口
    print("\n=== 滑动窗口(计算3日移动平均) ===")
    daily_sales = [1200, 1500, 1100, 1800, 2000, 1600, 1900]
    for window in SlidingWindow(daily_sales, 3):
        avg = sum(window) / len(window)
        print(f"  窗口 {window} -> 平均: ¥{avg:,.2f}")

    # 生成器管道分析
    print("\n=== 销售数据流式分析 ===")
    analyze_sales()
