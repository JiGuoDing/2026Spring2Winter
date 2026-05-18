# Ray Data API 速查

## 创建 Dataset

| API | 说明 | 示例 |
|-----|------|------|
| `ray.data.from_items()` | 从 Python list 创建 | `ray.data.from_items([{"x": 1}])` |
| `ray.data.from_pandas()` | 从 pandas DataFrame 创建 | `ray.data.from_pandas(df)` |
| `ray.data.from_numpy()` | 从 numpy array 创建 | `ray.data.from_numpy({"a": arr})` |
| `ray.data.from_arrow()` | 从 PyArrow Table 创建 | `ray.data.from_arrow(table)` |
| `ray.data.read_csv()` | 读取 CSV 文件 | `ray.data.read_csv("data.csv")` |
| `ray.data.read_json()` | 读取 JSON/JSONL 文件 | `ray.data.read_json("data.jsonl")` |
| `ray.data.read_parquet()` | 读取 Parquet 文件 | `ray.data.read_parquet("data.parquet")` |
| `ray.data.range()` | 创建整数序列 | `ray.data.range(1000)` |

## 查看数据

| API | 说明 | 示例 |
|-----|------|------|
| `ds.show()` | 打印前 N 行 | `ds.show(limit=5)` |
| `ds.take()` | 取前 N 行 | `ds.take(3)` |
| `ds.count()` | 统计行数 | `ds.count()` |
| `ds.schema()` | 查看 Schema | `ds.schema()` |
| `ds.columns()` | 查看列名 | `ds.columns()` |
| `ds.num_blocks()` | 查看分区数 | `ds.num_blocks()` |

## 转换操作

| API | 说明 | 示例 |
|-----|------|------|
| `ds.map()` | 逐行转换 | `ds.map(lambda row: {**row, "y": 1})` |
| `ds.flat_map()` | 一行变多行 | `ds.flat_map(lambda row: [row, row])` |
| `ds.filter()` | 过滤 | `ds.filter(lambda row: row["x"] > 0)` |
| `ds.map_batches()` | 批量转换 | `ds.map_batches(fn, batch_format="pandas")` |
| `ds.select_columns()` | 选择列 | `ds.select_columns(["x", "y"])` |
| `ds.drop_columns()` | 删除列 | `ds.drop_columns(["z"])` |

## 聚合操作

| API | 说明 | 示例 |
|-----|------|------|
| `ds.groupby()` | 分组 | `ds.groupby("category")` |
| `.count()` | 计数 | `ds.groupby("x").count()` |
| `.sum()` | 求和 | `ds.groupby("x").sum("y")` |
| `.mean()` | 均值 | `ds.groupby("x").mean("y")` |
| `.min()` / `.max()` | 最值 | `ds.groupby("x").min("y")` |
| `.map_groups()` | 自定义聚合 | `ds.groupby("x").map_groups(fn)` |

## 排序与分区

| API | 说明 | 示例 |
|-----|------|------|
| `ds.sort()` | 排序 | `ds.sort("x", descending=True)` |
| `ds.repartition()` | 重新分区 | `ds.repartition(num_blocks=10)` |
| `ds.random_shuffle()` | 随机洗牌 | `ds.random_shuffle()` |

## 输出

| API | 说明 | 示例 |
|-----|------|------|
| `ds.write_csv()` | 写 CSV | `ds.write_csv("output/")` |
| `ds.write_json()` | 写 JSON | `ds.write_json("output/")` |
| `ds.write_parquet()` | 写 Parquet | `ds.write_parquet("output/")` |
| `ds.to_pandas()` | 转 pandas | `ds.to_pandas()` |
| `ds.to_numpy()` | 转 numpy | `ds.to_numpy()` |
| `ds.to_arrow()` | 转 Arrow | `ds.to_arrow()` |

## 执行控制

| API | 说明 | 示例 |
|-----|------|------|
| `ds.materialize()` | 物化执行并缓存 | `ds.materialize()` |
| `ds.iter_rows()` | 迭代行 | `for row in ds.iter_rows()` |
| `ds.iter_batches()` | 迭代 batch | `for batch in ds.iter_batches()` |
