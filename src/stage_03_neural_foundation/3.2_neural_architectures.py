import math
import torch
import torch.nn as nn
import torch.nn.functional as F

VOCAB_SIZE = 130
EMBEDDING_DIM = 64
NUM_CLASSES = 4
MAX_LEN = 256

# =====================================================================
# 1. MULTI-SCALE 1D CharCNN (CNN Representation)
# =====================================================================
class CharCNN(nn.Module):
    """
    Multi-Scale 1D Character Convolutional Neural Network.
    Extracts n-gram syntactic attack features via parallel kernels (k=3, 5, 7).
    """
    def __init__(self, vocab_size: int = VOCAB_SIZE, embed_dim: int = EMBEDDING_DIM, num_classes: int = NUM_CLASSES):
        super(CharCNN, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        
        self.conv1 = nn.Conv1d(in_channels=embed_dim, out_channels=128, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(in_channels=embed_dim, out_channels=128, kernel_size=5, padding=2)
        self.conv3 = nn.Conv1d(in_channels=embed_dim, out_channels=128, kernel_size=7, padding=3)
        
        self.bn1 = nn.BatchNorm1d(128)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(128)
        
        self.pool = nn.AdaptiveMaxPool1d(1)
        self.dropout1 = nn.Dropout(0.4)
        
        self.fc1 = nn.Linear(128 * 3, 128)
        self.dropout2 = nn.Dropout(0.2)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x):
        emb = self.embedding(x).permute(0, 2, 1) # [batch, embed_dim, seq_len]
        c1 = self.pool(F.relu(self.bn1(self.conv1(emb)))).squeeze(-1)
        c2 = self.pool(F.relu(self.bn2(self.conv2(emb)))).squeeze(-1)
        c3 = self.pool(F.relu(self.bn3(self.conv3(emb)))).squeeze(-1)
        
        feat = torch.cat([c1, c2, c3], dim=1) # [batch, 384]
        feat = self.dropout1(feat)
        h = F.relu(self.fc1(feat))
        h = self.dropout2(h)
        return self.fc2(h)


# =====================================================================
# 2. Bi-LSTM WITH SELF-ATTENTION (RNN Representation)
# =====================================================================
class BiLSTMAttention(nn.Module):
    """
    Bidirectional LSTM with Temporal Self-Attention for sequence-aware payload modeling.
    """
    def __init__(self, vocab_size: int = VOCAB_SIZE, embed_dim: int = EMBEDDING_DIM, hidden_dim: int = 128, num_classes: int = NUM_CLASSES):
        super(BiLSTMAttention, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=0.3
        )
        self.attn = nn.Linear(hidden_dim * 2, 1)
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x):
        emb = self.embedding(x) # [batch, seq_len, embed_dim]
        lstm_out, _ = self.lstm(emb) # [batch, seq_len, hidden_dim * 2]
        
        attn_weights = F.softmax(self.attn(lstm_out), dim=1) # [batch, seq_len, 1]
        context = torch.sum(lstm_out * attn_weights, dim=1) # [batch, hidden_dim * 2]
        
        out = self.dropout(context)
        return self.fc(out)


# =====================================================================
# 3. TRANSFORMER ENCODER (Transformer Representation)
# =====================================================================
class TransformerEncoderNet(nn.Module):
    """
    Lightweight Deep Transformer Encoder with Multi-Head Self-Attention over ASCII byte sequences.
    """
    def __init__(self, vocab_size: int = VOCAB_SIZE, embed_dim: int = EMBEDDING_DIM, num_heads: int = 4, num_layers: int = 3, num_classes: int = NUM_CLASSES, max_len: int = MAX_LEN):
        super(TransformerEncoderNet, self).__init__()
        self.token_embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.pos_embedding = nn.Parameter(torch.zeros(1, max_len, embed_dim))
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=256,
            dropout=0.2,
            activation="gelu",
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.ln = nn.LayerNorm(embed_dim)
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(embed_dim, num_classes)

    def forward(self, x):
        # x: [batch, seq_len]
        seq_len = x.size(1)
        padding_mask = (x == 0) # [batch, seq_len]
        
        emb = self.token_embedding(x) + self.pos_embedding[:, :seq_len, :]
        h = self.transformer_encoder(emb, src_key_padding_mask=padding_mask) # [batch, seq_len, embed_dim]
        
        # Global Average Pooling (excluding pad tokens)
        mask = (~padding_mask).unsqueeze(-1).float()
        pooled = torch.sum(h * mask, dim=1) / torch.clamp(mask.sum(dim=1), min=1.0)
        
        pooled = self.ln(pooled)
        pooled = self.dropout(pooled)
        return self.fc(pooled)


def get_neural_model(model_name: str = "char_cnn", num_classes: int = NUM_CLASSES) -> nn.Module:
    """
    Factory function for all 3 Deep Learning architectures.
    """
    name = model_name.lower().replace("-", "_")
    if name in ["char_cnn", "charcnn", "cnn"]:
        return CharCNN(num_classes=num_classes)
    elif name in ["bilstm", "lstm", "bilstm_attention"]:
        return BiLSTMAttention(num_classes=num_classes)
    elif name in ["transformer", "secbert", "transformer_encoder"]:
        return TransformerEncoderNet(num_classes=num_classes)
    else:
        raise ValueError(f"Unknown model name: {model_name}. Choose 'char_cnn', 'bilstm', or 'transformer'.")
