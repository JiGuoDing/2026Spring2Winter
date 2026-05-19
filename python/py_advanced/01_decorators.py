"""
装饰器 (Decorators)

装饰器是Python中一种强大的语法糖，用于在不修改原函数代码的情况下扩展函数或方法的行为。
核心原理：基于闭包和高阶函数，将一个函数作为参数传入另一个函数，返回增强后的新函数。

应用场景：
- 日志记录、性能计时
- 权限校验与访问控制
- 缓存与重试机制
- 路由注册（Web框架如Flask）
"""

import time
import functools
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def timer(func):
    """计时装饰器：测量函数执行耗时"""
    @functools.wraps(func)  # 保留原函数的元信息（名称、文档等）
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        # 执行原函数并获取结果值
        # * *args 表示将元组展开，作为参数传递给 func
        # * **kwargs 表示将字典展开，作为参数传递给 func
        # * 这两个作为“万能中转站”，把调用时传入的所有参数原封不动地转发给原函数
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"{func.__name__} 执行耗时: {elapsed:.4f}秒")
        return result
    return wrapper

# ! @ 语法的调用：
'''
@retry(max_attempts=3, delay=0.5)
def foo(): ...

等价于 foo = retry(max_attempts=3, delay=0.5)(foo)
先接受一次参数，转为装饰器函数，再调用装饰器函数，返回增强后的函数
'''
def retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器（带参数）：函数失败时自动重试指定次数

    这是一个装饰器工厂函数，返回实际的装饰器。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} 第{attempt}次尝试失败: {e}")
                    if attempt < max_attempts:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def require_auth(role: str = "user"):
    """权限校验装饰器：模拟检查用户是否有指定角色权限"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 模拟从上下文获取当前用户角色
            current_user_role = kwargs.pop("current_user_role", "guest")
            allowed_roles = {"admin", role}
            if current_user_role not in allowed_roles:
                raise PermissionError(
                    f"权限不足: 需要 '{role}' 或 'admin' 角色，当前为 '{current_user_role}'"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ---------- 真实场景示例：数据处理管道 ----------

@timer
@retry(max_attempts=3, delay=0.5)
def fetch_user_data(user_id: int) -> dict:
    """模拟从远程API获取用户数据（可能因网络波动失败）"""
    import random
    if random.random() < 0.6:  # 60%概率模拟失败
        raise ConnectionError("API请求超时")
    return {"id": user_id, "name": f"用户_{user_id}", "email": f"user_{user_id}@example.com"}


@require_auth(role="admin")
def delete_user(user_id: int, current_user_role: str = "guest") -> str:
    """删除用户（需要admin权限）"""
    return f"用户 {user_id} 已被删除"


@timer
def batch_process(user_ids: list[int]) -> list[dict]:
    """批量获取用户数据，展示装饰器的组合使用"""
    results: list[dict] = []
    for uid in user_ids:
        try:
            data = fetch_user_data(uid)
            results.append(data)
        except ConnectionError as e:
            logger.error(f"获取用户 {uid} 数据失败: {e}")
    return results


if __name__ == "__main__":
    # 演示计时 + 重试装饰器
    print("=== 批量数据获取（计时 + 重试） ===")
    users = batch_process([1, 2, 3])
    print(f"成功获取 {len(users)} 条用户数据\n")

    # 演示权限装饰器
    print("=== 权限校验 ===")
    try:
        delete_user(user_id=42, current_user_role="guest")
    except PermissionError as e:
        print(f"预期错误: {e}")

    result = delete_user(user_id=42, current_user_role="admin")
    print(f"操作成功: {result}")
