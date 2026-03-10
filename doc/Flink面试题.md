# Flink 面试题

## 1. 窗口 Window

### 1.1 .reduce() 和 .aggregate() 的异同点

在 Flink 中，`.reduce()` 和 `.aggregate()` 都属于增量聚合算子，区别在于类型的灵活性。`.reduce()` 要求输入类型和输出类型必须一致，使用时只需实现一个 `reduce(value1, value2)` 方法，将两个元素合并为一个同类型的结果，适合求最大值、累加等场景，简单直接。`.aggregate()` 则更加灵活，输入类型、中间累加器类型、输出类型三者可以完全不同，使用时需要实现 `AggregateFunction` 接口中的四个方法：`createAccumulator()`（初始化累加器）、`add()`（定义每条数据如何累加到累加器）、`getResult()`（窗口触发时从累加器中提取最终结果）、`merge()`（合并两个累加器，用于 Session Window 等场景），适合求平均值这类需要维护中间状态且输出类型与输入不同的场景。总结来说，`.reduce()` 是 `.aggregate()` 的简化版，当输入输出类型相同时用 `.reduce()` 更简洁，当需要类型转换或自定义中间状态时用 `.aggregate()` 更合适，两者性能上都优于 `.process()` 全量计算。
