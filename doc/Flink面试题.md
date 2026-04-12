# Flink 面试题

prompt:

你是一个 Flink 及流处理系统方面的专家，我在为应聘流处理系统、实时处理相关后端岗位的面试做准备，所以接下来我会问你一些与 Flink 流式处理系统和后端相关的问题。注意我想把每个问题以及你给我的回答记录下来，因此你需要确保你的回答的正确性和严谨性，同时你要确保你的回答是有条理的、逻辑明确的，这样我在后续复盘时能方便地回顾，此外，你的回答应当是细致的、深入的，因为这是面试问题，不能仅仅局限于表面，要深挖内核。我会使用 markdown 做笔记，因此你最好以 markdown 的格式回答我的问题。同时最好辅以例子说明，这样便于我的理解，如果能有有关代码及详细注释就更好了。在最后你需要进行知识扩展，讲讲你认为和这个知识点相关联的其他知识点，不需要太细，只需要说明有着怎样的关联即可。另外，如果有括号的话，请用英文括号 () 而不是中文括号（）。在最后，你需要形成一个完整的、有条理的、连贯的、没有遗漏的对问题的回复，以便我以自然地回复面试官。

## 1. 窗口 Window

### 1.1 .reduce() 和 .aggregate() 的异同点

在 Flink 中，`.reduce()` 和 `.aggregate()` 都属于增量聚合算子，区别在于类型的灵活性。`.reduce()` 要求输入类型和输出类型必须一致，使用时只需实现一个 `reduce(value1, value2)` 方法，将两个元素合并为一个同类型的结果，适合求最大值、累加等场景，简单直接。`.aggregate()` 则更加灵活，输入类型、中间累加器类型、输出类型三者可以完全不同，使用时需要实现 `AggregateFunction` 接口中的四个方法：`createAccumulator()`（初始化累加器）、`add()`（定义每条数据如何累加到累加器）、`getResult()`（窗口触发时从累加器中提取最终结果）、`merge()`（合并两个累加器，用于 Session Window 等场景），适合求平均值这类需要维护中间状态且输出类型与输入不同的场景。总结来说，`.reduce()` 是 `.aggregate()` 的简化版，当输入输出类型相同时用 `.reduce()` 更简洁，当需要类型转换或自定义中间状态时用 `.aggregate()` 更合适，两者性能上都优于 `.process()` 全量计算。

## 2. 优化策略

### 2.1 在 Flink 中，如何处理数据倾斜问题？有哪些常见的优化手段？

#### 如何发现数据倾斜

在 Flink Web UI 中观察：

- `SubTask` 的 `Records Received` 和 `Bytes Received` 差异极大
- 某个 SubTask 的 Back Pressure 持续为 High
- 各 SubTask 完成时间差异显著

#### 核心优化策略

##### 策略一：Local Pre-Aggregation (两阶段聚合)

原理：在 `keyBy` + 全局聚合之前，先在本地 (SubTask 内) 做一次预聚合，大幅减少下游数据量

使用场景：`COUNT`, `SUM`, `MAX`, `MIN` 等可以分阶段计算的聚合操作

##### 策略二：keyBy 加盐 (Salt Key) + 分桶

原理：给热点 Key 加随机后缀，将一个热点 Key 拆分成多个 Key 并行处理，最后再合并

使用场景：热点 Key 明确，可以提前识别

##### 策略三：使用 rebalance() / rescale() 解决 Source 倾斜

原理：当数据倾斜来源于 Source 端分区不均时 (如 Kafka 某分区数据量远大于其他分区)，可以用 `rebalance()` 做轮询重分区

##### 策略四：自定义 Partitioner

原理：针对业务特点，实现自定义分区逻辑，将热点 Key 分散到多个 SubTask

##### 策略五：大表 Join 优化 (Broadcast Join)

原理：当一个大表和一个小表 Join 时，避免大表 shuffle，将小表广播到所有 SubTask，直接在本地做 Join，消除 Join Key 导致的倾斜

