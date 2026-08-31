import os
import torch
import numpy as np
import pandas as pd
from torch.utils.data import Dataset, DataLoader

# Vocabulary Mapping:
# 0: <PAD>
# 1: <UNK>
# 2 to 129: ASCII characters 0 to 127
PAD_IDX = 0
UNK_IDX = 1
VOCAB_SIZE = 130
MAX_LEN = 256

LABEL_MAP = {
    "benign": 0,
    "pathtrav": 1,
    "sqli": 2,
    "xss": 3
}

INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}

def encode_payload(text: str, max_len: int = MAX_LEN) -> np.ndarray:
    """
    Converts a raw payload string to a fixed-length numpy array of ASCII byte token IDs.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
        
    encoded = np.full(max_len, PAD_IDX, dtype=np.int64)
    for idx, char in enumerate(text[:max_len]):
        code = ord(char)
        if 0 <= code < 128:
            encoded[idx] = code + 2
        else:
            encoded[idx] = UNK_IDX
    return encoded

class PayloadDataset(Dataset):
    """
    PyTorch Dataset for HTTP Payload sequence classification.
    """
    def __init__(self, df: pd.DataFrame, max_len: int = MAX_LEN):
        # Filter for 4 core classes only
        df_filtered = df[df["final_label"].isin(LABEL_MAP.keys())].copy()
        
        self.payloads = df_filtered["sanitized_payload"].fillna("").astype(str).values
        self.labels = df_filtered["final_label"].map(LABEL_MAP).values.astype(np.int64)
        self.max_len = max_len

    def __len__(self):
        return len(self.payloads)

    def __getitem__(self, idx):
        x = encode_payload(self.payloads[idx], max_len=self.max_len)
        y = self.labels[idx]
        return torch.tensor(x, dtype=torch.long), torch.tensor(y, dtype=torch.long)

def get_dataloader(parquet_path: str, batch_size: int = 128, shuffle: bool = True, num_workers: int = 0) -> DataLoader:
    """
    Creates an optimized PyTorch DataLoader directly from a parquet filepath.
    """
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")
        
    df = pd.read_parquet(parquet_path)
    dataset = PayloadDataset(df)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )
