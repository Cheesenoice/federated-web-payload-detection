import os
import sys
import time
import copy
import logging
import importlib.util
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from torch.utils.data import Dataset, DataLoader, TensorDataset
from sklearn.metrics import f1_score, accuracy_score, classification_report, precision_score, recall_score

# Dynamic import helper for Stage 3 modules
def dynamic_import(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

CURRENT_DIR = os.path.dirname(__file__)
STAGE_03_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "stage_03_neural_foundation"))

arch_mod = dynamic_import("neural_archs", os.path.join(STAGE_03_DIR, "3.2_neural_architectures.py"))
get_neural_model = arch_mod.get_neural_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
PAD_IDX = 0
UNK_IDX = 1
VOCAB_SIZE = 130
MAX_LEN = 256

LABEL_MAP = {"benign": 0, "pathtrav": 1, "sqli": 2, "xss": 3}
INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}

# System Paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
CLIENTS_DIR = os.path.join(PROCESSED_DIR, "clients")
CACHE_TOKENIZED_DIR = os.path.join(ROOT_DIR, "data", "interim", "stage_04_tokenized")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_04_federated")
STAGE_03_MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_03_neural")
ROUND_CHECKPOINTS_DIR = os.path.join(MODELS_DIR, "round_checkpoints")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "stage_04_federated")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")

