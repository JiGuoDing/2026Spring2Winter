"""
================================================================================
  Ray 学习项目 · 第零课：Hello Ray —— 分布式计算的"你好，世界"
================================================================================

  🎯 学习目标
  ─────────
  1. 理解 Ray 是什么、能解决什么问题
  2. 掌握 ray.init() 启动/连接集群
  3. 理解 @ray.remote 装饰器如何将普通函数变为远程任务
  4. 理解 ray.get() / ray.put() 与对象引用 ObjectRef 的关系
  5. 初步建立 Ray 与 Flink 核心概念的对应关系

  📖 核心类比地图（Flink → Ray）
  ──────────────────────────────
  ┌─────────────────────────┬─────────────────────────────────────┐
  │ Flink 概念               │ Ray 对应概念                         │
  ├─────────────────────────┼─────────────────────────────────────┤
  │ JobManager (主节点)      │ Ray Head Node / GCS (全局控制服务)    │
  │ TaskManager (工作节点)   │ Ray Worker Node / Raylet             │
  │ Task Slot (资源槽位)     │ CPU/GPU 资源 (逻辑资源，非物理槽位)    │
  │ MapFunction 在集群分布执行│ @ray.remote 修饰的函数 (remote task)  │
  │ Flink State Backend      │ Ray Object Store (共享内存/磁盘)      │
  │ DataStream.map()         │ [task.remote() for ...] + ray.get() │
  │ Checkpoint / Savepoint   │ Actor 内部手动状态管理               │
  └─────────────────────────┴─────────────────────────────────────┘

  ⚠️  关键差异速览
  ────────────────
  Flink: 流优先，有界/无界数据流，DAG 编译时确定，状态自动管理
  Ray:   任务优先，任意 Python 函数分布式执行，DAG 运行时动态构建，状态手动管理
"""

import ray
import time
import os


# ============================================================================
# 第一部分：启动 Ray
# ============================================================================

# --- Flink 类比 ---
# ray.init() 相当于启动一个 Flink 集群：
#   - Flink: ./bin/start-cluster.sh  →  启动 JobManager + TaskManager
#   - Ray:   ray.init()               →  启动本地 Ray 集群（Head + Worker）
# 在 Flink 中，你通过 flink run 提交作业；在 Ray 中，代码本身就是"作业"。
# Ray 的特殊之处在于：你可以在交互式环境（Jupyter/IPython）中直接写分布式代码，
# 不需要先打包 JAR 再 submit —— 这是 "Python-native distributed computing" 的理念。

print("=" * 70)
print("  第一部分：启动 Ray 集群")
print("=" * 70)

# ray.init() 初始化 Ray 运行时，关键参数：
#   - address="auto"  : 自动发现并连接已有集群（类似 Flink 的 -m yarn-cluster 指定地址）
#   - ignore_reinit_error=True : 避免重复初始化报错（适合 notebook 场景）
#   - num_cpus=N       : 限制 Ray 可使用的 CPU 核心数（类似 Flink 的 taskmanager.numberOfTaskSlots）
#
# 此处我们在本地启动一个单节点"集群"，方便学习。
# ray.init(
#     address="auto",           # 若有已有集群则连接，否则创建本地集群
#     ignore_reinit_error=True, # 重复调用不抛异常
#     # 下面两个参数仅在首次创建集群时生效：

#     # num_cpus=4,             # 限制使用 4 个 CPU（Flink 类比: taskmanager.numberOfTaskSlots=4）
#     # _temp_dir="/tmp/ray",   # 临时目录（日志、对象溢出文件）
# )
ray.init()

print(f"✅ Ray 已启动")
print(f"   Ray 版本: {ray.__version__}")
print(f"   集群节点数: {len(ray.nodes())}")
print(f"   可用资源: {ray.available_resources()}")
# 典型输出: {'CPU': 8.0, 'memory': 1.6e+10, 'node:__internal_head__': 1.0, 'object_store_memory': 7.9e+09}


# ============================================================================
# 第二部分：第一个远程函数 —— 分布式版的 def
# ============================================================================

# --- Flink 类比 ---
# 在 Flink 中，你定义一个 MapFunction 或 ProcessFunction，它会在 TaskManager 上执行。
# Ray 的 @ray.remote 装饰器把任何 Python 函数变成"远程任务" —— 就像把 MapFunction
# 发送到集群去执行。区别在于：
#   - Flink: 逻辑封装在 DataStream.map(MapFunction) 中，由框架调度
#   - Ray:   显式调用 func.remote()，由应用代码触发调度
# 这个差异决定了 Ray 的"灵活性"：任务可以动态创建、有条件执行、按需并行。