##### 策略六：调整并行度与资源

原理：通过提高热点算子的并行度，增加处理能力来缓解倾斜带来的压力 (治标)

### 2.2 Flink 的 Operator Chain 是如何工作的？如何通过调整链优化作业性能？

Operator Chain 是 Flink 在同一个 Task 内将多个可串联算子拼接执行的运行时优化机制。它的核心目标是减少网络传输、序列化反序列化和线程切换开销，从而提升吞吐并降低延迟。

面试里可以先给一句定义：Operator Chain 本质上是把“本来可能跨线程/跨网络边界的算子”尽量下沉到同一个执行线程里，形成函数调用级别的数据传递。

#### 一、Operator Chain 是怎么形成的

Flink 在生成 JobGraph/ExecutionGraph 时，会判断两两相邻算子能否 chain。典型前提包括：

1. 上下游并行度一致。
2. 分区方式允许前向传输 (典型是 Forward，而不是需要 shuffle 的 keyBy/rebalance)。
3. 两个算子都允许 chaining (没有显式禁用)。
4. Slot sharing 与资源约束不冲突。

可以把它理解为：只要运行时不需要“重分发数据”，且调度约束允许，就有机会放进同一条链。

示意图如下：

```plaintext
未链式执行:
Source -> Map -> Filter -> Sink
  |        |        |       |
 TaskA   TaskB    TaskC   TaskD

链式执行后 (理想情况):
[Source -> Map -> Filter] -> Sink
      TaskA             TaskB
```

链起来后，链内记录通常通过内存对象直接传递，不必每步都走网络栈和序列化。

#### 二、Operator Chain 的收益与代价

##### 收益

1. 更低延迟
  减少跨 Task 边界传输，链内是本地调用路径。
2. 更高吞吐
  降低序列化和网络 buffer 开销，CPU 可更多用于业务计算。
3. 更低资源开销
  线程和网络连接数量减少，调度与上下文切换成本下降。

##### 代价和边界

1. 故障隔离粒度变粗
  同链算子共享同一执行上下文，定位热点与瓶颈有时不如拆链直观。
2. 反压传播更直接
  链尾慢会快速传导到链头，可能放大局部抖动。
3. 不适合“冷热算子混跑”
  一个极重 CPU 算子和轻算子强行链在一起，可能影响整体稳定性。

#### 三、哪些场景应当主动拆链

以下场景常见要考虑拆链：

1. 链中某个算子特别重
  例如复杂 JSON 解析、外部 RPC、加解密等，会拖慢整个链。
2. 需要独立调并行度或资源
  例如下游 sink 受限明显，希望单独扩并行度和 slot 资源。
3. 需要更清晰观测
  拆链后 Web UI 指标更细，便于定位反压来源。
4. 算子需要隔离故障域
  外部系统交互算子常单独链路更稳妥。

#### 四、如何通过调整 chain 做性能优化

##### 策略一：默认先让轻量算子链起来

对于纯计算轻操作 (map/filter/flatMap)，优先保持 chaining，先吃到低开销收益。

##### 策略二：在重算子前后打断链

把 CPU 或 IO 重负载算子独立出来，避免整链被单点拖慢。

##### 策略三：结合并行度与 slot sharing 调整

拆链通常要配合并行度、slot sharing group 一起看，否则可能只是“拆了图”，却没有得到资源收益。

##### 策略四：通过压测比较 P50/P99 与吞吐

不要只看平均吞吐，重点看尾延迟与反压持续时长，选更稳的方案。

#### 五、常用 API 与代码示例

