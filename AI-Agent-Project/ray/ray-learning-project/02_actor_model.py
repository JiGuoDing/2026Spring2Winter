"""
================================================================================
  Ray 学习项目 · 第二课：Actor 模型 —— 有状态分布式计算
================================================================================

  🎯 学习目标
  ─────────
  1. 理解 Actor 模型：有状态的远程对象
  2. 掌握 Actor 生命周期管理（__init__, 方法调用, 析构）
  3. 对比 Actor 与 Flink KeyedState / RichFunction
  4. 掌握 Actor 内并发控制（max_concurrency）
  5. 实现 Actor 间的消息传递与协作

  📖 Flink → Ray Actor 类比
  ───────────────────────────
  ┌──────────────────────────────┬─────────────────────────────────────┐
  │ Flink 概念                    │ Ray Actor                           │
  ├──────────────────────────────┼─────────────────────────────────────┤
  │ KeyedState (按 key 分片状态)  │ Actor 内部属性 (每个 Actor 一份状态) │
  │ RichFunction (open/close)    │ __init__ / 手动清理                  │
  │ ValueState<T>                │ self.field: T                       │
  │ MapState<K,V>                │ self.dict: Dict[K,V] (actor 内字典) │
  │ TimerService                 │ 手动 sleep/threading.Timer           │
  │ CheckpointedFunction         │ 需自己实现快照/恢复                   │
  │ KeyedProcessFunction         │ Actor 方法 (stateful method)         │
  └──────────────────────────────┴─────────────────────────────────────┘

  🔑 Actor 核心特性
  ─────────────────────────
  1. 有状态：Actor 是一个类实例，属性在多次方法调用之间保留
  2. 单线程：默认同一 Actor 的方法调用串行执行（线程安全由框架保证）
  3. 可寻址：每个 Actor 有全局唯一的 handle，任何任务都可以调用它
  4. 持久化：Actor 在创建后一直存活，直到被显式销毁或进程崩溃
"""

import ray
import time
import random
import os
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque


# ============================================================================
# 第一部分：第一个 Actor —— 有状态的计数器
# ============================================================================

print("=" * 70)
print("  第一部分：Hello Actor —— 有状态计数器")
print("=" * 70)

ray.init(address="auto", ignore_reinit_error=True)


# --- Flink 类比 ---
# 这个 Counter 就像 Flink 中使用 ValueState<Integer> 维护的一个计数器：
#   private transient ValueState<Integer> counterState;
#   public void open(...) { counterState = getRuntimeContext().getState(...); }
#   public void processElement(...) {
#       Integer current = counterState.value();
#       counterState.update(current + 1);
#   }
#
# Ray Actor 的 self.count 就是"状态"，且天然跨调用保持。
# 关键区别：Flink 的状态由框架通过 checkpoint 持久化，Ray Actor 的状态在内存中。

@ray.remote
class Counter:
    """
    一个分布式计数器 Actor。

    --- Flink 类比 ---
    类似 Flink 中使用 ValueState 维护的计数器，但：
    - Flink: 每个 key 一个 ValueState 实例，由 keyBy 分区
    - Ray: 每个 Actor 实例一个状态，由你手动管理有多少个 Actor
    """

    def __init__(self, name: str, initial_value: int = 0):
        """
        Actor 的构造函数。
        运行在创建 Actor 的 Worker 进程上。
        返回一个 ActorHandle，调用方可以远程调用这个 Actor 的方法。

        --- Flink 类比 ---
        类似 RichFunction.open(Configuration)，在算子实例初始化时调用。
        但 Ray 的 __init__ 可以接收任意参数，更灵活。
        """
        self.name = name
        self.count = initial_value
        self.created_at = time.time()
        self.call_history: List[str] = []  # 记录所有调用
        print(f"[Actor] Counter '{name}' 已创建 (PID={os.getpid()})")

    def increment(self, delta: int = 1) -> int:
        """
        增加计数并返回新值。
        每个方法调用都会排队串行执行，天然线程安全。

        --- Flink 类比 ---
        类似 ProcessFunction 中处理一条数据：
        ctx.timerService().registerProcessingTimeTimer(...)
        """
        self.count += delta
        self.call_history.append(f"increment({delta}) → {self.count}")
        return self.count

    def get_count(self) -> int:
        """查询当前计数（只读操作）。"""
        return self.count

    def reset(self) -> None:
        """重置计数器。"""
        old = self.count
        self.count = 0
        self.call_history.append(f"reset (was {old})")

    def get_stats(self) -> Dict:
        """获取计数器的统计信息。"""
        return {
            "name": self.name,
            "current_count": self.count,
            "uptime_seconds": time.time() - self.created_at,
            "call_history": self.call_history[-10:],  # 最近 10 条
            "pid": os.getpid(),
        }


