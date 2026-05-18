"""
================================================================================
  Ray 学习项目 · 第三课：资源管理与调度策略
================================================================================

  🎯 学习目标
  ─────────
  1. 理解 Ray 的资源模型：CPU/GPU/自定义资源
  2. 掌握资源指定语法：num_cpus / num_gpus / resources={}
  3. 理解 Placement Group（放置组）—— 类似 Flink SlotSharingGroup
  4. 掌握调度策略：SPREAD / STRICT_SPREAD / PACK / STRICT_PACK
  5. 对比 Flink Slot 模型与 Ray 资源模型的设计哲学

  📖 Flink → Ray 资源模型深度对比
  ──────────────────────────────────
  ┌─────────────────────────────────┬───────────────────────────────────────┐
  │ Flink 资源模型                   │ Ray 资源模型                            │
  ├─────────────────────────────────┼───────────────────────────────────────┤
  │ TaskSlot: 固定大小的资源容器      │ 逻辑资源: CPU/GPU 是"软限制"，可超分     │
  │ 每个 slot 独占内存               │ 内存非抢占式，对象溢出到磁盘              │
  │ SlotSharingGroup: 多个算子共享    │ Placement Group: 预留资源包              │
  │ 资源预分配 (slot 启动时分配)      │ 资源按需调度 (任务到来时动态分配)          │
  │ 确定性调度 (编译时确定)           │ 动态调度 (运行时按可用资源决定)            │
  │ Co-location 通过 slot 共享实现    │ Placement Group 精确控制共置/反共置       │
  └─────────────────────────────────┴───────────────────────────────────────┘

  🔑 关键差异
  ─────────────
  Flink 的 slot 是物理隔离的资源容器（JVM 进程内线程），slot 之间资源独立。
  Ray 的 CPU 是逻辑配额（logical resource），任务可以超额申请，调度器尽力满足。
  这意味着 Ray 更灵活但资源隔离更弱，Flink 更稳定但资源利用率可能更低。
"""

import ray
import time
import os
import math
from typing import List, Dict


# ============================================================================
# 第一部分：资源请求基础 —— num_cpus / num_gpus
# ============================================================================

print("=" * 70)
print("  第一部分：为任务/Actor 指定资源需求")
print("=" * 70)

ray.init()

print(f"\n集群可用资源: {ray.available_resources()}")
# 输出示例: {'CPU': 8.0, 'memory': 1.6e+10, 'object_store_memory': 7.9e+09}


# --- 远程任务指定资源 ---
# num_cpus 参数指定该任务所需的 CPU 数量（默认 = 1）
# 这是一个"逻辑配额"，Ray 调度器用它做资源记账，不会真的 pin 住物理 CPU
# --- Flink 类比 ---
# num_cpus 类似 Flink 中每个算子的"资源请求"，但 Flink 的资源是通过 slot 粒度来分配的，
# slot 数是固定的整数，而 Ray 的 CPU 资源可以是小数（如 num_cpus=0.5）

@ray.remote(num_cpus=2)  # 这个任务需要 2 个 CPU（逻辑配额）
def heavy_computation(data_size: int) -> float:
    """需要较多 CPU 资源的计算任务。"""
    # 模拟 CPU 密集型计算
    result = 0.0
    for i in range(data_size):
        result += math.sqrt(i + 1) * math.sin(i * 0.001)
    return result


@ray.remote(num_cpus=0.1)  # 只需 0.1 CPU —— 适合轻量级 IO 任务
def light_io_task(task_id: int) -> str:
    """轻量级 IO 任务，几乎不消耗 CPU。"""
    import random
    time.sleep(random.uniform(0.05, 0.15))  # 模拟 IO 等待
    return f"light_task_{task_id}_done"


# 当 heavy_computation 请求 num_cpus=2 时，如果你只有 8 个 CPU，
# 最多同时运行 4 个 heavy_computation 实例。
# 但 light_io_task (num_cpus=0.1) 可以同时跑 80 个，极大提升资源利用率。
# 这就是 Ray 资源模型灵活性的体现 —— Flink 的 slot 模型做不到这种粒度。

print("\n📌 资源需求对比:")
print("   heavy_computation: num_cpus=2 (最多同时 4 个，假设 8 CPU)")
print("   light_io_task:     num_cpus=0.1 (最多同时 80 个)")

# 提交任务
heavy_refs = [heavy_computation.remote(100_000) for _ in range(4)]
light_refs = [light_io_task.remote(i) for i in range(5)]

