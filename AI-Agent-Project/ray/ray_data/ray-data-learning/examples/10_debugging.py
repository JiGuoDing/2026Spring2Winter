"""10 - 调试与常见坑。

本示例展示：
- Schema 不一致问题
- 用户函数异常处理
- 脏数据处理
- OOM 预防
- 版本差异注意事项
"""

import ray
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ray_utils import get_data_path


def main():
    print("=" * 50)
    print("  调试与常见坑")
    print("=" * 50)

    ray.init(ignore_reinit_error=True, log_to_driver=False)

    # ==================== 1. Schema 不一致 ====================
    print("\n--- [1] Schema 不一致问题 ---")
    print("""
    常见问题：不同行的字段类型不一致。

    解决方案：
    - 确保所有行的相同字段类型一致
    - 使用 map_batches 统一类型
    - 读取前检查数据源
    """)

    # 演示：创建类型不一致的数据
    mixed_data = ray.data.from_items([
        {"id": 1, "value": 10},       # value 是 int
        {"id": 2, "value": "hello"},  # value 是 string（问题！）
        {"id": 3, "value": 30},
    ])

    print("  尝试创建类型不一致的数据集...")
    try:
        print(f"  Schema: {mixed_data.schema()}")
        mixed_data.show()
        print("  注意：Ray Data 可能会自动推断为统一类型，或者在某些版本报错")
    except Exception as e:
        print(f"  错误: {e}")

    # ==================== 2. 用户函数异常 ====================
    print("\n--- [2] 用户函数异常处理 ---")
    print("""
    常见问题：map/filter 函数抛出异常。

    解决方案：
    - 在函数内部 try-except
    - 返回默认值或跳过
    - 使用 logging 记录错误
    """)

    ds = ray.data.from_items([{"x": i} for i in range(10)])

    # 不好的写法：函数可能抛异常
    def bad_transform(row):
        return {"x": row["x"], "result": 10 / row["x"]}  # x=0 时除零

    # 好的写法：内部处理异常
    def safe_transform(row):
        try:
            result = 10 / row["x"] if row["x"] != 0 else 0.0
        except Exception:
            result = 0.0
        return {"x": row["x"], "result": result}

    print("  使用安全的转换函数:")
    ds_safe = ds.map(safe_transform)
    ds_safe.show()

    # ==================== 3. 脏数据处理 ====================
    print("\n--- [3] 脏数据处理 ---")
    dirty_path = get_data_path("dirty_users.csv")
    if os.path.exists(dirty_path):
        ds_dirty = ray.data.read_csv(dirty_path)
        print(f"  脏数据行数: {ds_dirty.count()}")
        ds_dirty.show(limit=5)

        # 清洗函数
        def clean_batch(batch: pd.DataFrame) -> pd.DataFrame:
            # 过滤无效 user_id
            batch = batch[batch["user_id"].notna() & (batch["user_id"] != "")]
            # 转换 age 为数值，无效值设为 NaN
            batch["age"] = pd.to_numeric(batch["age"], errors="coerce")
            # 过滤异常年龄
            batch = batch[(batch["age"] >= 0) & (batch["age"] <= 120)]
            # 填充缺失值
            batch["city"] = batch["city"].fillna("未知")
            batch["gender"] = batch["gender"].fillna("U")
            return batch

        print("\n  清洗后:")
        ds_clean = ds_dirty.map_batches(clean_batch, batch_format="pandas")
        print(f"  清洗后行数: {ds_clean.count()}")
        ds_clean.show(limit=5)
    else:
        print(f"  脏数据文件不存在: {dirty_path}")
        print("  请先运行: python scripts/generate_data.py")

    # ==================== 4. OOM 预防 ====================
    print("\n--- [4] OOM 预防 ---")
    print("""
    OOM（内存不足）常见原因与解决方案：

    1. batch_size 过大：
       - 解决：减小 batch_size，如 batch_size=1000

    2. 数据集过大无法放入内存：
       - 解决：使用 streaming 模式，或增加节点

    3. 物化过多中间结果：
       - 解决：避免不必要的 materialize()

    4. 用户函数内存泄漏：
       - 解决：确保函数内不持有大对象引用

    5. 数据格式选择：
       - Parquet 比 CSV 更省内存（列式存储，压缩）
    """)

    # ==================== 5. 版本差异 ====================
    print("\n--- [5] 版本差异注意事项 ---")
    print("""
    Ray Data API 在不同版本间有变化：

    1. Ray 2.0 -> 2.9+:
       - Dataset API 从 Experimental 转为 Stable
       - 部分旧 API 被弃用

    2. batch_format 参数：
       - 旧版本可能使用 "pandas" / "numpy" / "pyarrow"
       - 新版本统一为 BatchFormat 枚举

    3. from_items / from_pandas 等：
       - 参数签名可能有微调
       - 建议查看当前版本文档

    4. 序列化：
       - Ray 使用 CloudPickle 序列化用户函数
       - 避免使用 lambda 捕获不可序列化的对象

    调试技巧：
    - 使用 ray.data.from_items() 创建小数据集快速测试
    - 先在单个 batch 上测试转换函数
    - 使用 ds.show() 查看中间结果
    - 查看 Ray Dashboard 了解任务状态
    """)

    ray.shutdown()
    print("示例结束。")


if __name__ == "__main__":
    main()
