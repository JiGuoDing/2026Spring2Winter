# Flink 面试题

prompt:

你是一个 Flink 及流处理系统方面的专家，我在为应聘流处理系统、实时处理相关后端岗位的面试做准备，所以接下来我会问你一些与 Flink 流式处理系统和后端相关的问题。注意我想把每个问题以及你给我的回答记录下来，因此你需要确保你的回答的正确性和严谨性，同时你要确保你的回答是有条理的、逻辑明确的，这样我在后续复盘时能方便地回顾，此外，你的回答应当是细致的、深入的，因为这是面试问题，不能仅仅局限于表面，要深挖内核。我会使用 markdown 做笔记，因此你最好以 markdown 的格式回答我的问题。同时最好辅以例子说明，这样便于我的理解，如果能有有关代码及详细注释就更好了。在最后你需要进行知识扩展，讲讲你认为和这个知识点相关联的其他知识点，不需要太细，只需要说明有着怎样的关联即可。另外，如果有括号的话，请用英文括号 () 而不是中文括号（）。在最后，你需要形成一个完整的、有条理的、连贯的、没有遗漏的对问题的回复，以便我以自然地回复面试官。

## 1. 窗口 Window

### 1.1 .reduce() 和 .aggregate() 的异同点

在 Flink 中，`.reduce()` 和 `.aggregate()` 都属于增量聚合算子，区别在于类型的灵活性。`.reduce()` 要求输入类型和输出类型必须一致，使用时只需实现一个 `reduce(value1, value2)` 方法，将两个元素合并为一个同类型的结果，适合求最大值、累加等场景，简单直接。`.aggregate()` 则更加灵活，输入类型、中间累加器类型、输出类型三者可以完全不同，使用时需要实现 `AggregateFunction` 接口中的四个方法：`createAccumulator()`（初始化累加器）、`add()`（定义每条数据如何累加到累加器）、`getResult()`（窗口触发时从累加器中提取最终结果）、`merge()`（合并两个累加器，用于 Session Window 等场景），适合求平均值这类需要维护中间状态且输出类型与输入不同的场景。总结来说，`.reduce()` 是 `.aggregate()` 的简化版，当输入输出类型相同时用 `.reduce()` 更简洁，当需要类型转换或自定义中间状态时用 `.aggregate()` 更合适，两者性能上都优于 `.process()` 全量计算。

## 2. 优化策略

### 2.2 在 Flink 中，如何处理数据倾斜问题？有哪些常见的优化手段？

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
