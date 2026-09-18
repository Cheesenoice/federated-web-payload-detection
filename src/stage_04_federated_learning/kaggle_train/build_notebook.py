import json
import os

nb = {
    'cells': [],
    'metadata': {
        'kernelspec': {
            'display_name': 'Python 3',
            'language': 'python',
            'name': 'python3'
        },
        'language_info': {
            'codemirror_mode': {'name': 'ipython', 'version': 3},
            'file_extension': '.py',
            'mimetype': 'text/x-python',
            'name': 'python',
            'nbconvert_exporter': 'python',
            'pygments_lexer': 'ipython3',
            'version': '3.11.0'
        },
        'accelerator': 'GPU'
    },
    'nbformat': 4,
    'nbformat_minor': 4
}

def add_md(source):
    nb['cells'].append({
        'cell_type': 'markdown',
        'metadata': {},
        'source': [line + '\n' for line in source.strip().split('\n')]
    })

def add_code(source):
    nb['cells'].append({
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [line + '\n' for line in source.strip().split('\n')]
    })

# Cell 0: Header
add_md('''# 🛡️ Stage 4: Full-Scale Federated Learning Benchmark on 1.32M Web Payloads
### KMUTNB Cybersecurity Research Project | Federated Web Payload Detection

This notebook executes the complete **Stage 4 Federated Learning Suite** across **1.32 Million Payloads** distributed over **6 Non-IID Enterprise Client Silos**.

**Algorithms Benchmarked:**
1. **Centralized Learning Oracle** (Upper-bound baseline on pooled client data)
2. **Standard FedAvg** (McMahan et al., AISTATS 2017)
3. **FedProx** with Proximal Regularization $\\mu = 0.01$ (Li et al., MLSys 2020)
4. **FedAvgM** with Server Momentum $\\beta = 0.9$ (Hsu et al., NeurIPS 2019)
5. **Dual-Anchor FL (DAFL - Ours)** with Anchor Regularization $\\lambda = 0.02$
6. **Hybrid Ensemble** ($W_{base} + W_{fedavg}$ Soft Blending)

**Evaluation Holdouts:**
- **6 Local Client Test Sets**
- **Global Network Test B Holdout:** $354,808$ samples
- **External Out-of-Domain (OOD) Benchmark:** CSIC 2010 ($122,130$ samples)''')

# Cell 1: Environment & Path Discovery
add_code('''import os
import sys
import time
import copy
import json
import logging
import shutil
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from torch.utils.data import Dataset, DataLoader, ConcatDataset
from sklearn.metrics import f1_score, accuracy_score, classification_report, precision_score, recall_score
import matplotlib
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Device Configuration & Kaggle GPU Architecture Check
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("="*80)
print(f"🚀 RUNNING DEVICE: [{device}]")
if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"   GPU Model   : {gpu_name} (Architecture: sm_{cap[0]}{cap[1]})")
    print(f"   Total VRAM  : {vram_gb:.2f} GB")
    print(f"   CUDA Devices: {torch.cuda.device_count()} available")
    if cap[0] < 7:
        print("\n⚠️ WARNING: Tesla P100 (sm_60) lacks PyTorch 2.6 CUDA kernel images.")
        print("👉 RECOMMENDED FIX: In Kaggle Settings (right panel), set Accelerator to 'GPU T4 x2'.\n")
print("="*80)

# Dynamic Path Discovery
KAGGLE_INPUT_DIR = "/kaggle/input"
WORKING_DIR = "/kaggle/working" if os.path.exists("/kaggle") else "./outputs_kaggle"

DATA_ROOT = None
potential_paths = [
    os.path.join(KAGGLE_INPUT_DIR, "kmutnb-webpayload-full-data", "fedwebpayload_full_data"),
    os.path.join(KAGGLE_INPUT_DIR, "kmutnb-webpayload-full-data"),
    os.path.join(KAGGLE_INPUT_DIR, "fedwebpayload-full-data", "fedwebpayload_full_data"),
    os.path.join(KAGGLE_INPUT_DIR, "fedwebpayload-full-data"),
    "./fedwebpayload_full_data",
    "../fedwebpayload_full_data"
]

for p in potential_paths:
    if os.path.exists(os.path.join(p, "clients")) or os.path.exists(os.path.join(p, "pool_b_global_test.parquet")):
        DATA_ROOT = p
        break

if DATA_ROOT is None:
    for root, dirs, files in os.walk(KAGGLE_INPUT_DIR):
        if "pool_b_global_test.parquet" in files:
            DATA_ROOT = root
            break

print(f"📂 Resolved Data Root: {DATA_ROOT}")
CLIENTS_DIR = os.path.join(DATA_ROOT, "clients") if os.path.exists(os.path.join(DATA_ROOT, "clients")) else DATA_ROOT
CACHE_DIR = os.path.join(WORKING_DIR, "tokenized_cache")
MODELS_DIR = os.path.join(WORKING_DIR, "models")
ROUND_CKPT_DIR = os.path.join(MODELS_DIR, "round_checkpoints")
REPORTS_DIR = os.path.join(WORKING_DIR, "reports")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")

for d in [CACHE_DIR, MODELS_DIR, ROUND_CKPT_DIR, REPORTS_DIR, FIGURES_DIR]:
    os.makedirs(d, exist_ok=True)
print("✅ Environment directories initialized successfully.")
''')