```java
DataStream<Event> stream = env.addSource(new EventSource())
   .name("source");

DataStream<Event> parsed = stream
   .map(new ParseMapFunction())
   .name("parse")
   // 从这个算子开始一条新链，适合把后续重算子隔离
   .startNewChain();

DataStream<Event> enriched = parsed
   .map(new EnrichMapFunction())
   .name("enrich")
   // 禁止本算子与上下游 chain，适合重 CPU/外部调用场景
   .disableChaining();

DataStream<Event> filtered = enriched
   .filter(new RiskFilter())
   .name("risk-filter")
   // 让轻量过滤和下游可继续链式执行
   .slotSharingGroup("compute");

filtered
   .addSink(new AlertSink())
   .name("alert-sink")
   // sink 常常单独资源组，避免与上游互相影响
   .slotSharingGroup("sink");
```

代码解读：

1. `startNewChain()` 用于人为切分链边界。
2. `disableChaining()` 用于彻底禁止当前算子参与链。
3. `slotSharingGroup()` 控制资源共享域，常与链策略联动。

#### 六、一个可复盘的调优流程

1. 先看 Web UI：确认瓶颈是网络、CPU 还是下游外部系统。
2. 导出当前拓扑：观察哪些算子已 chain，哪些在跨 Task 传输。
3. 对重算子试验拆链：固定输入流量做 A/B 压测。
4. 对比指标：`numRecordsIn/Out`、busyTime、backPressure、P99 延迟。
5. 收敛方案：在吞吐、尾延迟、稳定性三者间取平衡，而不是只追单一峰值。

#### 七、常见误区

##### 1. 误区：链越长越好

错误。链过长会让瓶颈算子拖累整链，且可观测性变差。

##### 2. 误区：拆链一定提升性能

错误。拆链会增加网络和序列化开销，轻量算子盲目拆链反而降性能。

##### 3. 误区：只调 chain 不调资源

不完整。链策略必须与并行度、slot sharing、外部系统限流一起优化。

#### 八、面试时可以怎么总结

可以这样回答：Flink 的 Operator Chain 是把可串联算子放在同一 Task 内执行的运行时优化，核心收益是减少网络与序列化开销。优化时通常遵循“轻算子尽量链、重算子适度拆、并行度与资源组联动调优”的原则，并通过压测验证吞吐与 P99 延迟的综合收益。

#### 知识扩展

- Task 与 Slot：Operator Chain 最终落在 Task 执行单元上，理解 Slot 分配有助于解释链的资源边界。
- Forward/Shuffle 分区：是否需要重分区直接决定链能否跨算子成立。
- Back Pressure 机制：链内慢算子会更快向上游传播反压，和链设计强相关。
- Checkpoint 对齐成本：链结构会影响 barrier 传播路径与算子观测粒度。

## 3. State 状态管理

### 3.1 Flink 中的 Broadcast State 是什么？它在分布式计算中的作用是什么？

Boradcast State 是 Flink 中一种特殊的算子状态 (Operator State)，它允许将一条数据流 (通常是数据量较小、需要被所有并行子任务共享的流) 广播到所有并行 SubTask 中，每个 SubTask 都持有该状态的完整副本，从而实现 “一份数据，全局可见" 的效果。

```plaintext
普通 KeyedState (按 Key 分区):
                    ┌──────────────┐
数据流 ──keyBy()──▶  │  SubTask-0   │  只存储属于自己 Key 的状态
                    │  state: {A}  │
                    └──────────────┘
                    ┌──────────────┐
                  ▶ │  SubTask-1   │  只存储属于自己 Key 的状态
                    │  state: {B}  │
                    └──────────────┘

Broadcast State (广播状态):
                    ┌──────────────────────┐
广播流 ──────────▶   │  SubTask-0           │
                    │  broadcast: {A,B,C}  │  每个 SubTask 都有完整副本
                    └──────────────────────┘
                    ┌──────────────────────┐
              ──▶   │  SubTask-1           │
                    │  broadcast: {A,B,C}  │  完整副本
                    └──────────────────────┘
                    ┌──────────────────────┐
              ──▶   │  SubTask-2           │
                    │  broadcast: {A,B,C}  │  完整副本
                    └──────────────────────┘
```

在分布式流处理中，经常会遇到这样的需求：

