"""
数据类 (Dataclasses)

Python 3.7+ 引入的 @dataclass 装饰器，自动生成 __init__、__repr__、__eq__ 等方法，
大幅减少样板代码。相比普通类和 namedtuple，提供更灵活的数据容器。

核心特性：
- 自动生成 __init__、__repr__、__eq__、__hash__
- 支持默认值和默认工厂
- field() 精细控制字段行为（比较、序列化、repr）
- 继承与组合
- frozen=True 创建不可变对象
- slots=True 自动生成 __slots__ 优化内存

应用场景：
- 配置对象、DTO（数据传输对象）
- API请求/响应模型
- 领域模型的值对象
"""

from dataclasses import dataclass, field, asdict, astuple, replace
from datetime import datetime
from typing import ClassVar
import json


@dataclass(frozen=True, slots=True)
class Coordinate:
    """不可变坐标点（frozen=True 确保创建后不能修改）

    slots=True 自动生成 __slots__，减少内存占用。
    """
    latitude: float
    longitude: float

    def distance_to(self, other: "Coordinate") -> float:
        """计算与另一个坐标点的近似距离（单位：公里）"""
        import math
        R = 6371  # 地球半径（公里）
        lat1, lat2 = math.radians(self.latitude), math.radians(other.latitude)
        dlat = lat2 - lat1
        dlon = math.radians(other.longitude - self.longitude)
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@dataclass
class Address:
    """地址信息"""
    street: str
    city: str
    province: str
    postal_code: str


@dataclass(order=True)
class Task:
    """任务对象（order=True 自动生成比较方法，支持排序）

    priority 是唯一参与比较的字段（其余字段 compare=False），自动成为排序键。
    """
    task_id: int = field(compare=False)
    title: str = field(compare=False)
    priority: int = 1  # 优先级：1=低, 2=中, 3=高（排序键）
    created_at: datetime = field(default_factory=datetime.now, compare=False)
    tags: list[str] = field(default_factory=list, compare=False)

    def to_json(self) -> str:
        """序列化为JSON字符串"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return json.dumps(data, ensure_ascii=False, indent=2)


@dataclass
class OrderItem:
    """订单项"""
    product_name: str
    unit_price: float
    quantity: int

    @property
    def subtotal(self) -> float:
        return self.unit_price * self.quantity


@dataclass
class Order:
    """订单对象：展示数据类的组合使用"""
    order_id: str
    customer_name: str
    items: list[OrderItem] = field(default_factory=list)
    discount: float = 0.0
    _total_cache: float | None = field(default=None, init=False, repr=False)

    # ClassVar 标注的字段不会被 @dataclass 处理
    TAX_RATE: ClassVar[float] = 0.13

    @property
    def subtotal(self) -> float:
        return sum(item.subtotal for item in self.items)

    @property
    def tax(self) -> float:
        return self.subtotal * self.TAX_RATE

    @property
    def total(self) -> float:
        if self._total_cache is None:
            self._total_cache = self.subtotal - self.discount + self.tax
        return self._total_cache

    def add_item(self, product_name: str, unit_price: float, quantity: int) -> None:
        self.items.append(OrderItem(product_name, unit_price, quantity))
        self._total_cache = None  # 清除缓存

    def summary(self) -> str:
        lines = [f"订单 {self.order_id} - {self.customer_name}"]
        for item in self.items:
            lines.append(f"  {item.product_name} x{item.quantity} @ ¥{item.unit_price:.2f} = ¥{item.subtotal:.2f}")
        lines.append(f"  小计: ¥{self.subtotal:.2f} | 折扣: -¥{self.discount:.2f} | 税: ¥{self.tax:.2f}")
        lines.append(f"  合计: ¥{self.total:.2f}")
        return "\n".join(lines)


if __name__ == "__main__":
    # 不可变坐标
    print("=== 不可变坐标（frozen + slots） ===")
    beijing = Coordinate(39.9042, 116.4074)
    shanghai = Coordinate(31.2304, 121.4737)
    print(f"北京: {beijing}")
    print(f"上海: {shanghai}")
    print(f"距离: {beijing.distance_to(shanghai):.0f} 公里")

    # 尝试修改 frozen 对象
    try:
        beijing.latitude = 40.0
    except AttributeError as e:
        print(f"frozen 保护: {e}")

    # 任务排序
    print("\n=== 任务排序（order=True） ===")
    tasks = [
        Task(1, "写文档", priority=1),
        Task(2, "修复Bug", priority=3),
        Task(3, "代码审查", priority=2),
        Task(4, "部署上线", priority=3),
    ]
    for task in sorted(tasks, reverse=True):  # 按优先级降序
        print(f"  [{task.priority}] {task.title}")

    # replace 创建修改副本（frozen对象的修改方式）
    print("\n=== replace 修改副本 ===")
    updated_task = replace(tasks[0], priority=2, title="写技术文档")
    print(f"  原始: {tasks[0]}")
    print(f"  副本: {updated_task}")

    # 订单系统
    print("\n=== 订单系统 ===")
    order = Order("ORD-2024-001", "张三", discount=50.0)
    order.add_item("机械键盘", 399.0, 2)
    order.add_item("无线鼠标", 129.0, 1)
    order.add_item("显示器", 2499.0, 1)
    print(order.summary())

    # 序列化
    print("\n=== JSON序列化 ===")
    task_json = tasks[1].to_json()
    print(task_json)