# Cell 2: Vectorized Tokenizer & Data Loader
add_code('''# Constants & Label Mapping
PAD_IDX = 0
UNK_IDX = 1
VOCAB_SIZE = 130
MAX_LEN = 256
LABEL_MAP = {"benign": 0, "pathtrav": 1, "sqli": 2, "xss": 3}
INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}

def encode_strings_vectorized(texts, max_len=MAX_LEN):
    """Ultra-fast ASCII byte tokenization into contiguous uint8 arrays."""
    n = len(texts)
    arr = np.full((n, max_len), PAD_IDX, dtype=np.uint8)
    for i, s in enumerate(texts):
        if not isinstance(s, str):
            s = str(s) if s is not None else ""
        b = s.encode("ascii", errors="replace")[:max_len]
        for j in range(len(b)):
            val = b[j]
            arr[i, j] = (val + 2) if val < 128 else UNK_IDX
    return arr

class FastPretokenizedDataset(Dataset):
    def __init__(self, x_uint8_tensor, y_int64_tensor):
        self.x = x_uint8_tensor
        self.y = y_int64_tensor

    def __len__(self):
        return len(self.x)

    def __getitem__(self, idx):
        return self.x[idx].long(), self.y[idx]

def get_or_create_tokenized_dataset(parquet_path, cache_name):
    cache_path = os.path.join(CACHE_DIR, f"{cache_name}.pt")
    if os.path.exists(cache_path):
        data = torch.load(cache_path)
        return FastPretokenizedDataset(data["x"], data["y"])
        
    print(f"   [Pre-tokenizing] {cache_name} from {os.path.basename(parquet_path)}...")
    df = pd.read_parquet(parquet_path)
    df_filtered = df[df["final_label"].isin(LABEL_MAP.keys())].copy()
    
    texts = df_filtered["sanitized_payload"].fillna("").astype(str).values
    labels = df_filtered["final_label"].map(LABEL_MAP).values.astype(np.int64)
    
    x_tensor = torch.from_numpy(encode_strings_vectorized(texts, max_len=MAX_LEN))
    y_tensor = torch.from_numpy(labels)
    
    torch.save({"x": x_tensor, "y": y_tensor}, cache_path)
    mb_size = x_tensor.element_size() * x_tensor.nelement() / (1024*1024)
    print(f"      -> Cached {cache_name}.pt ({len(x_tensor):,} samples, {mb_size:.1f} MB)")
    return FastPretokenizedDataset(x_tensor, y_tensor)

def load_client_loaders(batch_size=512):
    train_loaders, val_loaders, client_sample_counts = {}, {}, {}
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
    client_test_loaders = {}
    for i in range(1, 7):
        cid = f"client_{i}"
        path = os.path.join(CLIENTS_DIR, f"{cid}_test.parquet")
        ds = get_or_create_tokenized_dataset(path, f"{cid}_test")
        client_test_loaders[cid] = DataLoader(ds, batch_size=batch_size, shuffle=False, pin_memory=torch.cuda.is_available())
        
    b_path = os.path.join(DATA_ROOT, "pool_b_global_test.parquet")
    b_ds = get_or_create_tokenized_dataset(b_path, "pool_b_global_test")
    global_b_loader = DataLoader(b_ds, batch_size=batch_size, shuffle=False, pin_memory=torch.cuda.is_available())
    
    # OOD CSIC
    ood_cache_path = os.path.join(CACHE_DIR, "ood_csic2010.pt")
    if os.path.exists(ood_cache_path):
        ood_data = torch.load(ood_cache_path)
        ood_ds = FastPretokenizedDataset(ood_data["x"], ood_data["y"])
    else:
        ood_parquet = os.path.join(DATA_ROOT, "ood_csic2010.parquet")
        if os.path.exists(ood_parquet):
            ood_df = pd.read_parquet(ood_parquet)
        else:
            manifest_df = pd.read_parquet(os.path.join(DATA_ROOT, "sample_manifest.parquet"))
            ood_df = manifest_df[(manifest_df["pool_id"] == "OOD") & (manifest_df["final_label"].isin(LABEL_MAP.keys()))]
            
        texts = ood_df["sanitized_payload"].fillna("").astype(str).values
        labels = ood_df["final_label"].map(LABEL_MAP).values.astype(np.int64)
        x_tensor = torch.from_numpy(encode_strings_vectorized(texts, max_len=MAX_LEN))
        y_tensor = torch.from_numpy(labels)
        torch.save({"x": x_tensor, "y": y_tensor}, ood_cache_path)
        ood_ds = FastPretokenizedDataset(x_tensor, y_tensor)
        
    ood_loader = DataLoader(ood_ds, batch_size=batch_size, shuffle=False, pin_memory=torch.cuda.is_available())
    return client_test_loaders, global_b_loader, ood_loader
''')