> 有一条持续更新的配置流 (规则、维度表、黑名单等)，需要被所有 SubTask 实时感知，并用来处理另一条高吞吐的数据流。

Broadcast State 的价值：提供了一种低延迟、动态更新、全局共享的状态共享机制。

#### Broadcast State 的数据模型

Broadcast State 只支持 `MapState` 形式，即 `Map<K, V>` 结构

```java
// Broadcast State 的描述符，只能是 MapStateDescriptor
MapStateDescriptor<String, Rule> ruleStateDescriptor = new MapStateDescriptor<>(
    "rule-broadcast-state",   // 状态名称
    Types.STRING,             // Key 类型 (规则 ID)
    Types.POJO(Rule.class)    // Value 类型 (规则内容)
);
```

> 为什么只支持 Map？ Map 结构便于按 Key 进行精准的增删改查，而 Broadcast State 通常用于存储规则集合，Map 能天然支持规则的动态新增、修改和删除。

#### Broadcast State 的核心 API

Flink 提供两种使用 Broadcast State 的方式，取决于数据流是否需要 `keyBy`

```plaintext
数据主流 (非广播流)
    │
    │   .connect(broadcastStream)
    │◀──────────────────────────── 广播流.broadcast(descriptor)
    │
    ▼
BroadcastConnectedStream
    │
    │   .process(BroadcastProcessFunction)     ← 非 KeyedStream
    │   .process(KeyedBroadcastProcessFunction) ← KeyedStream
    │
    ▼
  输出流
```

##### 非 keyed 场景：BroadcastProcessFunction

##### keyed 场景：KeyedBroadcastProcessFunction

`KeyedBroadcastProcessFunction` 比 `BroadcastProcessFunction` 多了访问 KeyedState 的能力。

#### Broadcast State 的内部机制

##### 数据流向机制

```plaintext
广播流数据 (一条规则更新消息)
       │
       │  Flink 运行时将此消息复制 N 份
       │  (N = 下游算子的并行度)
       │
       ▼
  ┌────┴────┐
  ├─────────┤──▶ SubTask-0.processBroadcastElement() ──▶ BroadcastState-0
  ├─────────┤──▶ SubTask-1.processBroadcastElement() ──▶ BroadcastState-1
  ├─────────┤──▶ SubTask-2.processBroadcastElement() ──▶ BroadcastState-2
  └─────────┘──▶ SubTask-3.processBroadcastElement() ──▶ BroadcastState-3

每个 SubTask 独立维护一份完整的 Broadcast State 副本
```

##### 读写权限设计 (重要)

| 方法                      | 可访问的状态                              | 广播状态权限 |
| ------------------------- | ----------------------------------------- | ------------ |
| processElement()          | BroadcastState (只读) + KeyedState (读写) | 只读         |
| processBroadcastElement() | BroadcastState (读写)                     | 读写         |

> 为什么 `processElement()` 中广播状态只读？
>
> `processElement()` 由多个 SubTask 并行执行，如果允许写入广播状态，不同 SubTask 对同一个 Key 对写入会产生竞争，导致各 SubTask 的广播状态出现不一致。而 `processBroadcastElement()` 由于广播机制保证每个 SubTask 都独立执行相同的写入逻辑，所以可以安全写入，最终所有副本保持一致。

##### Checkpoint 机制

```plaintext
Checkpoint 触发
       │
       ▼
每个 SubTask 独立将自己的 Broadcast State 副本序列化
并写入 State Backend (如 RocksDB / 内存)

SubTask-0 ──保存──▶ checkpoint/subtask-0/broadcast-state
SubTask-1 ──保存──▶ checkpoint/subtask-1/broadcast-state
SubTask-2 ──保存──▶ checkpoint/subtask-2/broadcast-state

恢复时：
每个 SubTask 从自己的 checkpoint 文件中独立恢复广播状态
```

> 注意：由于每个 SubTask 都保存完整副本，Broadcast State 的存储开销 = 单副本大小 × 并行度，因此广播状态不宜过大。

