"""
元类 (Metaclasses)

元类是"创建类的类"。在Python中，一切皆对象，类本身也是元类的实例。
默认情况下，所有类都是 type 的实例。通过自定义元类，可以拦截类的创建过程，
在类定义时注入属性、方法或执行验证。

核心原理：
- class 语句执行时，Python 调用元类的 __new__ 和 __init__ 来创建类对象
- type(name, bases, dict) 是最基本的元类
- __new__ 在类创建之前执行，可修改类的属性字典
- __init_subclass__ 是更轻量的替代方案（Python 3.6+）

应用场景：
- API框架中的自动注册（如Django Model、SQLAlchemy）
- 接口约束（强制子类实现特定方法）
- 单例模式
- ORM字段映射
"""

from typing import Any
import json


# ---------- 基础元类示例：强制子类实现抽象方法 ----------

class InterfaceMeta(type):
    """接口元类：强制所有子类必须实现指定的方法

    在类创建时检查是否遗漏了必须实现的方法。
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
        # 记录当前类是否定义了 _required_methods（即是否是接口定义）
        is_interface = "_required_methods" in namespace
        own_required = namespace.pop("_required_methods", [])

        # 收集父类的 _required_methods
        required: list[str] = []
        for base in bases:
            if hasattr(base, "_required_methods"):
                required.extend(base._required_methods)

        cls = super().__new__(mcs, name, bases, namespace)

        # 接口类自身不检查，只检查非接口子类
        if not is_interface and required:
            for method_name in required:
                if not callable(getattr(cls, method_name, None)):
                    raise TypeError(
                        f"类 '{name}' 必须实现方法 '{method_name}'"
                    )

        return cls


class Serializer(metaclass=InterfaceMeta):
    """序列化器接口：所有实现类必须提供 serialize 和 deserialize 方法"""
    _required_methods = ["serialize", "deserialize"]


# ---------- 使用 __init_subclass__ 的轻量方案 ----------

class PluginRegistry:
    """插件注册表：使用 __init_subclass__ 自动注册所有子类

    __init_subclass__ 是比元类更简洁的替代方案。
    """
    _plugins: dict[str, type] = {}

    def __init_subclass__(cls, plugin_name: str = "", **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        name = plugin_name or cls.__name__.lower()
        PluginRegistry._plugins[name] = cls

    @classmethod
    def get_plugin(cls, name: str) -> type | None:
        return cls._plugins.get(name)

    @classmethod
    def list_plugins(cls) -> list[str]:
        return list(cls._plugins.keys())


# ---------- 真实场景示例：ORM字段映射 ----------

class Field:
    """ORM字段描述符"""

    def __init__(self, field_type: type, primary_key: bool = False, nullable: bool = True) -> None:
        self.field_type = field_type
        self.primary_key = primary_key
        self.nullable = nullable
        self.name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def validate(self, value: Any) -> bool:
        if value is None:
            return self.nullable
        return isinstance(value, self.field_type)


class ModelMeta(type):
    """ORM模型元类：收集字段定义，生成表结构信息"""

    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
        fields: dict[str, Field] = {}

        # 从父类继承字段
        for base in bases:
            if hasattr(base, "_fields"):
                fields.update(base._fields)

        # 收集当前类定义的字段
        for key, value in namespace.items():
            if isinstance(value, Field):
                fields[key] = value

        cls = super().__new__(mcs, name, bases, namespace)
        cls._fields = fields
        cls._table_name = name.lower() + "s"
        return cls


class Model(metaclass=ModelMeta):
    """ORM模型基类"""

    _fields: dict[str, Field]
    _table_name: str

    def __init__(self, **kwargs: Any) -> None:
        for field_name, field_obj in self._fields.items():
            value = kwargs.get(field_name)
            if not field_obj.validate(value):
                raise ValueError(f"字段 '{field_name}' 验证失败: 值={value}")
            setattr(self, field_name, value)

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self._fields}

    def __repr__(self) -> str:
        fields_str = ", ".join(
            f"{name}={getattr(self, name)!r}" for name in self._fields
        )
        return f"{type(self).__name__}({fields_str})"

    @classmethod
    def create_table_sql(cls) -> str:
        """生成建表SQL"""
        type_map = {str: "TEXT", int: "INTEGER", float: "REAL"}
        columns = []
        for name, field_obj in cls._fields.items():
            col_type = type_map.get(field_obj.field_type, "TEXT")
            pk = " PRIMARY KEY" if field_obj.primary_key else ""
            null = "" if field_obj.nullable else " NOT NULL"
            columns.append(f"    {name} {col_type}{pk}{null}")
        return f"CREATE TABLE {cls._table_name} (\n" + ",\n".join(columns) + "\n);"


# ---------- 具体模型定义 ----------

class User(Model):
    id = Field(int, primary_key=True)
    username = Field(str, nullable=False)
    email = Field(str, nullable=False)
    age = Field(int)


class Article(Model):
    id = Field(int, primary_key=True)
    title = Field(str, nullable=False)
    content = Field(str)
    author_id = Field(int, nullable=False)


# ---------- 插件系统示例 ----------

class JsonPlugin(PluginRegistry, plugin_name="json"):
    """JSON序列化插件"""
    @staticmethod
    def dump(data: dict) -> str:
        return json.dumps(data, ensure_ascii=False)

class CsvPlugin(PluginRegistry, plugin_name="csv"):
    """CSV序列化插件"""
    @staticmethod
    def dump(data: dict) -> str:
        return ",".join(str(v) for v in data.values())


if __name__ == "__main__":
    # 接口元类强制实现
    print("=== 接口元类 ===")
    try:
        class BadSerializer(Serializer):
            pass  # 忘记实现 serialize 和 deserialize
    except TypeError as e:
        print(f"  约束生效: {e}")

    class JsonOkSerializer(Serializer):
        def serialize(self, data): return json.dumps(data)
        def deserialize(self, text): return json.loads(text)

    print(f"  JsonOkSerializer 创建成功")

    # ORM模型
    print("\n=== ORM模型 ===")
    user = User(id=1, username="张三", email="zhangsan@example.com", age=25)
    print(f"  {user}")
    print(f"  字典: {user.to_dict()}")
    print(f"\n  建表SQL:\n{User.create_table_sql()}")

    # 字段验证
    try:
        User(id="not_int", username="test", email="test@example.com")
    except ValueError as e:
        print(f"\n  验证失败: {e}")

    # 插件注册表
    print("\n=== 插件注册表 ===")
    print(f"  已注册插件: {PluginRegistry.list_plugins()}")
    json_plugin = PluginRegistry.get_plugin("json")
    if json_plugin:
        print(f"  JSON插件: {json_plugin.dump({'name': '测试'})}")
