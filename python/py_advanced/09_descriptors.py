"""
描述符 (Descriptors)

描述符是实现了特定协议（__get__、__set__、__delete__）的对象，
可以自定义属性的访问行为。描述符是 property、classmethod、staticmethod 等内置功能的底层机制。

描述符协议：
- __get__(self, obj, objtype=None)：访问属性时调用
- __set__(self, obj, value)：设置属性时调用
- __delete__(self, obj)：删除属性时调用

分类：
- 数据描述符：同时实现 __get__ 和 __set__（优先级高于实例字典）
- 非数据描述符：只实现 __get__（优先级低于实例字典）

应用场景：
- 属性验证和类型检查
- 延迟计算（缓存属性）
- ORM字段映射
- 方法绑定（Python内部机制）
"""

from typing import Any, Callable, TypeVar

T = TypeVar("T")


class BaseDescriptor:
    """描述符基类：抽取公共的 __set_name__ 和 __get__ 逻辑"""

    def __init__(self) -> None:
        self.name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        return obj.__dict__.get(self.name)


class Validated(BaseDescriptor):
    """验证描述符：在设置属性值时执行类型检查和自定义验证函数"""

    def __init__(self, field_type: type, validator: Callable[[Any], bool] | None = None,
                 error_msg: str = "") -> None:
        super().__init__()
        self.field_type = field_type
        self.validator = validator
        self.error_msg = error_msg

    def __set__(self, obj: Any, value: Any) -> None:
        if not isinstance(value, self.field_type):
            raise TypeError(f"'{self.name}' 必须是 {self.field_type.__name__}，收到 {type(value).__name__}")
        if self.validator and not self.validator(value):
            raise ValueError(f"'{self.name}' 验证失败: {self.error_msg}")
        obj.__dict__[self.name] = value


class CachedProperty:
    """缓存属性描述符：首次访问时计算，之后直接返回缓存值

    非数据描述符（只实现 __get__），实例可以覆盖它。
    """

    def __init__(self, func: Callable[[Any], T]) -> None:
        self.func = func
        self.attr_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = f"_cached_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> T:
        if obj is None:
            return self  # type: ignore
        if self.attr_name not in obj.__dict__:
            obj.__dict__[self.attr_name] = self.func(obj)
        return obj.__dict__[self.attr_name]


class RangeChecked(BaseDescriptor):
    """范围检查描述符：限制数值在指定范围内"""

    def __init__(self, min_val: float, max_val: float) -> None:
        super().__init__()
        self.min_val = min_val
        self.max_val = max_val

    def __set__(self, obj: Any, value: Any) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(f"'{self.name}' 必须是数值类型")
        if not (self.min_val <= value <= self.max_val):
            raise ValueError(f"'{self.name}' 必须在 [{self.min_val}, {self.max_val}] 范围内")
        obj.__dict__[self.name] = value


# ---------- 真实场景示例：产品管理系统 ----------

class Product:
    """产品类：展示多种描述符的组合使用"""

    # 使用验证描述符
    name = Validated(str, validator=lambda v: len(v) > 0, error_msg="名称不能为空")
    price = RangeChecked(0.01, 999999.99)
    stock = RangeChecked(0, 100000)

    def __init__(self, name: str, price: float, stock: int, cost: float) -> None:
        self.name = name
        self.price = price
        self.stock = stock
        self._cost = cost  # 私有属性

    @CachedProperty
    def profit_margin(self) -> float:
        """利润率（缓存属性：首次访问时计算）"""
        # 模拟复杂计算
        return (self.price - self._cost) / self.price

    @CachedProperty
    def inventory_value(self) -> float:
        """库存总价值（缓存属性）"""
        return self.price * self.stock

    def restock(self, quantity: int) -> None:
        self.stock = self.stock + quantity  # 触发 RangeChecked 验证

    def apply_discount(self, rate: float) -> None:
        """打折（会触发价格范围检查）"""
        self.price = round(self.price * (1 - rate), 2)

    def __repr__(self) -> str:
        return f"Product({self.name!r}, ¥{self.price:.2f}, 库存={self.stock})"


class ColorDescriptor(BaseDescriptor):
    """颜色描述符：自动将字符串转换为RGB元组"""

    def __set__(self, obj: Any, value: str | tuple[int, int, int]) -> None:
        rgb: tuple[int, int, int]
        if isinstance(value, str):
            hex_str = value.lstrip("#")
            if len(hex_str) != 6:
                raise ValueError(f"无效的颜色值: #{hex_str}")
            rgb = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))  # type: ignore
        elif isinstance(value, tuple) and len(value) == 3:
            rgb = value  # type: ignore
        else:
            raise TypeError("颜色必须是 '#RRGGBB' 字符串或 (r, g, b) 元组")
        if not all(0 <= v <= 255 for v in rgb):
            raise ValueError("RGB值必须在 0-255 范围内")
        obj.__dict__[self.name] = rgb


class Theme:
    """主题配置：展示自定义描述符类型转换"""
    primary = ColorDescriptor()
    secondary = ColorDescriptor()

    def __init__(self, primary: str | tuple, secondary: str | tuple) -> None:
        self.primary = primary
        self.secondary = secondary


if __name__ == "__main__":
    # 验证描述符
    print("=== 验证描述符 ===")
    laptop = Product("笔记本电脑", 5999.0, 50, 3500.0)
    print(f"  {laptop}")

    try:
        laptop.name = ""  # 空名称验证
    except ValueError as e:
        print(f"  验证失败: {e}")

    try:
        laptop.price = -100  # 范围检查
    except ValueError as e:
        print(f"  范围检查: {e}")

    # 缓存属性
    print("\n=== 缓存属性 ===")
    print(f"  利润率: {laptop.profit_margin:.1%}")  # 首次计算
    print(f"  利润率: {laptop.profit_margin:.1%}")  # 使用缓存
    print(f"  库存价值: ¥{laptop.inventory_value:,.2f}")

    # 价格操作触发验证
    print("\n=== 价格操作 ===")
    laptop.apply_discount(0.1)
    print(f"  打9折后: ¥{laptop.price:.2f}")

    laptop.restock(100)
    print(f"  补货后库存: {laptop.stock}")

    # 颜色描述符
    print("\n=== 颜色描述符（类型转换） ===")
    theme = Theme("#FF5733", (100, 200, 50))
    print(f"  主色: {theme.primary}")
    print(f"  副色: {theme.secondary}")

    theme.primary = "#00FF00"
    print(f"  修改后主色: {theme.primary}")