# Cell 3: Neural Architectures & Evaluation Tools
add_code('''EMBEDDING_DIM = 64
NUM_CLASSES = 4

class TransformerEncoderNet(nn.Module):
    """Character-Level 3-Layer Transformer Encoder with Multi-Head Self-Attention."""
    def __init__(self, vocab_size=VOCAB_SIZE, embed_dim=EMBEDDING_DIM, num_heads=4, num_layers=3, num_classes=4, max_len=MAX_LEN):
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
        seq_len = x.size(1)
        padding_mask = (x == 0)
        emb = self.token_embedding(x) + self.pos_embedding[:, :seq_len, :]
        h = self.transformer_encoder(emb, src_key_padding_mask=padding_mask)
        mask = (~padding_mask).unsqueeze(-1).float()
        pooled = torch.sum(h * mask, dim=1) / torch.clamp(mask.sum(dim=1), min=1.0)
        pooled = self.ln(pooled)
        pooled = self.dropout(pooled)
        return self.fc(pooled)

def load_w_base(device):
    w_base_candidates = [
        os.path.join(DATA_ROOT, "W_base.pt"),
        os.path.join(DATA_ROOT, "models", "W_base.pt"),
        "./W_base.pt"
    ]
    path = next((p for p in w_base_candidates if os.path.exists(p)), None)
    if path is None:
        raise FileNotFoundError("W_base.pt anchor not found in dataset root.")
    ckpt = torch.load(path, map_location=device)
    model = TransformerEncoderNet(num_classes=4).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    return model, "transformer", ckpt["model_state_dict"]

def aggregate_weighted_parameters(client_states, client_weights):
    total_weight = sum(client_weights.values())
    aggregated_state = {}
    first_cid = list(client_states.keys())[0]
    for key in client_states[first_cid].keys():
        agg_tensor = torch.zeros_like(client_states[first_cid][key], dtype=torch.float32)
        for cid, state in client_states.items():
            weight = client_weights[cid] / total_weight
            agg_tensor += state[key].to(torch.float32) * weight
        aggregated_state[key] = agg_tensor.to(client_states[first_cid][key].dtype)
    return aggregated_state

def evaluate_loader_metrics(model, loader, device):
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
    algo_slug = algo_name.lower().replace(" ", "_").replace("-", "_")
    ckpt_path = os.path.join(ROUND_CKPT_DIR, f"{algo_slug}_round_{round_num:02d}.pt")
    torch.save({"algorithm": algo_name, "round": round_num, "model_type": model_type, "model_state_dict": global_state, "metrics": metrics_dict}, ckpt_path)
''')