heavy_results = ray.get(heavy_refs)
light_results = ray.get(light_refs)
print(f"\n   重任务完成: {len(heavy_results)} 个")
print(f"   轻任务完成: {len(light_results)} 个")


# ============================================================================
# 第二部分：自定义资源 —— 模拟 GPU/FPGA/数据库连接
# ============================================================================

# --- Flink 类比 ---
# Flink 中无法自定义资源类型（只有 slot 内存和 CPU），但可以通过 ExternalResource
# 框架来管理 GPU 等特殊资源。Ray 允许你定义任意命名的逻辑资源。
#
# ⚠️ 自定义资源需要在 ray.init() 时预先声明，否则任务会因找不到资源而永远挂起。
# 正确的启动方式：
#   ray.init(resources={"db_connections": 3})  # 声明集群有 3 个"数据库连接"资源
#
# 下面我们用一个安全的替代方案来演示自定义资源的概念：
# 使用 num_cpus=0.5 配合注释说明，模拟"资源类型化"的效果。

print("\n" + "=" * 70)
print("  第二部分：自定义资源类型")
print("=" * 70)

# 演示：声明一个标记了特殊资源需求的任务
# 在生产环境中，你可以这样定义需要 GPU 或其他自定义资源的任务：
#
#   @ray.remote(num_gpus=1)
#   def train_model(data): ...
#
#   @ray.remote(resources={"db_connections": 1})
#   def query_database(query_id): ...
#
# 其中 resources={"db_connections": 1} 需要在 ray.init() 中预先声明：
#   ray.init(resources={"db_connections": 3})
# 这样调度器就会确保同时最多运行 3 个 query_database 任务。

# 安全演示：用 num_cpus=0.5 模拟"数据库连接池"的限流效果
@ray.remote(num_cpus=0.5)
def query_database(query_id: int) -> dict:
    """
    模拟数据库查询任务。
    使用 num_cpus=0.5 作为"逻辑资源配额"，效果类似 Flink 中 AsyncFunction
    的信号量控制，但由 Ray 调度器集中管理。
    """
    time.sleep(0.2)  # 模拟查询延迟
    return {
        "query_id": query_id,
        "result": f"data_for_query_{query_id}",
        "pid": os.getpid(),
    }


# 提交 8 个查询任务，每个 num_cpus=0.5，如果总 CPU=8，最多同时 16 个
# 这模拟了"自定义资源限流"的效果 —— 用 CPU 配额来间接控制并发数
print("\n📌 数据库查询任务（用 num_cpus=0.5 模拟限流）:")
start = time.time()
db_refs = [query_database.remote(i) for i in range(8)]
db_results = ray.get(db_refs)
for r in db_results:
    print(f"   {r}")
print(f"   总耗时: {time.time() - start:.2f}s")
print(f"\n💡 技巧: 自定义资源需要在 ray.init(resources={{...}}) 中预先声明。")
print(f"   如果你有真正的自定义资源需求（如 GPU），请使用:")
print(f"   ray.init(resources={{'db_connections': 3}})  # 预先声明")

# ============================================================================
# 第三部分：Placement Group —— 资源预留与共置
# ============================================================================

# --- Flink 类比 ---
# Placement Group 类似于 Flink 的 SlotSharingGroup + CoLocationGroup：
# - SlotSharingGroup: 多个算子共享同一个 slot（共置在同一 JVM 中）
# - CoLocationGroup: 强制某些并行实例部署在同一 TaskManager 上
#
# Ray 的 Placement Group 提供了更精细的控制：
# - 预留资源包（bundle），多任务共享这些资源
# - 控制 bundle 的部署策略（SPREAD/PACK/STRICT_SPREAD/STRICT_PACK）

print("\n" + "=" * 70)
print("  第三部分：Placement Group —— 资源预留与任务共置")
print("=" * 70)

from ray.util.placement_group import (
    placement_group,
    placement_group_table,
    remove_placement_group,
)
from ray.util.scheduling_strategies import PlacementGroupSchedulingStrategy


# 创建一个 Placement Group:
# - bundles: [{"CPU": 2}, {"CPU": 2}]  两个资源包，每个 2 CPU
# - strategy: "PACK" 表示尽量把两个 bundle 放在同一个节点上（最小化网络延迟）
#   SPREAD 则尽量分散到不同节点（提高容错）
#   STRICT_PACK 强制所有 bundle 在同一节点
#   STRICT_SPREAD 强制每个 bundle 在不同节点
pg = placement_group([{"CPU": 2}, {"CPU": 2}], strategy="PACK")

