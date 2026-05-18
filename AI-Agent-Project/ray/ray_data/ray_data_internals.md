# Ray Data 底层运行机制百科全书

> 本文档由浅入深讲解 Ray Data 的内部架构、执行引擎、内存管理、Shuffle 机制、容错原理等底层细节，并附带面试深度题。
>
> 对应项目：`ray-data-learning/`（示例代码见 `examples/` 和 `projects/`）

---

# Part 1：底层运行逻辑与机制

---

## 第1章：Ray Data 全景概览

### 1.1 Ray Data 在 Ray 生态中的位置

Ray 是一个统一的分布式计算框架，其核心组件包括：

```
Ray 生态
├── Ray Core          — 分布式 Task / Actor / Object Store 基础设施
├── Ray Data          — 分布式数据处理（本文重点）
├── Ray Train         — 分布式模型训练
├── Ray Serve         — 模型在线服务
├── Ray Tune          — 超参数调优
└── Ray Cluster       — 多节点集群管理与自动伸缩
```

Ray Data 构建在 Ray Core 之上，直接使用 Ray 的 Task、Actor、Object Store 等原语来实现分布式数据处理。它不是一个独立的计算引擎，而是 Ray Core 的上层应用。

### 1.2 Ray Data 的设计目标

1. **为 ML 工作流原生设计**：与 Ray Train/Serve 无缝集成，支持流式数据消费
2. **统一批处理与推理**：一套 API 同时支持 ETL、特征工程、批量推理
3. **流式执行**：默认流式处理，避免全量物化带来的内存压力
4. **GPU 原生支持**：一等公民的 GPU 资源管理

### 1.3 核心抽象

| 抽象 | 说明 |
|------|------|
| **Dataset** | 分布式数据集，用户面对的主要接口。惰性构建执行计划 |
| **Block** | 数据分区单元，`Union[pyarrow.Table, pandas.DataFrame]` |
| **RefBundle** | Block 引用的打包，包含 `List[Tuple[ObjectRef, BlockMetadata]]` |
| **LogicalOperator** | 逻辑执行计划节点（ReadOp, MapBatches, Filter, Sort...） |
| **PhysicalOperator** | 物理执行算子，实际调度 Task/Actor 处理数据 |
| **StreamingExecutor** | 流式执行引擎，驱动整个 Operator 拓扑的运行 |

---

## 第2章：Dataset 的内部表示

### 2.1 Dataset 对象结构

`Dataset` 对象本身只存在于 **driver 进程**（用户脚本所在的进程），它不持有实际数据。其核心字段包括：

```python
class Dataset:
    _plan: LogicalPlan          # 逻辑执行计划
    _logical_plan: LogicalPlan  # 同上（历史命名）
    _current_executor: Executor # 当前执行器（StreamingExecutor）
    _current_lazy_execution: bool
```

关键认知：**Dataset 是一个惰性的计划容器，不是数据容器。** 实际数据以 Block 的形式分布在集群各节点的 Object Store 中。

### 2.2 Block：数据的实际载体

Block 是 Ray Data 的最小数据单元，类型定义为：

```python
Block = Union[pyarrow.Table, pandas.DataFrame]
```

`BlockType` 枚举只有两个值：`ARROW` 和 `PANDAS`。

#### 为什么有两种 Block 类型？

- **PyArrow Table**：列式存储，内存效率高，支持零拷贝切片，是默认和推荐的内部格式
- **Pandas DataFrame**：用户更熟悉，某些操作（如复杂 groupby）更方便

转换路径：
- `batch_to_block()` 是入口函数
- cuDF DataFrame → 调用 `.to_arrow(preserve_index=False)` 转为 Arrow（GPU→CPU 高效传输）
- Pandas DataFrame → 根据 `DataContext.batch_to_block_arrow_format` 决定保留还是转 Arrow
- Dict → 先尝试 Arrow，失败回退 Pandas

### 2.3 BlockAccessor 设计模式

Ray Data 使用 `BlockAccessor` 模式来统一操作两种 Block 类型：

```python
class BlockAccessor:
    @staticmethod
    def for_block(block: Block) -> "BlockAccessor":
        if isinstance(block, pa.Table) or isinstance(block, pa.RecordBatch):
            return ArrowBlockAccessor(block)
        elif isinstance(block, pd.DataFrame):
            return PandasBlockAccessor(block)
        else:
            raise ValueError(f"Unknown block type: {type(block)}")
```

这个设计存在的原因是：**希望将 `pyarrow.Table` 直接作为顶层 Ray Object 存储，不需要额外的包装类。** `BlockAccessor` 提供了统一的接口：行迭代、切片、列操作、排序、分区、采样、聚合、shuffle、格式转换等。

### 2.4 BlockMetadata：Block 的元信息

```python
class BlockMetadata:
    num_rows: Optional[int]           # 行数
    size_bytes: Optional[int]         # 字节大小
    exec_stats: Optional[BlockExecStats]       # 执行统计
    task_exec_stats: Optional[TaskExecWorkerStats]  # 任务级统计
    input_files: Optional[Tuple[str, ...]]     # 输入文件列表
```

`BlockExecStats` 包含详细的性能指标：
- `task_idx`：任务编号
- `node_id`：执行节点（从 `ray.runtime_context` 获取）
- `start_time_s` / `end_time_s` / `wall_time_s`：时间统计
- `udf_time_s`：用户函数执行时间
- `block_ser_time_s`：Block 序列化时间
- `cpu_time_s`：CPU 时间
- `max_uss_bytes`：峰值内存（Unique Set Size）

### 2.5 内存布局

```
Driver 进程
├── Dataset 对象（轻量级，只有计划）
├── ObjectRef[Block_0] ──→ Node A Object Store → Block_0 (pyarrow.Table)
├── ObjectRef[Block_1] ──→ Node B Object Store → Block_1 (pandas.DataFrame)
├── ObjectRef[Block_2] ──→ Node A Object Store → Block_2 (pyarrow.Table)
└── ...
```

- N 个 Block = N 个 ObjectRef（在 driver）+ N 个实际数据块（分布在各节点 Object Store）
- Block 在 Object Store 中是**不可变的**，创建后不能修改
- `ray.get()` 访问 numpy 数组时使用**零拷贝**（shared memory）

---

## 第3章：惰性执行与执行计划

### 3.1 两阶段规划架构

Ray Data 使用两阶段规划：

```
用户 API 调用
    ↓
Logical Plan（逻辑计划）→ 逻辑优化
    ↓
Physical Plan（物理计划）→ 物理优化
    ↓
StreamingExecutor 执行
```

### 3.2 Logical Plan（逻辑计划）

每个用户 API 调用会在逻辑计划 DAG 中添加一个 `LogicalOperator` 节点：

```python
# 用户代码
ds = ray.data.read_parquet("data.parquet")  # → ReadOp
ds = ds.filter(lambda row: row["age"] > 25) # → Filter
ds = ds.map(lambda row: {**row, "y": 1})    # → MapBatches
ds = ds.select_columns(["age", "y"])        # → Project
```

对应的逻辑计划 DAG：

```
ReadOp → Filter → MapBatches → Project
```

主要的 LogicalOperator 类型：
- `ReadOp`：数据读取
- `MapBatches`：批量转换
- `Filter`：过滤
- `Project`：列投影
- `FlatMap`：一行变多行
- `Sort`：排序
- `Repartition`：重分区
- `Aggregate`：聚合
- `RandomShuffle`：随机洗牌

### 3.3 逻辑优化

逻辑优化阶段执行以下优化：