print("\n" + "=" * 70)
print("  第二部分：@ray.remote —— 把普通函数变成远程任务")
print("=" * 70)


# 步骤1：定义一个普通 Python 函数，然后加上 @ray.remote 装饰器
@ray.remote
def hello_ray(name: str, delay: float = 0.5) -> str:
    """
    一个最简单的 Ray 远程任务。

    参数:
        name:  要打招呼的名字
        delay: 模拟计算耗时（秒），体现分布式并行的意义
    返回:
        问候语字符串

    --- Flink 类比 ---
    这个函数就像一个 MapFunction<String, String>:
      public String map(String name) { return "你好, " + name; }

    区别在于：
    - Flink 中这个函数作为 DataStream 算子的回调被框架调用
    - Ray 中你主动调用 hello_ray.remote("张三") 来触发执行
    """
    # os.getpid() 可以证明这个函数运行在不同的进程中
    time.sleep(delay)  # 模拟一个耗时的操作
    return f"你好, {name}！(进程 ID: {os.getpid()})"


# 步骤2：调用远程函数
# .remote() 会立即返回一个 ObjectRef（对象引用），不会阻塞等待结果
# 类比：Flink 中你提交一个 job 后得到 JobID，而非直接拿到结果
result_ref: ray.ObjectRef = hello_ray.remote("张三", delay=0.3)

print(f"\n📦 .remote() 返回的类型: {type(result_ref)}")
# 输出: <class 'ray._raylet.ObjectRef'>
print(f"   ObjectRef（对象引用）长这样: {result_ref}")
# 输出: ObjectRef(xxx...) —— 这是一个分布式指针，指向集群中的计算结果


# 步骤3：用 ray.get() 取回结果
# ray.get() 会阻塞当前线程，直到远程任务完成
# 类比：Flink 的 collect() sink 或 REST API 查询 Job 结果
result: str = ray.get(result_ref)
print(f"\n📬 ray.get() 取回的结果: {result}")


# ============================================================================
# 第三部分：并行执行 —— Ray 的"分布式 for 循环"
# ============================================================================

# --- Flink 类比 ---
# Flink 中并行由 parallelism 参数控制：env.setParallelism(4)
# 所有算子自动按该并行度执行。Ray 中并行是"显式"的：
# 你创建 N 个 .remote() 调用，Ray 尽可能并行调度它们。

print("\n" + "=" * 70)
print("  第三部分：并行执行 —— 分布式 for 循环")
print("=" * 70)

names = ["Alice", "Bob", "Charlie", "Diana"]

# 方式 A: 串行执行（逐个等待）—— 你平时写 Python 的方式
print("\n🐢 串行执行:")
start = time.time()
for name in names:
    ref = hello_ray.remote(name, delay=0.3)
    print(f"  {ray.get(ref)}")  # 每次 ray.get() 都阻塞，失去并行性
print(f"  总耗时: {time.time() - start:.2f}s")

# 方式 B: 并行执行 —— Ray 的正确打开方式
# 先把所有任务"发射"出去（不等待），再统一收集结果
print("\n🚀 并行执行:")
start = time.time()
# 第一步：批量提交任务，拿到一组 ObjectRef
refs = [hello_ray.remote(name, delay=0.3) for name in names]
# 第二步：统一等待所有结果
results = ray.get(refs)  # ray.get() 接受一个 ObjectRef 列表
for r in results:
    print(f"  {r}")
print(f"  总耗时: {time.time() - start:.2f}s")

# 💡 如果一切正常，串行 ≈ 1.2s（4×0.3s），并行 ≈ 0.3s（4 个任务同时跑）
# 这就是 Ray 最核心的价值：用 for 循环的语法，获得分布式并行的能力。


# ============================================================================
# 第四部分：Object Store —— Ray 的共享内存
# ============================================================================

# --- Flink 类比 ---
# Flink 中，数据在算子之间通过 Network Buffer 传输（分区 shuffle、广播等）。
# 中间状态存储在 State Backend（RocksDB/内存）中。
#
# Ray 的 Object Store 是一个分布式共享内存层（基于 Apache Arrow/Plasma）：
#   - ray.put(obj)   → 把对象存入 Object Store，返回 ObjectRef
#   - ray.get(ref)   → 从 Object Store 取回对象
#   - 零拷贝共享    → 同一节点上的多个任务可以通过共享内存访问同一份数据
#
# 关键区别：
#   Flink 的算子间数据传输是"流式"的（边处理边传），
#   Ray 的 Object Store 是"快照式"的（先算完、存下来、再被下一个任务读取）。