# 创建 Actor 实例 —— .remote() 返回 ActorHandle，而不是 ObjectRef
# --- Flink 类比 ---
# 类似在 Flink 算子中初始化一个 ValueState 描述符，但 Actor 让你"主动"创建实例
my_counter: ray.actor.ActorHandle = Counter.remote("订单计数器", initial_value=100)

print(f"\n📦 ActorHandle 类型: {type(my_counter)}")

# 调用 Actor 的方法 —— .increment.remote() 返回 ObjectRef
print("\n📌 调用 Actor 方法:")
ref1 = my_counter.increment.remote(5)    # 异步调用，返回 ObjectRef
ref2 = my_counter.increment.remote(3)    # 排队等待，ref1 执行完后才执行 ref2
print(f"   increment(5) 返回: {ray.get(ref1)}")
print(f"   increment(3) 返回: {ray.get(ref2)}")

# 调用统计方法
stats = ray.get(my_counter.get_stats.remote())
print(f"\n📊 计数器统计: {stats}")


# ============================================================================
# 第二部分：Actor 的并发控制 —— max_concurrency
# ============================================================================

# --- Flink 类比 ---
# Flink 中每个算子实例串行处理数据（单线程模型），天然保证顺序。
# Ray Actor 默认也是串行的（max_concurrency=1），但可以配置为允许并发。

print("\n" + "=" * 70)
print("  第二部分：Actor 并发控制 —— 串行 vs 并发")
print("=" * 70)


@ray.remote
class SerialProcessor:
    """串行处理器（默认 max_concurrency=1）—— 类似 Flink 单线程算子。"""

    def __init__(self):
        self.processed = 0
        self.current = None

    def process(self, item_id: int) -> str:
        """处理一个项目。同一时间只有一个 process 在执行。"""
        self.current = item_id
        self.processed += 1
        time.sleep(0.1)  # 模拟 IO 操作
        return f"串行处理: item_{item_id}, 总共处理: {self.processed}"


@ray.remote(concurrency_groups={
    "io": 4,      # io 组允许 4 个并发调用
    "compute": 2, # compute 组允许 2 个并发调用
})
class ConcurrentProcessor:
    """
    并发处理器 —— 通过 concurrency_groups 允许不同的方法有不同的并发度。

    注意：若方法属于同一个并发组，共享该组的并发限制；
    若方法未指定并发组，默认使用 max_concurrency（如果设置了的话），否则串行。

    --- Flink 类比 ---
    Flink 中实现并发需要增加算子并行度（scale out），不能在一个算子实例内并发。
    Ray Actor 可以在单个实例内配置并发，这更适合 IO 密集型场景。
    """

    def __init__(self):
        self.results = {}

    @ray.method(concurrency_group="io")
    def io_task(self, task_id: int) -> str:
        """模拟 IO 密集型任务（如数据库查询），允许 4 个并发。"""
        time.sleep(random.uniform(0.1, 0.3))
        result = f"IO任务_{task_id}_完成"
        self.results[task_id] = result
        return result

    @ray.method(concurrency_group="compute")
    def cpu_task(self, task_id: int) -> str:
        """模拟 CPU 密集型任务，允许 2 个并发。"""
        total = sum(i * i for i in range(500_000))  # 一定量的计算
        result = f"CPU任务_{task_id}_完成"
        self.results[task_id] = result
        return result

    def get_results(self) -> dict:
        """获取所有结果。"""
        return dict(self.results)


# 实验：串行 vs 并发
print("\n📌 串行处理（Flink 默认模型）:")
serial = SerialProcessor.remote()
start = time.time()
refs = [serial.process.remote(i) for i in range(5)]
results_serial = ray.get(refs)
print(f"   结果: {results_serial}")
print(f"   总耗时: {time.time() - start:.2f}s (5 × 0.1s ≈ 0.5s)")