# 等待资源就绪（类似 Flink 中等待 slot 分配完成）
ray.get(pg.ready())
print(f"\n📦 Placement Group 已就绪:")
print(f"   状态: {pg.bundle_specs}")
print(f"   {placement_group_table(pg)}")


@ray.remote(num_cpus=2)
def compute_in_group(task_id: int, sleep_s: float) -> str:
    """在 Placement Group 预留的资源中运行的任务。"""
    time.sleep(sleep_s)
    return f"PG任务_{task_id}_完成 (节点={ray.get_runtime_context().node_id.hex()[:8]})"


# 使用 PlacementGroupSchedulingStrategy 将任务调度到预留资源上
# --- Flink 类比 ---
# 这就相当于将多个算子放入同一个 SlotSharingGroup，
# 确保它们共享（靠近）同一组资源
strategy = PlacementGroupSchedulingStrategy(
    placement_group=pg,
    placement_group_bundle_index=0,  # 使用第 0 个 bundle
)

print("\n📌 使用 Placement Group 调度任务:")
refs = []
for i in range(3):
    # 通过 scheduling_strategy 将任务绑定到指定的 Placement Group
    refs.append(compute_in_group.options(
        scheduling_strategy=strategy
    ).remote(i, 0.2))

results_pg = ray.get(refs)
for r in results_pg:
    print(f"   {r}")

# 清理 Placement Group
remove_placement_group(pg)
print("\n   Placement Group 已清理")


# ============================================================================
# 第四部分：Actor 资源绑定与 GPU 示例
# ============================================================================

print("\n" + "=" * 70)
print("  第四部分：Actor 资源绑定 —— 模拟 GPU 推理服务")
print("=" * 70)


# --- Flink 类比 ---
# Flink 中如果想使用 GPU 做推理，通常需要 ML 模型作为外部服务部署，
# Flink 算子通过 AsyncIO 调用该服务。这种做法引入网络开销。
# Ray 允许 Actor 直接绑定 GPU 资源，将模型加载到 Actor 内，实现零网络延迟的在线推理。

@ray.remote(num_gpus=0)  # 设为 0 因为我们没有真实 GPU，用 CPU 模拟
class ModelInferenceService:
    """
    模拟一个模型推理服务 Actor。
    在真实场景中，num_gpus=1 会将此 Actor 调度到有 GPU 的节点。
    """

    def __init__(self, model_name: str):
        # 模拟模型加载（在真实场景中，这里用 GPU 显存加载模型权重）
        self.model_name = model_name
        self.call_count = 0
        print(f"  🤖 模型 '{model_name}' 已加载 (PID={os.getpid()})")
        # 模拟 GPU 显存预热
        time.sleep(0.3)

    def predict(self, input_data: str) -> dict:
        """执行推理。"""
        self.call_count += 1
        # 模拟推理耗时
        time.sleep(0.05)
        return {
            "model": self.model_name,
            "input": input_data,
            "prediction": f"result_for_{input_data}",
            "call_number": self.call_count,
        }

    def get_stats(self) -> dict:
        return {
            "model": self.model_name,
            "total_calls": self.call_count,
            "worker_pid": os.getpid(),
        }


# 创建两个推理服务实例（在真实场景中各自绑定到不同 GPU）
model_a = ModelInferenceService.options(num_cpus=1).remote("bert-base")
model_b = ModelInferenceService.options(num_cpus=1).remote("gpt-neo")

# 模拟推理请求分发
print("\n📌 模型推理请求:")
inputs = ["今天天气真好", "人工智能改变世界", "分布式计算很有趣"]
for text in inputs:
    # 轮询分配请求到两个模型实例
    chosen = model_a if len(text) % 2 == 0 else model_b
    result = ray.get(chosen.predict.remote(text))
    print(f"   {result}")

print(f"\n   模型统计:")
print(f"   {ray.get(model_a.get_stats.remote())}")
print(f"   {ray.get(model_b.get_stats.remote())}")


# ============================================================================
# 第五部分：资源模型对比 —— Ray vs Flink Slot
# ============================================================================

print("\n" + "=" * 70)
print("  第五部分：Ray 资源模型 vs Flink Slot 模型")
print("=" * 70)

