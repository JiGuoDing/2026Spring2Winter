"""
================================================================================
  Ray 学习项目 · 第一课：远程任务与分布式 DAG
================================================================================

  🎯 学习目标
  ─────────
  1. 深入理解 remote task 的生命周期与调度机制
  2. 掌握动态 DAG 的构建：条件分支、循环展开、嵌套任务
  3. 理解 Object Store 的数据局部性（data locality）原理
  4. 掌握任务粒度划分的最佳实践
  5. 对比理解 Ray 的任务调度 vs Flink 的算子链

  📖 Flink → Ray 深度类比
  ────────────────────────
  ┌──────────────────────────────┬──────────────────────────────────────┐
  │ Flink 概念                    │ Ray 对应                              │
  ├──────────────────────────────┼──────────────────────────────────────┤
  │ Operator Chain (算子链)       │ 单一 remote task 内顺序执行           │
  │ JobGraph → ExecutionGraph    │ 动态 ObjectRef 依赖图                 │
  │ Task 部署到 TaskSlot          │ Task 调度到 Worker 的 CPU 资源        │
  │ Network Shuffle (分区传输)    │ Object Store 跨节点复制 (自动)         │
  │ 反压 (Backpressure)           │ 无内置反压，靠"生产者-消费者"手动控制   │
  │ AsyncIO (异步外部调用)        │ 天然支持，remote task 内随意写 IO      │
  └──────────────────────────────┴──────────────────────────────────────┘

  ⚠️  关键认知
  ────────────
  Ray 的"任务"和 Flink 的"任务"不是一回事：
  - Flink Task = 一个并行实例（如并行的 map 算子），持续运行，处理流经的数据
  - Ray Task = 一个函数的单次执行（invocation），有明确的输入→输出，
    执行完毕即释放资源。更像 FaaS（函数即服务）中的一次调用。
"""

import ray
import time
import random
import os
from typing import List, Dict, Any


# ============================================================================
# 第一部分：深入理解远程任务
# ============================================================================

print("=" * 70)
print("  第一部分：远程任务启动方式对比")
print("=" * 70)

ray.init(address="auto", ignore_reinit_error=True)


# --- 远程任务参数传递机制 ---
# 当调用 func.remote(arg1, arg2) 时：
# 1. 如果 arg 是普通 Python 对象 → Ray 自动序列化(cloudpickle)并拷贝到目标节点
# 2. 如果 arg 是 ObjectRef         → Ray 传递引用，不拷贝数据
#    任务执行时遇到 ray.get(ref) 才去取数据（利用共享内存或网络拉取）
# 这类似于 Flink 中的：
#   普通对象 = 闭包变量，随 Task 序列化到 TaskManager
#   ObjectRef = Broadcast State / 分布式缓存引用

@ray.remote
def analyze_number(n: int) -> dict:
    """
    模拟一个需要一定计算资源的分析任务。
    --- Flink 类比: 就像 FlatMapFunction<Integer, Map<String, Object>> ---
    """
    # 模拟不同程度的计算耗时
    time.sleep(random.uniform(0.05, 0.2))
    return {
        "number": n,
        "square": n ** 2,
        "is_even": n % 2 == 0,
        "worker_pid": os.getpid(),  # 证明分布在不同进程
        "worker_node": ray.get_runtime_context().node_id.hex()[:8],
    }


# 演示参数传递
print("\n📌 传递普通值 vs ObjectRef:")

# 方式1：传递普通值（Ray 自动序列化）
tasks_normal = [analyze_number.remote(i) for i in range(4)]
results_normal = ray.get(tasks_normal)

# 方式2：先把数据放入 Object Store，再传引用（适合大数据）
big_data = list(range(4))
big_data_ref = ray.put(big_data)  # 存入 Object Store

@ray.remote
def analyze_list(data_ref: ray.ObjectRef) -> List[dict]:
    """接收 ObjectRef，在需要时才 ray.get() 取数据。"""
    data = ray.get(data_ref)
    return [{"index": i, "value": i * 2} for i in data]

results_via_ref = ray.get(analyze_list.remote(big_data_ref))
print(f"   方式1（传值）: {len(results_normal)} 条结果")
print(f"   方式2（传引用）: {len(results_via_ref)} 条结果")


# ============================================================================
# 第二部分：动态 DAG —— 条件分支与循环展开
# ============================================================================

# --- Flink 类比 ---
# 这是 Ray 相比 Flink 最核心的优势之一：任务 DAG 可以在运行时根据计算结果动态决定
# 下一步做什么，而 Flink 的 DAG 结构必须在编译时确定。
#
# Flink 中如果你想"根据数据决定走哪条分支"，只能通过 Side Output 或 ProcessFunction
# 来模拟；而 Ray 中这就像写普通的 if/else 一样自然。

