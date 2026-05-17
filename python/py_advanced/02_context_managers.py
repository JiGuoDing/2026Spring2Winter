"""
上下文管理器 (Context Managers)

上下文管理器通过 `with` 语句管理资源的获取和释放，确保资源在使用后被正确清理，
即使发生异常也能执行清理操作，避免资源泄漏。

实现方式：
1. 基于类：实现 __enter__ 和 __exit__ 方法
2. 基于生成器：使用 @contextmanager 装饰器

应用场景：
- 文件/数据库连接管理
- 锁的获取与释放
- 临时修改全局状态（如工作目录、环境变量）
- 计时和性能监控
"""

import os
import time
import sqlite3
import tempfile
from contextlib import contextmanager, suppress
from typing import Generator, Any


class DatabaseConnection:
    """基于类的上下文管理器：管理SQLite数据库连接的生命周期

    自动处理连接的打开、提交/回滚和关闭。
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def __enter__(self) -> sqlite3.Connection:
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式提升并发性能
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.conn:
            if exc_type is None:
                self.conn.commit()   # 无异常时提交
            else:
                self.conn.rollback() # 有异常时回滚
            self.conn.close()
        return False  # 不抑制异常，继续向上传播

# * 函数本身不能直接配 with，但是如果函数返回的是一个上下文管理器，或者被 @contextmanager 包装过，那么就能被 with 使用
@contextmanager
def temp_directory(prefix: str = "tmp_") -> Generator[str, None, None]:
    """基于生成器的上下文管理器：创建临时目录，退出时自动清理

    使用 @contextmanager 装饰器，将生成器函数转化为上下文管理器。
    # * yield 之前的代码相当于 __enter__，yield 之后的代码相当于 __exit__，yield 传出去的值，会绑定到 with 后面的 as 变量上
    """
    tmp_dir = tempfile.mkdtemp(prefix=prefix)
    try:
        yield tmp_dir  # 将临时目录路径提供给 with 块
    finally:
        # 无论是否发生异常，都清理临时目录
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


@contextmanager
def timer_context(label: str = "操作") -> Generator[dict, None, None]:
    """计时上下文管理器：测量代码块执行时间，并通过共享字典返回结果"""
    result: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield result  # 允许 with 块向字典写入数据
    finally:
        result["elapsed"] = time.perf_counter() - start
        result["label"] = label


# ---------- 真实场景示例：数据库初始化与数据操作 ----------

def setup_and_populate_db(db_path: str) -> None:
    """使用上下文管理器安全地初始化数据库并插入测试数据"""
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0
            )
        """)
        # 批量插入商品数据
        products = [
            ("机械键盘", 399.0, 50),
            ("无线鼠标", 129.0, 200),
            ("显示器", 2499.0, 30),
            ("USB集线器", 79.0, 500),
        ]
        cursor.executemany(
            "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
            products
        )


def query_products(db_path: str, min_price: float = 0) -> list[tuple]:
    """查询商品，展示上下文管理器自动处理连接关闭"""
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, price, stock FROM products WHERE price >= ? ORDER BY price",
            (min_price,)
        )
        return cursor.fetchall()


if __name__ == "__main__":
    # 使用临时目录上下文管理器
    with temp_directory(prefix="demo_") as tmp_dir:
        db_path = os.path.join(tmp_dir, "shop.db")
        print(f"数据库路径: {db_path}")

        # 使用数据库上下文管理器
        setup_and_populate_db(db_path)
        products = query_products(db_path, min_price=100)

        print("\n价格 >= 100 的商品：")
        for name, price, stock in products:
            print(f"  {name}: ¥{price:.2f} (库存: {stock})")

    # 使用计时上下文管理器
    with timer_context("数据查询") as t:
        # 此处 tmp_dir 已被清理，模拟一个耗时操作
        time.sleep(0.1)
        t["rows"] = 42  # 向结果字典写入自定义数据

    print(f"\n计时结果: {t['label']} 耗时 {t['elapsed']:.4f}秒，处理 {t['rows']} 行")

    # suppress：优雅地忽略特定异常
    with suppress(FileNotFoundError):
        os.remove("/不存在的文件.txt")  # 不会报错，静默跳过
    print("\nsuppress 演示：FileNotFoundError 已被静默处理")