#### 使用限制和注意事项

```java
// ⚠️ 注意事项 1：广播状态数据量不能过大
// 广播状态会在每个 SubTask 存一份完整副本
// 建议：单个 Broadcast State 控制在 MB 级别，通常不超过 100MB

// ⚠️ 注意事项 2：processBroadcastElement() 中不能访问 KeyedState
// KeyedBroadcastProcessFunction 中：
// processElement()         ✅ 可以访问 KeyedState
// processBroadcastElement() ❌ 不能访问 KeyedState (没有当前 Key 的上下文)

// ⚠️ 注意事项 3：广播流并行度通常设为 1
// 若广播流并行度 > 1，相同 Key 的更新消息可能乱序到达不同 SubTask
// 导致各 SubTask 的广播状态出现短暂不一致
ruleStream
    .setParallelism(1)       // 推荐设为 1，保证顺序
    .broadcast(ruleStateDesc);

// ⚠️ 注意事项 4：Broadcast State 只支持 MapStateDescriptor
// 不能使用 ValueStateDescriptor / ListStateDescriptor 等
// ✅ 正确
MapStateDescriptor<String, Rule> desc = new MapStateDescriptor<>(...);
// ❌ 错误 (编译报错)
ValueStateDescriptor<Rule> desc = new ValueStateDescriptor<>(...);
```

## 4. 架构演进

### 4.1 Flink 2.0 的存算分离架构是怎样的？具体是怎么实现的？

Flink 2.0 语境下的“存算分离”，核心不是简单地把一个组件拆成两半，而是将实时计算与状态存储解耦：计算层负责接收数据、执行算子、维护窗口和状态访问逻辑；存储层负责持久化保存大状态、增量变化和检查点数据。这样做的目标是让计算节点尽量保持轻量化，降低本地磁盘和内存压力，同时提升弹性扩缩容能力和故障恢复效率。

从面试角度看，可以把它理解为三个层次的变化：

1. 状态不再完全依赖本地机器

   传统 Flink 很依赖 TaskManager 本地的状态后端，例如 RocksDB 本地盘状态加上 checkpoint 远端持久化。存算分离后，状态的主存放位置更偏向远端共享存储或分层存储，本地只保留热点缓存和短期工作集。

2. 计算与状态的访问路径被重新设计

   算子访问状态时，不再默认认为所有数据都在本地，而是通过运行时的状态访问层去读写远端状态。系统会结合本地缓存、增量日志和异步刷写来降低远端访问开销。

3. 恢复和迁移更轻量

   当作业失败、扩缩容或重新调度时，不需要把大量状态文件跟着计算节点一起搬走，而是让新计算节点重新挂载远端状态并按需拉取热点数据，从而减少恢复时间和资源浪费。

#### 核心实现思路

Flink 的存算分离通常不是单一技术点，而是由下面几部分共同支撑：

##### 1. 远端状态存储

状态的最终持久化位置从“机器本地”转向“共享存储”或“远端存储系统”，例如对象存储、分布式文件系统，或者专门的状态服务层。计算节点只负责读写状态的访问请求，不再承担全部持久化压力。

##### 2. 本地缓存 + 异步刷新

为了避免每次状态访问都直连远端存储，运行时一般会保留一层本地缓存，保存高频访问的 key、窗口状态或算子元数据。写入则尽量采用异步方式批量提交，减少远端 I/O 放大。

##### 3. 增量变更日志 (Changelog)

很多实现不会每次都把整个状态重新写一遍，而是记录“状态变更日志”。例如某个 `ValueState` 从 `10` 变成 `12`，系统只记录这次变更，而不是重新上传整个状态快照。这样 checkpoint 更小、恢复时也更快。

##### 4. 快照与日志结合

更完整的做法通常是“全量快照 + 增量日志”组合：

- 全量快照用于提供一个可恢复的基线
- 增量日志用于记录两次快照之间的变化