print("\n" + "=" * 70)
print("  第二部分：动态 DAG —— 运行时决定计算图结构")
print("=" * 70)


@ray.remote
def classify_data(batch_id: int) -> str:
    """模拟数据分类：根据 batch 内容返回其类别标签。"""
    time.sleep(0.1)
    # 用随机数模拟分类结果
    categories = ["normal", "anomaly", "critical"]
    return random.choice(categories)


@ray.remote
def handle_normal(batch_id: int) -> dict:
    """处理正常数据 —— 简单记录即可。"""
    return {"batch": batch_id, "action": "log_only", "cost_ms": 5}

@ray.remote
def handle_anomaly(batch_id: int) -> dict:
    """处理异常数据 —— 需要深度分析。"""
    time.sleep(0.2)  # 更深度的分析
    return {"batch": batch_id, "action": "deep_analysis", "cost_ms": 200}

@ray.remote
def handle_critical(batch_id: int) -> dict:
    """处理严重异常 —— 触发告警 + 全量诊断。"""
    time.sleep(0.3)  # 最重的处理逻辑
    return {"batch": batch_id, "action": "alert_and_diagnose", "cost_ms": 300}


# 动态 DAG 的核心：根据任务结果，在 Python 代码层面决定下一步
batch_ids = list(range(6))
print(f"\n处理 {len(batch_ids)} 个批次，动态路由到不同处理分支:\n")

# 第一步：并行分类所有 batch
classify_refs = [classify_data.remote(bid) for bid in batch_ids]
categories = ray.get(classify_refs)

# 第二步：根据分类结果，动态分配处理任务
# 💡 这步在 Flink 中必须通过 SideOutput + 多个 sink 来模拟
# 在 Ray 中就是自然的 if/elif，对于复杂动态逻辑极其友好
handle_refs = []
for bid, cat in zip(batch_ids, categories):
    if cat == "normal":
        handle_refs.append(handle_normal.remote(bid))
    elif cat == "anomaly":
        handle_refs.append(handle_anomaly.remote(bid))
    else:
        handle_refs.append(handle_critical.remote(bid))
    print(f"  batch_{bid} → {cat} → 路由到 handle_{cat}")

results = ray.get(handle_refs)
print(f"\n所有处理结果:")
for r in results:
    print(f"  {r}")


# ============================================================================
# 第三部分：嵌套远程任务 —— 递归式并行
# ============================================================================

# --- Flink 类比 ---
# Flink 不支持算子内动态创建新算子。
# Ray 的远程任务内部可以再调用 .remote() 创建子任务，实现递归并行。
# 这在实现"分治算法"（如分布式排序、树遍历）时非常强大。

print("\n" + "=" * 70)
print("  第三部分：嵌套远程任务 —— 递归并行（分治算法）")
print("=" * 70)


@ray.remote
def parallel_sum(arr: List[int], threshold: int = 3) -> int:
    """
    分布式递归求和：如果数组长度大于阈值，拆成两半并行计算。
    这是一个经典的 MapReduce 模式在 Ray 上的自然表达。

    --- Flink 类比 ---
    类似 Flink 的 keyBy 后做增量聚合，但 Ray 可以动态决定是否拆分，
    而 Flink 的分区策略在编译时固定。
    """
    n = len(arr)
    if n <= threshold:
        # 基本情况：数组足够小，直接本地计算
        return sum(arr)
    else:
        # 递归情况：拆分成两个子任务并行执行
        mid = n // 2
        left_ref  = parallel_sum.remote(arr[:mid], threshold)
        right_ref = parallel_sum.remote(arr[mid:], threshold)
        # 等待两个子任务完成并合并
        return ray.get(left_ref) + ray.get(right_ref)


test_array = list(range(1, 21))  # 1 到 20
print(f"测试数组: {test_array}")
result = ray.get(parallel_sum.remote(test_array, threshold=5))
print(f"分布式求和结果: {result}  (期望: {sum(test_array)})")


# ============================================================================
# 第四部分：任务粒度 —— 多少算"合适"？
# ============================================================================

# --- Flink 类比 ---
# Flink 中任务粒度由 slot 数量和算子并行度决定，你不需要关心单个"调用"的开销。
# Ray 中每个 .remote() 都是一次独立调度，有固定开销（~1ms 级别），
# 因此任务不能太细（避免调度开销大于计算开销），也不能太粗（失去并行性）。

print("\n" + "=" * 70)
print("  第四部分：任务粒度实验 —— 找到最佳并行度")
print("=" * 70)