print("\n📌 并发处理（Ray Actor 特有）:")
concurrent = ConcurrentProcessor.remote()
start = time.time()
# io_task 允许 4 个并发，所以 5 个任务分成两批
io_refs = [concurrent.io_task.remote(i) for i in range(5)]
results_io = ray.get(io_refs)
print(f"   IO 任务结果: {results_io}")
print(f"   总耗时: {time.time() - start:.2f}s (4并发 + 1排队 ≈ 0.3~0.6s)")
print(f"   全部结果: {ray.get(concurrent.get_results.remote())}")


# ============================================================================
# 第三部分：Actor 的生命周期管理
# ============================================================================

print("\n" + "=" * 70)
print("  第三部分：Actor 生命周期 —— 创建、存活、销毁")
print("=" * 70)


@ray.remote
class LifecycleActor:
    """展示 Actor 完整生命周期的示例。"""

    def __init__(self, actor_id: str):
        self.actor_id = actor_id
        self.alive = True
        self.operation_count = 0
        print(f"  🟢 Actor {actor_id} 已创建")

    def do_work(self) -> str:
        self.operation_count += 1
        return f"Actor {self.actor_id}: 第 {self.operation_count} 次操作"

    def shutdown(self) -> None:
        """优雅关闭。"""
        self.alive = False
        print(f"  🔴 Actor {self.actor_id} 正在优雅关闭 (共 {self.operation_count} 次操作)")

    def __del__(self):
        """
        Actor 被销毁时的回调（Python 标准析构函数）。
        注意：Ray 没有类似 Flink RichFunction.close() 的内置终止回调，
        __del__ 的执行时机不确定，不应依赖它释放关键资源。
        生产环境中应该像上面的 shutdown() 方法一样，显式调用清理逻辑。
        """
        print(f"  💀 Actor {self.actor_id} 被 Python GC 回收 (PID={os.getpid()})")

    def check_health(self) -> bool:
        return self.alive


actor_a = LifecycleActor.remote("worker-A")
actor_b = LifecycleActor.remote("worker-B")

print("\n📌 Actor 正在运行:")
for i in range(3):
    print(f"  {ray.get(actor_a.do_work.remote())}")

print(f"\n  Actor A 健康检查: {ray.get(actor_a.check_health.remote())}")

# 主动销毁 Actor
ray.get(actor_a.shutdown.remote())

# ray.kill() 可以强制终止 Actor（类似 kill -9）
ray.kill(actor_b)  # 强制终止 Actor B

time.sleep(0.5)  # 等待清理完成
print("\n  两个 Actor 均已被销毁")

# --- Flink 类比 ---
# Actor 的 __init__  ≈ RichFunction.open()
# Actor 的方法调用  ≈ ProcessFunction.processElement()
# Actor 的 shutdown ≈ RichFunction.close() 或 手动触发清理
# ray.kill(actor)   ≈ 关闭 Flink 集群的某个 TaskManager


# ============================================================================
# 第四部分：Actor 作为 Flink KeyedState 的替代
# ============================================================================

# --- Flink 类比 ---
# 在 Flink 中实现"按用户聚合"：
#   stream.keyBy(e -> e.userId)
#         .process(new KeyedProcessFunction() {
#             ValueState<Long> totalSpend;
#             void processElement(Order order, Context ctx, Collector out) {
#                 Long current = totalSpend.value();
#                 totalSpend.update(current + order.amount);
#                 out.collect(new UserSpend(order.userId, totalSpend.value()));
#             }
#         });
#
# 在 Ray 中实现"按用户聚合"：
#   为每个用户创建一个 Actor，Actor 内部维护该用户的聚合状态。
#   区别：Flink 自动按 key 分区路由；Ray 需要你手动路由到对应的 Actor。

print("\n" + "=" * 70)
print("  第四部分：Actor 替代 KeyedState —— 按用户聚合")
print("=" * 70)


