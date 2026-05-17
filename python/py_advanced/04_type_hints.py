"""
类型提示 (Type Hints)

Python 3.5+ 引入的类型提示系统，通过注解为变量、函数参数和返回值标注类型。
类型提示不影响运行时行为，但能显著提升代码可读性、IDE支持和静态检查能力。

核心特性：
- 基础类型标注（int, str, float, bool）
- 容器类型（list, dict, tuple, set）
- Union / Optional 联合类型
- TypeVar 泛型
- Protocol 结构化子类型（鸭子类型的类型安全版）
- TypeAlias 类型别名
- Literal 字面量类型

应用场景：
- 大型项目的接口契约定义
- API参数和返回值的文档化
- 静态类型检查（mypy, pyright）
"""

from typing import (
    Any, TypeVar, Generic, Protocol, TypeAlias, Literal,
    runtime_checkable, overload
)
from dataclasses import dataclass

# ---------- 类型别名 ----------

Vector: TypeAlias = list[float]
Matrix: TypeAlias = list[Vector]
UserId: TypeAlias = int


# ---------- Protocol（结构化子类型） ----------

@runtime_checkable  # 允许在运行时用 isinstance 检查
class Renderable(Protocol):
    """可渲染对象的协议：任何实现了 render() 方法的对象都满足此协议"""
    def render(self) -> str: ...


@runtime_checkable
class Serializable(Protocol):
    """可序列化对象的协议"""
    def to_dict(self) -> dict[str, Any]: ...


# ---------- 泛型类 ----------

T = TypeVar("T")

@dataclass
class Page(Generic[T]):
    """泛型分页容器：用于API分页响应"""
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


# ---------- 具体数据类型 ----------

@dataclass
class UserProfile:
    """用户资料"""
    user_id: UserId
    name: str
    email: str
    tags: list[str]

    def render(self) -> str:
        return f"[{self.user_id}] {self.name} <{self.email}>"

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "tags": self.tags,
        }


@dataclass
class Product:
    """商品信息"""
    product_id: int
    name: str
    price: float

    def render(self) -> str:
        return f"{self.name} (¥{self.price:.2f})"

    def to_dict(self) -> dict[str, Any]:
        return {"product_id": self.product_id, "name": self.name, "price": self.price}


# ---------- 类型安全的函数 ----------

def dot_product(a: Vector, b: Vector) -> float:
    """计算两个向量的点积"""
    if len(a) != len(b):
        raise ValueError("向量维度不一致")
    return sum(x * y for x, y in zip(a, b))


def paginate(items: list[T], page: int, page_size: int) -> Page[T]:
    """泛型分页函数：对任意类型的列表进行分页"""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return Page(
        items=items[start:end],
        total=total,
        page=page,
        page_size=page_size,
    )


def render_all(items: list[Renderable]) -> str:
    """接受任何满足 Renderable 协议的对象列表"""
    return "\n".join(item.render() for item in items)


# ---------- Literal 类型与重载 ----------

@overload
def format_value(value: int, fmt: Literal["hex"]) -> str: ...
@overload
def format_value(value: float, fmt: Literal["percent"]) -> str: ...
@overload
def format_value(value: str, fmt: Literal["upper"]) -> str: ...

def format_value(value, fmt):
    """根据格式字面量类型执行不同的格式化"""
    if fmt == "hex":
        return hex(int(value))
    elif fmt == "percent":
        return f"{float(value) * 100:.1f}%"
    elif fmt == "upper":
        return str(value).upper()
    raise ValueError(f"不支持的格式: {fmt}")


# ---------- 真实场景示例：用户管理API ----------

class UserService:
    """用户管理服务：展示类型提示在实际业务中的应用"""

    def __init__(self) -> None:
        self._users: dict[UserId, UserProfile] = {}

    def add_user(self, user: UserProfile) -> None:
        self._users[user.user_id] = user

    def get_user(self, user_id: UserId) -> UserProfile | None:
        return self._users.get(user_id)

    def search_by_tag(self, tag: str) -> list[UserProfile]:
        return [u for u in self._users.values() if tag in u.tags]

    def list_users(self, page: int = 1, page_size: int = 10) -> Page[UserProfile]:
        all_users = list(self._users.values())
        return paginate(all_users, page, page_size)


if __name__ == "__main__":
    # 类型安全的向量运算
    print("=== 向量运算 ===")
    v1: Vector = [1.0, 2.0, 3.0]
    v2: Vector = [4.0, 5.0, 6.0]
    print(f"点积: {dot_product(v1, v2)}")  # 32.0

    # Protocol 检查
    print("\n=== Protocol 结构化子类型 ===")
    user = UserProfile(1, "张三", "zhangsan@example.com", ["admin", "dev"])
    product = Product(101, "机械键盘", 399.0)

    for item in [user, product]:
        # 两个类都没有继承 Renderable，但都满足协议
        print(f"  {type(item).__name__} 是 Renderable? {isinstance(item, Renderable)}")
        print(f"  {type(item).__name__} 是 Serializable? {isinstance(item, Serializable)}")

    # 泛型分页
    print("\n=== 泛型分页 ===")
    service = UserService()
    for i in range(1, 26):
        service.add_user(UserProfile(i, f"用户{i}", f"user{i}@example.com", ["dev"]))

    page1 = service.list_users(page=1, page_size=5)
    print(f"第1页: 共{page1.total}人，当前{len(page1.items)}人，总{page1.total_pages}页")
    print(render_all(page1.items))

    # Literal 重载
    print("\n=== Literal 类型格式化 ===")
    print(f"  十六进制: {format_value(255, 'hex')}")
    print(f"  百分比:   {format_value(0.856, 'percent')}")
    print(f"  大写:     {format_value('hello', 'upper')}")
