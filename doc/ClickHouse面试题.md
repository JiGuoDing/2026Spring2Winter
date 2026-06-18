# ClickHouse 面试题

## prompt

你是 ClickHouse、OLAP 数据库和实时分析系统方面的专家。我正在为应聘数据仓库、数据工程、数据平台、实时数仓、OLAP 引擎、MPP 数据库、湖仓一体、数据服务和后端数据系统等相关岗位做面试准备。接下来我会向你提问一些与 ClickHouse 架构原理、表引擎、MergeTree、分区和排序键、主键索引、数据跳数索引、物化视图、投影、查询执行、数据写入、集群部署、副本和分片、Distributed 表、ClickHouse Keeper、性能优化、集群运维以及与 Kafka、Flink、Spark、Hive、S3、HDFS 等生态集成相关的问题。

请你在回答时注意以下要求：

1. **准确严谨**
   - 确保回答在技术上正确、严谨，避免含糊或不确定的表述。
   - 如果涉及 ClickHouse 的内部机制或架构设计，请尽量从列式存储、MergeTree 表引擎、Part、Partition、Primary Key、ORDER BY、稀疏索引、数据跳数索引、分片副本、Distributed 表、后台 Merge、向量化执行和资源管理等角度解释清楚。

2. **结构清晰**
   - 使用 Markdown 格式回答，方便我记录和复盘。
   - 回答要有清晰的层次结构，例如：概念定义、核心原理、执行流程、设计方法、优缺点、典型场景、性能优化、面试回答总结等。

3. **深入但不冗长**
   - 不要只停留在表面概念，要适当深入到底层原理和设计动机。
   - 但也要避免过度发散，重点围绕面试中可能被追问的内容展开。

4. **结合例子说明**
   - 如果有必要，请结合具体例子帮助理解。
   - 如果适合使用 SQL、伪代码、建表示例、导入示例或查询执行链路示例，请给出简洁示例，并添加必要注释。

5. **便于面试表达**
   - 在回答最后，请给出一段完整、连贯、适合在面试中直接表达的总结性回答。
   - 这段回答要自然、有逻辑，避免像背诵定义。

6. **知识扩展**
   - 在最后补充与当前问题相关的知识点，例如 MergeTree、ReplacingMergeTree、SummingMergeTree、AggregatingMergeTree、ReplicatedMergeTree、Distributed 表、ClickHouse Keeper、稀疏索引、数据跳数索引、物化视图、Projection、TTL、后台 Merge、Kafka Engine、S3 表函数、冷热分层、低基数字段优化等。
   - 扩展部分不需要过细，只需说明它们和当前问题的关联。

另外，如果回答中出现括号，请使用英文括号 ()，不要使用中文括号。

## 1. ClickHouse 基础

### 1.1 什么是 ClickHouse？它主要解决什么问题？

ClickHouse 是一个面向 OLAP 场景的列式分析型数据库，主要用于在大规模数据上进行低延迟查询、多维分析、报表统计、日志分析、用户行为分析和实时数据服务。

面试里可以先用一句话概括：ClickHouse 是一个以列式存储和向量化执行为核心的高性能 OLAP 数据库，特别适合对海量明细数据做快速过滤、聚合和分析查询。

#### 一、ClickHouse 的核心定位

ClickHouse 不是传统 OLTP 数据库，它不适合承担高并发事务写入、复杂事务处理、跨行强一致更新这类业务库职责。它更适合面向分析查询，也就是 OLAP (Online Analytical Processing) 场景。

典型特点包括：

1. 支持海量数据的聚合、过滤、排序和明细查询。
2. 支持高吞吐批量写入和准实时查询。
3. 内部使用列式存储、压缩、稀疏索引、向量化执行等机制提升查询性能。
4. 支持丰富的表引擎，可以针对不同场景选择不同的数据组织方式。

#### 二、ClickHouse 主要解决的问题

在数据平台中，ClickHouse 经常用于解决以下问题：