恢复时先加载基线快照，再回放增量日志，最终还原出最新状态。

#### 典型运行流程

```plaintext
数据进入算子
  │
  ▼
算子先查本地缓存
  │
  ├─ 命中：直接读写本地缓存，减少远端访问
  │
  └─ 未命中：向远端状态存储拉取对应状态
          │
          ▼
       更新本地缓存并继续计算
          │
          ▼
       产生状态变更日志或异步刷写
          │
          ▼
      checkpoint 时统一持久化
```

#### 为什么这能称为“存算分离”？

因为它把“算”的生命周期和“存”的生命周期拆开了：

- 算可以按资源弹性伸缩，实例可以更轻、更短生命周期
- 存由独立的持久化层承接，状态可以跨任务、跨节点长期保留

这和传统的“计算节点自己背着全部状态走”相比，最大的区别就是：计算节点不再是状态唯一载体。

#### 优势

- 扩缩容更快：新节点不必完整搬运大状态，主要是按需加载热点数据
- 恢复更快：失败后依赖远端持久化和增量日志恢复，避免大规模本地重建
- 资源利用率更高：本地磁盘和内存压力下降，计算层更容易做弹性调度
- 大状态更友好：对超大窗口、复杂维表关联、长周期状态更有优势

#### 代价和限制

- 状态访问延迟会上升：远端存储一定比纯本地状态慢，所以必须依赖缓存和增量机制
- 系统复杂度更高：需要处理一致性、回放顺序、缓存失效和写放大问题
- 对网络和远端存储依赖更强：网络抖动或存储热点会直接影响作业稳定性

#### 举个例子

假设一个订单实时风控作业需要维护用户近 30 天的行为画像状态：

- 传统模式下，这些状态大概率放在 TaskManager 本地 RocksDB，checkpoint 时再整体快照到远端
- 存算分离模式下，用户画像状态可能先写入远端状态层，本地只缓存最近活跃用户的画像数据
- 当作业重启或扩容时，新并行实例直接挂载远端状态，按需恢复最近活跃 key 的数据，而不是把整个画像库重新导入一遍

```java
// 伪代码：表达存算分离下“本地缓存 + 远端状态”的访问方式
public class RiskProcessFunction extends KeyedProcessFunction<String, OrderEvent, String> {

  @Override
  public void processElement(OrderEvent event, Context ctx, Collector<String> out) throws Exception {
    // 1. 优先读取本地缓存中的用户画像
    UserProfile profile = localCache.get(event.getUserId());

    // 2. 缓存未命中时，再从远端状态层拉取
    if (profile == null) {
      profile = remoteStateStore.get(event.getUserId());
      localCache.put(event.getUserId(), profile); // 回填缓存
    }

    // 3. 基于画像和实时事件计算风控分
    String result = evaluate(event, profile);
    out.collect(result);

    // 4. 状态更新只写变更，不一定每次都全量刷盘
    remoteStateStore.update(event.getUserId(), profile);
  }
}
```

#### 面试时可以怎么总结

可以直接概括为：Flink 2.0 的存算分离，本质上是把状态从计算节点中抽离出来，由远端持久化层承担主存储职责，计算节点只保留热点缓存和执行逻辑。实现上通常依赖远端状态存储、本地缓存、异步刷写、增量日志和快照恢复等机制，最终目标是提升大状态作业的弹性、恢复速度和资源利用率。

#### 知识扩展

- Checkpoint 和 Savepoint：存算分离后仍然依赖一致性快照机制做恢复和迁移
- RocksDB State Backend：理解它有助于对比本地状态后端和远端状态层的差异
- Changelog State Backend：它和存算分离关系很紧密，都是通过记录增量来减少全量状态搬运
- 资源隔离与弹性伸缩：存算分离的收益最终会体现在作业扩缩容和故障恢复上
- 大状态优化：例如 TTL、分层存储、热点缓存和状态压缩，都是和这个主题强相关的配套能力