# Cell 4: Centralized Oracle
add_code('''print("="*80)
print("=== STARTING STAGE 4.1: CENTRALIZED ORACLE (UPPER BOUND) ===")
print("="*80)
central_model, model_type, _ = load_w_base(device)
train_loaders, val_loaders, _ = load_client_loaders(batch_size=512)

pooled_train_ds = ConcatDataset([loader.dataset for loader in train_loaders.values()])
pooled_val_ds = ConcatDataset([loader.dataset for loader in val_loaders.values()])
print(f"Pooled Centralized Training Samples:   {len(pooled_train_ds):,}")
print(f"Pooled Centralized Validation Samples: {len(pooled_val_ds):,}")

central_train_loader = DataLoader(pooled_train_ds, batch_size=512, shuffle=True, pin_memory=torch.cuda.is_available())
central_val_loader = DataLoader(pooled_val_ds, batch_size=512, shuffle=False, pin_memory=torch.cuda.is_available())

criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
optimizer = torch.optim.AdamW(central_model.parameters(), lr=3e-4, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-5)
scaler = torch.amp.GradScaler(enabled=torch.cuda.is_available())

epochs = 10
best_val_f1, best_state = 0.0, None
start_t = time.time()

for ep in range(1, epochs + 1):
    ep_t0 = time.time()
    central_model.train()
    total_loss = 0.0
    for x, y in central_train_loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
            loss = criterion(central_model(x), y)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        total_loss += loss.item()
    scheduler.step()
    val_acc, val_f1, _, _, _ = evaluate_loader_metrics(central_model, central_val_loader, device)
    ep_time = time.time() - ep_t0
    print(f"   [Centralized] Epoch {ep:02d}/{epochs:02d} ({ep_time:.1f}s) | Train Loss: {total_loss/len(central_train_loader):.4f} | Val F1: {val_f1*100:.2f}% (Acc: {val_acc*100:.2f}%)")
    if val_f1 > best_val_f1:
        best_val_f1, best_state = val_f1, copy.deepcopy(central_model.state_dict())

torch.save({"algorithm": "Centralized_Oracle", "model_type": model_type, "model_state_dict": best_state, "val_f1": best_val_f1}, os.path.join(MODELS_DIR, "W_centralized.pt"))
print(f"✅ Saved Centralized Oracle Checkpoint to {MODELS_DIR}/W_centralized.pt (Total: {time.time()-start_t:.1f}s)\n")
''')

# Cell 5: Standard FedAvg
add_code('''print("="*80)
print("=== STARTING STAGE 4.2: STANDARD FEDERATED AVERAGING (FedAvg) ===")
print("="*80)
global_model, model_type, global_state = load_w_base(device)
train_loaders, val_loaders, client_sample_counts = load_client_loaders(batch_size=512)
_, global_b_loader, _ = load_test_holdouts(batch_size=512)

rounds, local_epochs = 10, 3
history_fedavg = []

def train_local(cid, state, lr=3e-4):
    local_m = TransformerEncoderNet(num_classes=4).to(device)
    local_m.load_state_dict(copy.deepcopy(state))
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(local_m.parameters(), lr=lr, weight_decay=1e-4)
    scaler = torch.amp.GradScaler(enabled=torch.cuda.is_available())
    local_m.train()
    for _ in range(local_epochs):
        for x, y in train_loaders[cid]:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                loss = criterion(local_m(x), y)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
    _, v_f1, _, _, _ = evaluate_loader_metrics(local_m, val_loaders[cid], device)
    return local_m.state_dict(), v_f1

for r in range(1, rounds + 1):
    t0 = time.time()
    c_states, c_f1s = {}, {}
    for i in range(1, 7):
        cid = f"client_{i}"
        s, f1 = train_local(cid, global_state)
        c_states[cid], c_f1s[cid] = s, f1
    global_state = aggregate_weighted_parameters(c_states, client_sample_counts)
    global_model.load_state_dict(global_state)
    b_acc, b_f1, _, _, _ = evaluate_loader_metrics(global_model, global_b_loader, device)
    round_t = time.time() - t0
    print(f"   [FedAvg] Round {r:02d}/{rounds:02d} ({round_t:.1f}s) -> Global Test B Macro F1: {b_f1*100:.2f}% (Acc: {b_acc*100:.2f}%)")
    entry = {"Algorithm": "FedAvg", "Round": r, "Global_Test_B_Acc": b_acc, "Global_Test_B_Macro_F1": b_f1, "Time_s": round_t}
    history_fedavg.append(entry)
    save_round_checkpoint("FedAvg", r, global_state, model_type, entry)

pd.DataFrame(history_fedavg).to_csv(os.path.join(REPORTS_DIR, "history_fedavg.csv"), index=False)
torch.save({"algorithm": "FedAvg", "model_type": model_type, "model_state_dict": global_state}, os.path.join(MODELS_DIR, "W_fedavg.pt"))
print(f"✅ Saved FedAvg Checkpoint & Round Histories.\n")
''')