@ray.remote
class UserAggregator:
    """
    单个用户的聚合器 Actor。
    每个用户一个 Actor 实例，Actor 内部维护该用户的聚合状态。

    --- Flink 类比 ---
    这个 Actor 就像一个"keyed operator instance"，
    但并非自动由 keyBy 分区 —— 需要你手动将消息路由到正确的 Actor。
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.total_amount: float = 0.0
        self.order_count: int = 0
        self.recent_orders: deque = deque(maxlen=5)  # 只保留最近 5 条

    def add_order(self, order_id: str, amount: float) -> Dict:
        """
        处理一个新订单。

        和 Flink 的 processElement 一样，这个方法内可以：
        - 更新状态（self.total_amount）
        - 访问历史（self.recent_orders）
        - 输出结果（return value）
        """
        self.total_amount += amount
        self.order_count += 1
        self.recent_orders.append({"order_id": order_id, "amount": amount})

        # 检查是否触发"大客户"标记
        is_vip = self.total_amount > 1000.0

        return {
            "user_id": self.user_id,
            "order_id": order_id,
            "amount": amount,
            "total_spend": round(self.total_amount, 2),
            "order_count": self.order_count,
            "is_vip": is_vip,
        }

    def get_summary(self) -> Dict:
        """获取该用户的聚合摘要。"""
        return {
            "user_id": self.user_id,
            "total_spend": round(self.total_amount, 2),
            "order_count": self.order_count,
            "recent_orders": list(self.recent_orders),
        }


# 创建用户聚合器注册表（主进程中维护路由表）
user_actors: Dict[str, ray.actor.ActorHandle] = {}

def get_or_create_user_actor(user_id: str) -> ray.actor.ActorHandle:
    """
    获取或创建用户对应的 Actor。
    这相当于 Flink 的 keyBy 路由逻辑：相同的 user_id 路由到同一个 Actor。

    💡 这就是 Ray 和 Flink 的关键区别：
    Flink 的 keyBy 是隐式的、框架自动完成的；
    Ray 中你需要自己实现路由表（但这也给了你完全的控制权）。
    """
    if user_id not in user_actors:
        user_actors[user_id] = UserAggregator.remote(user_id)
    return user_actors[user_id]


# 模拟订单流：一批订单，按 user_id 路由到对应的 Aggregator
# --- Flink 类比 ---
# 这就相当于 DataStream<Order>.keyBy(Order::getUserId).process(UserAggregator)
orders = [
    ("U001", "order_01", 150.0),
    ("U002", "order_02", 200.0),
    ("U001", "order_03", 300.0),
    ("U003", "order_04", 500.0),
    ("U001", "order_05", 100.0),
    ("U002", "order_06", 900.0),  # U002 累计 1100 → 成为 VIP
    ("U001", "order_07", 500.0),  # U001 累计 1050 → 成为 VIP
    ("U003", "order_08", 200.0),
]

print("\n模拟订单流处理:\n")
result_refs = []
for user_id, order_id, amount in orders:
    actor = get_or_create_user_actor(user_id)
    ref = actor.add_order.remote(order_id, amount)
    result_refs.append(ref)

# 收集所有结果
results = ray.get(result_refs)
for r in results:
    vip_tag = "⭐VIP" if r["is_vip"] else "     "
    print(f"  [{r['user_id']}] {r['order_id']}: "
          f"¥{r['amount']:6.1f} → 累计 ¥{r['total_spend']:8.2f} {vip_tag}")

# 打印每个用户的最终汇总
print(f"\n{'='*50}")
print("各用户最终汇总:")
for user_id in sorted(user_actors.keys()):
    summary = ray.get(user_actors[user_id].get_summary.remote())
    print(f"  {summary}")


# ============================================================================
# 第五部分：Actor 之间的协作 —— 消息传递模式
# ============================================================================

# --- Flink 类比 ---
# Flink 中不同算子通过 DataStream 连接（connect/union/broadcast），
# 数据传输由框架管理，保证 exactly-once。
# Ray 中 Actor 之间通过直接调用对方的方法来通信，更灵活但没有传输保证。

print("\n" + "=" * 70)
print("  第五部分：Actor 协作 —— 分布式协调器模式")
print("=" * 70)


@ray.remote
class WorkerActor:
    """工作 Actor —— 执行具体的计算任务。"""

    def __init__(self, worker_id: int, coordinator_handle: ray.actor.ActorHandle):
        self.worker_id = worker_id
        self.coordinator = coordinator_handle  # 持有协调器的引用
        self.tasks_done = 0
        self.total_result = 0

    def compute(self, value: int) -> int:
        """执行计算并汇报给协调器。"""
        result = value ** 2
        self.tasks_done += 1
        self.total_result += result
        # Actor 调用另一个 Actor 的方法 —— 这就是 Actor 之间的消息传递
        # --- Flink 类比 ---
        # 类似 Flink 的 Side Output 或 外部服务调用，但 Ray 的 Actor 间调用
        # 是"原生"的，可以直接传 ObjectRef 和复杂 Python 对象
        self.coordinator.report_progress.remote(self.worker_id, result)
        return result

    def get_worker_stats(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "tasks_done": self.tasks_done,
            "total_result": self.total_result,
        }


@ray.remote
class CoordinatorActor:
    """协调器 Actor —— 收集 Worker 的进度，统一汇报。"""

    def __init__(self):
        self.progress: Dict[int, List[int]] = defaultdict(list)  # worker_id → results

    def report_progress(self, worker_id: int, result: int) -> None:
        """接收 Worker 的进度报告。"""
        self.progress[worker_id].append(result)

    def get_summary(self) -> Dict:
        """获取全局进度总结。"""
        summary = {}
        for wid, results in self.progress.items():
            summary[wid] = {
                "count": len(results),
                "total": sum(results),
                "values": results,
            }
        return summary


# 搭建协作系统
coordinator = CoordinatorActor.remote()
workers = [WorkerActor.remote(i, coordinator) for i in range(3)]

print(f"创建了 {len(workers)} 个 Worker + 1 个 Coordinator\n")

# 分发任务
task_refs = []
for i in range(10):
    worker_idx = i % len(workers)   # 轮询分配
    # Worker 执行计算后会自动汇报给 Coordinator
    task_refs.append(workers[worker_idx].compute.remote(i))

# 等待所有任务完成
ray.get(task_refs)

# 查看每个 Worker 的本地统计
print("Worker 本地统计:")
for w in workers:
    stats = ray.get(w.get_worker_stats.remote())
    print(f"  {stats}")

# 查看协调器的全局统计
print(f"\n协调器全局统计:")
global_summary = ray.get(coordinator.get_summary.remote())
for wid, data in sorted(global_summary.items()):
    print(f"  Worker {wid}: {data['count']} 个任务, 总结果={data['total']}, 值={data['values']}")


# ============================================================================
# 收尾
# ============================================================================

ray.shutdown()
print("\n✅ Ray 已关闭")


# ============================================================================
# 📝 面试问题自检
# ============================================================================

"""
Q9: Ray Actor 和 Flink 的 KeyedState 在状态管理上的核心区别是什么？
────────────────────────────────────────────────────────────────
A: 1. 分区机制：
      Flink: keyBy 自动根据 key 的 hash 分区，每个 key 有独立的 ValueState
      Ray Actor: 需要手动维护 Actor 路由表（如 Dict[str, ActorHandle]）
   2. 持久化：
      Flink: Checkpoint 机制自动将状态持久化到 RocksDB/HDFS
      Ray Actor: 状态只存在于 Actor 进程内存中，需要自行实现持久化
   3. 生命周期：
      Flink: KeyedState 随 key 的存在而存在，可由 TTL 清理
      Ray Actor: Actor 的生命周期由代码显式管理（创建/销毁）