1. **谓词下推（Predicate Pushdown）**：将 Filter 操作推到 ReadOp 附近，减少读取的数据量。`LogicalOperatorSupportsPredicatePassThrough` 接口定义了两种行为：
   - `PASSTHROUGH`：直接传递谓词
   - `PASSTHROUGH_WITH_SUBSTITUTION`：带列名替换的谓词传递

2. **投影下推（Projection Pushdown）**：通过列替换映射（column substitution map）将列裁剪推到数据源，只读取需要的列

3. **Limit 下推**：将 `limit` 操作推到数据源，减少读取行数

### 3.4 Physical Plan（物理计划）

逻辑计划通过 `create_planner()` 编译为物理计划。每个逻辑算子通过专门的 `plan_*` 函数转换：

| 逻辑算子 | 物理编译函数 | 物理算子 |
|---------|------------|---------|
| ReadOp | `plan_read_op` | InputDataBuffer + MapOperator |
| MapBatches | `plan_udf_map_op` | TaskPoolMapOperator / ActorPoolMapOperator |
| Filter | `plan_filter_op` | MapOperator（内部 filter 逻辑） |
| Project | `plan_project_op` | MapOperator（列选择逻辑） |
| Sort | `plan_sort_op` | AllToAllOperator（三阶段） |
| Repartition | `plan_repartition_op` | AllToAllOperator 或 StreamingRepartition |

一个逻辑算子可能展开为多个物理算子。例如 `ReadOp` 变成 `InputDataBuffer`（数据缓冲）+ `MapOperator`（数据转换）。

### 3.5 物理优化

物理优化阶段运行以下规则：

1. **FuseOperators**：将兼容的连续 Map 算子合并，消除中间 Block 的序列化/反序列化开销。合并后的算子内部链接多个转换函数。

2. **InheritTargetMaxBlockSizeRule**：继承目标最大 Block 大小配置

3. **ConfigureMapTaskMemoryUsingOutputSize**：根据输出大小配置 Map 任务内存

### 3.6 物化触发条件

以下操作会触发执行计划的实际执行：

| 触发操作 | 说明 |
|---------|------|
| `show()` | 打印前 N 行 |
| `take(n)` | 取前 N 行 |
| `count()` | 统计行数 |
| `schema()` | 获取 Schema |
| `materialize()` | 强制执行并缓存结果 |
| `iter_rows()` | 逐行迭代 |
| `iter_batches()` | 按 batch 迭代 |
| `to_pandas()` | 转为 pandas |
| `to_numpy()` | 转为 numpy |
| `to_arrow()` | 转为 Arrow |
| `write_parquet()` | 写 Parquet |
| `write_csv()` | 写 CSV |

---

## 第4章：流式执行引擎（StreamingExecutor）

### 4.1 StreamingExecutor 架构

```python
class StreamingExecutor(Executor, threading.Thread):
    ...
```

StreamingExecutor 同时继承了 `Executor` 和 `threading.Thread`，它在**守护线程**中运行（线程名：`StreamingExecutor-{dataset_id}`），不会阻塞 driver 进程的 generator yield。

核心设计思想：**以完全流式的方式执行 Dataset DAG**，通过构建 Operator 拓扑，在资源约束下最大化吞吐量。

### 4.2 Operator 拓扑（Topology）

DAG 被物化为一个 `Topology`——有序字典 `OrderedDict[PhysicalOperator, OpState]`：

```
Topology 结构：
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  ReadOperator    │────→│  MapOperator     │────→│  OutputNode     │
│  (OpState)       │     │  (OpState)       │     │  (OpState)      │
│  input_queue: [] │     │  input_queue: ←──│     │  input_queue: ←──│
│  output_queue: ──→│     │  output_queue: ──→│     │  output_queue: []│
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

每个 Operator 拥有：
- **输入队列**：别名自上游的输出队列（直接引用，无需复制）
- **输出队列**：`RefBundle` 对象的队列
- **内部队列**：可选（`InternalQueueOperatorMixin`）

拓扑有一个显式的输出节点（sink），是数据流的终点。

### 4.3 调度循环（每步三个阶段）

StreamingExecutor 的核心是一个 while 循环，每步执行三个阶段：

#### 阶段一：处理完成的任务

```python
process_completed_tasks()
```

调用 `ray.wait()` 阻塞等待任务完成，将完成的 `RefBundle` 拉入对应 Operator 的输出队列。每次调用会处理多个完成的任务以提高并行度。

#### 阶段二：算子选择与调度

```python
select_operator_to_run()
```

在一个紧密循环中选择下一个要执行的算子，考虑：
- ResourceManager 的资源约束
- 背压策略（BackpressurePolicy）
- 可插拔的排序器（Ranker）
- 活性保证（Liveness Enforcement）

选中的算子调用 `dispatch_next_task()` 提交任务。

#### 阶段三：状态更新与自动伸缩

```python
update_operator_states()
```

刷新拓扑状态，触发 `ClusterAutoscaler` 和 `ActorAutoscaler` 的 `try_trigger_scaling()`。

### 4.4 背压机制（Backpressure）

背压通过可插拔的 `BackpressurePolicy` 对象实现，在任务处理和算子选择两个阶段都被咨询。

关键方法 `_consumer_idling()`：检查输出节点的队列是否为空。**即使背压策略阻塞了所有调度，活性保证也会强制至少调度一个任务**，防止死锁。

背压参数示例：
- `downstream_capacity_backpressure_ratio = 10.0`：下游容量背压比率
- 动态输出队列大小调整
- 基于消费者饥饿、下游空闲检测、资源竞争的解除阻塞条件

### 4.5 流式分割（Streaming Split）

```python
shards = ds.streaming_split(n=4, equal=True)
```

将数据集分割为 N 个不重叠的分片，每个分片支持相同的迭代器协议，用于多 worker 分布式训练。**无需物化所有数据即可流式消费。**

---

## 第5章：任务调度与执行模型

### 5.1 TaskPoolMapOperator：无状态任务

用于 `map`、`filter`、`map_batches` 的默认执行模式。

#### 调度流程

```python
def _try_schedule_task(self):
    # 1. 构建 TaskContext
    task_ctx = TaskContext(task_idx, ...)

    # 2. 计算动态 remote args
    dynamic_remote_args = self._get_dynamic_remote_args(task_ctx)

    # 3. 提交 streaming remote task
    ref = cached_remote_fn(_map_task).options(
        num_returns="streaming",
        **self._remote_args,
        **dynamic_remote_args,
    ).remote(block, ctx, *fn_args, **fn_kwargs)
```

关键特点：
- 使用 `cached_remote_fn` 缓存远程函数引用，避免重复序列化
- `num_returns="streaming"`：使用 streaming generator，任务可以逐步产出多个 Block
- 每个 Block 由独立的 Ray Task 处理，在不同的 worker 进程中并行执行
- 资源声明：`num_cpus`、`num_gpus`、`memory`

### 5.2 ActorPoolMapOperator：有状态任务

用于 `ActorPoolStrategy` 模式，典型场景：模型推理（需要在 GPU 上保持模型状态）。

#### Actor 动态生成

```python
map_worker_cls_name = f"MapWorker_{operator_id}"
MapWorker = type(map_worker_cls_name, (_MapWorker,), {})
```

每个 ActorPoolMapOperator 生成一个具名的 Actor 类，便于在 Ray Dashboard 中区分不同算子的 Actor。

#### 堆选择算法（Heap-Based Selection）

```
全局最小堆: _alive_actors_to_in_flight_tasks_heap
├── Actor_0: 1 个正在执行的任务
├── Actor_1: 3 个正在执行的任务
├── Actor_2: 0 个正在执行的任务  ← 选中（最少任务数）
└── Actor_3: 2 个正在执行的任务