# Cell 6: FedProx
add_code('''print("="*80)
print("=== STARTING STAGE 4.3: FEDPROX (mu=0.01) ===")
print("="*80)
global_model, model_type, global_state = load_w_base(device)
train_loaders, val_loaders, client_sample_counts = load_client_loaders(batch_size=512)
_, global_b_loader, _ = load_test_holdouts(batch_size=512)

MU_PROXIMAL = 0.01
rounds, local_epochs = 10, 3
history_fedprox = []

def train_fedprox(cid, g_state, mu=MU_PROXIMAL):
    local_m = TransformerEncoderNet(num_classes=4).to(device)
    local_m.load_state_dict(copy.deepcopy(g_state))
    g_tensors = {k: v.clone().detach().to(device) for k, v in g_state.items()}
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(local_m.parameters(), lr=3e-4, weight_decay=1e-4)
    scaler = torch.amp.GradScaler(enabled=torch.cuda.is_available())
    local_m.train()
    for _ in range(local_epochs):
        for x, y in train_loaders[cid]:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                loss = criterion(local_m(x), y)
                prox = sum(torch.sum((p - g_tensors[n]) ** 2) for n, p in local_m.named_parameters() if n in g_tensors)
                total_loss = loss + (mu / 2.0) * prox
            scaler.scale(total_loss).backward()
            scaler.step(optimizer)
            scaler.update()
    _, v_f1, _, _, _ = evaluate_loader_metrics(local_m, val_loaders[cid], device)
    return local_m.state_dict(), v_f1

for r in range(1, rounds + 1):
    t0 = time.time()
    c_states, c_f1s = {}, {}
    for i in range(1, 7):
        cid = f"client_{i}"
        s, f1 = train_fedprox(cid, global_state)
        c_states[cid], c_f1s[cid] = s, f1
    global_state = aggregate_weighted_parameters(c_states, client_sample_counts)
    global_model.load_state_dict(global_state)
    b_acc, b_f1, _, _, _ = evaluate_loader_metrics(global_model, global_b_loader, device)
    round_t = time.time() - t0
    print(f"   [FedProx] Round {r:02d}/{rounds:02d} ({round_t:.1f}s) -> Global Test B Macro F1: {b_f1*100:.2f}% (Acc: {b_acc*100:.2f}%)")
    entry = {"Algorithm": "FedProx", "Round": r, "Global_Test_B_Acc": b_acc, "Global_Test_B_Macro_F1": b_f1, "Time_s": round_t}
    history_fedprox.append(entry)
    save_round_checkpoint("FedProx", r, global_state, model_type, entry)

pd.DataFrame(history_fedprox).to_csv(os.path.join(REPORTS_DIR, "history_fedprox.csv"), index=False)
torch.save({"algorithm": "FedProx", "model_type": model_type, "model_state_dict": global_state}, os.path.join(MODELS_DIR, "W_fedprox.pt"))
print(f"✅ Saved FedProx Checkpoint & Round Histories.\n")
''')

