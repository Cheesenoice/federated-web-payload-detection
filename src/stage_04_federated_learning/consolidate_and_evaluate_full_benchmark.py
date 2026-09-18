import os
import sys
import glob
import shutil
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import f1_score, accuracy_score, classification_report, precision_score, recall_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STAGING_DIR = os.path.join(ROOT_DIR, "data", "interim", "kaggle_extracted_4track")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_04_federated")
ROUND_CKPT_DIR = os.path.join(MODELS_DIR, "round_checkpoints")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "stage_04_federated")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")
DATA_ROOT = os.path.join(ROOT_DIR, "src", "stage_04_federated_learning", "kaggle_train", "fedwebpayload_full_data")
CACHE_DIR = os.path.join(ROOT_DIR, "data", "interim", "stage_04_tokenized")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(ROUND_CKPT_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# -------------------------------------------------------------------------
# STEP 1: CONSOLIDATE EXTRACTED FILES INTO REPO STRUCTURE
# -------------------------------------------------------------------------
print("="*80)
print("STEP 1: ORGANIZING KAGGLE OUTPUTS INTO PROJECT DIRECTORIES")
print("="*80)

track_dirs = sorted(glob.glob(os.path.join(STAGING_DIR, "KMUTNB_TRACK*")))
for td in track_dirs:
    print(f"Processing: {os.path.basename(td)}")
    # Copy root models
    m_dir = os.path.join(td, "models")
    if os.path.exists(m_dir):
        for f in glob.glob(os.path.join(m_dir, "*.pt")):
            shutil.copy2(f, MODELS_DIR)
            print(f"  -> Model saved: {os.path.basename(f)}")
        # Copy round checkpoints
        r_dir = os.path.join(m_dir, "round_checkpoints")
        if os.path.exists(r_dir):
            for rf in glob.glob(os.path.join(r_dir, "*.pt")):
                shutil.copy2(rf, ROUND_CKPT_DIR)
            print(f"  -> Round Checkpoints: {len(glob.glob(os.path.join(r_dir, '*.pt')))} saved")
            
    # Copy reports & histories
    rep_dir = os.path.join(td, "reports")
    if os.path.exists(rep_dir):
        for f in glob.glob(os.path.join(rep_dir, "*.csv")):
            shutil.copy2(f, REPORTS_DIR)
            print(f"  -> Report CSV saved: {os.path.basename(f)}")

print(f"\nTotal Models in {MODELS_DIR}: {len(glob.glob(os.path.join(MODELS_DIR, '*.pt')))}")
print(f"Total Round Checkpoints in {ROUND_CKPT_DIR}: {len(glob.glob(os.path.join(ROUND_CKPT_DIR, '*.pt')))}")

# -------------------------------------------------------------------------
# STEP 2: MASTER BENCHMARK EVALUATION ACROSS ALL 539K TEST SAMPLES
# -------------------------------------------------------------------------
print("\n" + "="*80)
print("STEP 2: RUNNING MASTER BENCHMARK EVALUATION (539,553 TEST SAMPLES)")
print("="*80)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Computing Device: [{device}]")

# Model Architecture
PAD_IDX = 0
UNK_IDX = 1
VOCAB_SIZE = 130
MAX_LEN = 256
EMBEDDING_DIM = 64
NUM_CLASSES = 4
LABEL_MAP = {"benign": 0, "pathtrav": 1, "sqli": 2, "xss": 3}
INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}

def encode_strings_vectorized(texts, max_len=MAX_LEN):
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
        data = torch.load(cache_path, map_location="cpu")
        return FastPretokenizedDataset(data["x"], data["y"])
        
    print(f"   [Pre-tokenizing] {cache_name} from {os.path.basename(parquet_path)}...")
    df = pd.read_parquet(parquet_path)
    df_filtered = df[df["final_label"].isin(LABEL_MAP.keys())].copy()
    texts = df_filtered["sanitized_payload"].fillna("").astype(str).values
    labels = df_filtered["final_label"].map(LABEL_MAP).values.astype(np.int64)
    x_tensor = torch.from_numpy(encode_strings_vectorized(texts, max_len=MAX_LEN))
    y_tensor = torch.from_numpy(labels)
    torch.save({"x": x_tensor, "y": y_tensor}, cache_path)
    return FastPretokenizedDataset(x_tensor, y_tensor)

class TransformerEncoderNet(nn.Module):
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

class HybridEnsemble(nn.Module):
    def __init__(self, base_m, fed_m, alpha=0.3):
        super().__init__()
        self.base_m = base_m
        self.fed_m = fed_m
        self.alpha = alpha
    def forward(self, x):
        return self.alpha * F.softmax(self.base_m(x), dim=1) + (1.0 - self.alpha) * F.softmax(self.fed_m(x), dim=1)

# Load Test Sets
CLIENTS_DIR = os.path.join(DATA_ROOT, "clients")
client_test_loaders = {}
for i in range(1, 7):
    cid = f"client_{i}"
    p = os.path.join(CLIENTS_DIR, f"{cid}_test.parquet")
    ds = get_or_create_tokenized_dataset(p, f"{cid}_test_full")
    client_test_loaders[cid] = DataLoader(ds, batch_size=512, shuffle=False)

b_path = os.path.join(DATA_ROOT, "pool_b_global_test.parquet")
b_ds = get_or_create_tokenized_dataset(b_path, "pool_b_global_test_full")
global_b_loader = DataLoader(b_ds, batch_size=512, shuffle=False)

ood_path = os.path.join(DATA_ROOT, "ood_csic2010.parquet")
ood_ds = get_or_create_tokenized_dataset(ood_path, "ood_csic2010_full")
ood_loader = DataLoader(ood_ds, batch_size=512, shuffle=False)

print(f"Loaded 6 Client Test sets: {[len(loader.dataset) for loader in client_test_loaders.values()]}")
print(f"Loaded Global Test B: {len(b_ds):,} samples")
print(f"Loaded OOD CSIC 2010: {len(ood_ds):,} samples")

W_BASE_PATH = os.path.join(DATA_ROOT, "W_base.pt")

models_to_eval = [
    ("Foundation W_base", W_BASE_PATH, "single"),
    ("Centralized Oracle", os.path.join(MODELS_DIR, "W_centralized.pt"), "single"),
    ("Standard FedAvg", os.path.join(MODELS_DIR, "W_fedavg.pt"), "single"),
    ("FedProx (mu=0.01)", os.path.join(MODELS_DIR, "W_fedprox.pt"), "single"),
    ("FedAvgM (beta=0.9)", os.path.join(MODELS_DIR, "W_fedavgm.pt"), "single"),
    ("DAFL (Ours, lambda=0.02)", os.path.join(MODELS_DIR, "W_dafl.pt"), "single"),
    ("Hybrid Ensemble (W_base+W_fed)", os.path.join(MODELS_DIR, "W_fedavg.pt"), "ensemble_fedavg"),
    ("Hybrid Ensemble (W_base+W_dafl)", os.path.join(MODELS_DIR, "W_dafl.pt"), "ensemble_dafl")
]

def eval_m(m, loader):
    m.eval()
    preds, trues = [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            logits = m(x)
            preds.extend(torch.argmax(logits, dim=1).cpu().numpy())
            trues.extend(y.numpy())
    acc = accuracy_score(trues, preds)
    macro_f1 = f1_score(trues, preds, labels=[0, 1, 2, 3], average="macro", zero_division=0)
    return acc, macro_f1

base_ckpt = torch.load(W_BASE_PATH, map_location=device)
base_model = TransformerEncoderNet(num_classes=4).to(device)
base_model.load_state_dict(base_ckpt["model_state_dict"])

summary_rows = []

for name, path, mode in models_to_eval:
    if not os.path.exists(path):
        print(f"Skipping missing model: {path}")
        continue
    ckpt = torch.load(path, map_location=device)
    if mode == "single":
        m = TransformerEncoderNet(num_classes=4).to(device)
        m.load_state_dict(ckpt["model_state_dict"])
    else:
        fm = TransformerEncoderNet(num_classes=4).to(device)
        fm.load_state_dict(ckpt["model_state_dict"])
        m = HybridEnsemble(base_model, fm, alpha=0.3).to(device)
        
    c_f1s = [eval_m(m, client_test_loaders[f"client_{i}"])[1] for i in range(1, 7)]
    avg_local = np.mean(c_f1s)
    b_acc, b_f1 = eval_m(m, global_b_loader)
    ood_acc, ood_f1 = eval_m(m, ood_loader)
    
    row = {
        "Method": name,
        "Avg_Local_Test_F1": round(avg_local, 4),
        "Client_1_Test_F1": round(c_f1s[0], 4),
        "Client_2_Test_F1": round(c_f1s[1], 4),
        "Client_3_Test_F1": round(c_f1s[2], 4),
        "Client_4_Test_F1": round(c_f1s[3], 4),
        "Client_5_Test_F1": round(c_f1s[4], 4),
        "Client_6_Test_F1": round(c_f1s[5], 4),
        "Global_Test_B_Acc": round(b_acc, 4),
        "Global_Test_B_Macro_F1": round(b_f1, 4),
        "OOD_CSIC_Acc": round(ood_acc, 4),
        "OOD_CSIC_Macro_F1": round(ood_f1, 4)
    }
    summary_rows.append(row)
    print(f"[{name:<32}] -> Global Test B F1: {b_f1*100:.2f}% | OOD CSIC F1: {ood_f1*100:.2f}% (Acc: {ood_acc*100:.2f}%)")

df_summary = pd.DataFrame(summary_rows)
df_summary.to_csv(os.path.join(REPORTS_DIR, "federated_algorithms_master_benchmark.csv"), index=False)

print("\n" + "="*120)
print("STAGE 4: FULL-SCALE 1.32M FEDERATED LEARNING MASTER BENCHMARK (PUBLICATION TABLE 4)")
print("="*120)
print(df_summary[["Method", "Avg_Local_Test_F1", "Global_Test_B_Acc", "Global_Test_B_Macro_F1", "OOD_CSIC_Acc", "OOD_CSIC_Macro_F1"]].to_string(index=False))
print("="*120)

# -------------------------------------------------------------------------
# STEP 3: RENDER PUBLICATION FIGURES AT 300 DPI
# -------------------------------------------------------------------------
print("\nSTEP 3: RENDERING PUBLICATION FIGURES (300 DPI)")
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
        
plt.title("Federated Convergence on Global Test B ($N=354,808$ Full Scale 1.32M)", fontsize=12, fontweight="bold")
plt.xlabel("Communication Round (R)", fontweight="bold")
plt.ylabel("Global Macro F1-Score (%)", fontweight="bold")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "fig1_convergence_comparison.png"), dpi=300)
plt.close()

# OOD Bar Chart
plt.figure(figsize=(12, 5.5), dpi=300)
x = np.arange(len(df_summary))
width = 0.35
plt.bar(x - width/2, df_summary["Global_Test_B_Macro_F1"]*100, width, label="In-Domain Test B F1 (%)", color="#1e40af")
plt.bar(x + width/2, df_summary["OOD_CSIC_Macro_F1"]*100, width, label="OOD CSIC 2010 F1 (%)", color="#ea580c")
plt.xticks(x, df_summary["Method"], rotation=25, ha="right", fontweight="bold")
plt.title("Generalization Gap: In-Domain Test B vs. Zero-Shot Out-of-Domain CSIC 2010", fontsize=12, fontweight="bold")
plt.ylabel("Macro F1-Score (%)", fontweight="bold")
plt.grid(axis="y", linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "fig2_ood_generalization_gap.png"), dpi=300)
plt.close()

print(f"Generated all 300 DPI plots in {FIGURES_DIR}")
print("\nMASTER CONSOLIDATION COMPLETE!")
