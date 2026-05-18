"""07 - 并行与性能：parallelism / concurrency / num_cpus / repartition。

本示例展示：
- parallelism 控制读取并行度
- concurrency 控制转换并行度
- num_cpus 资源分配
- repartition 对性能的影响
"""

import ray
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 50)
    print("  并行与性能")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # 创建数据
    ds = ray.data.from_items([{"id": i, "value": i} for i in range(500)])
    print(f"原始数据: {ds.count()} 行, {ds.num_blocks()} 个分区\n")

    # ==================== 1. 并行度控制 ====================
    print("--- [1] parallelism: 读取并行度 ---")
    print("  parallelism 参数控制数据被分成多少个 block")
    ds_high = ray.data.range(1000, parallelism=10)
    ds_low = ray.data.range(1000, parallelism=2)
    print(f"  parallelism=10: {ds_high.num_blocks()} 个 block")
    print(f"  parallelism=2:  {ds_low.num_blocks()} 个 block")

    # ==================== 2. map 并发控制 ====================
    print("\n--- [2] concurrency: 转换并发数 ---")

    def slow_transform(row):
        """模拟耗时转换。"""
        time.sleep(0.001)  # 模拟 1ms 处理时间
        return {**row, "processed": True}

    # 使用默认并发
    start = time.time()
    ds.map(slow_transform).materialize()
    t1 = time.time() - start
    print(f"  默认并发: {t1:.2f}s")

    # ==================== 3. num_cpus 资源分配 ====================
    print("\n--- [3] num_cpus: 资源分配 ---")
    print("""
    num_cpus 参数指定每个任务使用的 CPU 核心数：
    - num_cpus=0.5: 每个任务使用半个 CPU，允许更多并发
    - num_cpus=1: 每个任务使用一个 CPU（默认）
    - num_cpus=2: 每个任务使用两个 CPU，适合计算密集型
    """)

    # ==================== 4. repartition 对性能的影响 ====================
    print("--- [4] repartition 对性能的影响 ---")
    print(f"  原始分区数: {ds.num_blocks()}")

    # 增加分区数
    ds_more = ds.repartition(num_blocks=10)
    print(f"  增加到 10 个分区: {ds_more.num_blocks()}")

    # 减少分区数
    ds_fewer = ds.repartition(num_blocks=2)
    print(f"  减少到 2 个分区: {ds_fewer.num_blocks()}")

    # ==================== 5. 性能建议 ====================
    print("\n" + "=" * 50)
    print("  性能优化建议")
    print("=" * 50)
    print("""
    1. 分区数选择：
       - 一般设为 CPU 核心数的 2-4 倍
       - 太少: 并行度不够，资源浪费
       - 太多: 调度开销大，小任务多

    2. batch_size 选择：
       - 默认通常够用
       - 内存充足时可增大以减少调度开销
       - 内存紧张时应减小

    3. num_cpus 设置：
       - CPU 密集型: num_cpus=1 或更高
       - I/O 密集型: num_cpus=0.5 可提高并发

    4. 物化策略：
       - 多次使用的数据集尽早 materialize
       - 避免重复计算

    5. 监控工具：
       - Ray Dashboard: http://127.0.0.1:8265
       - 查看任务分布、资源使用、执行时间
    """)

    ray.shutdown()
    print("示例结束。")


if __name__ == "__main__":
    main()