# Cell 7: FedAvgM
add_code('''print("="*80)
print("=== STARTING STAGE 4.4: FEDAVGM (beta=0.9) ===")
print("="*80)
global_model, model_type, global_state = load_w_base(device)
train_loaders, val_loaders, client_sample_counts = load_client_loaders(batch_size=512)
_, global_b_loader, _ = load_test_holdouts(batch_size=512)

BETA_MOMENTUM = 0.9
velocity_buffer = {k: torch.zeros_like(v, dtype=torch.float32) for k, v in global_state.items()}
rounds, local_epochs = 10, 3
history_fedavgm = []

for r in range(1, rounds + 1):
    t0 = time.time()
    c_states = {}
    for i in range(1, 7):
        cid = f"client_{i}"
        s, _ = train_local(cid, global_state)
        c_states[cid] = s
    w_avg = aggregate_weighted_parameters(c_states, client_sample_counts)
    
    new_global = {}
    for k in global_state.keys():
        delta = global_state[k].to(torch.float32) - w_avg[k].to(torch.float32)
        velocity_buffer[k] = BETA_MOMENTUM * velocity_buffer[k] + delta
        new_tensor = global_state[k].to(torch.float32) - velocity_buffer[k]
        new_global[k] = new_tensor.to(global_state[k].dtype)
        
    global_state = new_global
    global_model.load_state_dict(global_state)
    b_acc, b_f1, _, _, _ = evaluate_loader_metrics(global_model, global_b_loader, device)
    round_t = time.time() - t0
    print(f"   [FedAvgM] Round {r:02d}/{rounds:02d} ({round_t:.1f}s) -> Global Test B Macro F1: {b_f1*100:.2f}% (Acc: {b_acc*100:.2f}%)")
    entry = {"Algorithm": "FedAvgM", "Round": r, "Global_Test_B_Acc": b_acc, "Global_Test_B_Macro_F1": b_f1, "Time_s": round_t}
    history_fedavgm.append(entry)
    save_round_checkpoint("FedAvgM", r, global_state, model_type, entry)

pd.DataFrame(history_fedavgm).to_csv(os.path.join(REPORTS_DIR, "history_fedavgm.csv"), index=False)
torch.save({"algorithm": "FedAvgM", "model_type": model_type, "model_state_dict": global_state}, os.path.join(MODELS_DIR, "W_fedavgm.pt"))
print(f"✅ Saved FedAvgM Checkpoint & Round Histories.\n")
''')

# Cell 8: DAFL & Hybrid Ensemble
add_code('''print("="*80)
print("=== STARTING STAGE 4.5 & 4.6: DAFL (lambda=0.02) & HYBRID ENSEMBLE ===")
print("="*80)
global_model, model_type, global_state = load_w_base(device)
base_model, _, _ = load_w_base(device)
base_tensors = {k: v.clone().detach().to(device) for k, v in global_state.items()}

LAMBDA_ANCHOR = 0.02
rounds, local_epochs = 10, 3
history_dafl = []

def train_dafl(cid, g_state, lambda_reg=LAMBDA_ANCHOR):
    local_m = TransformerEncoderNet(num_classes=4).to(device)
    local_m.load_state_dict(copy.deepcopy(g_state))
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(local_m.parameters(), lr=3e-4, weight_decay=1e-4)
    scaler = torch.amp.GradScaler(enabled=torch.cuda.is_available())
    local_m.train()
    for _ in range(local_epochs):
        for x, y in train_loaders[cid]:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                loss = criterion(local_m(x), y)
                anchor_loss = sum(torch.sum((p - base_tensors[n]) ** 2) for n, p in local_m.named_parameters() if n in base_tensors)
                total_loss = loss + (lambda_reg / 2.0) * anchor_loss
            scaler.scale(total_loss).backward()
            scaler.step(optimizer)
            scaler.update()
    _, v_f1, _, _, _ = evaluate_loader_metrics(local_m, val_loaders[cid], device)
    return local_m.state_dict(), v_f1

for r in range(1, rounds + 1):
    t0 = time.time()
    c_states = {}
    for i in range(1, 7):
        cid = f"client_{i}"
        s, _ = train_dafl(cid, global_state)
        c_states[cid] = s
    global_state = aggregate_weighted_parameters(c_states, client_sample_counts)
    global_model.load_state_dict(global_state)
    b_acc, b_f1, _, _, _ = evaluate_loader_metrics(global_model, global_b_loader, device)
    round_t = time.time() - t0
    print(f"   [DAFL] Round {r:02d}/{rounds:02d} ({round_t:.1f}s) -> Global Test B Macro F1: {b_f1*100:.2f}% (Acc: {b_acc*100:.2f}%)")
    entry = {"Algorithm": "DAFL", "Round": r, "Global_Test_B_Acc": b_acc, "Global_Test_B_Macro_F1": b_f1, "Time_s": round_t}
    history_dafl.append(entry)
    save_round_checkpoint("DAFL", r, global_state, model_type, entry)

pd.DataFrame(history_dafl).to_csv(os.path.join(REPORTS_DIR, "history_dafl.csv"), index=False)
torch.save({"algorithm": "DAFL", "model_type": model_type, "model_state_dict": global_state}, os.path.join(MODELS_DIR, "W_dafl.pt"))

# Hybrid Ensemble Definition
class HybridEnsemble(nn.Module):
    def __init__(self, base_m, fed_m, alpha=0.3):
        super().__init__()
        self.base_m = base_m
        self.fed_m = fed_m
        self.alpha = alpha
    def forward(self, x):
        return self.alpha * F.softmax(self.base_m(x), dim=1) + (1.0 - self.alpha) * F.softmax(self.fed_m(x), dim=1)

fed_ckpt = torch.load(os.path.join(MODELS_DIR, "W_fedavg.pt"), map_location=device)
fed_m = TransformerEncoderNet(num_classes=4).to(device)
fed_m.load_state_dict(fed_ckpt["model_state_dict"])
ensemble_model = HybridEnsemble(base_model, fed_m, alpha=0.3).to(device)

torch.save({"algorithm": "Hybrid_Ensemble", "model_type": "transformer", "base_model_state_dict": base_model.state_dict(), "fed_model_state_dict": fed_m.state_dict()}, os.path.join(MODELS_DIR, "W_ensemble.pt"))
print(f"✅ Saved DAFL Checkpoint & Hybrid Ensemble.\n")
''')