print("""
  ┌─── Flink Slot 模型 ─────────────────────────────────┐
  │                                                       │
  │  TaskManager (JVM)                                    │
  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
  │  │ Slot 0  │ │ Slot 1  │ │ Slot 2  │ │ Slot 3  │    │
  │  │ ┌─────┐ │ │ ┌─────┐ │ │ ┌─────┐ │ │ ┌─────┐ │    │
  │  │ │map()│ │ │ │map()│ │ │ │map()│ │ │ │map()│ │    │
  │  │ │keyBy│ │ │ │keyBy│ │ │ │keyBy│ │ │ │keyBy│ │    │
  │  │ │sink │ │ │ │sink │ │ │ │sink │ │ │ │sink │ │    │
  │  │ └─────┘ │ │ └─────┘ │ │ └─────┘ │ │ └─────┘ │    │
  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
  │                                                       │
  │  特点:                                                │
  │  ✓ 物理资源隔离 (每个 slot 独立内存空间)                │
  │  ✓ 资源确定性强 (slot 数 × 内存 = 固定资源消耗)        │
  │  ✗ 灵活性差 (slot 粒度粗，slot 数固定)                 │
  │  ✗ 资源利用率受 slot 粒度限制                          │
  └───────────────────────────────────────────────────────┘

  ┌─── Ray 逻辑资源模型 ─────────────────────────────────┐
  │                                                       │
  │  Worker Node                                          │
  │  ┌──────────────────────────────────────────────┐    │
  │  │  可用资源: CPU=8.0, memory=16GB               │    │
  │  │  ┌─────┐┌─────┐┌───┐┌───┐┌───┐┌───┐┌───┐  │    │
  │  │  │T 2CP││T 1CP││T.5││T.5││T 1 ││T 1 ││T.1│  │    │
  │  │  │  U  ││  U  ││CPU││CPU││CPU ││CPU ││CPU │  │    │
  │  │  └─────┘└─────┘└───┘└───┘└───┘└───┘└───┘  │    │
  │  └──────────────────────────────────────────────┘    │
  │                                                       │
  │  特点:                                                │
  │  ✓ 灵活粒度 (CPU 可小数: 0.1, 0.5, 2.0)               │
  │  ✓ 资源超分 (可提交超过物理 CPU 数 3-5 倍的任务)       │
  │  ✓ 支持自定义资源 (GPU, FPGA, 虚拟资源)                │
  │  ✗ 弱隔离 (无内存隔离，任务共享进程)                    │
  │  ✗ 可能资源竞争 (CPU 超分时存在争抢)                    │
  └───────────────────────────────────────────────────────┘
""")


# ============================================================================
# 第六部分：实战 —— 资源感知的分布式排序
# ============================================================================

print("=" * 70)
print("  第六部分：实战 —— 不同资源策略的对比实验")
print("=" * 70)


@ray.remote(num_cpus=2)
def sort_large_chunk(chunk_id: int, size: int) -> dict:
    """
    模拟一个大块的排序任务（需要 2 CPU）。
    如果只给 1 CPU 会很慢，给 2 CPU 可以利用多线程/multiprocessing 加速。
    """
    import random as rnd
    data = [rnd.random() for _ in range(size)]
    start = time.time()
    sorted_data = sorted(data)  # Python 的 sorted 是单线程的，这里模拟 CPU 工作
    elapsed = time.time() - start
    return {
        "chunk_id": chunk_id,
        "size": size,
        "sorted_first": sorted_data[0],
        "time_s": round(elapsed, 4),
        "pid": os.getpid(),
    }


# 不同资源策略的对比
stages = [
    ("少量大任务 (CPU=2)", [sort_large_chunk.remote(i, 200_000) for i in range(4)]),
    ("大量小任务 (CPU=2)", [sort_large_chunk.remote(i, 50_000) for i in range(16)]),
]

for name, refs in stages:
    print(f"\n📌 {name}:")
    start = time.time()
    results = ray.get(refs)
    print(f"   耗时: {time.time() - start:.3f}s, 进程数: {len(set(r['pid'] for r in results))}")
    for r in results:
        print(f"     chunk_{r['chunk_id']:2d}: {r['size']} 条, {r['time_s']}s")


# ============================================================================
# 第七部分：调度策略 —— NodeAffinitySchedulingStrategy
# ============================================================================

print("\n" + "=" * 70)
print("  第七部分：调度策略 —— 节点亲和性")
print("=" * 70)