每节点堆: per_node_heaps
├── Node_A: [Actor_0(1), Actor_2(0)]
├── Node_B: [Actor_1(3), Actor_3(2)]
```

选择逻辑：
1. 按数据本地性排序首选节点（按 Block 字节数降序）
2. 在首选节点的堆中找最空闲的 Actor
3. 如果首选节点没有可用 Actor，回退到全局堆

#### 自动伸缩

`AutoscalingActorConfig` 配置：
- `min_size` / `max_size` / `initial_size`：Actor 池大小范围
- 扩容阈值：`actor_pool_util_upscaling_threshold = 1.75`（利用率 > 175% 时扩容）
- 缩容阈值：`actor_pool_util_downscaling_threshold = 0.5`（利用率 < 50% 时缩容）
- 缩容防抖：10 秒内不重复缩容

#### Actor 容错

- `max_restarts = -1`：无限重启
- `max_task_retries = -1`：无限任务重试
- 状态检测：通过 Ray GCS 检查 `DEAD` / `RESTARTING` / `ALIVE`

### 5.3 调度策略

| 策略 | 使用场景 | 说明 |
|------|---------|------|
| `SPREAD` | 默认 | 任务均匀分布在集群各节点 |
| `DEFAULT` | 大参数（>50 MiB） | Ray 的本地性感知调度 |
| `PACK` | Placement Group | 尽量在同一节点调度 |

当任务的参数超过 `large_args_threshold`（默认 50 MiB）时，自动切换到 `DEFAULT` 策略，优先将任务调度到持有大参数的节点。

---

## 第6章：内存管理

### 6.1 Ray Object Store

每个节点有一个 Object Store 进程，提供分布式共享内存：

- **不可变性**：对象创建后不能修改，支持无锁复制
- **零拷贝**：numpy 数组通过 shared memory 直接访问，无需反序列化
- **分布式引用计数**：引用归零时自动释放
- **Object Spilling**：Object Store 满时自动溢写到磁盘

#### Object Spilling 性能

| 指标 | 性能 |
|------|------|
| 写入吞吐 | 230-570 MiB/s |
| 恢复吞吐 | 505-1361 MiB/s |
| 默认溢写位置 | 会话临时目录 |
| 实现位置 | `local_object_manager.cc` |

### 6.2 Ray Data ResourceManager

`ResourceManager` 是 Ray Data 专用的资源追踪器，每个调度循环步骤更新一次。

#### 追踪的资源维度

| 维度 | 说明 |
|------|------|
| CPU | 逻辑核心数 |
| GPU | GPU 设备数 |
| Memory | 堆内存 |
| Object Store Memory | 共享内存 |

#### 关键追踪分类

- `_mem_op_internal`：待处理任务输出的 Object Store 内存（Block 正在生成但尚未 yield）
- `_mem_op_outputs`：算子输出的 Object Store 内存（包括内部输出队列和外部缓冲区）
- Object Store 内存分数：启用 `OpResourceAllocator` 时为 50%，否则为 25%

### 6.3 Block 大小配置

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `target_max_block_size` | 128 MiB | 内存占用 ≈ `2 * num_cpus * block_size` |
| `target_min_block_size` | 1 MiB | 优先于 `read_op_min_num_blocks` |
| Shuffle target block size | 1 GiB | 所有输入必须物化，小 Block 无性能优势 |
| `streaming_read_buffer_size` | 32 MiB | 流式读取缓冲区 |

**为什么 `target_max_block_size` 是 128 MiB？** 内存占用公式：`2 * num_cpus * block_size`。假设 8 核 CPU，内存占用 = 2 × 8 × 128 MiB = 2 GiB，这是一个合理的内存预算。

### 6.4 ReservationOpResourceAllocator

资源分配采用**预留模型**：

```
全局资源限制
├── 预留部分（50%）：平均分配给各活跃算子
│   ├── 算子 A: 25%
│   └── 算子 B: 25%
└── 共享池（50%）：各算子竞争使用
```

规则：
1. 每个算子的预留 = `reservation_ratio × global_limits / num_eligible_ops`
2. 至少一半预留用于输出
3. 未预留的资源形成共享池，平均分配给活跃算子
4. 下游算子预算低于最小调度资源时，可向上游借用
5. **死锁预防**：对阻塞式物化算子设置无限内存预算

---

## 第7章：Shuffle 机制

### 7.1 Shuffle 策略选择

通过 `DataContext.shuffle_strategy` 配置：

| 策略 | 说明 |
|------|------|
| `HASH_SHUFFLE` | **默认**。基于 key 哈希分配，用于 groupby/map_groups |
| `SORT_SHUFFLE_PULL_BASED` | 拉取式排序 shuffle |
| `SORT_SHUFFLE_PUSH_BASED` | 推送式排序 shuffle |
| `GPU_SHUFFLE` | GPU 专用 shuffle |

### 7.2 Exoshuffle 架构

Ray Data 的 Shuffle 实现基于 Exoshuffle 论文（VLDB 2022, arxiv:2203.05072）：

> "一个构建在 Ray 之上的库，将 shuffle 控制面与数据面分离，同时不牺牲性能，达到与单体 shuffle 系统竞争的性能和可扩展性。"

核心思想：
- **控制面**：决定数据如何分区、路由
- **数据面**：实际的 Block 传输和合并
- 两者解耦，可以独立优化

### 7.3 两阶段 Map-Reduce

所有 Shuffle 操作使用 `ExchangeTaskSpec` 定义的两阶段 Map-Reduce：

```
输入 Blocks
    ↓
┌─────────────────────┐
│  Map 阶段            │  每个输入 Block 被分区/洗牌
│  Block_0 → [P0, P1]  │
│  Block_1 → [P0, P1]  │
│  Block_2 → [P0, P1]  │
└─────────────────────┘
    ↓
┌─────────────────────┐
│  Reduce 阶段         │  分区被合并为输出 Block
│  [P0 from all] → Out_0 │
│  [P1 from all] → Out_1 │
└─────────────────────┘
    ↓
输出 Blocks
```

### 7.4 Sort Shuffle 三阶段

`Sort` 算子使用 `SortTaskSpec` 定义的三阶段：

```
阶段 1: 采样（Sampling）
├── 从每个已排序 Block 中随机采样
└── 计算分区边界

阶段 2: Map（重分区）
├── 根据边界将数据分配到不同分区
└── 每个分区内部有序

阶段 3: Reduce（合并）
├── 将来自不同 Block 的同分区数据合并
└── 归并排序，输出全局有序
```

### 7.5 Hash Shuffle

用于 `groupby().map_groups()` 和带 key 的 `repartition()`：

- 行根据 group key 的哈希值分配到输出分区
- `max_hash_shuffle_aggregators`：最大聚合器数（默认：`min(集群CPU数 × 2, 128)`）
- 每个聚合器是一个独立的 Actor

### 7.6 Split-Based Repartition

当 `shuffle=False` 时，`Repartition` 使用单阶段的 split 方式：

- 只做 Block 的合并/拆分，不做全量数据重分布
- 成本远低于 shuffle-based repartition
- 适合只需要调整 Block 数量的场景

### 7.7 Shuffle 的阻塞性

**Shuffle 操作是阻塞式的（materializing）**：

- `HashShufflingOperatorBase`、`AllToAllOperator`、`ZipOperator` 都是阻塞的
- 阻塞意味着：**暂停流式处理，等待所有输入 Block 到达后才能开始处理**
- 这是 Shuffle 的固有特性——无法在流式模式下完成全局数据重分布

```
流式管道:
Read → Map → Filter → [阻塞: Shuffle] → Map → Output
                       ↑
                 所有数据在此处物化
```

---

## 第8章：容错机制

### 8.1 Ray Core 血统恢复

当 Object Store 中的值丢失（如节点故障），Ray 的恢复流程：

```
1. 在其他节点搜索同一对象的副本
   ├── 找到 → 使用副本
   └── 未找到 → 继续步骤 2