# Cell 9: Master Evaluation & Publication Table 4
add_code('''print("="*80)
print("=== STAGE 4.7: MASTER FEDERATED BENCHMARK EVALUATION (ALL HOLDOUTS) ===")
print("="*80)
client_test_loaders, global_b_loader, ood_loader = load_test_holdouts(batch_size=512)

models_to_eval = [
    ("Foundation W_base", os.path.join(DATA_ROOT, "W_base.pt"), "single"),
    ("Centralized Oracle", os.path.join(MODELS_DIR, "W_centralized.pt"), "single"),
    ("Standard FedAvg", os.path.join(MODELS_DIR, "W_fedavg.pt"), "single"),
    ("FedProx (mu=0.01)", os.path.join(MODELS_DIR, "W_fedprox.pt"), "single"),
    ("FedAvgM (beta=0.9)", os.path.join(MODELS_DIR, "W_fedavgm.pt"), "single"),
    ("DAFL (Ours, lambda=0.02)", os.path.join(MODELS_DIR, "W_dafl.pt"), "single"),
    ("Hybrid Ensemble (W_base+W_fed)", os.path.join(MODELS_DIR, "W_ensemble.pt"), "ensemble")
]

def eval_m(m, loader):
    m.eval()
    preds, trues = [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                out = m(x)
            preds.extend(torch.argmax(out, dim=1).cpu().numpy())
            trues.extend(y.numpy())
    acc = accuracy_score(trues, preds)
    f1 = f1_score(trues, preds, labels=[0, 1, 2, 3], average="macro", zero_division=0)
    return acc, f1

summary_rows = []
for name, path, mode in models_to_eval:
    if not os.path.exists(path):
        continue
    ckpt = torch.load(path, map_location=device)
    if mode == "single":
        m = TransformerEncoderNet(num_classes=4).to(device)
        m.load_state_dict(ckpt["model_state_dict"])
    else:
        bm, _, _ = load_w_base(device)
        fm = TransformerEncoderNet(num_classes=4).to(device)
        fm.load_state_dict(ckpt["fed_model_state_dict"])
        m = HybridEnsemble(bm, fm, alpha=0.3).to(device)
        
    c_f1s = [eval_m(m, client_test_loaders[f"client_{i}"])[1] for i in range(1, 7)]
    avg_local = np.mean(c_f1s)
    b_acc, b_f1 = eval_m(m, global_b_loader)
    ood_acc, ood_f1 = eval_m(m, ood_loader)
    
    summary_rows.append({
        "Method": name,
        "Avg_Local_Test_F1": round(avg_local, 4),
        "Client_1_Test_F1": round(c_f1s[0], 4),
        "Client_3_Test_F1": round(c_f1s[2], 4),
        "Client_5_Test_F1": round(c_f1s[4], 4),
        "Global_Test_B_Acc": round(b_acc, 4),
        "Global_Test_B_Macro_F1": round(b_f1, 4),
        "OOD_CSIC_Acc": round(ood_acc, 4),
        "OOD_CSIC_Macro_F1": round(ood_f1, 4)
    })

df_summary = pd.DataFrame(summary_rows)
df_summary.to_csv(os.path.join(REPORTS_DIR, "federated_algorithms_master_benchmark.csv"), index=False)

print("\n" + "="*120)
print("STAGE 4: FEDERATED LEARNING ALGORITHMS MASTER BENCHMARK (PUBLICATION TABLE 4)")
print("="*120)
print(df_summary.to_string(index=False))
print("="*120)
''')