1. 报表查询慢：传统离线数仓查询延迟较高，不适合交互式分析。
2. 明细分析难：业务希望在海量明细数据上快速做过滤、聚合和下钻。
3. 日志检索和指标分析成本高：监控、埋点、行为日志通常数据量大、字段多、查询维度灵活。
4. 数据服务响应慢：需要为接口、看板或运营系统提供低延迟聚合查询。

#### 三、ClickHouse 的典型使用场景

- 实时 BI 看板：订单、广告、流量、支付等指标快速查询。
- 用户行为分析：基于事件明细做留存、漏斗、路径和分群分析。
- 日志分析：对服务日志、埋点日志、监控数据做过滤和聚合。
- 指标分析：承接时序指标、宽表指标和多维聚合查询。
- 数据服务：为业务系统提供低延迟 SQL 或接口查询能力。
- 离线数仓加速：把 Hive、Spark 或湖仓加工后的结果写入 ClickHouse 提供快速查询。

#### 四、面试时可以怎么总结

可以这样回答：ClickHouse 是一个面向 OLAP 场景的列式分析型数据库，底层通过列式存储、数据压缩、稀疏索引、向量化执行和 MergeTree 表引擎来提升查询性能。它常用于实时看板、日志分析、用户行为分析、指标分析和数据服务场景，解决传统离线数仓查询延迟高、明细数据分析慢、交互式分析体验差等问题。

#### 知识扩展

- OLAP：ClickHouse 的核心使用场景，面向分析查询而不是事务处理
- 列式存储：提升聚合和过滤查询效率
- MergeTree：ClickHouse 最核心的表引擎家族
- 稀疏索引：通过主键索引减少读取的数据范围
- 数据服务：ClickHouse 常作为宽表查询和聚合查询的服务层

### 1.2 ClickHouse 的整体架构是怎样的？分片、副本和 Distributed 表分别是什么？

ClickHouse 的基本架构由多个 ClickHouse Server 节点组成。每个节点既可以存储数据，也可以执行查询。集群模式下，数据通常会按分片 (Shard) 水平切分，并通过副本 (Replica) 提升可用性，跨分片查询通常通过 Distributed 表完成。

可以把 ClickHouse 理解成一个偏 Shared-Nothing 的分布式分析系统：每个节点保存自己负责的数据，查询时多个节点并行扫描本地数据，再把中间结果汇总。

#### 一、ClickHouse Server 的职责

ClickHouse Server 是最核心的进程，常见职责包括：

1. 接收客户端 SQL 请求，支持 HTTP、Native TCP、JDBC、ODBC 等访问方式。
2. 管理本地表的数据文件、元数据、后台 Merge 和 Mutation。
3. 执行 Scan、Filter、Aggregate、Join、Sort 等查询算子。
4. 参与分布式查询，把子查询下发到其他分片节点。
5. 维护副本数据同步和分布式 DDL 执行。

ClickHouse 不像一些 MPP 数据库那样有固定的 FE/BE 两层角色，更多是每个 Server 都可以承担接入、存储和计算职责。

#### 二、分片和副本

分片用于水平扩展容量和计算能力。比如一张大表的数据可以按用户 ID 或订单 ID 分散到多个 Shard 上，每个 Shard 只保存一部分数据。

副本用于提升可用性和读能力。同一个 Shard 可以有多个 Replica，每个 Replica 保存相同的数据。某个副本不可用时，查询可以路由到其他副本。

生产环境中，如果使用 ReplicatedMergeTree 系列表引擎，副本之间通常依赖 ClickHouse Keeper 或 ZooKeeper 协调元数据和复制任务。

#### 三、Distributed 表的作用

Distributed 表本身通常不存储数据，它更像一层分布式查询入口。用户查询 Distributed 表时，ClickHouse 会根据集群配置把查询下发到各个分片的本地表，再汇总结果。

一个典型模式是：

1. 每个节点上创建本地表，比如 events_local。
2. 再创建 Distributed 表，比如 events_all。
3. 写入或查询 events_all 时，由 ClickHouse 根据分片规则路由到各个本地表。

#### 四、一次查询的大致流程

一次分布式 SQL 查询通常会经历以下流程：