@ray.remote
def compute_chunk(data: List[int]) -> int:
    """对一个数据块执行计算。"""
    # 模拟 CPU 密集型计算
    return sum(x ** 2 for x in data)

# 固定总数据量，比较不同分块策略
TOTAL_SIZE = 100_000
data = list(range(TOTAL_SIZE))

for num_chunks in [1, 4, 16, 64, 256]:
    chunk_size = TOTAL_SIZE // num_chunks
    chunks = [data[i:i+chunk_size] for i in range(0, TOTAL_SIZE, chunk_size)]

    start = time.time()
    refs = [compute_chunk.remote(chunk) for chunk in chunks]
    total = sum(ray.get(refs))
    elapsed = time.time() - start

    print(f"  分块数={num_chunks:3d}, 每块={chunk_size:6d}条, "
          f"耗时={elapsed:.4f}s, 结果={total}")
# 观察：
# - 分块太少 → 并行度不足
# - 分块太多 → 调度开销显著
# - 最佳分块数通常在 CPU 核心数的 1-4 倍之间


# ============================================================================
# 第五部分：任务重试与容错
# ============================================================================

# --- Flink 类比 ---
# Flink 有完善的 checkpoint 机制，任务失败后从最近 checkpoint 恢复。
# Ray 默认不提供自动容错，但你可以通过 max_retries 参数实现任务级重试。
# 这是一种"重试算"而非"从快照恢复"的模式，适合幂等的无状态任务。

print("\n" + "=" * 70)
print("  第五部分：任务重试机制")
print("=" * 70)


# max_retries 参数：任务抛出异常时自动重试
# 注意：只对任务执行期间的异常重试，不包括节点宕机
@ray.remote(max_retries=3)
def flaky_task(task_id: int) -> str:
    """一个不稳定的任务，有时会失败，需要重试。"""
    # 模拟偶发失败：30% 概率抛出异常
    if random.random() < 0.3:
        raise RuntimeError(f"任务 {task_id} 模拟失败！")
    time.sleep(0.05)
    return f"任务 {task_id} 成功 (PID={os.getpid()})"


class TaskTimeoutError(Exception):
    """自定义异常：任务超时。"""
    pass

@ray.remote
def task_with_timeout(data: int, timeout_s: float) -> int:
    """
    模拟一个可能超时的任务。

    注意：Ray 的 remote task 没有原生的"超时"参数，
    超时需要在调用侧用 ray.wait(timeout=...) 实现。
    """
    if data == 10:  # 特殊值模拟慢任务
        time.sleep(5.0)
    return data * 2


print("\n📌 重试示例:")
retry_refs = [flaky_task.remote(i) for i in range(5)]
for ref in retry_refs:
    try:
        result = ray.get(ref)
        print(f"  ✅ {result}")
    except RuntimeError as e:
        # 重试 3 次后仍失败才会抛出异常
        print(f"  ❌ {e}")

print("\n📌 超时示例:")
timeout_ref = task_with_timeout.remote(10, timeout_s=1.0)
done, pending = ray.wait([timeout_ref], timeout=2.0)
if not done:
    print(f"  ⏰ 任务超时（2 秒内未完成），还有 {len(pending)} 个未完成")
else:
    print(f"  ✅ 任务在超时前完成: {ray.get(done[0])}")


# ============================================================================
# 第六部分：与 Flink 调度模型的深度对比
# ============================================================================

print("\n" + "=" * 70)
print("  第六部分：Ray 调度 vs Flink 调度 —— 可视化对比")
print("=" * 70)

print("""
  ┌─── Flink 调度模型（声明式）────────────────────────────┐
  │                                                         │
  │  Source ──→ Map ──→ KeyBy ──→ Window ──→ Sink          │
  │    │         │        │         │         │             │
  │   (slot)   (slot)   (slot)    (slot)    (slot)         │
  │                                                         │
  │  • DAG 在编译时固定                                      │
  │  • 每个算子实例常驻，持续处理数据                           │
  │  • 反压自动传播                                          │
  │  • Checkpoint 自动管理状态                               │
  └─────────────────────────────────────────────────────────┘

  ┌─── Ray 调度模型（命令式）───────────────────────────────┐
  │                                                         │
  │  main() {                                              │
  │    a_ref = task_a.remote()    // 即时调度               │
  │    b_ref = task_b.remote()    // 即时调度               │
  │    if ray.get(a_ref) > 10:    // 动态判断               │
  │      c_ref = task_c.remote(b_ref) // 条件调度           │
  │    else:                                               │
  │      d_ref = task_d.remote()   // 另一分支              │
  │  }                                                     │
  │                                                         │
  │  • DAG 运行时动态构建                                     │
  │  • 任务执行完即释放资源                                    │
  │  • 无内置反压，需手动控制并发                               │
  │  • 容错靠重试或应用层实现                                  │
  └─────────────────────────────────────────────────────────┘
""")