2. 重新执行创建该对象的原始 Task
   └── Task 参数通过相同机制递归重建

3. 重建完成，数据恢复
```

限制条件：
- `ray.put()` 创建的对象**不可恢复**（无血统信息）
- Task 必须是**确定性和幂等的**
- 非 Actor Task 默认重试 3 次
- Object 的 owner 进程必须存活
- 血统内存上限：1 GB（`RAY_max_lineage_bytes`）

### 8.2 Ray Data 容错机制

| 机制 | 配置 | 默认值 | 说明 |
|------|------|-------|------|
| 错误 Block 预算 | `max_errored_blocks` | 0 | 每次执行容忍的总失败数（负数=无限） |
| Map 错误重试 | `retried_map_errors` | `False` | `True`=全部重试, `False`=不重试, 或错误模式列表 |
| Map 重试上限 | `max_map_retries` | 3 | 每个 Map 任务的最大重试次数 |
| IO 错误重试 | `retried_io_errors` | AWS 错误子串 | 先子串匹配，再正则匹配 |
| Actor 任务重试 | `max_task_retries` | -1（无限） | Actor 任务重试次数 |
| Actor 重启 | `max_restarts` | -1（无限） | Actor 重启次数 |

### 8.3 Actor 生命周期容错

`refresh_actor_state()` 通过 Ray GCS 检测 Actor 状态变化：

```
Actor 状态机:
ALIVE ──故障──→ DEAD ──重启──→ RESTARTING ──完成──→ ALIVE
  │              │               │
  └─ 从堆中移除  └─ 从堆中移除   └─ 排除在 alive 堆外，资源记为 pending
```

- `DEAD` 或 `Unknown`：从调度堆中移除
- `RESTARTING`：排除在 alive 堆外，资源追踪为 pending
- `ALIVE`（重启后）：恢复到 alive 堆

### 8.4 关闭序列（7步）

```
1. 设置 _shutdown = True，join 调度线程（2s 超时）
2. 更新统计指标，标记终态（FINISHED 或 FAILED）
3. 冻结最终统计，重置 ResourceManager
4. 关闭所有算子（带计时器，可选强制 kill）
5. 排空拓扑队列（保留 sink 输出用于 live multi-split 场景）
6. 触发成功/失败回调
7. 通知集群自动伸缩器
```

---

## 第9章：资源管理详解

### 9.1 ResourceManager 全局追踪

`ResourceManager` 每个调度循环步骤更新一次，追踪：

```python
class ResourceManager:
    _global_cpu: float          # 全局 CPU 使用
    _global_gpu: float          # 全局 GPU 使用
    _global_memory: float       # 全局内存使用
    _global_object_store: float # 全局 Object Store 使用
```

`get_global_limits()` 每秒刷新一次：
```
global_limit = min(用户指定值, 集群总量 × memory_fraction) - 排除资源
```

### 9.2 每算子资源分配

`TaskPoolMapOperator` 追踪：

```python
current_logical_usage += per_task_resource_allocation  # 任务提交时
current_logical_usage -= callback_value                # 任务完成时
```

`per_task_resource_allocation` 从 `ray_remote_args` 中读取 `num_cpus`、`num_gpus`、`memory`。**不使用的资源显式设为 0**，防止"囤积资源预算"。

### 9.3 Actor 池并发控制

```python
max_tasks_in_flight_per_actor = max_concurrency * 2
```

堆选择使用 `rank = 当前任务数`，当最小 rank >= `max_tasks_in_flight_per_actor` 时，选择失败（Actor 全忙）。

每个 Actor 追踪三个计数器：
- `total_usage`：总资源使用
- `pending_restarting_usage`：待处理/重启中的资源使用
- `per_actor_usage`：每个 Actor 的资源使用

### 9.4 IdleDetector

```python
class IdleDetector:
    check_interval = 10    # 每 10 秒检查一次
    warn_after = 60        # 60 秒无输出则警告
```

追踪每个算子的 `num_task_outputs_generated`，检测管道是否停滞。

---

## 第10章：Ray 2.x 关键变化

### 10.1 流式执行成为默认

最重大的变化：从全量物化（bulk）执行切换到流式（streaming）执行。`StreamingExecutor` 取代了旧的批量执行器，实现了管道化处理——不同算子可以并发运行，数据增量式地流经算子图。

### 10.2 DataContext 集中配置

`DataContext`（通过 `DataContext.get_current()` 获取）成为集中配置单例，取代了分散的配置方式。关键配置项：

```python
class DataContext:
    execution_options: ExecutionOptions   # 执行选项
    shuffle_strategy: ShuffleStrategy     # Shuffle 策略
    target_max_block_size: int            # Block 大小
    actor_pool_util_upscaling_threshold: float
    actor_pool_util_downscaling_threshold: float
    max_errored_blocks: int
    ...
