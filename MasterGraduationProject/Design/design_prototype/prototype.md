# 毕业设计

## 思路记录

- 把 Flink 状态用作 Agent 多轮会话/跨会话的知识库的缓存，缓存最近最常访问的知识资料
- <br />

## 整体框架

面向 SLO 与知识库缓存优化的流式 Agent 推理系统

### 点 1：推理时间预测

基于熵的推理长度预测

基于线性预测（TODO 需替换）的推理时间预测

<br />

<br />

### 点 2：面向 SLO 的参数调整

目标：保证 SLO 的情况下最小化语义库缓存容量以及推理并行度，尽可能降低成本

语义库缓存容量扩缩

推理并行度及批次大小扩缩 （利用推理时间）

<br />

<br />

### 点 3：语义记忆算子

计算两个 prompt 的相似度（embedding 相似度 + TODO 另一个相似度）

语义相似命中则该 prompt 直接短路到回复存储算子

<br />

```
Source → StateFetcher → Batcher → Inferencer → Sink
            ↑ 升级为「语义记忆算子」（embedding 索引 + 语义检索）
            ↑ 语义命中 → 短路 Batcher+Inferencer（省 GPU）
```