1. 客户端连接任意一个 ClickHouse Server。
2. Server 解析 SQL，生成本地或分布式执行计划。
3. 如果查询的是 Distributed 表，Server 会把子查询发送到相关 Shard。
4. 各个 Shard 上的节点并行扫描本地 MergeTree 数据。
5. 本地节点完成过滤、预聚合或排序等计算。
6. 发起节点汇总各分片结果，并返回给客户端。

#### 五、面试时可以怎么总结

可以这样回答：ClickHouse 的集群由多个 Server 节点组成，每个节点都可以存储数据和执行查询。数据通过 Shard 做水平切分，通过 Replica 做高可用和读扩展，跨分片查询通常通过 Distributed 表完成。查询 Distributed 表时，请求会被下发到多个分片并行执行，再由发起节点汇总结果。副本协调通常依赖 ClickHouse Keeper 或 ZooKeeper，核心目标是让存储、计算和查询并行扩展。

#### 知识扩展

- Shard：用于横向拆分数据，提升容量和并行计算能力
- Replica：用于容错和读扩展
- Distributed 表：分布式查询和分布式写入的逻辑入口
- ReplicatedMergeTree：支持副本复制的 MergeTree 表引擎
- ClickHouse Keeper：ClickHouse 自带的协调服务，可替代 ZooKeeper 用于副本协调

### 1.3 ClickHouse 有哪些核心功能？

ClickHouse 的核心功能可以从数据写入、表引擎、查询分析、性能加速、生态集成和运维管理几个方面理解。

#### 一、数据写入能力

ClickHouse 支持多种写入方式，适配不同数据来源和实时性要求。

常见方式包括：

- Insert Into：适合通过 SQL 写入小批量或批量数据。
- HTTP 接口：适合服务端程序或脚本直接导入数据。
- clickhouse-client：适合命令行导入和运维操作。
- Kafka Engine：适合持续消费 Kafka 数据，并配合物化视图落入 MergeTree 表。
- Flink Connector：适合把 Flink 实时计算结果写入 ClickHouse。
- S3、HDFS、File 表函数：适合从对象存储、HDFS 或本地文件读取外部数据。

面试中可以强调：ClickHouse 写入通常更适合批量追加，不适合像 OLTP 数据库一样频繁单行更新。

#### 二、表引擎能力

ClickHouse 的表引擎非常丰富，决定了数据的存储方式、复制方式、聚合语义和查询行为。

常见表引擎包括：

1. MergeTree：最核心的本地存储引擎，适合大多数明细分析场景。
2. ReplacingMergeTree：适合按 Key 做最终去重或保留最新版本。
3. SummingMergeTree：适合对部分数值列做预聚合。
4. AggregatingMergeTree：适合保存聚合函数中间状态。
5. ReplicatedMergeTree：适合副本复制和高可用场景。
6. Distributed：适合作为分布式查询入口。
7. Kafka：适合接入 Kafka 流数据。

不同表引擎决定了数据写入后的组织方式，也会影响查询性能、去重语义和运维复杂度。

#### 三、查询分析能力

ClickHouse 支持丰富的 SQL 分析能力，常见能力包括：

- 多维聚合
- 明细过滤
- 窗口函数
- 数组和 Map 函数
- JSON 和半结构化数据处理
- 近似计算函数
- 字典 (Dictionary)
- 物化视图
- Projection
- 外部数据源查询

ClickHouse 的函数库很丰富，在日志分析、行为分析、指标分析中经常能减少额外 ETL 工作。

#### 四、性能优化能力

ClickHouse 内置了多种性能优化机制，例如：

1. 列式存储：只读取查询需要的列，减少 IO。
2. 压缩编码：同类型数据连续存储，压缩率高。
3. 稀疏主键索引：通过 ORDER BY 构建索引，减少扫描范围。
4. 数据跳数索引：通过 BloomFilter、MinMax、Set、NGram 等索引跳过无关数据块。
5. 向量化执行：按列批量处理数据，提高 CPU 执行效率。
6. 物化视图和 Projection：预先组织或计算数据，减少查询现场计算成本。

#### 五、生态集成能力

ClickHouse 可以和常见大数据生态集成，例如：