print("\n" + "=" * 70)
print("  第四部分：Object Store —— 分布式共享内存")
print("=" * 70)

# ray.put() 将本地对象显式放入 Object Store
# 这在你想"预加载"一个大数据集供多个远程任务共享时非常有用
data = {"temperature": 25.6, "humidity": 0.65, "timestamp": "2026-05-15T10:00:00"}
data_ref: ray.ObjectRef = ray.put(data)
print(f"\n📤 ray.put() 将对象存入 Object Store")
print(f"   ObjectRef: {data_ref}")

# 远程任务可以直接接收 ObjectRef，Ray 会透明地处理数据传输
@ray.remote
def read_shared_data(shared_data_ref: ray.ObjectRef) -> dict:
    """从 Object Store 读取共享数据并做处理。"""
    # 注意：这里需要 ray.get() 来解引用，但这不会产生网络拷贝
    # 如果任务和被引用的对象在同一节点，共享内存直接访问（零拷贝）
    # ! 添加以下这句会报错，因为 shared_data_ref 已经被自动解引用为了真实 data 对象，而不再是 ObjectRef
    # data = ray.get(shared_data_ref)
    return {
        "processor": os.getpid(),
        "original": shared_data_ref,
        "heat_index": shared_data_ref["temperature"] * shared_data_ref["humidity"],  # 一个假的计算
        "type": type(shared_data_ref), # 查看 shared_data_ref 的类型
        # ! 发现输出为 dict，说明 shared_data_ref 被自动解引用为真实 data 对象了
    }

# ! Ray 会自动把传给远程函数的 ObjectRef 解引用，例如这里的 data_ref 传给远程函数 read_shared_data 时，会自动将 data_ref 解引用为真实 data 对象
# ! 也就是说 read_shared_data(data_ref) 收到的的不是 ObjectRef，而是 data_ref 指向的真实对象
result2 = ray.get(read_shared_data.remote(data_ref))
print(f"   ✅ 远程任务从 Object Store 读取到数据: {result2}")


# ============================================================================
# 第五部分：任务间依赖 —— 构建分布式 DAG
# ============================================================================

# --- Flink 类比 ---
# Flink 中 DAG 在编译时确定：source → map → keyBy → window → sink
# Ray 中 DAG 是运行时动态构建的：你把一个 ObjectRef 传给另一个 .remote() 调用即可
#
# 这带来一个巨大优势：DAG 结构可以根据数据内容动态决定。
# 代价是：你失去了 Flink 的优化器（如算子链、状态 TTL 自动管理）。

print("\n" + "=" * 70)
print("  第五部分：任务依赖 —— 动态构建 DAG")
print("=" * 70)


@ray.remote
def fetch_raw_logs(source: str) -> list[str]:
    """阶段1：模拟从某个数据源获取原始日志。"""
    print(f"  [阶段1] 从 {source} 拉取日志... (进程 {os.getpid()})")
    time.sleep(0.2)
    return [
        f"[{source}] INFO  user_login  user_id=001",
        f"[{source}] WARN  high_cpu     usage=92%",
        f"[{source}] ERROR db_timeout   retry=3",
    ]


@ray.remote
def parse_logs(raw_logs_ref: ray.ObjectRef) -> list[dict]:
    """阶段2：解析日志，提取结构化字段。
    它接收阶段1的 ObjectRef，Ray 自动建立依赖关系。
    """
    # raw_logs = ray.get(raw_logs_ref)  # 等待阶段1完成
    print(f"  [阶段2] 解析 {len(raw_logs_ref)} 条日志... (进程 {os.getpid()})")
    parsed = []
    for log in raw_logs_ref:
        parts = log.split()
        parsed.append({
            "source":  parts[0].strip("[]"),
            "level":   parts[1],
            "message": parts[2],
            "detail":  " ".join(parts[3:]),
        })
    return parsed


@ray.remote
def generate_report(parsed_logs_ref: ray.ObjectRef) -> str:
    """阶段3：根据解析结果生成报告。"""
    # logs = ray.get(parsed_logs_ref)
    print(f"  [阶段3] 生成报告，共 {len(parsed_logs_ref)} 条... (进程 {os.getpid()})")
    levels = {}
    for log in parsed_logs_ref:
        levels[log["level"]] = levels.get(log["level"], 0) + 1
    return f"📊 报告: 日志总数={len(parsed_logs_ref)}, 级别分布={levels}"


