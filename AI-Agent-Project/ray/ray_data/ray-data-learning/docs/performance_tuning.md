# Ray Data 性能优化指南

## 1. Batch Size 选择

batch_size 控制每个 Task 处理多少行数据。

```python
# 默认 batch_size（通常够用）
ds.map_batches(fn, batch_format="pandas")

# 自定义 batch_size
ds.map_batches(fn, batch_format="pandas", batch_size=1000)
```

建议：
- 内存充足：增大 batch_size（减少调度开销）
- 内存紧张：减小 batch_size（避免 OOM）
- GPU 推理：使用较大 batch_size（256-1024）

## 2. 并行度控制

### 读取并行度
```python
# 指定读取时的并行度
ds = ray.data.read_csv("data.csv", parallelism=10)
```

### 转换并行度
```python
# 通过 num_cpus 控制每个任务的资源
ds.map_batches(fn, num_cpus=0.5)  # 允许更多并发
ds.map_batches(fn, num_cpus=2)    # 计算密集型
```

### 经验法则
- 分区数 = CPU 核心数 × 2-4
- 每个分区大小建议 10MB-100MB

## 3. Repartition

调整数据分布，影响后续操作的并行度。

```python
# 增加分区（提高并行度）
ds = ds.repartition(num_blocks=20)

# 减少分区（减少调度开销）
ds = ds.repartition(num_blocks=2)
```

注意：repartition 本身会触发 shuffle，有成本。

## 4. Shuffle 优化

### 避免不必要的 shuffle
```python
# 不好：先 shuffle 再过滤
ds.groupby("x").count().filter(lambda row: row["count"] > 10)

# 好：先过滤再 shuffle（如果能过滤的话）
ds.filter(lambda row: row["x"] in valid_keys).groupby("x").count()
```

### 使用 map_groups 替代复杂 groupby
```python
# 复杂 groupby 可能触发多次 shuffle
ds.groupby("x").map_groups(complex_agg_fn)
```

## 5. Materialize 策略

```python
# 多次使用的数据集尽早物化
cached = expensive_transform(ds).materialize()

# 后续操作使用物化结果
result1 = cached.filter(lambda row: row["x"] > 0)
result2 = cached.filter(lambda row: row["x"] <= 0)
```

## 6. 数据格式选择

| 格式 | 读取速度 | 写入速度 | 压缩率 | 类型保留 | 推荐场景 |
|------|---------|---------|--------|---------|---------|
| CSV | 慢 | 快 | 低 | 否 | 数据交换 |
| JSON | 慢 | 中 | 低 | 部分 | 日志、API |
| Parquet | 快 | 中 | 高 | 是 | 生产环境 |

建议：生产环境优先使用 Parquet。

## 7. 内存管理

### 避免 OOM
```python
# 减小 batch_size
ds.map_batches(fn, batch_size=500)

# 避免不必要的 materialize
ds.filter(fn).map(fn2).show()  # 链式操作，不物化中间结果
```

### 监控内存
- 使用 Ray Dashboard 查看内存使用
- 关注 Object Store 使用情况

## 8. Ray Dashboard

访问 http://127.0.0.1:8265 查看：
- 任务执行状态
- 资源使用情况
- 数据传输量
- 执行时间线

## 9. 常见性能问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 任务执行慢 | 并行度不够 | 增加 parallelism / repartition |
| 内存不足 | batch_size 太大 | 减小 batch_size |
| 重复计算 | 未物化中间结果 | 使用 materialize() |
| 传输慢 | 数据格式不高效 | 使用 Parquet |
| 调度开销大 | 分区太多 | 减少分区数 |