- Kafka：通过 Kafka Engine 和物化视图持续写入。
- Flink：通过 Connector 写入 ClickHouse 或读取 ClickHouse。
- Spark：用于离线加工后写入 ClickHouse。
- Hive、HDFS、S3：通过表函数、外部表或集成能力读取外部数据。
- BI 工具：通过 JDBC、ODBC、HTTP 等方式连接 ClickHouse。

#### 六、面试时可以怎么总结

可以这样回答：ClickHouse 的核心功能包括高吞吐数据写入、丰富的 MergeTree 表引擎、标准 SQL 分析、列式查询加速、物化视图和 Projection 预计算，以及与 Kafka、Flink、Spark、S3、HDFS 等生态的集成。它既能承接准实时写入，也能支撑低延迟明细分析和聚合查询，所以在日志分析、实时看板、用户行为分析和数据服务场景中比较常见。

#### 知识扩展

- Kafka Engine：常用于实时消费 Kafka 数据
- 物化视图：常用于把 Kafka 数据落入目标表，或做预聚合
- Dictionary：适合维表查询和维度映射
- Projection：类似表内的数据投影，可以优化特定查询模式
- ReplacingMergeTree：常用于最终一致的去重和更新模拟

### 1.4 ClickHouse 有哪些核心特性？为什么查询速度比较快？

ClickHouse 查询速度快，核心原因不是某一个单点优化，而是列式存储、数据组织、索引裁剪、执行引擎和并行计算多层能力共同作用的结果。

#### 一、列式存储

ClickHouse 使用列式存储。对于分析查询来说，通常只需要访问少量字段，比如查询订单金额、下单时间和渠道，而不需要读取整行所有字段。

列式存储的优势包括：

1. 只读取需要的列，减少磁盘 IO。
2. 同类型数据连续存储，压缩效果更好。
3. 更适合向量化执行和批量计算。

#### 二、MergeTree 数据组织

MergeTree 是 ClickHouse 最核心的表引擎。数据写入后会形成多个不可变的数据 Part，后台再不断把小 Part 合并成更大的 Part。

MergeTree 表通常会指定 PARTITION BY、ORDER BY 和 PRIMARY KEY，其中 ORDER BY 决定数据在磁盘上的排序方式，也是查询裁剪能力的关键。

如果查询条件能命中排序键前缀，ClickHouse 就可以通过稀疏索引快速定位需要读取的数据范围。

#### 三、稀疏主键索引

ClickHouse 的主键索引不是传统数据库里的 B+Tree 二级索引，而是一种基于排序数据的稀疏索引。

它不会为每一行都建立索引，而是按 Granule 记录关键位置。查询时先根据条件定位可能命中的 Granule，再读取对应的数据块。

这种设计索引体积小、适合大规模分析数据，但也意味着主键不负责唯一性约束。

#### 四、数据跳数索引和分区裁剪

ClickHouse 支持多种数据跳数索引，例如：

- MinMax：适合范围过滤。
- BloomFilter：适合高基数字段等值过滤。
- Set：适合局部低基数字段过滤。
- NGram 或 Token BloomFilter：适合部分文本检索场景。

分区裁剪和数据跳数索引的目标都是减少实际扫描的数据量。分区通常按日期或业务范围切分，数据跳数索引则用于在更细粒度上跳过无关数据块。

#### 五、向量化执行和并行计算

ClickHouse 执行 SQL 时不是逐行处理，而是按列批量处理一批数据。这样可以减少函数调用开销，提高 CPU Cache 命中率，并更好地利用 SIMD 等 CPU 能力。

在单机内，ClickHouse 会利用多线程并行扫描和计算；在集群内，可以通过分片让多个节点并行执行查询。

#### 六、物化视图和 Projection

对于固定维度、固定指标的查询，如果每次都扫描明细表现场聚合，成本会比较高。ClickHouse 可以通过物化视图提前把明细数据转换成汇总表，也可以通过 Projection 在表内部维护适合某些查询的物理布局。

查询命中这些预先组织好的数据后，可以减少现场计算和扫描成本。

#### 七、面试时可以怎么总结