Q10: Actor 的 max_concurrency 和 Flink 的 parallelism 有何不同？
─────────────────────────────────────────────────────────────
A: Flink 的 parallelism 是"横向扩展"——增加算子实例的数量，每个实例串行处理。
   增加 parallelism = 增加 Task Slot 占用 = 增加资源消耗。
   Actor 的 max_concurrency 是"纵向并发"——同一个 Actor 实例内部允许多个方法
   调用同时执行。这适用于 IO 密集型场景（如数据库查询），不增加 Actor 数量。
   但需要注意：多个并发调用会同时修改 self.xxx 属性，需要自行保证线程安全。

Q11: 在什么场景下应该使用 Ray Actor 而不是 Flink？
─────────────────────────────────────────────
A: 1. 需要"按用户/按实体"维护长生命周期状态，且状态结构复杂（不是简单的聚合值）
   2. 需要 Actor 之间直接通信（如分布式训练中的参数服务器模式）
   3. 工作负载以 RPC 风格的"请求-响应"为主，而非流式处理
   4. 需要动态创建/销毁计算单元（如在线推理中按模型版本动态管理模型实例）
   如果工作是标准的 ETL 流水线、实时聚合、窗口计算，Flink 更合适。

Q12: Actor 之间互相调用时有什么风险？
───────────────────────────────────
A: 1. 死锁风险：Actor A 等待 Actor B 的返回值，Actor B 同时等待 Actor A
   2. Actor 崩溃导致级联失败：一个 Actor 不可用会影响所有依赖它的 Actor
   3. 调试困难：调用链跨多个进程/节点，日志分散
   4. 解决思路：避免环形依赖、使用超时（ray.wait timeout）、添加健康检查机制
"""

print("\n" + "=" * 70)
print("  🎉 第二课完成！继续运行 03_resource_management.py 学习资源管理")
print("=" * 70)