os.makedirs(CACHE_TOKENIZED_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(ROUND_CHECKPOINTS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

W_BASE_PATH = os.path.join(STAGE_03_MODELS_DIR, "W_base.pt")

def get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")

def encode_strings_vectorized(texts, max_len=MAX_LEN):
    """
    High-speed vectorized ASCII byte tokenization into contiguous uint8 numpy array.
    Zero Python overhead during training.
    """
    n = len(texts)
    arr = np.full((n, max_len), PAD_IDX, dtype=np.uint8)
    for i, s in enumerate(texts):
        if not isinstance(s, str):
            s = str(s) if s is not None else ""
        b = s.encode("ascii", errors="replace")[:max_len]
        for j in range(len(b)):
            val = b[j]
            if val < 128:
                arr[i, j] = val + 2
            else:
                arr[i, j] = UNK_IDX
    return arr

class FastPretokenizedDataset(Dataset):
    """
    Ultra-fast contiguous memory Dataset serving pre-tokenized uint8 tensors directly.
    """
    def __init__(self, x_uint8_tensor, y_int64_tensor):
        self.x = x_uint8_tensor
        self.y = y_int64_tensor

    def __len__(self):
        return len(self.x)

    def __getitem__(self, idx):
        return self.x[idx].long(), self.y[idx]

def get_or_create_tokenized_dataset(parquet_path, cache_name):
    """
    Checks if tokenized tensor cache exists on disk; if not, pre-tokenizes and saves.
    """
    cache_path = os.path.join(CACHE_TOKENIZED_DIR, f"{cache_name}.pt")
    if os.path.exists(cache_path):
        data = torch.load(cache_path)
        return FastPretokenizedDataset(data["x"], data["y"])
        
    logger.info(f"Pre-tokenizing & caching dataset [{cache_name}] from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    df_filtered = df[df["final_label"].isin(LABEL_MAP.keys())].copy()
    
    texts = df_filtered["sanitized_payload"].fillna("").astype(str).values
    labels = df_filtered["final_label"].map(LABEL_MAP).values.astype(np.int64)
    
    x_uint8 = encode_strings_vectorized(texts, max_len=MAX_LEN)
    x_tensor = torch.from_numpy(x_uint8)
    y_tensor = torch.from_numpy(labels)
    
    torch.save({"x": x_tensor, "y": y_tensor}, cache_path)
    logger.info(f"Saved tokenized cache [{cache_name}.pt] ({x_tensor.element_size() * x_tensor.nelement() / (1024*1024):.1f} MB)")
    return FastPretokenizedDataset(x_tensor, y_tensor)

def load_client_loaders(batch_size=512):
    """Loads ultra-fast DataLoaders for all 6 client training and validation sets."""
    train_loaders = {}
    val_loaders = {}
    client_sample_counts = {}
    
    for i in range(1, 7):
        cid = f"client_{i}"
        t_path = os.path.join(CLIENTS_DIR, f"{cid}_train.parquet")
        v_path = os.path.join(CLIENTS_DIR, f"{cid}_val.parquet")
        
        t_ds = get_or_create_tokenized_dataset(t_path, f"{cid}_train")
        v_ds = get_or_create_tokenized_dataset(v_path, f"{cid}_val")
        
        train_loaders[cid] = DataLoader(t_ds, batch_size=batch_size, shuffle=True, pin_memory=torch.cuda.is_available())
        val_loaders[cid] = DataLoader(v_ds, batch_size=batch_size, shuffle=False, pin_memory=torch.cuda.is_available())
        client_sample_counts[cid] = len(t_ds)
        
    return train_loaders, val_loaders, client_sample_counts

def load_test_holdouts(batch_size=512):
    """Loads all test holdouts: 6 local client tests, Global Test B, and OOD CSIC."""
    client_test_loaders = {}
    for i in range(1, 7):
        cid = f"client_{i}"
        path = os.path.join(CLIENTS_DIR, f"{cid}_test.parquet")
        ds = get_or_create_tokenized_dataset(path, f"{cid}_test")
        client_test_loaders[cid] = DataLoader(ds, batch_size=batch_size, shuffle=False, pin_memory=torch.cuda.is_available())
        
    b_path = os.path.join(PROCESSED_DIR, "pool_b_global_test.parquet")
    b_ds = get_or_create_tokenized_dataset(b_path, "pool_b_global_test")
    global_b_loader = DataLoader(b_ds, batch_size=batch_size, shuffle=False, pin_memory=torch.cuda.is_available())
    
    # OOD CSIC
    ood_cache_path = os.path.join(CACHE_TOKENIZED_DIR, "ood_csic2010.pt")
    if os.path.exists(ood_cache_path):
        ood_data = torch.load(ood_cache_path)
        ood_ds = FastPretokenizedDataset(ood_data["x"], ood_data["y"])
    else:
        manifest_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "sample_manifest.parquet"))
        ood_df = manifest_df[(manifest_df["pool_id"] == "OOD") & (manifest_df["final_label"].isin(LABEL_MAP.keys()))]
        texts = ood_df["sanitized_payload"].fillna("").astype(str).values
        labels = ood_df["final_label"].map(LABEL_MAP).values.astype(np.int64)
        x_tensor = torch.from_numpy(encode_strings_vectorized(texts, max_len=MAX_LEN))
        y_tensor = torch.from_numpy(labels)
        torch.save({"x": x_tensor, "y": y_tensor}, ood_cache_path)
        ood_ds = FastPretokenizedDataset(x_tensor, y_tensor)
        
    ood_loader = DataLoader(ood_ds, batch_size=batch_size, shuffle=False, pin_memory=torch.cuda.is_available())
    return client_test_loaders, global_b_loader, ood_loader

def load_w_base(device):
    """Loads canonical pre-trained foundation anchor W_base."""
    if not os.path.exists(W_BASE_PATH):
        raise FileNotFoundError(f"W_base checkpoint not found at {W_BASE_PATH}")
    ckpt = torch.load(W_BASE_PATH, map_location=device)
    model_type = ckpt.get("model_type", "transformer")
    model = get_neural_model(model_type, num_classes=4).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    return model, model_type, ckpt["model_state_dict"]

def aggregate_weighted_parameters(client_states, client_weights):
    """
    Computes exact proportional coordinate-wise weighted average of client state dicts:
    w_global = sum_{k=1}^K (n_k / N) * w_k
    """
    total_weight = sum(client_weights.values())
    aggregated_state = {}
    
    first_cid = list(client_states.keys())[0]
    for key in client_states[first_cid].keys():
        aggregated_tensor = torch.zeros_like(client_states[first_cid][key], dtype=torch.float32)
        for cid, state in client_states.items():
            weight = client_weights[cid] / total_weight
            aggregated_tensor += state[key].to(torch.float32) * weight
            
        aggregated_state[key] = aggregated_tensor.to(client_states[first_cid][key].dtype)
        
    return aggregated_state

def evaluate_loader_metrics(model, loader, device):
    """Evaluates accuracy, macro F1, precision, recall, and detailed classification report."""
    model.eval()
    all_preds, all_trues = [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                logits = model(x)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_trues.extend(y.numpy())
            
    acc = accuracy_score(all_trues, all_preds)
    macro_f1 = f1_score(all_trues, all_preds, labels=[0, 1, 2, 3], average="macro", zero_division=0)
    macro_prec = precision_score(all_trues, all_preds, labels=[0, 1, 2, 3], average="macro", zero_division=0)
    macro_rec = recall_score(all_trues, all_preds, labels=[0, 1, 2, 3], average="macro", zero_division=0)
    rep = classification_report(all_trues, all_preds, labels=[0, 1, 2, 3], target_names=[INV_LABEL_MAP[i] for i in range(4)], output_dict=True, zero_division=0)
    return acc, macro_f1, macro_prec, macro_rec, rep

def save_round_checkpoint(algo_name, round_num, global_state, model_type, metrics_dict):
    """Saves per-round weights checkpoint for granular checkpoint tracking."""
    algo_slug = algo_name.lower().replace(" ", "_").replace("-", "_")
    ckpt_filename = f"{algo_slug}_round_{round_num:02d}.pt"
    ckpt_path = os.path.join(ROUND_CHECKPOINTS_DIR, ckpt_filename)
    torch.save({
        "algorithm": algo_name,
        "round": round_num,
        "model_type": model_type,
        "model_state_dict": global_state,
        "metrics": metrics_dict
    }, ckpt_path)