可以这样回答：ClickHouse 查询快主要依赖几方面能力：首先是列式存储，可以减少 IO 并提升压缩效率；其次是 MergeTree 按 ORDER BY 组织数据，并通过稀疏主键索引快速定位数据范围；再加上分区裁剪和数据跳数索引，可以进一步减少扫描量；执行层通过向量化和多线程充分利用 CPU；集群层还能通过分片并行查询；对于固定查询模式，还可以用物化视图和 Projection 提前组织数据。所以 ClickHouse 的性能来自存储、索引、执行和数据建模的整体协同。

#### 知识扩展

- ORDER BY：决定数据物理排序，是 ClickHouse 表设计的关键
- Primary Key：主要用于稀疏索引裁剪，不保证唯一性
- Granule：ClickHouse 稀疏索引和读取裁剪的重要粒度
- Data Skipping Index：用于跳过不相关数据块
- Projection：可以为同一张表维护额外的查询优化布局

### 1.5 MergeTree 表引擎、分区、主键和排序键应该怎么理解？

MergeTree 是 ClickHouse 最重要的表引擎家族，也是面试中最容易被追问的部分。理解 MergeTree，要抓住几个关键词：Part、Partition、ORDER BY、Primary Key、后台 Merge 和最终一致。

#### 一、MergeTree 的基本思想

MergeTree 适合大量追加写入。每批数据写入后，会先形成一个或多个不可变的 Part。随着写入增多，后台线程会不断把小 Part 合并成大 Part，减少文件数量并优化查询效率。

这种设计的好处是写入吞吐高，适合分析型场景。但代价是很多操作不是立即完成的，比如去重、聚合、删除和更新通常依赖后台 Merge 或 Mutation。

#### 二、Partition 的作用

Partition 是表数据的粗粒度划分方式，常见做法是按日期分区，例如按天或按月。

分区的作用包括：

1. 查询时可以根据分区条件裁剪无关数据。
2. 运维上可以按分区删除、归档或迁移数据。
3. TTL 可以按分区或数据时间进行冷热管理。

分区不宜过细。如果按小时甚至更细粒度分区，可能会产生大量 Part，增加后台 Merge 和元数据管理压力。

#### 三、ORDER BY 的作用

ORDER BY 是 ClickHouse 表设计中最关键的字段，它决定数据在每个 Part 内的物理排序方式。

ORDER BY 设计得好，查询条件就更容易命中稀疏索引，减少扫描数据量。例如用户行为表经常按 tenant_id、event_date、user_id 查询，就可以考虑把这些高频过滤字段放到排序键前部。

需要注意的是，ORDER BY 不是 SQL 查询里的排序输出，而是建表时的数据存储排序。

#### 四、Primary Key 的作用

ClickHouse 中 Primary Key 默认通常和 ORDER BY 相同，也可以是 ORDER BY 的前缀。它主要用于构建稀疏索引，帮助查询定位数据范围。

它和 MySQL 主键有明显区别：

1. 不保证唯一性。
2. 不负责行级约束。
3. 不适合随机点查。
4. 主要用于查询裁剪。

因此面试中不要把 ClickHouse Primary Key 解释成传统事务数据库的唯一主键。

#### 五、建表示例

```sql
CREATE TABLE user_events
(
    event_date Date,
    tenant_id UInt64,
    user_id UInt64,
    event_name LowCardinality(String),
    event_time DateTime,
    properties String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (tenant_id, event_date, user_id, event_time);
```

这个例子里：

1. PARTITION BY toYYYYMM(event_date) 表示按月分区，方便按时间裁剪和管理。
2. ORDER BY (tenant_id, event_date, user_id, event_time) 表示数据按这些字段排序，适合租户、时间、用户维度的过滤查询。
3. event_name 使用 LowCardinality(String)，适合低基数字符串字段，能降低存储和计算成本。

#### 六、面试时可以怎么总结

可以这样回答：MergeTree 是 ClickHouse 最核心的表引擎，数据写入后会形成不可变的 Part，再由后台 Merge 合并优化。Partition 负责粗粒度数据管理和分区裁剪，通常按日期设计；ORDER BY 决定数据物理排序，是查询性能的关键；Primary Key 主要用于稀疏索引裁剪，不保证唯一性。设计表时要根据高频查询条件选择排序键，避免分区过细和小批量高频写入，否则容易造成 Part 过多和 Merge 压力。