# Cell 10: Render Publication Figures
add_code('''# Render Figures
plt.figure(figsize=(10, 5), dpi=300)
files = {
    "FedAvg": (os.path.join(REPORTS_DIR, "history_fedavg.csv"), "#2563eb", "o"),
    "FedProx": (os.path.join(REPORTS_DIR, "history_fedprox.csv"), "#d97706", "s"),
    "FedAvgM": (os.path.join(REPORTS_DIR, "history_fedavgm.csv"), "#059669", "^"),
    "DAFL (Ours)": (os.path.join(REPORTS_DIR, "history_dafl.csv"), "#7c3aed", "D")
}

for name, (path, color, marker) in files.items():
    if os.path.exists(path):
        df = pd.read_csv(path)
        plt.plot(df["Round"], df["Global_Test_B_Macro_F1"] * 100, marker=marker, label=name, color=color, linewidth=2)
        
plt.title("Federated Convergence on Global Test B ($N=354,808$)", fontsize=12, fontweight="bold")
plt.xlabel("Communication Round (R)", fontweight="bold")
plt.ylabel("Global Macro F1-Score (%)", fontweight="bold")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "fig1_convergence_comparison.png"), dpi=300)
plt.show()

# OOD Bar Chart
plt.figure(figsize=(11, 5), dpi=300)
x = np.arange(len(df_summary))
width = 0.35
plt.bar(x - width/2, df_summary["Global_Test_B_Macro_F1"]*100, width, label="In-Domain Test B F1 (%)", color="#1e40af")
plt.bar(x + width/2, df_summary["OOD_CSIC_Macro_F1"]*100, width, label="OOD CSIC 2010 F1 (%)", color="#ea580c")
plt.xticks(x, df_summary["Method"], rotation=25, ha="right", fontweight="bold")
plt.title("In-Domain vs Out-of-Domain Generalization Gap", fontsize=12, fontweight="bold")
plt.ylabel("Macro F1-Score (%)", fontweight="bold")
plt.grid(axis="y", linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "fig2_ood_generalization_gap.png"), dpi=300)
plt.show()
print(f"✅ Saved all publication plots to {FIGURES_DIR}")
''')

# Cell 11: Auto-bundle all outputs into a single downloadable ZIP
add_code('''# Final Step: Bundle all Checkpoints, CSVs, Figures into a single downloadable ZIP archive
bundle_zip_base = os.path.join(WORKING_DIR, "KMUTNB_STAGE_04_FULL_BENCHMARK_RESULTS")
print("="*80)
print("📦 PACKING ALL MODELS, CHECKPOINTS, CSVS & FIGURES INTO DOWNLOADABLE ZIP...")
print("="*80)

# Create a clean packaging directory excluding the raw token cache to keep ZIP small
package_dir = os.path.join(WORKING_DIR, "export_bundle")
os.makedirs(package_dir, exist_ok=True)

shutil.copytree(MODELS_DIR, os.path.join(package_dir, "models"), dirs_exist_ok=True)
shutil.copytree(REPORTS_DIR, os.path.join(package_dir, "reports"), dirs_exist_ok=True)

shutil.make_archive(bundle_zip_base, 'zip', package_dir)
zip_path = bundle_zip_base + ".zip"
zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)

print(f"🎉 SUCCESS! All research artifacts packaged into:")
print(f"   👉 {zip_path} ({zip_size_mb:.2f} MB)")
print("="*80)
print("You can download this ZIP file directly from the Kaggle Output panel on the right sidebar!")
''')

nb_out_path = r'C:\Users\huynh\Desktop\fedwebpayload\src\stage_04_federated_learning\kaggle_train\stage_04_full_federated_benchmark.ipynb'
with open(nb_out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=2)

print(f'Successfully created Kaggle Notebook at: {nb_out_path}')
