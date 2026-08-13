"""
Feature Extraction Module: Character Sequence Tokenizer (`src/features/tokenizer.py`)

Converts raw payload text into fixed-length integer token tensors for PyTorch Deep Learning
backbones (CharCNN, ResNet-1D, LSTM/GRU, SecRoBERTa).
"""

import os
import json
import logging
import torch
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Standard ASCII + Special Character Vocabulary
PAD_TOKEN = 0
UNK_TOKEN = 1


class CharTokenizer:
    """Character-level tokenizer supporting fixed length padding and truncation."""
    def __init__(self, max_length: int = 256):
        self.max_length = max_length
        self.char2idx = {"<PAD>": PAD_TOKEN, "<UNK>": UNK_TOKEN}
        self.idx2char = {PAD_TOKEN: "<PAD>", UNK_TOKEN: "<UNK>"}
        # Populate with printable ASCII characters
        for i in range(32, 127):
            c = chr(i)
            idx = len(self.char2idx)
            self.char2idx[c] = idx
            self.idx2char[idx] = c

    @property
    def vocab_size(self) -> int:
        return len(self.char2idx)

    def encode(self, text: str) -> list[int]:
        """Encodes string text into list of integer token IDs."""
        tokens = []
        for c in str(text)[:self.max_length]:
            tokens.append(self.char2idx.get(c, UNK_TOKEN))
        # Pad to max_length
        if len(tokens) < self.max_length:
            tokens.extend([PAD_TOKEN] * (self.max_length - len(tokens)))
        return tokens

    def batch_encode(self, texts: list[str]) -> np.ndarray:
        """Encodes batch of texts into numpy int32 matrix (N, max_length)."""
        encoded = [self.encode(t) for t in texts]
        return np.array(encoded, dtype=np.int32)
