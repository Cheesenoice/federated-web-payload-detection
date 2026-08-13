"""
Generate 4x 6x6 Non-IID Cross-Client Evaluation Matrices (`src/eval/generate_4x6x6_matrices.py`)

Computes full 6x6 Macro-F1 evaluation matrices for 15 FL rounds:
  1. Baseline: Local-Only Models (No FL)
  2. FL Algorithm 1: FedAvg
  3. FL Algorithm 2: FedProx
  4. FL Algorithm 3: FedLC
  5. FL Algorithm 4: FedPayload-DAFL (PROPOSED METHOD)

Outputs JSON to `data/reporting/full_4x6x6_matrices.json`.
"""

import os
import sys
import json
import logging
import torch
import numpy as np
import pandas as pd
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import f1_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.models.charcnn import CharCNN
from src.training.losses import FedLCCalibratedLoss
from src.federated.aggregate import aggregate_fedavg, aggregate_dafl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
FEATURES_DIR = os.path.join(DATA_DIR, "features")
REPORTING_DIR = os.path.join(DATA_DIR, "reporting")
os.makedirs(REPORTING_DIR, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
LABEL_MAP = {"pathtrav": 0, "sqli": 1, "xss": 2, "benign": 3}


def evaluate_model_on_loader(model, loader):
    model.eval()
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for bx, by in loader:
            bx, by = bx.to(DEVICE), by.to(DEVICE)
            preds = model(bx).argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(by.cpu().numpy())
    return f1_score(all_targets, all_preds, average="macro", zero_division=0)


def run_generate_4x6x6_matrices(fl_rounds: int = 15):
    logger.info(f"=== GENERATING 4x 6x6 CROSS-CLIENT MATRICES ({fl_rounds} FL ROUNDS) ===")

    client_loaders = {}
    client_tensors = {}
    client_labels = {}
    client_counts = []

    for c_id in range(1, 7):
        df_c = pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}.parquet"))
        y_c = np.array([LABEL_MAP.get(lbl, 3) for lbl in df_c["label_multiclass"]])
        c_tokens = np.load(os.path.join(FEATURES_DIR, f"client_{c_id}_tokens.npy"))

        ds = TensorDataset(torch.from_numpy(c_tokens).long(), torch.from_numpy(y_c).long())
        loader = DataLoader(ds, batch_size=128, shuffle=False)

        client_tensors[c_id] = c_tokens
        client_labels[c_id] = y_c
        client_loaders[c_id] = loader

        counts = [int((y_c == i).sum()) for i in range(4)]
        client_counts.append(counts)

    all_matrices = {}

    # ------------------------------------------------------------------
    # 1. Local-Only 6x6 Matrix (No FL)
    # ------------------------------------------------------------------
    logger.info("Building Matrix 0: Local-Only (No FL)...")
    local_models = {}
    for c_id in range(1, 7):
        ds_train = TensorDataset(torch.from_numpy(client_tensors[c_id]).long(), torch.from_numpy(client_labels[c_id]).long())
        train_loader = DataLoader(ds_train, batch_size=64, shuffle=True)
        
        m = CharCNN(vocab_size=128, num_classes=4).to(DEVICE)
        opt = torch.optim.Adam(m.parameters(), lr=1e-3)
        crit = torch.nn.CrossEntropyLoss()

        m.train()
        for epoch in range(3):
            for bx, by in train_loader:
                bx, by = bx.to(DEVICE), by.to(DEVICE)
                opt.zero_grad()
                loss = crit(m(bx), by)
                loss.backward()
                opt.step()
        local_models[c_id] = m

    mat_local = np.zeros((6, 6))
    for i in range(6):
        for j in range(6):
            mat_local[i, j] = evaluate_model_on_loader(local_models[i+1], client_loaders[j+1])

    all_matrices["Local-Only"] = mat_local.tolist()

    # ------------------------------------------------------------------
    # 2. Compute 6x6 Matrix for FedAvg, FedProx, FedLC, FedPayload-DAFL
    # ------------------------------------------------------------------
    algos = ["FedAvg", "FedProx", "FedLC", "FedPayload-DAFL"]

    for algo in algos:
        logger.info(f"Building 6x6 Matrix for FL Algorithm: {algo} ({fl_rounds} rounds)...")
        global_m = CharCNN(vocab_size=128, num_classes=4).to(DEVICE)

        client_models_post_fl = {}

        for r in range(fl_rounds):
            client_weights = []
            for i in range(6):
                c_id = i + 1
                local_m = CharCNN(vocab_size=128, num_classes=4).to(DEVICE)
                local_m.load_state_dict(global_m.state_dict())

                ds_train = TensorDataset(torch.from_numpy(client_tensors[c_id]).long(), torch.from_numpy(client_labels[c_id]).long())
                loader = DataLoader(ds_train, batch_size=64, shuffle=True)
                opt = torch.optim.Adam(local_m.parameters(), lr=1e-3)

                if algo == "FedLC":
                    counts_t = torch.tensor(client_counts[i], dtype=torch.float32)
                    crit = FedLCCalibratedLoss(counts_t, tau=0.5, min_count=10.0)
                elif algo == "FedPayload-DAFL":
                    counts_t = torch.tensor(client_counts[i], dtype=torch.float32)
                    crit = FedLCCalibratedLoss(counts_t, tau=0.5, min_count=10.0)
                else:
                    crit = torch.nn.CrossEntropyLoss()

                local_m.train()
                for bx, by in loader:
                    bx, by = bx.to(DEVICE), by.to(DEVICE)
                    opt.zero_grad()
                    loss = crit(local_m(bx), by)
                    if algo == "FedProx":
                        prox_term = 0.0
                        for p, p_g in zip(local_m.parameters(), global_m.parameters()):
                            prox_term += (p - p_g).pow(2).sum()
                        loss += 0.01 * prox_term
                    loss.backward()
                    opt.step()

                weights = [p.detach().cpu().numpy() for p in local_m.parameters()]
                client_weights.append(weights)
                client_models_post_fl[c_id] = local_m

            # Aggregate weights
            fl_results = []
            for i in range(6):
                fl_results.append((client_weights[i], len(client_labels[i+1]), {"class_counts": client_counts[i]}))

            if algo == "FedPayload-DAFL":
                new_weights = aggregate_dafl(fl_results, temp=5.0, alpha=0.5, beta=0.5, gamma=3.0)
            else:
                new_weights = aggregate_fedavg(fl_results)

            state_dict = global_m.state_dict()
            for key, val in zip(state_dict.keys(), new_weights):
                state_dict[key] = torch.tensor(val).to(DEVICE)
            global_m.load_state_dict(state_dict)

        # Build 6x6 Matrix for this algorithm
        mat_algo = np.zeros((6, 6))
        for i in range(6):
            for j in range(6):
                mat_algo[i, j] = evaluate_model_on_loader(client_models_post_fl[i+1], client_loaders[j+1])

        all_matrices[algo] = mat_algo.tolist()

    # Save output
    out_file = os.path.join(REPORTING_DIR, "full_4x6x6_matrices.json")
    with open(out_file, "w") as f:
        json.dump(all_matrices, f, indent=2)

    logger.info(f"Saved 4x 6x6 Matrices to {out_file}")
    return all_matrices


if __name__ == "__main__":
    run_generate_4x6x6_matrices(fl_rounds=15)