# ============================================================================
# 第七部分：实战 —— 使用 ray.wait() 实现"投机执行"
# ============================================================================

print("=" * 70)
print("  第七部分：投机执行 —— 同时跑多个策略，取最快的")
print("=" * 70)


@ray.remote
def expensive_computation(seed: int) -> int:
    """一个计算结果取决于输入 seed 的耗时任务。"""
    time.sleep(random.uniform(0.2, 0.8))
    return seed * 7 + 3


# 启动 5 个不同 seed 的任务，取最快完成的 2 个
# 这在 Flink 中几乎不可能做到（Flink DAG 编译时固定）
refs = [expensive_computation.remote(i * 100) for i in range(5)]
print(f"启动 {len(refs)} 个投机任务...")

# 只等最快的 2 个
done, pending = ray.wait(refs, num_returns=2, timeout=None)
fastest_results = ray.get(done)
print(f"最快的 2 个结果: {fastest_results}")

# 取消剩余任务（注意：Ray 没有内置的"取消运行中的任务"功能，
# 剩余任务会继续执行完毕，只是我们不取结果了）
print(f"剩余 {len(pending)} 个任务将被丢弃（仍在运行但结果不再获取）")


# ============================================================================
# 收尾
# ============================================================================

ray.shutdown()
print("\n✅ Ray 已关闭")


# ============================================================================
# 📝 面试问题自检
# ============================================================================

"""
Q5: Ray 的 remote task 和 Flink 的一个算子实例（如 MapFunction）有何本质不同？
──────────────────────────────────────────────────────────────────────────
A: 1. 生命周期：Flink 算子实例常驻在 TaskManager 上，持续处理流经的数据；
      Ray 的 remote task 是"一次性"的：接收输入、计算、返回结果、释放资源。
   2. 状态：Flink 算子可通过 RuntimeContext 访问 KeyedState/OperatorState；
      Ray remote task 是无状态的（状态只能通过参数传入或 Object Store 共享）。
   3. 调度：Flink 算子由 JobManager 静态分配到 TaskSlot；
      Ray remote task 由 Raylet 动态调度到有空闲资源的 Worker。
   4. 类比：Ray remote task 更像 AWS Lambda 的一次调用，而非一个长期运行的服务。

Q6: 如果一个 Ray 任务需要访问外部数据库，应该怎么做？和 Flink 的 AsyncIO 相比如何？
──────────────────────────────────────────────────────────────────────────
A: 在 Ray 中，直接在 remote task 函数体内写数据库连接代码即可，因为每个 task
   都是一个完整的 Python 函数执行。这比 Flink 的 AsyncIO 简单得多：
   - Flink: 需要实现 AsyncFunction，管理连接池、超时、结果顺序
   - Ray: conn = psycopg2.connect(...); result = cur.execute(...); return result
   但是！Ray 没有 Flink AsyncIO 的背压控制和有序输出保证，你需要自己管理
   并发数（用 max_concurrency 或信号量）。

Q7: 描述一个 Ray 适合但 Flink 不适合的场景。
───────────────────────────────────────────
A: 典型的 ML 训练超参搜索（Hyperparameter Tuning）：你需要并行跑 100 组不同
   超参的组合，每组训练耗时不同（有的 1 分钟，有的 10 分钟），并且你希望随时
   查看中间结果、动态停止表现差的组合、根据早期结果调整后续参数空间。
   - Flink: 流处理框架，不是为这种"离散的、动态的、不等时的"任务设计的
   - Ray: 每个训练任务是一个 remote task，用 ray.wait() 实时监控进度，
     主进程可以根据结果动态决定下一步参数 —— 这是 Ray 的原生强项。

Q8: Ray 的任务调度开销有多大？如何判断任务粒度是否合理？
─────────────────────────────────────────────────────
A: 单个 .remote() 调度的开销约 1-3ms（包括序列化、网络通信、调度决策）。
   经验法则：单个任务计算时间 > 100ms 才值得"远程化"。
   如果每个任务只做 < 10ms 的计算，应该考虑批处理：
   把多个小任务合并成一个（传入一个 batch/list 而非单个元素）。
   可以通过类似第四部分的实验来找到最佳分块大小。
"""

print("\n" + "=" * 70)
print("  🎉 第一课完成！继续运行 02_actor_model.py 学习 Actor 模型")
print("=" * 70)
