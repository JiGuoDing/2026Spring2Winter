# 导入 PyTorch 主包（提供张量 Tensor、自动求导、GPU 计算等核心能力）
import torch

# 从 torch 中导入 nn（neural network）模块，里面有常见神经网络层和基类
from torch import nn

# torch.rand(4, 4): 生成一个 4x4 的张量，元素服从 [0, 1) 的均匀分布随机数
# 这个函数常用于：快速造测试数据、检查张量形状是否符合预期
random_torch = torch.rand(4, 4)

# print: 将张量打印到输出区，便于观察随机值和形状
print(random_torch)

# 自定义类 TokenEmbedding：
# 作用：把词表中的整数索引映射成可训练的稠密向量（Embedding）
# 继承 nn.Embedding：复用 PyTorch 词嵌入实现
class TokenEmbedding(nn.Embedding):
    def __init__(self, vocab_size, d_model):
        """
        自定义类作用：初始化词向量层。

        参数说明：
        - vocab_size: 词汇表大小
        - d_model: 每个 token 的向量维度（Transformer 隐藏维）
        """
        # nn.Embedding(num_embeddings, embedding_dim, padding_idx=1)
        # - num_embeddings: 词表大小
        # - embedding_dim: 向量维度
        # - padding_idx=1: 索引 1 作为 PAD，通常不参与有效语义学习
        super(TokenEmbedding, self).__init__(vocab_size, d_model, padding_idx=1)


# 自定义类 PositionEmbedding：
# 作用：生成固定正弦/余弦位置编码，为模型提供顺序信息。
class PositionEmbedding(nn.Module):
    def __init__(self, d_model, max_len, device):
        # 初始化 nn.Module 基类
        super(PositionEmbedding, self).__init__()

        # torch.zeros(max_len, d_model): 创建位置编码矩阵 [max_len, d_model]
        encoding = torch.zeros(max_len, d_model, device=device)

        # torch.arange(0, max_len): 位置索引 0~max_len-1
        pos = torch.arange(0, max_len, device=device).float().unsqueeze(dim=1)

        # torch.arange(0, d_model, step=2): 取偶数维下标
        _2i = torch.arange(0, d_model, step=2, device=device).float()

        # 偶数维使用 sin：PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
        encoding[:, 0::2] = torch.sin(pos / (10000 ** (_2i / d_model)))

        # 奇数维使用 cos：PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
        encoding[:, 1::2] = torch.cos(pos / (10000 ** (_2i / d_model)))

        # register_buffer: 注册为“缓冲区”而不是参数。
        # 作用：不参与梯度更新，但会跟随 model.to(device) / state_dict 保存加载。
        self.register_buffer('encoding', encoding)

    def forward(self, x):
        """
        自定义函数作用：按输入序列长度返回对应位置编码。

        参数：
        - x: 输入张量。可为 token id（[batch, seq_len]）或 embedding（[batch, seq_len, d_model]）

        返回：
        - 位置编码，形状 [1, seq_len, d_model]，可与 [batch, seq_len, d_model] 自动广播相加
        """
        # 错误写法（已注释）：
        # 问题：当 x 是 embedding（3 维）时，下面解包会报错 “too many values to unpack”。
        # batch_size, seq_len = x.size()

        # 正确写法：统一取第 1 维作为序列长度，兼容 2 维和 3 维输入。
        seq_len = x.size(1)

        # 取前 seq_len 个位置编码，并在最前面补 batch 维（大小为 1）便于广播相加。
        return self.encoding[:seq_len, :].unsqueeze(0)


# 自定义类 TransformerEmbedding：
# 作用：token embedding + position embedding，再做 dropout。
class TransformerEmbedding(nn.Module):
    def __init__(self, vocab_size, d_model, max_len, drop_prob, device):
        # 初始化父类
        super(TransformerEmbedding, self).__init__()

        # TokenEmbedding: token 索引 -> 词向量
        self.tok_emb = TokenEmbedding(vocab_size=vocab_size, d_model=d_model)

        # PositionEmbedding: 生成固定位置编码
        self.pos_emb = PositionEmbedding(max_len=max_len, d_model=d_model, device=device)

        # nn.Dropout(p): 训练时随机置零一部分元素，降低过拟合
        self.drop_out = nn.Dropout(p=drop_prob)

    def forward(self, x):
        """
        自定义函数作用：融合语义信息与位置信息。

        参数：
        - x: token 索引张量（形状 [batch_size, seq_len]）

        返回：
        - 融合后的输入表示（形状 [batch_size, seq_len, d_model]）
        """
        # 查表得到 token 向量：[batch, seq_len, d_model]
        tok_emb = self.tok_emb(x)

        # 错误写法（已注释）：
        # 问题：虽然传 tok_emb 也可工作，但初学者容易误解 PositionEmbedding 只接受 embedding 输入。
        # 更清晰的逻辑是传原始 x，让“长度提取”职责更明确。
        # pos_emb = self.pos_emb(tok_emb)

        # 正确写法：直接用 token 索引张量 x 获取序列长度。
        pos_emb = self.pos_emb(x)  # [1, seq_len, d_model]

        # 相加时发生广播：
        # tok_emb [batch, seq, d_model] + pos_emb [1, seq, d_model]
        return self.drop_out(tok_emb + pos_emb)