```

### 10.3 Hash Shuffle 成为默认

`HASH_SHUFFLE` 取代了基于排序的 shuffle 方法，通过专用的聚合器 Actor 和可配置的并行度实现。

### 10.4 Operator Fusion

`FuseOperators` 物理优化规则将兼容的连续 Map 算子合并，减少阶段间的序列化开销。

### 10.5 资源预留系统

`ReservationOpResourceAllocator` 提供了可配置的预留比例（默认 50%），确保每个算子有资源保障，同时允许共享池溢出。

### 10.6 表达式过滤与投影

`Filter` 和 `Project` 算子增加了基于表达式的路径（除了 UDF 路径），支持通过逻辑计划进行谓词下推和投影下推优化。

### 10.7 Datasource V2

`use_datasource_v2 = True` 成为默认，读取通过 V2 管道进行，改进了并行度检测和读取任务生成。

### 10.8 自动伸缩改进

Actor 池自动伸缩增加了可配置阈值、防抖机制（10 秒缩容防抖）和空闲检测（10 秒间隔，60 秒警告）。

### 10.9 背压系统

可插拔的 `BackpressurePolicy` 框架，支持动态输出队列大小调整，基于消费者饥饿和下游空闲检测的解除阻塞条件。

---

## 第11章：核心源码索引

| 源文件路径 | 职责 |
|-----------|------|
| `_internal/execution/streaming_executor.py` | 流式执行器、调度循环、关闭序列 |
| `_internal/execution/operators/task_pool_map_operator.py` | 无状态任务执行 |
| `_internal/execution/operators/actor_pool_map_operator.py` | Actor 池生命周期、自动伸缩、本地性 |
| `_internal/execution/resource_manager.py` | 资源追踪、预留分配器、空闲检测 |
| `_internal/execution/interfaces/execution_options.py` | ExecutionOptions、preserve_order |
| `_internal/logical/operators/map_operator.py` | 逻辑 Map 算子（MapBatches, Filter, Project, FlatMap） |
| `_internal/logical/operators/all_to_all_operator.py` | Shuffle 逻辑算子（Sort, Repartition, Aggregate） |
| `_internal/logical/optimizers.py` | 优化流水线、算子融合 |
| `_internal/planner/plan_read_op.py` | ReadOp 到物理计划的编译 |
| `_internal/planner/plan_udf_map_op.py` | UDF Map 到物理计划的编译 |
| `block.py` | Block 类型、BlockAccessor、BlockMetadata |
| `context.py` | DataContext、Shuffle 配置、Block 大小、自动伸缩配置 |

---

# Part 2：面试深度题

---

## 一、架构与设计（5题）

### Q1: Ray Data 的 Dataset 对象本身存储数据吗？数据实际存储在哪里？

**答：** 不存储。`Dataset` 对象只存在于 driver 进程，是一个惰性的执行计划容器，核心字段是 `_plan: LogicalPlan`。实际数据以 Block（`pyarrow.Table` 或 `pandas.DataFrame`）的形式存储在集群各节点的 **Ray Object Store**（共享内存）中。Dataset 通过 `ObjectRef` 列表引用这些 Block。一个 N 个 Block 的 Dataset = driver 中的 N 个 ObjectRef + 分布在各节点 Object Store 中的 N 个实际数据块。

**关键要点：** Dataset 是计划容器，不是数据容器。理解这一点是理解惰性执行的基础。

---

### Q2: Ray Data 的两阶段规划是什么？为什么要分两阶段？

**答：** 两阶段指 **Logical Plan（逻辑计划）** 和 **Physical Plan（物理计划）**。

- **逻辑计划**：由 `LogicalOperator` 节点组成的 DAG，描述"做什么"（what）。每个用户 API 调用添加一个逻辑节点（ReadOp, MapBatches, Filter...）
- **物理计划**：由 `PhysicalOperator` 组成，描述"怎么做"（how）。通过 `plan_*` 函数从逻辑算子编译而来

分两阶段的原因：
1. **优化空间**：逻辑计划阶段可做谓词下推、投影下推、Limit 下推等优化
2. **解耦**：同一逻辑操作可以有多种物理实现（如 MapBatches 可以用 TaskPool 或 ActorPool）
3. **算子融合**：物理优化阶段的 `FuseOperators` 可以合并兼容的连续算子

---

### Q3: 什么是 RefBundle？它在 Ray Data 中起什么作用？

**答：** `RefBundle` 是 Block 引用的打包，定义为 `List[Tuple[ObjectRef, BlockMetadata]]`。

它在 Operator 之间传递，作为数据流的基本单元：
- 不包含实际数据，只包含 ObjectRef（引用）和元数据
- 物理算子消费和产出 RefBundle 流
- StreamingExecutor 的队列中存放的是 RefBundle

设计原因：避免在 Operator 之间复制数据，通过引用传递实现零拷贝的数据流。

---

### Q4: BlockAccessor 模式的设计动机是什么？

**答：** Ray Data 支持两种 Block 后端：`pyarrow.Table` 和 `pandas.DataFrame`。`BlockAccessor` 是一个静态工厂模式：

```python
BlockAccessor.for_block(block) → ArrowBlockAccessor 或 PandasBlockAccessor
```

设计动机：**希望将 `pyarrow.Table` 直接作为顶层 Ray Object 存储，不需要额外的包装类。** 如果用继承（如统一的 Block 基类），就必须包装 PyArrow Table，增加一层间接性。BlockAccessor 模式让两种 Block 类型保持原样，通过外部适配器提供统一接口。

---

### Q5: Ray Data 与 Ray Core 的关系是什么？Ray Data 用了哪些 Ray Core 原语？

**答：** Ray Data 构建在 Ray Core 之上，使用以下原语：

| Ray Core 原语 | Ray Data 用途 |
|---------------|--------------|
| `@ray.remote` 函数 | TaskPoolMapOperator 中的无状态任务 |
| `@ray.remote` 类 | ActorPoolMapOperator 中的有状态 Actor |
| Object Store | 存储 Block 数据 |
| `ObjectRef` | RefBundle 中的 Block 引用 |
| `ray.wait()` | StreamingExecutor 等待任务完成 |
| 资源调度（CPU/GPU/Memory） | ResourceManager 声明每任务资源 |
| Placement Group | 调度策略（PACK/SPREAD） |
| 血统恢复 | Block 丢失时重新计算 |
| 自动伸缩 | 集群和 Actor 池伸缩 |

---

## 二、执行模型（5题）

### Q6: Ray Data 的惰性执行是如何实现的？哪些操作是惰性的，哪些会触发执行？

**答：** 惰性执行通过"记录操作到逻辑计划 DAG，延迟到需要结果时才执行"实现。

**惰性操作**（只添加逻辑节点）：`map`、`flat_map`、`filter`、`map_batches`、`select_columns`、`drop_columns`、`sort`、`repartition`、`groupby`

**触发执行的操作**（需要实际数据）：`show`、`take`、`count`、`schema`、`materialize`、`iter_rows`、`iter_batches`、`to_pandas`、`to_numpy`、`to_arrow`、`write_parquet`、`write_csv`

实现机制：惰性操作调用时，只是在 `_plan` 中添加一个新的 `LogicalOperator` 节点。触发执行时，`_plan` 被编译为物理计划，交给 `StreamingExecutor` 执行。

---

### Q7: StreamingExecutor 的调度循环是什么样的？每步做哪些事情？

**答：** StreamingExecutor 在守护线程中运行一个 while 循环，每步三个阶段：

1. **`process_completed_tasks()`**：调用 `ray.wait()` 等待任务完成，将完成的 RefBundle 拉入算子输出队列
2. **`select_operator_to_run()`**：在资源约束和背压策略下选择下一个执行的算子，调用 `dispatch_next_task()` 提交任务
3. **`update_operator_states()`**：刷新拓扑状态，触发自动伸缩

这个循环持续运行直到所有算子完成或发生不可恢复的错误。

---

### Q8: TaskPoolMapOperator 和 ActorPoolMapOperator 的区别是什么？各适合什么场景？

**答：**

| 维度 | TaskPoolMapOperator | ActorPoolMapOperator |
|------|-------------------|---------------------|
| 状态 | 无状态 | 有状态 |
| 实现 | Ray Task | Ray Actor |
| 适用 | map/filter/map_batches 默认 | ActorPoolStrategy |
| 典型场景 | ETL、特征工程 | 模型推理（需保持 GPU 上的模型） |
| 容错 | 重试（默认 3 次） | 无限重启 + 无限重试 |
| 调度 | 简单的资源声明 | 堆选择 + 本地性感知 |
| 伸缩 | 固定并发 | 自动伸缩 Actor 池 |

**选择依据：** 如果转换函数是无状态的（每次调用独立），用 TaskPool。如果需要在多次调用间保持状态（如加载到 GPU 的模型），用 ActorPool。

---

### Q9: 什么是 Operator Fusion？它如何提高性能？

**答：** `FuseOperators` 是物理优化阶段的一个规则，将兼容的连续 Map 算子合并为一个算子。

例如：
```
原始: MapA → MapB → MapC
融合: Map[A+B+C]
```

性能提升：
- **消除中间序列化**：原本每个算子输出的 Block 都要序列化到 Object Store，再由下一个算子反序列化。融合后，中间 Block 在内存中直接传递
- **减少 Task 调度开销**：原本 3 个 Task 变成 1 个 Task
- **减少 Object Store 压力**：中间结果不占用 Object Store

兼容条件：两个 Map 算子必须都是 TaskPoolMapOperator（或兼容的类型），且资源需求兼容。

---

### Q10: 流式执行与全量物化执行的区别是什么？

**答：**

**全量物化（Bulk Execution）**：
```
Read ALL blocks → Map ALL blocks → Filter ALL blocks → Output
```
每个阶段必须等前一个阶段**完全完成**才能开始。内存中需要同时容纳所有中间结果。

**流式执行（Streaming Execution）**：
```
Read block_0 → Map block_0 → Filter block_0 → Output block_0
Read block_1 → Map block_1 → Filter block_1 → Output block_1
...（管道化并行）
```
不同算子可以**并发运行**，数据增量式流经管道。一个 Block 完成 Read 后立即进入 Map，无需等待所有 Block 读完。

**优势：**
1. 内存效率高：不需要同时容纳所有中间结果
2. 吞吐量高：不同算子并行，GPU/CPU 不空闲
3. 首结果延迟低：第一个 Block 可以快速产出

**例外：** Shuffle 操作（Sort、groupby）是阻塞的，必须物化所有输入后才能开始。

---

## 三、内存与资源（5题）

### Q11: Ray Object Store 的零拷贝机制是如何工作的？

**答：** Ray 的 Object Store 使用操作系统的共享内存（shared memory）实现：

1. 写入端：Task 将结果写入 Object Store 的共享内存区域
2. 读取端：通过 `ray.get()` 获取时，numpy 数组直接映射到共享内存，**无需复制**
3. 不可变保证：Object 创建后不可修改，所以无需加锁

对于非 numpy 对象（如 Python dict），需要反序列化（通过 CloudPickle），不是零拷贝。

**Ray Data 中的意义：** Block 存储为 PyArrow Table 或 Pandas DataFrame，其中 PyArrow Table 的底层 buffer 可以利用零拷贝。这使得同一 Block 可以被多个算子高效访问。

---

### Q12: Object Spilling 是什么？什么情况下会触发？对性能有什么影响？

**答：** Object Spilling 是 Ray 的内存溢写机制。当 Object Store 达到容量上限时，自动将部分对象溢写到磁盘。

**触发条件：** Object Store 使用率接近 100%，且有新对象需要写入

**性能数据：**
- 写入吞吐：230-570 MiB/s
- 恢复吞吐：505-1361 MiB/s
- 相比内存访问（~10 GiB/s），慢 10-50 倍

**对 Ray Data 的影响：**
- Shuffle 操作最容易触发（需要物化所有输入）
- 大数据集的 `materialize()` 可能触发
- 建议：适当减小 `target_max_block_size`，使用流式处理避免全量物化

---

### Q13: `target_max_block_size` 的默认值 128 MiB 是怎么来的？

**答：** 内存占用公式：`memory_footprint ≈ 2 × num_cpus × block_size`

系数 2 来自：一个 Block 在处理时，输入和输出各占一份内存。

以 8 核 CPU 为例：`2 × 8 × 128 MiB = 2 GiB`，这是一个合理的内存预算，在大多数机器上不会导致 OOM。

Block 太大：内存压力大，可能 OOM
Block 太小：调度开销大，Task 数量多，Object Store 元数据开销大

---

### Q14: ReservationOpResourceAllocator 的工作原理是什么？如何防止死锁？

**答：** 工作原理：

```
全局资源
├── 预留部分（reservation_ratio=50%）：平均分给 N 个活跃算子
│   每个算子: 50% / N
└── 共享池（50%）：各算子竞争
```

规则：
1. 至少一半预留用于输出
2. 下游算子资源不足时可向上游借用
3. 非活跃算子的预留资源回收到共享池

**死锁预防：** 对阻塞式物化算子（如 Shuffle 的 AllToAllOperator）设置**无限内存预算**。因为这些算子必须等待所有输入到达才能开始输出，如果限制其内存预算，会导致输入无法全部到达，形成死锁。

---

### Q15: Ray Data 如何追踪和限制内存使用？

**答：** `ResourceManager` 在每个调度循环步骤更新一次，追踪四个维度：CPU、GPU、Memory、Object Store Memory。

具体追踪：
- `_mem_op_internal`：正在生成但尚未 yield 的 Block（Object Store 内存）
- `_mem_op_outputs`：算子输出队列中的 Block（包括内部队列和外部缓冲区）
- 外部消费者缓冲：通过 `set_external_consumer_bytes()` 追踪迭代器缓冲的字节数

全局限制每秒刷新一次：
```
limit = min(用户指定, 集群总量 × memory_fraction) - excluded_resources
```

Object Store 内存分数：启用 OpResourceAllocator 时 50%，否则 25%。

---

## 四、Shuffle（5题）

### Q16: 为什么 Shuffle 操作是阻塞的？能不能做成流式的？

**答：** Shuffle 操作本质上需要**全局数据重分布**——同一 group key 的所有数据必须到达同一节点才能进行聚合。这意味着必须等所有输入 Block 到齐后才能开始处理。

流式 Shuffle 的困难：
1. 不知道一个 key 的所有数据是否已经到达
2. 如果提前处理部分数据，后续到达的同 key 数据需要合并，复杂度高
3. 需要维护全局的 key 分布信息

**Ray Data 的选择：** Shuffle 算子（AllToAllOperator）是 materializing 的——暂停流式管道，物化所有输入后再执行。这是性能和复杂度之间的权衡。

**Exoshuffle 的优化方向：** 将控制面（决定数据路由）和数据面（实际传输）分离，可以在控制面做优化（如预计算分区边界），但数据面仍然需要物化。

---

### Q17: Sort Shuffle 的三阶段分别做什么？为什么需要采样阶段？

**答：**

**阶段 1 - 采样（Sampling）：**
- 从每个 Block 中随机采样
- 根据采样结果计算全局排序的分区边界

**阶段 2 - Map（重分区）：**
- 每个 Block 根据边界被切分为多个分区
- 分区 i 包含所有在边界 [i, i+1) 范围内的数据

**阶段 3 - Reduce（合并）：**
- 来自不同 Block 的同分区数据被归并排序
- 输出全局有序的 Block

**为什么需要采样？** 如果不采样，就无法知道数据的分布，可能导致严重的数据倾斜（一个分区的数据量远大于其他分区）。采样可以近似估计数据分布，计算出均匀的分区边界。

---

### Q18: Hash Shuffle 和 Sort Shuffle 的区别是什么？各适合什么场景？

**答：**

| 维度 | Hash Shuffle | Sort Shuffle |
|------|-------------|-------------|
| 分区依据 | key 的哈希值 | 排序后的分区边界 |
| 阶段数 | 2（Map + Reduce） | 3（采样 + Map + Reduce） |
| 输出顺序 | 分区内无序 | 全局有序 |
| 默认策略 | 是 | 否 |
| 适用场景 | groupby、map_groups | sort、需要全局有序 |
| 数据倾斜 | 可能（热点 key） | 较少（采样均衡） |

**选择依据：** 如果只需要分组聚合，用 Hash Shuffle 更快（少一个阶段）。如果需要全局排序，必须用 Sort Shuffle。

---

### Q19: `repartition(shuffle=False)` 和 `repartition(shuffle=True)` 有什么区别？

**答：**

**`shuffle=True`（默认）：**
- 使用 Hash Shuffle 进行全量数据重分布
- 数据在节点间传输
- 成本高，但可以改变数据的物理分布

**`shuffle=False`：**
- 使用 Split-Based Repartition
- 只做 Block 的合并/拆分，**不在节点间传输数据**
- 成本低，但只改变 Block 数量，不改变数据分布

**使用场景：**
- `shuffle=False`：只需要调整 Block 数量（如合并小 Block 减少调度开销）
- `shuffle=True`：需要数据重新分布（如为后续的 join/groupby 做准备）

---

### Q20: Exoshuffle 论文的核心贡献是什么？

**答：** Exoshuffle（VLDB 2022, arxiv:2203.05072）的核心贡献是：

1. **控制面与数据面分离**：Shuffle 的逻辑（如何分区、路由）和物理（数据传输、合并）解耦
2. **构建在 Ray 之上**：利用 Ray 的 Task/Actor/Object Store 原语，不需要专用的 Shuffle 服务
3. **性能竞争**：达到与 Spark 等单体 Shuffle 系统竞争的性能和可扩展性
4. **灵活性**：通过分离设计，可以轻松实现不同的 Shuffle 策略（Hash、Sort、Range）

**对 Ray Data 的影响：** Ray Data 的 Shuffle 实现基于 Exoshuffle 架构，支持多种 Shuffle 策略（HASH_SHUFFLE、SORT_SHUFFLE、GPU_SHUFFLE），通过 `DataContext.shuffle_strategy` 配置。

---

## 五、容错与可靠性（4题）

### Q21: Ray 的血统恢复（Lineage Recovery）是什么？有什么限制？

**答：** 血统恢复是 Ray 的核心容错机制。每个 Object 都记录了创建它的 Task 的血统信息。当 Object 丢失时：

1. 搜索其他节点上的副本
2. 没有副本则重新执行原始 Task
3. Task 参数通过相同机制递归重建

**限制：**
- `ray.put()` 创建的对象不可恢复（没有血统）
- Task 必须确定性和幂等（重试必须产生相同结果）
- 非 Actor Task 默认重试 3 次
- Object 的 owner 进程必须存活
- 血统内存上限 1 GB

**Ray Data 中的应用：** Block 由 Task 产生，天然具有血统。如果某个节点故障导致 Block 丢失，Ray Data 可以重新执行产生该 Block 的 Task 来恢复数据。

---

### Q22: `max_errored_blocks` 的作用是什么？生产环境中应该如何设置？

**答：** `max_errored_blocks` 控制一次执行中允许的最大失败 Block 数。

- **默认 0**：任何错误都会导致整个执行失败
- **正数 N**：最多容忍 N 个 Block 失败，超过则执行失败
- **负数**：无限容忍错误（不推荐）

**生产环境建议：**
- 对于关键数据管道：设为 0，任何错误都应调查
- 对于脏数据处理：设为一个小正数（如 10），容忍少量异常数据
- 配合 `retried_map_errors` 使用：先重试，重试用完再计入错误预算

---

### Q23: ActorPoolMapActor 的容错机制是如何工作的？

**答：** ActorPoolMapOperator 中的 Actor 有三层容错：

1. **Task 重试**：`max_task_retries = -1`（无限）。单个任务失败时自动重试
2. **Actor 重启**：`max_restarts = -1`（无限）。Actor 进程崩溃时自动重启
3. **状态检测**：通过 Ray GCS 检测 Actor 状态：
   - `DEAD`：从调度堆移除
   - `RESTARTING`：排除在 alive 堆外，资源记为 pending
   - `ALIVE`（重启后）：恢复到调度堆

**实际效果：** 即使 Actor 所在节点完全故障，Ray 会在其他节点重新创建 Actor，恢复模型状态，继续处理任务。对用户来说是透明的。

---

### Q24: StreamingExecutor 的关闭序列为什么要 7 步？可以简化吗？

**答：** 7 步关闭序列的每一步都有特定目的：

1. **设置标志 + join 线程**：通知调度线程停止，等待最多 2s
2. **更新统计**：记录终态（成功/失败），用于监控和调试
3. **冻结统计 + 重置资源**：防止后续操作修改统计，释放资源管理器
4. **关闭算子**：释放算子持有的资源（如 Actor、文件句柄），带计时器防止卡死
5. **排空队列**：保留 sink 输出供消费者读取，排空中间队列释放内存
6. **触发回调**：通知外部监听器执行完成
7. **通知自动伸缩器**：停止请求新节点，避免浪费

不能简化的原因：如果跳过某些步骤，可能导致资源泄漏（如 Actor 未关闭）、统计不准确、或消费者无法获取最后的数据。

---

## 六、性能优化（4题）

### Q25: 如何优化 Ray Data 管道的性能？关键调优点有哪些？

**答：** 关键调优维度：

1. **Block 大小**：`target_max_block_size`（默认 128 MiB）。太大→内存压力，太小→调度开销
2. **并行度**：`parallelism`（读取时）和 `num_cpus`（转换时）。太低→资源浪费，太高→调度开销
3. **batch_size**：`map_batches` 的 batch_size。GPU 推荐大 batch（256-1024），CPU 根据内存调整
4. **Shuffle 优化**：先 filter 再 groupby，减少 shuffle 数据量
5. **Materialize 策略**：多次使用的数据集尽早物化，避免重复计算
6. **数据格式**：生产用 Parquet（列式、压缩、类型保留）
7. **Operator Fusion**：确保兼容的连续 Map 算子被融合

---

### Q26: 为什么说"先 filter 再 groupby"能提高性能？

**答：** groupby 是 Shuffle 操作，成本与数据量成正比。Shuffle 涉及：
- 网络 I/O：数据在节点间传输
- 磁盘 I/O：可能触发 Object Spilling
- 序列化/反序列化：Block 的序列化开销

如果先 filter 过滤掉不需要的数据，Shuffle 的数据量减少，所有成本都降低。

```
慢: ds.groupby("x").count().filter(lambda r: r["count"] > 10)
    → Shuffle 全部数据 → 过滤

