# math: Python 标准数学库，这里用 math.sqrt 做缩放点积中的开方
import math

# 导入 PyTorch 主包
import torch

# 导入 nn：包含 Module、Linear、Softmax 等神经网络组件
from torch import nn

# torch.rand(128, 32, 512): 生成随机输入张量
# 维度通常解释为 [batch_size, seq_len, d_model]
x = torch.rand(128, 32, 512)


# 自定义类 MultiHeadAttention：
# 作用：实现 Transformer 的多头注意力计算。
class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_head):
        # 初始化父类
        super(MultiHeadAttention, self).__init__()
        self.n_head = n_head
        self.d_model = d_model

        # 错误写法（已注释）：
        # 问题：若 d_model 不能被 n_head 整除，后续 view 会报错且不易定位。
        # n_d = self.d_model // self.n_head

        # 正确做法：提前做显式检查，错误信息更清晰。
        if d_model % n_head != 0:
            raise ValueError(f'd_model({d_model}) 必须能被 n_head({n_head}) 整除。')

        # nn.Linear: 线性变换层，用于生成 Q/K/V
        self.w_q = nn.Linear(d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model)

        # 多头拼接后的输出线性层
        self.w_concat = nn.Linear(d_model, d_model)

        # nn.Softmax(dim=-1): 在最后一维归一化为概率分布
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, q, k, v, mask=None):
        """
        自定义函数作用：执行多头注意力前向传播。

        参数：
        - q, k, v: 查询/键/值张量（常见形状 [batch, seq_len, d_model]）
        - mask: 可选掩码，0 表示被屏蔽位置

        返回：
        - out: 注意力输出（形状 [batch, q_len, d_model]）
        """
        # 错误写法（已注释）：
        # 问题：只从 q 读取 time，然后用于 k/v 的 view。
        # 在交叉注意力（q_len != k_len）时会形状错误。
        # batch, time, dimension = q.shape

        # 正确写法：分别读取 q/k/v 的序列长度，更通用。
        batch, q_len, dimension = q.shape
        _, k_len, _ = k.shape
        _, v_len, _ = v.shape

        # 保证键和值长度一致（标准 attention 要求）
        if k_len != v_len:
            raise ValueError(f'k_len({k_len}) 与 v_len({v_len}) 必须一致。')

        # 每个头的维度 = d_model / n_head
        n_d = self.d_model // self.n_head

        # 先线性投影得到 Q/K/V
        q, k, v = self.w_q(q), self.w_k(k), self.w_v(v)

        # view: 拆分头维度；permute: 调整为 [batch, head, time, head_dim]
        q = q.view(batch, q_len, self.n_head, n_d).permute(0, 2, 1, 3)
        k = k.view(batch, k_len, self.n_head, n_d).permute(0, 2, 1, 3)
        v = v.view(batch, v_len, self.n_head, n_d).permute(0, 2, 1, 3)

        # 缩放点积注意力：QK^T / sqrt(head_dim)
        score = q @ k.transpose(2, 3) / math.sqrt(n_d)

        # masked_fill: 在 mask==0 的位置填极小值，softmax 后接近 0
        if mask is not None:
            score = score.masked_fill(mask == 0, -1e9)

        # softmax 得到权重，再与 V 相乘得到上下文
        score = self.softmax(score) @ v

        # permute + contiguous + view: 恢复为 [batch, q_len, d_model]
        score = score.permute(0, 2, 1, 3).contiguous().view(batch, q_len, dimension)

        # 最终线性映射融合多头信息
        out = self.w_concat(score)
        return out
