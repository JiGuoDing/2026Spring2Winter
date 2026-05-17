"""
闭包 (Closures)

闭包是指一个内部函数引用了外部函数的变量，即使外部函数已经执行完毕，
内部函数仍然可以访问那些变量。闭包是函数式编程的重要概念。

核心原理：
- 内部函数持有对外部作用域变量的引用（非值拷贝）
- 外部函数返回内部函数，内部函数"记住"了外部的环境
- 变量通过 LEGB 规则查找（Local -> Enclosing -> Global -> Built-in）

应用场景：
- 工厂函数（根据参数生成不同行为的函数）
- 状态保持（不使用类的情况下维护状态）
- 回调函数与事件处理
- 柯里化（Currying）和偏函数
"""

from collections import deque
from typing import Callable, Any


def make_multiplier(factor: float) -> Callable[[float], float]:
    """工厂函数：根据 factor 生成不同的乘法函数

    返回的函数"记住"了 factor 的值。
    """
    def multiply(x: float) -> float:
        return x * factor  # factor 来自外部作用域
    return multiply


def make_accumulator(initial: float = 0) -> tuple[Callable[[float], float], Callable[[], float]]:
    """创建累加器：返回 (添加函数, 获取当前值函数)

    展示闭包如何在不使用类的情况下维护可变状态。
    """
    total = initial  # 被内部函数引用的外部变量

    def add(amount: float) -> float:
        nonlocal total  # 声明修改外部变量
        total += amount
        return total

    def get_total() -> float:
        return total

    return add, get_total


def make_validator(rules: list[Callable[[str], tuple[bool, str]]]) -> Callable[[str], list[str]]:
    """验证器工厂：组合多个验证规则，返回统一的验证函数

    每个规则是一个函数，接收输入值，返回 (是否通过, 错误信息)。
    """
    def validate(value: str) -> list[str]:
        errors: list[str] = []
        for rule in rules:
            passed, message = rule(value)
            if not passed:
                errors.append(message)
        return errors

    return validate


def make_rate_limiter(max_calls: int, time_window: float) -> Callable[[], bool]:
    """速率限制器：在指定时间窗口内限制调用次数

    使用闭包维护调用时间戳列表。
    """
    import time
    call_times: deque[float] = deque()  # 闭包持有的状态（deque 支持 O(1) 的 popleft）

    def allow() -> bool:
        now = time.monotonic()
        # 清除过期的调用记录
        while call_times and call_times[0] <= now - time_window:
            call_times.popleft()
        if len(call_times) < max_calls:
            call_times.append(now)
            return True
        return False

    return allow


def curry(func: Callable) -> Callable:
    """自动柯里化装饰器：将多参数函数转换为链式单参数调用

    例如：add(1, 2, 3) -> add(1)(2)(3)
    """
    import inspect
    params = inspect.signature(func).parameters
    num_args = len(params)

    def curried(*args: Any) -> Any:
        if len(args) >= num_args:
            return func(*args[:num_args])
        return lambda *more: curried(*args, *more)

    return curried


# ---------- 真实场景示例：权限与配置管理 ----------

def make_auth_middleware(required_role: str) -> Callable[[dict], dict | None]:
    """认证中间件工厂：根据所需角色创建不同的认证检查函数

    模拟Web框架中的中间件模式。
    """
    def check(user_context: dict) -> dict | None:
        user_role = user_context.get("role", "guest")
        permissions = {
            "guest": ["read"],
            "user": ["read", "write"],
            "admin": ["read", "write", "delete", "manage"],
        }
        allowed = permissions.get(user_role, [])
        if required_role in allowed or user_role == "admin":
            return {"allowed": True, "user": user_context.get("name", "unknown")}
        return None  # 拒绝访问

    return check


if __name__ == "__main__":
    # 工厂函数
    print("=== 工厂函数 ===")
    double = make_multiplier(2)
    triple = make_multiplier(3)
    print(f"  double(5) = {double(5)}")
    print(f"  triple(5) = {triple(5)}")

    # 累加器
    print("\n=== 累加器 ===")
    add, get_total = make_accumulator(100)
    print(f"  初始值: {get_total()}")
    print(f"  +10: {add(10)}")
    print(f"  +20: {add(20)}")
    print(f"  当前: {get_total()}")

    # 验证器
    print("\n=== 验证器组合 ===")
    rules = [
        (lambda v: (len(v) >= 6, "长度不能少于6个字符")),
        (lambda v: (any(c.isupper() for c in v), "必须包含大写字母")),
        (lambda v: (any(c.isdigit() for c in v), "必须包含数字")),
    ]
    validate_password = make_validator(rules)

    for pwd in ["abc", "abcdef", "Abcdef", "Abcdef1"]:
        errors = validate_password(pwd)
        status = "通过" if not errors else f"失败: {'; '.join(errors)}"
        print(f"  '{pwd}' -> {status}")

    # 速率限制
    print("\n=== 速率限制器(3次/秒) ===")
    limiter = make_rate_limiter(max_calls=3, time_window=1.0)
    for i in range(5):
        print(f"  请求 {i+1}: {'允许' if limiter() else '拒绝'}")

    # 柯里化
    print("\n=== 柯里化 ===")
    @curry
    def add_three(a: int, b: int, c: int) -> int:
        return a + b + c

    print(f"  add_three(1, 2, 3) = {add_three(1, 2, 3)}")
    print(f"  add_three(1)(2)(3) = {add_three(1)(2)(3)}")
    print(f"  add_three(1, 2)(3) = {add_three(1, 2)(3)}")

    # 认证中间件
    print("\n=== 认证中间件 ===")
    write_check = make_auth_middleware("write")
    delete_check = make_auth_middleware("delete")

    users = [
        {"name": "张三", "role": "user"},
        {"name": "管理员", "role": "admin"},
    ]
    for user in users:
        write_result = write_check(user)
        delete_result = delete_check(user)
        print(f"  {user['name']}: 写入={'允许' if write_result else '拒绝'}, "
              f"删除={'允许' if delete_result else '拒绝'}")