快: ds.filter(lambda r: r["x"] in valid_keys).groupby("x").count()
    → 先过滤 → 只 Shuffle 有效数据
```

---

### Q27: `materialize()` 的使用时机是什么？什么时候不应该用？

**答：**

**应该用的场景：**
1. 一个数据集会被多次使用（如训练集和验证集的预处理结果）
2. 调试时想立即看到中间结果
3. 缓存耗时的转换结果（如复杂的特征工程）
4. 在 Shuffle 之前物化，避免重复 Shuffle

**不应该用的场景：**
1. 数据集只使用一次（浪费内存和时间）
2. 内存不足以容纳完整结果（会触发 Object Spilling）
3. 链式操作中间不需要查看结果
4. 流式消费场景（如 `iter_batches`，物化反而增加内存压力）

---

### Q28: 如何诊断和解决数据倾斜问题？

**答：** 数据倾斜的症状：某些 Task 的执行时间远大于其他 Task。

**诊断方法：**
1. 查看 Ray Dashboard 中的任务执行时间分布
2. 检查 `BlockExecStats` 中的 `wall_time_s`
3. 统计 groupby key 的分布

**解决方案：**
1. **过滤热点 key**：先过滤或单独处理
2. **采样**：对大数据集采样后再 groupby
3. **Repartition**：增加分区数，分散热点
4. **两阶段聚合**：先局部聚合（map-side combine），再全局聚合
5. **自定义分区**：对热点 key 使用专门的哈希函数

---

## 七、与 Spark/Dask 对比（4题）

### Q29: Ray Data 与 Spark 的 Shuffle 实现有什么区别？

**答：**

| 维度 | Ray Data | Spark |
|------|---------|-------|
| 架构 | Exoshuffle（控制面/数据面分离） | 内置于 Spark Engine |
| 中间存储 | Ray Object Store（共享内存） | 磁盘 + 内存 |
| Shuffle Manager | 可插拔策略（Hash/Sort/GPU） | SortShuffleManager / HashShuffleManager |
| 数据传输 | 通过 Ray Object Store | 通过 Netty HTTP / Shuffle Service |
| GPU 支持 | 原生 GPU Shuffle | 需要 RAPIDS Accelerator |
| 灵活性 | 高（策略可配置） | 中（内置实现） |

Spark 的 Shuffle 更成熟，有专用的 Shuffle Service 和磁盘溢写优化。Ray Data 的 Shuffle 更灵活，直接利用 Ray 的 Object Store，减少了额外的服务依赖。

---

### Q30: Ray Data 相比 Dask 的优势和劣势是什么？

**答：**

**优势：**
1. **ML 原生**：与 Ray Train/Serve 无缝集成，支持流式训练
2. **GPU 支持**：原生 GPU 资源管理和 GPU Shuffle
3. **Actor 模型**：有状态计算（如模型推理）更自然
4. **流式执行**：默认流式处理，内存效率更高
5. **统一框架**：ETL + 训练 + 推理 + 服务在同一框架

**劣势：**
1. **生态成熟度**：Dask 的 DataFrame API 更接近 pandas，用户更熟悉
2. **调度器**：Dask 的分布式调度器更成熟，有更丰富的调度策略
3. **社区规模**：Dask 社区更大，文档更完善
4. **纯数据处理**：对于纯 ETL 场景，Dask 可能更简单直接

---

### Q31: Ray Data 的流式执行与 Spark Structured Streaming 有什么区别？

**答：**

| 维度 | Ray Data | Spark Structured Streaming |
|------|---------|---------------------------|
| 数据源 | 批处理文件为主 | 流式源（Kafka、Socket）为主 |
| 执行模型 | 一次性批处理（内部流式） | 持续流式处理 |
| 触发模式 | 手动触发（show/materialize） | 持续触发（micro-batch / continuous） |
| 状态管理 | 无状态（除非用 Actor） | 有状态（watermark、window） |
| 端到端保证 | 无 | Exactly-once |

Ray Data 的"流式"是指**执行引擎内部的管道化处理**，而非外部的流式数据源。它仍然是批处理模型，但执行时以流式方式进行。

---

### Q32: 为什么 Ray Data 要重新实现一套数据处理引擎，而不是直接用 Spark/Dask？

**答：** 核心原因是**与 Ray 生态的深度集成**：

1. **共享内存零拷贝**：Block 直接存在 Ray Object Store，训练/推理可以直接读取，无需序列化/传输
2. **Actor 模型**：模型推理需要在 GPU 上保持状态，Spark/Dask 的 Task 模型不支持
3. **统一调度**：数据处理和训练/推理在同一 Ray 集群调度，资源利用率更高
4. **流式消费**：`streaming_split` 直接对接 Ray Train 的多 worker 训练，无需中间存储
5. **GPU 原生**：GPU 资源管理是一等公民，不需要额外插件

如果用 Spark 做 ETL，再用 Ray 做训练，数据需要在两个系统间传输（序列化→网络→反序列化），这是巨大的开销。Ray Data 消除了这个开销。

---

## 八、实战场景题（4题）

### Q33: 一个 Ray Data 管道出现 OOM，如何排查和解决？

**答：** 排查步骤：

1. **确认 OOM 位置**：查看 Ray Dashboard，确认是哪个算子/Task OOM
2. **检查 Block 大小**：`target_max_block_size` 是否过大
3. **检查是否有 Shuffle**：Shuffle 操作会物化所有输入，内存峰值高
4. **检查是否有 materialize**：不必要的物化占用内存

解决方案（按优先级）：
1. 减小 `batch_size`：降低单个 Task 的内存占用
2. 减小 `target_max_block_size`：降低 Block 大小
3. 避免不必要的 `materialize()`：使用流式处理
4. 先 filter 再 shuffle：减少 Shuffle 数据量
5. 增加 `repartition` 次数：分散内存压力
6. 增加集群节点：扩大总体内存容量

---

### Q34: 如何用 Ray Data 实现一个高吞吐的批量推理管道？

**答：** 关键设计：

```python
# 1. 使用 ActorPoolStrategy 保持模型在 GPU 上
@ray.remote(num_gpus=1)
class ModelActor:
    def __init__(self, model_path):
        self.model = load_model(model_path).to("cuda")

    def predict(self, batch):
        with torch.no_grad():
            return self.model(batch)

