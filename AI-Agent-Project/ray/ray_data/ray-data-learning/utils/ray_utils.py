"""Ray 初始化与管理工具函数。"""

import ray
import os


def init_ray(num_cpus=None, dashboard_port=8265):
    """初始化 Ray 运行时。

    Args:
        num_cpus: 指定 CPU 核心数，None 表示自动检测
        dashboard_port: Dashboard 端口号

    Returns:
        Ray 上下文信息字典
    """
    if ray.is_initialized():
        print("Ray 已经初始化，跳过重复初始化")
        return ray.cluster_resources()

    # 初始化 Ray，关闭 dashboard 以加快启动速度
    ray.init(
        num_cpus=num_cpus or os.cpu_count(),
        ignore_reinit_error=True,
        log_to_driver=False,
    )

    resources = ray.cluster_resources()
    print(f"Ray 初始化完成")
    print(f"  可用 CPU: {resources.get('CPU', 0)}")
    print(f"  可用内存: {resources.get('memory', 0) / 1e9:.1f} GB")
    print(f"  Dashboard: http://127.0.0.1:{dashboard_port}")
    return resources


def shutdown_ray():
    """关闭 Ray 运行时。"""
    if ray.is_initialized():
        ray.shutdown()
        print("Ray 已关闭")
    else:
        print("Ray 未初始化，无需关闭")


def get_data_path(filename):
    """获取 data/raw/ 下的文件绝对路径。

    Args:
        filename: 文件名，如 'users.csv'

    Returns:
        文件的绝对路径
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", "raw", filename)


def get_output_path(filename):
    """获取 data/processed/ 下的输出文件绝对路径。

    Args:
        filename: 文件名

    Returns:
        文件的绝对路径
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)
