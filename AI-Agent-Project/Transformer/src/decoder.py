import torch
from torch import nn
from torch.nn import functional as F

from layernorm import LayerNorm
from attention import MultiHeadAttention
from encoder import PositionWiseFeedForward
from embedding import TransformerEmbedding

class DecoderLayer(nn.Module):
    def __init__(self, d_model, ffn_hidden_size, n_head, drop_prob=0.1):
        super().__init__()
        self.maskedAttention = MultiHeadAttention(d_model=d_model, n_head=n_head)
        self.norm1 = LayerNorm(d_model)
        self.dropout1 = nn.Dropout(drop_prob)
        self.crossAttention = MultiHeadAttention(d_model=d_model, n_head=n_head)
        self.norm2 = LayerNorm(d_model)
        self.ffn = PositionWiseFeedForward(d_model=d_model, hidden_size=ffn_hidden_size, dropout=drop_prob)
        self.norm3 = LayerNorm(d_model)
        self.dropout3 = nn.Dropout(drop_prob)
        
    def forward(self, enc_out, dec_out, t_mask, s_mask):
        _x = dec_out
        x = self.maskedAttention(dec_out, dec_out, dec_out, t_mask)
        x = self.dropout1(x)
        x = self.norm1(x + _x)
        _x = x
        x = self.crossAttention(dec_out, enc_out, enc_out, s_mask)
        x = self.norm2(x + _x)
        _x = x
        x = self.ffn(x)
        x = self.dropout3(x)
        x = self.norm3(x + _x)
        return x
    
class Decoder(nn.Module):
    def __init__(self, dec_voc_size, max_len, d_model, ffn_hidden_size, n_head, n_layer, drop_prob, device):
        super().__init__()
        self.embedding = TransformerEmbedding(vocab_size=dec_voc_size, d_model=d_model, max_len=max_len, drop_prob=drop_prob, device=device)
        self.layers = nn.ModuleList(
            [
                DecoderLayer(d_model=d_model, ffn_hidden_size=ffn_hidden_size, n_head=n_head, drop_prob=drop_prob)
                for _ in range(n_layer)
            ]
        )
        self.fc = nn.Linear(d_model, dec_voc_size)
        
    def forward(self, enc_out, dec_out, t_mask, s_mask):
        dec_out = self.embedding(dec_out)
        for layer in self.layers:
            dec_out = layer(enc_out, dec_out, t_mask, s_mask)
        dec = self.ffn(dec_out)
        return dec_out