# 2. 使用 map_batches + ActorPoolStrategy
ds = ray.data.read_parquet("input/")
predictions = ds.map_batches(
    predict_fn,
    batch_format="pandas",
    batch_size=256,          # GPU 用大 batch
    num_gpus=1,              # 每个任务一个 GPU
    concurrency=4,           # 4 个并发 Actor
)

# 3. 流式写出
predictions.write_parquet("output/")
```

优化要点：
- `batch_size=256`：GPU 利用率高
- `num_gpus=1`：每个 Actor 独占一个 GPU
- `concurrency=4`：4 个 Actor 并行推理
- 流式写出：避免物化所有结果
- 使用 ActorPoolStrategy：模型只加载一次

---

### Q35: 如何处理数据源 Schema 不一致的问题？

**答：** Schema 不一致的常见原因：不同文件/分区的列类型不同、列缺失、列多余。

解决方案：

```python
# 1. 统一 Schema 的 map_batches 函数
def normalize_schema(batch: pd.DataFrame) -> pd.DataFrame:
    # 确保所有必需列存在
    for col in REQUIRED_COLUMNS:
        if col not in batch.columns:
            batch[col] = DEFAULT_VALUES[col]

    # 统一类型
    batch["age"] = pd.to_numeric(batch["age"], errors="coerce").fillna(0).astype(int)
    batch["amount"] = pd.to_numeric(batch["amount"], errors="coerce").fillna(0.0)

    # 选择和排序列
    batch = batch[REQUIRED_COLUMNS]

    return batch

