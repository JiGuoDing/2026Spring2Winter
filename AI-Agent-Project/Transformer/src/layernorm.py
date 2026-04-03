# math: Python 标准数学库（本例中保留导入，帮助理解数学公式）
import math

# 导入 PyTorch 主包（张量 Tensor、自动求导、GPU 支持等）
import torch

# 从 torch 导入 nn（neural network）模块，包含 Module、Parameter 等神经网络组件
from torch import nn

# 自定义类 LayerNorm：
# 作用：实现“层归一化（Layer Normalization）”。
# 对每个样本在最后一个维度上做标准化，再进行可学习的缩放（gamma）和偏移（beta）。
class LayerNorm(nn.Module):
    def __init__(self, d_model, eps=1e-10):
        """
        参数说明：
        - d_model: 最后一维特征数（也就是归一化的维度大小）
        - eps: 防止除零的小常数
        """
        # 正确初始化 nn.Module 基类。
        # 旧写法 super(LayerNorm).__init__() 是错误的，会导致初始化异常。
        super().__init__()

        # nn.Parameter: 可训练参数，训练时会被优化器更新。
        # gamma 初始为 1：相当于“先不缩放”。
        self.gamma = nn.Parameter(torch.ones(d_model))

        # beta 初始为 0：相当于“先不平移”。
        self.beta = nn.Parameter(torch.zeros(d_model))

        # 保存 eps，后续归一化时使用
        self.eps = eps

    def forward(self, x):
        """
        前向传播：输入 x -> 标准化 -> 仿射变换。

        输入：
        - x: 形状通常为 [batch_size, seq_len, d_model] 或 [N, d_model]

        输出：
        - 与 x 同形状的归一化结果
        """
        # x.mean(dim=-1, keepdim=True):
        # 在最后一维求均值，keepdim=True 使结果可与 x 广播。
        mean = x.mean(dim=-1, keepdim=True)

        # x.var(dim=-1, unbiased=False, keepdim=True):
        # 在最后一维求方差。unbiased=False 表示按总体方差公式（与很多深度学习实现一致）。
        var = x.var(dim=-1, unbiased=False, keepdim=True)

        # 标准化公式：(x - mean) / sqrt(var + eps)
        # 注意这里必须用 torch.sqrt（逐元素对张量开方），
        # 不能用 math.sqrt（math.sqrt 只适用于 Python 标量）。
        out = (x - mean) / torch.sqrt(var + self.eps)

        # 仿射变换：y = gamma * out + beta
        # gamma/beta 的形状是 [d_model]，会自动广播到前面维度。
        out = self.gamma * out + self.beta
        return out
