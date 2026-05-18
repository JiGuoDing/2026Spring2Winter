# Ray Data 常见坑与解决方案

## 1. Schema 不一致

**问题**: 不同行的相同字段类型不同。

```python
# 问题数据
data = [
    {"id": 1, "value": 10},      # value 是 int
    {"id": 2, "value": "hello"}, # value 是 string
]
```

**解决**:
```python
# 统一类型
def fix_types(row):
    row["value"] = str(row["value"])  # 统一转为 string
    return row

ds = ray.data.from_items(data).map(fix_types)
```

## 2. Batch Format 错误

**问题**: map_batches 的返回格式与 batch_format 不匹配。

```python
# 错误：batch_format="pandas" 但返回 dict
def bad_fn(batch: pd.DataFrame) -> dict:
    return {"x": batch["x"].tolist()}  # 错误

# 正确：返回与 batch_format 一致的格式
def good_fn(batch: pd.DataFrame) -> pd.DataFrame:
    batch["y"] = batch["x"] * 2
    return batch
```

**解决**: 确保函数返回类型与 batch_format 一致。

## 3. 用户函数异常

**问题**: map/filter 函数抛出异常，导致任务失败。

```python
# 问题：除零错误
def bad_fn(row):
    return {"result": 10 / row["x"]}  # x=0 时崩溃
```

**解决**:
```python
def safe_fn(row):
    try:
        result = 10 / row["x"] if row["x"] != 0 else 0.0
    except Exception:
        result = 0.0
    return {"result": result}
```

## 4. OOM（内存不足）

**问题**: 数据集或 batch 太大，超出内存。

**解决**:
```python
# 1. 减小 batch_size
ds.map_batches(fn, batch_size=500)

# 2. 避免不必要的 materialize
ds.filter(fn).show()  # 不要先 materialize 再 filter

# 3. 使用流式处理
for batch in ds.iter_batches(batch_size=100):
    process(batch)
```

## 5. Lambda 函数序列化失败

**问题**: Lambda 捕获了不可序列化的对象。

```python
# 问题：捕获了文件句柄
f = open("data.txt")
ds.map(lambda row: f.read())  # 失败：文件句柄不可序列化
```

**解决**:
```python
# 在函数内部打开文件
def process(row):
    with open("data.txt") as f:
        return {"data": f.read()}

ds.map(process)
```

## 6. 忘记物化

**问题**: 惰性操作链太长，每次 show() 都重新计算。

```python
# 问题：每次 show() 都重新计算
step1 = ds.filter(fn1)
step2 = step1.map(fn2)
step3 = step2.filter(fn3)
step3.show()  # 计算 fn1 -> fn2 -> fn3
step3.show()  # 又计算一遍
```

**解决**:
```python
# 物化中间结果
step3 = ds.filter(fn1).map(fn2).filter(fn3).materialize()
step3.show()  # 使用缓存
step3.show()  # 使用缓存
```

## 7. 版本差异

**问题**: API 在不同 Ray 版本间有变化。

**解决**:
- 查看当前版本的官方文档
- 注意弃用警告
- 使用 `ray.__version__` 检查版本

## 8. 数据倾斜

**问题**: 某些 key 的数据量远大于其他 key，导致任务执行不均衡。

**解决**:
```python
# 1. 先过滤或采样
ds.filter(lambda row: row["key"] in sampled_keys)

# 2. 使用 repartition 均衡分布
ds = ds.repartition(num_blocks=100)

# 3. 对热点 key 单独处理
hot_key_data = ds.filter(lambda row: row["key"] == hot_key)
cold_key_data = ds.filter(lambda row: row["key"] != hot_key)
```

## 9. 调试技巧

```python
# 1. 使用小数据集测试
small_ds = ray.data.from_items(data[:10])
result = small_ds.map(fn)
result.show()

# 2. 查看中间结果
step1 = ds.filter(fn1)
print(f"Step 1 行数: {step1.count()}")
step1.show(limit=3)

# 3. 使用 try-except 包裹用户函数
def safe_fn(row):
    try:
        return transform(row)
    except Exception as e:
        print(f"Error: {e}, row: {row}")
        return row  # 返回原数据

# 4. 查看 Ray Dashboard
# http://127.0.0.1:8265
```