# 2. 应用
ds = ray.data.read_csv("data/")
ds = ds.map_batches(normalize_schema, batch_format="pandas")
```

预防措施：
- 使用 Parquet 格式（Schema 写在文件元数据中）
- 在数据生成端强制 Schema 校验
- 使用 `schema` 参数显式指定读取 Schema

---

### Q36: 如何让 Ray Data 管道对接 Ray Train 进行分布式训练？

**答：** 使用 `streaming_split` 实现流式数据分发：

```python
import ray
from ray import train
from ray.train.torch import TorchTrainer

# 1. 准备数据集
ds = ray.data.read_parquet("training_data/")
ds = ds.random_shuffle()

# 2. 定义训练函数
def train_func():
    # 获取当前 worker 的数据分片
    shard = train.get_dataset_shard("train")

    for epoch in range(10):
        for batch in shard.iter_batches(batch_size=32, batch_format="pandas"):
            # 训练逻辑
            loss = model.train_step(batch)
            train.report({"loss": loss})

# 3. 配置 Trainer
trainer = TorchTrainer(
    train_func,
    scaling_config=ScalingConfig(num_workers=4, use_gpu=True),
    datasets={"train": ds},
)

# 4. 开始训练
result = trainer.fit()
```

关键点：
- `streaming_split` 自动将数据集分给 4 个 worker，无需手动分割
- `iter_batches` 流式消费，不需要物化所有数据
- `random_shuffle` 保证每个 epoch 的数据顺序不同
- 数据直接从 Object Store 读取，零拷贝

---

## 附录：关键概念速查表

| 概念 | 一句话解释 |
|------|-----------|
| Dataset | 惰性的分布式数据集，是执行计划容器而非数据容器 |
| Block | `Union[pyarrow.Table, pandas.DataFrame]`，数据的实际载体 |
| RefBundle | `List[Tuple[ObjectRef, BlockMetadata]]`，算子间传递的数据引用 |
| LogicalOperator | 逻辑计划节点，描述"做什么" |
| PhysicalOperator | 物理算子，描述"怎么做"，调度 Task/Actor |
| StreamingExecutor | 流式执行引擎，在守护线程中运行调度循环 |
| TaskPoolMapOperator | 无状态任务执行，每个 Block 一个 Ray Task |
| ActorPoolMapOperator | 有状态 Actor 池，支持自动伸缩和本地性调度 |
| Object Store | 分布式共享内存，存储 Block 数据 |
| Object Spilling | Object Store 满时溢写到磁盘 |
| ResourceManager | 追踪 CPU/GPU/Memory/Object Store 使用 |
| Backpressure | 背压机制，防止下游处理不过来 |
| Operator Fusion | 合并兼容的连续 Map 算子，减少序列化开销 |
| Shuffle | 全局数据重分布，阻塞式执行 |
| Exoshuffle | 控制面/数据面分离的 Shuffle 架构 |
| Lineage Recovery | 基于血统的对象恢复，重执行创建 Task |
| streaming_split | 将数据集流式分割给多个训练 worker |
| DataContext | 集中配置单例，管理所有 Ray Data 配置 |