#### 知识扩展

- Part：ClickHouse 数据写入后的物理数据片段
- Merge：后台合并 Part，优化读取性能
- Mutation：用于更新和删除，但通常成本较高
- LowCardinality：适合低基数字符串列的编码优化
- TTL：可以用于数据过期、冷热分层和列级生命周期管理

### 1.6 使用 ClickHouse 时有哪些注意事项和优化建议？

ClickHouse 性能很强，但它不是万能数据库。使用时要围绕 OLAP 场景、批量写入、合理建模和查询裁剪来设计，避免把它当成传统事务数据库使用。

#### 一、避免高频单行写入

ClickHouse 更适合批量写入。每次写入都会生成数据 Part，如果大量小批次或单行写入，就会产生很多小 Part，增加后台 Merge 压力，严重时影响查询和写入稳定性。

常见建议包括：

1. 客户端攒批后写入。
2. 通过 Kafka、Flink 或 Buffer 机制削峰。
3. 控制写入频率和每批数据大小。

#### 二、谨慎使用更新和删除

ClickHouse 支持 UPDATE 和 DELETE，但它们通常通过 Mutation 异步改写数据，成本比 OLTP 数据库高很多。

如果业务需要频繁更新，可以考虑：

1. 使用 ReplacingMergeTree 保留最新版本。
2. 通过版本号字段实现最终去重。
3. 在查询时使用 FINAL，但要注意 FINAL 可能带来额外查询成本。
4. 对强实时强一致更新需求，优先考虑 OLTP 数据库。

#### 三、合理设计分区和排序键

分区和排序键直接影响查询性能。

常见建议包括：

1. 分区通常按日期设计，不要过细。
2. ORDER BY 前缀优先放高频过滤字段。
3. 排序键要兼顾过滤、聚合和数据分布。
4. 不要把过多字段塞进排序键，避免索引和写入成本上升。

#### 四、控制 Join 使用方式

ClickHouse 擅长大宽表过滤和聚合，但复杂 Join 不是它最擅长的模式。对于高频查询，可以通过宽表化、预聚合、Dictionary 或物化视图减少现场 Join。

如果必须 Join，需要关注：

1. 小表尽量放右侧，便于构建 Hash Table。
2. 控制 Join 输入数据量，先过滤再 Join。
3. 对维表可以考虑 Dictionary。
4. 跨分片 Join 要特别关注数据分布和网络开销。

#### 五、利用物化视图和预聚合

对于固定查询模式，比如按天、渠道、城市统计订单金额，可以把明细数据通过物化视图写入汇总表，避免每次都扫描大明细表。

示例：

```sql
CREATE MATERIALIZED VIEW mv_order_daily
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(order_date)
ORDER BY (order_date, channel)
AS
SELECT
    order_date,
    channel,
    sum(amount) AS amount
FROM orders
GROUP BY order_date, channel;
```

这个例子表示写入 orders 后，ClickHouse 可以把按日期和渠道聚合后的结果维护到物化视图目标表中，用于加速固定指标查询。

#### 六、面试时可以怎么总结

可以这样回答：使用 ClickHouse 时，首先要明确它适合 OLAP 分析，不适合高频事务更新；写入上要尽量批量导入，避免单行高频写入导致小 Part 过多；建模上要重点设计 PARTITION BY 和 ORDER BY，让查询能利用分区裁剪和稀疏索引；对于更新删除，要理解 Mutation 和 ReplacingMergeTree 的最终一致语义；对于复杂 Join 和固定报表，要考虑宽表化、Dictionary、物化视图或预聚合。整体来说，ClickHouse 的优化核心是减少扫描量、减少现场计算，并让数据组织方式贴近查询模式。

#### 知识扩展

- 小 Part 问题：高频小批写入会增加 Merge 压力
- FINAL：可以查询去重后的结果，但可能增加查询成本
- Mutation：适合低频数据修正，不适合高频在线更新
- Dictionary：适合维表映射和维度补充
- 宽表化：用空间换时间，减少查询时复杂 Join

