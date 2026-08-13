"""
Character-Level Convolutional Neural Network (`src/models/charcnn.py`)

Kim (2014) style parallel Conv1D network for web payload detection.
Extracts character-level n-gram feature representations across parallel filter widths (3, 4, 5).

Input: LongTensor (batch_size, seq_len) — CharTokenizer token IDs
Output: FloatTensor (batch_size, num_classes) — Logits
"""

import torch
import torch.nn as nn


class CharCNN(nn.Module):
    def __init__(
        self,
        vocab_size: int = 128,
        num_classes: int = 4,
        embed_dim: int = 32,
        num_filters: int = 64,
        kernel_sizes: tuple = (3, 4, 5),
        dropout: float = 0.3
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(in_channels=embed_dim, out_channels=num_filters, kernel_size=k)
            for k in kernel_sizes
        ])
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(num_filters * len(kernel_sizes), num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len) -> emb: (batch, embed_dim, seq_len)
        emb = self.embedding(x).transpose(1, 2)
        pooled = []
        for conv in self.convs:
            # (batch, num_filters, seq_len - k + 1)
            c = torch.relu(conv(emb))
            # Max-over-time pooling -> (batch, num_filters)
            pooled.append(c.max(dim=2)[0])
        cat = torch.cat(pooled, dim=1)
        out = self.dropout(cat)
        return self.fc(out)
