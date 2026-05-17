# Python 进阶用法学习项目

本项目涵盖 Python 核心进阶语法，每个主题一个独立文件，包含真实开发场景示例。

## 项目结构

```
py_advanced/
├── README.md                    # 本文件
├── 01_decorators.py             # 装饰器
├── 02_context_managers.py       # 上下文管理器
├── 03_generators.py             # 生成器与迭代器
├── 04_type_hints.py             # 类型提示
├── 05_dataclasses.py            # 数据类
├── 06_closures.py               # 闭包
├── 07_metaclasses.py            # 元类
├── 08_async_programming.py      # 异步编程
├── 09_descriptors.py            # 描述符
└── 10_functools_itertools.py    # functools 与 itertools
```

## 各文件说明

| 文件 | 主题 | 核心知识点 |
|------|------|-----------|
| `01_decorators.py` | 装饰器 | 函数装饰器、带参数装饰器、装饰器组合、functools.wraps |
| `02_context_managers.py` | 上下文管理器 | `__enter__`/`__exit__`、`@contextmanager`、资源管理 |
| `03_generators.py` | 生成器与迭代器 | `yield`、生成器管道、`__iter__`/`__next__`、惰性求值 |
| `04_type_hints.py` | 类型提示 | 泛型、Protocol、TypeAlias、Literal、`@overload` |
| `05_dataclasses.py` | 数据类 | `@dataclass`、`field()`、`frozen`、`slots`、`asdict`/`replace` |
| `06_closures.py` | 闭包 | 作用域链、工厂函数、状态保持、柯里化 |
| `07_metaclasses.py` | 元类 | `type`、`__new__`、`__init_subclass__`、接口约束、ORM映射 |
| `08_async_programming.py` | 异步编程 | `async/await`、`asyncio.gather`、信号量、异步迭代器 |
| `09_descriptors.py` | 描述符 | `__get__`/`__set__`、数据描述符、缓存属性、属性验证 |
| `10_functools_itertools.py` | functools & itertools | `lru_cache`、`partial`、`chain`、`groupby`、`accumulate` |

## 运行方式

每个文件可独立运行，直接使用 Python 解释器执行：

```bash
# 运行单个文件
python 01_decorators.py
python 02_context_managers.py

# 运行所有文件
for f in py_advanced/*.py; do python "$f"; echo "---"; done
```

## 环境要求

- Python >= 3.10（使用了 `X | Y` 联合类型语法）
- 无需安装第三方依赖，全部使用标准库
