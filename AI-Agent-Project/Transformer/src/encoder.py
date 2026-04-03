import torch
from torch import nn
from torch.nn import functional as F

from embedding import TransformerEmbedding
from attention import MultiHeadAttention
from layernorm import LayerNorm

class PositionWiseFeedForward(nn.Module):
    def __init__(self, d_model, hidden_size, dropout=0.1):
        super().__init__()
        self.fc1 = nn.Linear(d_model, hidden_size)
        self.fc2 = nn.Linear(hidden_size, d_model)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x
    
    
class EncoderLayer(nn.Module):
    def __init__(self, d_model, ffn_hidden_size, n_head, dropout=0.1):
        super().__init__()
        self.attention = MultiHeadAttention(d_model, n_head)
        self.norm1 = LayerNorm(d_model)
        self.dropout1 = nn.Dropout(dropout)
        self.ffn = PositionWiseFeedForward(d_model=d_model, hidden_size=ffn_hidden_size, dropout=dropout)
        self.norm2 = LayerNorm(d_model)
        self.dropout2 = nn.Dropout(dropout)
        
    def forward(self, x, mask=None):
        _x = x
        # 多头自注意力机制
        x = self.attention(x, x, x, mask)
        x = self.dropout1(x)
        # 层归一化和残差连接
        x = self.norm1(x + _x)
        _x = x
        # 前馈神经网络
        x = self.ffn(x)
        x = self.dropout2(x)
        # 层归一化和残差连接
        x = self.norm2(x + _x)
        return x
    
class Encoder(nn.Module):
    def __init__(self, enc_voc_size, max_len, d_model, ffn_hidden_size, n_head, n_layer, dropout=0.1, device='cpu'):
        super().__init__()
        self.embedding = TransformerEmbedding(vocab_size=enc_voc_size, d_model=d_model, max_len=max_len, drop_prob=dropout, device=device)
        self.layers = nn.ModuleList(
            [
                EncoderLayer(d_model=d_model, ffn_hidden_size=ffn_hidden_size, n_head=n_head, dropout=dropout)
                for _ in range(n_layer)
            ]
        )
    
    def forward(self, x, mask):
        x = self.embedding(x)
        for layer in self.layers:
            x = layer(x, mask)
        return x