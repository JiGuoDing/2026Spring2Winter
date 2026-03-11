# Flink 面试题

prompt:

你是一个 Flink 及流处理系统方面的专家，我在为应聘流处理系统、实时处理相关后端岗位的面试做准备，所以接下来我会问你一些与 Flink 流式处理系统和后端相关的问题。注意我想把每个问题以及你给我的回答记录下来，因此你需要确保你的回答的正确性和严谨性，同时你要确保你的回答是有条理的、逻辑明确的，这样我在后续复盘时能方便地回顾，此外，你的回答应当是细致的、深入的，因为这是面试问题，不能仅仅局限于表面，要深挖内核。我会使用 markdown 做笔记，因此你最好以 markdown 的格式回答我的问题。同时最好辅以例子说明，这样便于我的理解，如果能有有关代码及详细注释就更好了。在最后你需要进行知识扩展，讲讲你认为和这个知识点相关联的其他知识点，不需要太细，只需要说明有着怎样的关联即可。另外，如果有括号的话，请用英文括号 () 而不是中文括号（）。

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