# 构建 DAG（通过传递 ObjectRef 隐式建立依赖）
print("\n构建任务 DAG:")
# 返回一个指向字符串列表的 ObjectRef
raw_ref   = fetch_raw_logs.remote("app-server-01")     # 阶段1
# 返回一个指向字典列表的 ObjectRef
parsed_ref = parse_logs.remote(raw_ref)                  # 阶段2 ← 依赖阶段1
# 返回一个指向字符串的 ObjectRef
report    = ray.get(generate_report.remote(parsed_ref))  # 阶段3 ← 依赖阶段2
print(f"\n{report}")


# ============================================================================
# 第六部分：ray.wait() —— 非阻塞等待
# ============================================================================

# --- Flink 类比 ---
# Flink 中你一般不会"等待某个特定任务完成" —— 框架替你管理所有数据流的生命周期。
# Ray 中因为是手动调度，你经常需要"等最快完成的几个任务"，这很像 Java 的
# CompletableFuture.anyOf() 或 Future.get(timeout)。
# ray.wait() 用于：我有 N 个任务在跑，我想先处理最快完成的那个。

print("\n" + "=" * 70)
print("  第六部分：ray.wait() —— 非阻塞等待")
print("=" * 70)


@ray.remote
def slow_computation(x: int, delay: float) -> int:
    """耗时不等的计算任务。"""
    time.sleep(delay)
    return x * x

# 启动 5 个耗时不同的任务
refs = [slow_computation.remote(i, delay=0.1 + i * 0.1) for i in range(5)]
print(f"启动 {len(refs)} 个任务，耗时分别为 0.1s ~ 0.5s")

# ray.wait() 返回一个元组: (done_refs, pending_refs)
# num_returns=1 表示"只要有一个完成就返回"
done, pending = ray.wait(refs, num_returns=1, timeout=None)
print(f"🏁 第一个完成的任务结果: {ray.get(done[0])}")
print(f"   还有 {len(pending)} 个任务未完成")

# 等待剩余任务
remaining_results = ray.get(list(pending))
print(f"   剩余结果: {remaining_results}")


# ============================================================================
# 第七部分：关闭 Ray
# ============================================================================

# 在本地开发环境中，建议显式 shutdown 释放资源
# 在长期运行的服务中，通常不需要 shutdown
print("\n" + "=" * 70)
print("  第七部分：关闭 Ray")
print("=" * 70)

ray.shutdown()
print("✅ Ray 已关闭")


# ============================================================================
# 📝 面试问题自检
# ============================================================================

"""
Q1: Ray 的 @ray.remote 和 Flink 的 DataStream.map() 有什么本质区别？
──────────────────────────────────────────────────────────────────────
A: 两者都可以实现分布式执行用户逻辑，但核心差异在于：
   1. 调度模型：Flink 是"声明式"的 —— 你定义 DAG，框架编译后自动调度；
      Ray 是"命令式"的 —— 你用 .remote() 显式调用，运行时动态构建 DAG。
   2. 状态管理：Flink 的 map 在 KeyedStream 中自动享有状态后端；
      Ray 的 remote task 是无状态的，状态需要你自己管理（或用 Actor）。
   3. 容错机制：Flink 通过 checkpoint 自动恢复；Ray 默认没有自动容错，
      任务失败需要你手动重试（或在任务中实现幂等性）。

Q2: ray.put() 和 ray.get() 分别在什么场景下使用？
──────────────────────────────────────────────────────
A: ray.put(obj) 用于将一个大型对象提前放入 Object Store，使得
   多个后续远程任务可以零拷贝地共享这份数据（类似 Flink 的 Broadcast 变量）。
   ray.get(ref) 用于从 Object Store 取回计算结果，会阻塞直到结果就绪。
   注意：如果 ref 指向的对象在远程节点，ray.get() 会触发网络传输。

Q3: Ray 的 Object Store 和 Flink 的 State Backend 有何不同？
───────────────────────────────────────────────────────
A: Object Store 是共享内存/磁盘层，用于在任务之间传递中间结果（类似中间数据的
   缓存层）。Flink 的 State Backend 是持久化状态存储，用于存 Window 状态、
   KeyedState 等。前者是"无 schema 的数据快照"，后者是"有 schema 的状态表"。
   前者更适合无状态计算的中间结果共享，后者更适合有状态流处理。

Q4: ray.wait() 的实际应用场景是什么？
───────────────────────────────────────
A: 典型的"投机执行"（speculative execution）：启动多个相同任务（或不同策略），
   取最快完成的那个。也可以用于实现超时控制、渐进式结果收集等。
   这在 Flink 中不容易做到，因为 Flink 的 DAG 是预编译的，没有这种动态能力。
"""

print("\n" + "=" * 70)
print("  🎉 第零课完成！继续运行 01_remote_tasks.py 学习远程任务与 DAG")
print("=" * 70)
