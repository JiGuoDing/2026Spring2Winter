# Batch Inference 项目

## 目标

使用 Ray Data 的 map_batches 进行批量推理，输出预测结果。

## 运行

```bash
# 先生成数据
python ../../scripts/generate_data.py

# 运行批量推理
python main.py
```

## 处理步骤

1. 生成/加载简单模型
2. 准备推理数据
3. 使用 map_batches 批量预测
4. 输出预测结果
5. 说明如何扩展到 GPU

## GPU 扩展

将 `num_gpus=1` 添加到 map_batches 参数即可使用 GPU。