# 获取当前所有节点信息
nodes = ray.nodes()
print(f"\n集群节点:")
for node in nodes:
    print(f"  NodeID={node['NodeID'][:8]}..., "
          f"Alive={node['Alive']}, "
          f"Resources={node.get('Resources', {})}")

# NodeAffinitySchedulingStrategy: 将任务调度到特定节点
# 适用场景：数据本地性（数据在某个节点上）、许可证绑定节点、硬件特性

# 获取 head node 的 ID
head_node_id = None
for node in nodes:
    if node['Alive']:
        head_node_id = node['NodeID']
        break

if head_node_id and len(nodes) > 0:
    from ray.util.scheduling_strategies import NodeAffinitySchedulingStrategy

    @ray.remote
    def pinned_task(task_name: str) -> str:
        return (f"任务 '{task_name}' 运行在节点: "
                f"{ray.get_runtime_context().node_id.hex()[:8]}")

    # 显式绑定到特定节点（软亲和性：prefer 但允许调度到其他节点）
    # 硬亲和性用 Placement Group 的 STRICT_PACK
    affinity = NodeAffinitySchedulingStrategy(
        node_id=head_node_id,
        soft=True,  # True=尽量调度到此节点，False=必须调度到此节点
    )

    ref = pinned_task.options(scheduling_strategy=affinity).remote("节点绑定测试")
    print(f"\n📌 节点亲和性调度: {ray.get(ref)}")


# ============================================================================
# 收尾
# ============================================================================

ray.shutdown()
print("\n✅ Ray 已关闭")


# ============================================================================
# 📝 面试问题自检
# ============================================================================

"""
Q13: Ray 的 num_cpus 和 Flink 的 TaskSlot 有什么本质区别？
───────────────────────────────────────────────────────
A: Flink 的 TaskSlot 是 JVM 内的物理资源容器，slot 独占分配的内存，
   一个 slot 挂了不影响其他 slot。slot 数量在启动时固定。
   Ray 的 num_cpus 是逻辑配额（logical resource），用于调度决策，
   不会真的"分配"CPU 线程。任务可以超额提交（>物理 CPU 数），
   调度器尽力满足但不保证不出现资源竞争。这类似 Kubernetes 的 CPU request vs limit。

Q14: 什么场景下应该使用 Placement Group？
────────────────────────────────────────
A: 1. 多个任务需要共置在同一节点上（大数据传输，避免网络开销）
   2. 需要保证资源预留（类似 Flink 的 slot 预分配，确保关键任务有资源）
   3. 分布式训练中 driver-worker 之间的低延迟通信
   4. 多阶段流水线，需要前后阶段共享内存（同一个 PG 的 bundle 共享节点）
   类比 Flink 的 SlotSharingGroup，但 Placement Group 可以做更精细的控制。

Q15: 如果 Ray 集群只有 8 个 CPU，你提交了 100 个 num_cpus=1 的任务会怎样？
──────────────────────────────────────────────────────────────────────
A: 不会报错，不会丢任务。Ray 调度器会将任务排队，每次选择 8 个执行，
   完成的释放 CPU 后，未开始的才会被调度。这叫做"逻辑资源记账"，
   而不是"物理资源分配"。如果所有任务都设置了 num_cpus=0.1，
   理论上可以同时执行 80 个。但要注意：如果任务实际消耗远超声明的 CPU，
   会造成资源争抢（thrashing），影响所有任务的执行效率。
   优秀实践：CPU 密集型设 num_cpus=1，IO 密集型设 num_cpus=0.1~0.5。

Q16: Flink 的 Slot 和 Ray 的 Placement Group 在资源利用率上有何差异？
─────────────────────────────────────────────────────────────────
A: Flink Slot 模型：如果一个 slot 内的某个算子很闲、另一个很忙，
   该 slot 的整体资源不能被其他 Job 利用 —— "slot 碎片化"问题。
   Ray PG 模型：bundle 内的资源是逻辑的，PG 外的任务仍可调度到同一节点
   的剩余资源上 —— 更灵活但弱隔离。
   选择：对资源隔离要求高（如生产环境 SLA）选 Flink/Strict PG；
   对资源利用率要求高（如开发/实验环境）选 Ray 默认调度。
"""

print("\n" + "=" * 70)
print("  🎉 第三课完成！继续运行 04_data_pipeline.py 学习完整流水线")
print("=" * 70)