### 1.7 ClickHouse 里的分片是什么？它解决了什么问题？

ClickHouse 里的分片 (Shard) 是指把一张逻辑表的数据水平拆分到多个节点或多个节点组上。每个分片只保存全量数据的一部分，多个分片合在一起才构成完整数据集。

面试里可以先用一句话概括：分片的核心作用是把数据和查询压力拆散到多台机器上，从而提升存储容量、写入吞吐和查询并行度。

#### 一、分片的基本概念

在单机 ClickHouse 中，一张表的数据都保存在一个节点上。如果数据量持续增长，单机的磁盘、CPU、内存和 IO 都会成为瓶颈。

分片就是把数据按某种规则拆到多个 Shard 中。例如订单表可以按 user_id 或 order_id 做 Hash 分片：

1. Shard 1 保存一部分用户或订单的数据。
2. Shard 2 保存另一部分用户或订单的数据。
3. Shard 3 再保存另一部分数据。

这样每个节点只承担一部分数据存储和查询计算。

#### 二、分片主要解决什么问题

分片主要解决三个问题。

第一是存储容量扩展。单机磁盘容量有限，分片后可以把数据分散到多台机器上，总容量随着节点数量增加而增加。

第二是查询并行度提升。查询全表或大范围数据时，不同分片可以并行扫描自己本地的数据，再把结果汇总，整体查询速度通常会比单机更好。

第三是写入吞吐提升。数据写入时可以分散到多个分片，减少单个节点的写入压力。

#### 三、分片和副本的区别

分片和副本经常一起出现，但它们解决的问题不同。

分片是水平切分数据，用于扩展容量和计算能力。不同分片保存的是不同数据。

副本是复制同一份数据，用于提升可用性和读能力。同一个分片的多个副本保存的是相同数据。

可以简单理解为：Shard 解决扩展问题，Replica 解决容错问题。

#### 四、Distributed 表和分片的关系

ClickHouse 中跨分片查询通常通过 Distributed 表完成。

常见做法是：

1. 在每个分片节点上创建本地表，例如 events_local。
2. 创建一张 Distributed 表，例如 events_all。
3. 查询 events_all 时，ClickHouse 会把请求下发到多个分片的本地表。
4. 各个分片并行计算后，把结果返回给发起节点汇总。

Distributed 表本身更像一个逻辑入口，它负责把查询或写入路由到真实的本地表。

#### 五、分片设计的注意事项

分片不是越多越好，设计不合理也会带来问题。

常见注意事项包括：

1. 分片 Key 要尽量让数据分布均匀，避免某个 Shard 数据量或请求量特别大。
2. 查询经常按某个维度过滤时，可以考虑让分片 Key 和查询模式匹配，减少跨分片扫描。
3. 分片数量要结合数据规模、机器资源和运维复杂度设计，过多分片会增加网络、元数据和调度成本。
4. 跨分片 Join、全局排序和去重通常成本更高，需要特别关注执行计划和数据分布。
5. 如果使用副本，还要考虑 ReplicatedMergeTree、ClickHouse Keeper 或 ZooKeeper 的协调成本。

#### 六、面试时可以怎么总结

可以这样回答：ClickHouse 里的分片就是把一张逻辑表的数据水平拆分到多个 Shard 上，每个分片保存一部分数据。它主要解决单机容量、写入吞吐和查询计算能力不足的问题。查询 Distributed 表时，ClickHouse 会把查询下发到多个分片并行执行，再汇总结果。分片和副本不一样，分片是为了扩展，不同分片保存不同数据；副本是为了容错，同一分片的多个副本保存相同数据。设计分片时要重点关注分片 Key 是否均匀、是否贴合查询模式，以及跨分片查询带来的网络和计算成本。

#### 知识扩展

- Shard：水平拆分数据，提升容量和并行计算能力
- Replica：复制同一份数据，提升可用性和读能力
- Distributed 表：访问多个分片的逻辑入口
- Sharding Key：决定数据写入哪个分片，影响数据均衡和查询效率
- 跨分片查询：需要汇总多个分片结果，可能带来网络和聚合成本
