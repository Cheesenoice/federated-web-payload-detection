"""
Client 1-6 Disjoint Cross-Evaluation Matrix Engine (`src/eval/evaluate_client_matrix.py`)

Adapted from C:\\Users\\huynh\\Desktop\\thailand\\project\\fedwebpayload architecture.

Guarantees:
  1. No Train Set Evaluation: Models are strictly evaluated on held-out client_j_test splits.
  2. Aggregated Global Model Evaluation: Evaluates the aggregated global_model across held-out client test sets.
  3. Full 4x 6x6 Matrices: Computes 6x6 matrices for Local-Only, FedAvg, FedProx, FedLC, and FedPayload-DAFL.
"""

import os
import sys
import json
import logging
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import f1_score, recall_score, accuracy_score

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


def eval_on_loader(model, loader):
    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for bx, by in loader:
            bx, by = bx.to(DEVICE), by.to(DEVICE)
            preds = model(bx).argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(by.cpu().numpy())
    return f1_score(all_targets, all_preds, average="macro", zero_division=0)


def run_client_matrix_evaluation(rounds=5):
    logger.info("=== STARTING RIGOROUS CLIENT 1-6 DISJOINT MATRIX EVALUATION ===")

    train_loaders = {}
    test_loaders = {}
    client_labels = {}
    client_counts = []

    for c_id in range(1, 7):
        df_tr = pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}_train.parquet"))
        df_te = pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}_test.parquet"))

        y_tr = np.array([LABEL_MAP.get(lbl, 3) for lbl in df_tr["label_multiclass"]])
        y_te = np.array([LABEL_MAP.get(lbl, 3) for lbl in df_te["label_multiclass"]])

        tr_tokens = np.load(os.path.join(FEATURES_DIR, f"client_{c_id}_train_tokens.npy"))
        te_tokens = np.load(os.path.join(FEATURES_DIR, f"client_{c_id}_test_tokens.npy"))

        ds_tr = TensorDataset(torch.from_numpy(tr_tokens).long(), torch.from_numpy(y_tr).long())
        ds_te = TensorDataset(torch.from_numpy(te_tokens).long(), torch.from_numpy(y_te).long())

        train_loaders[c_id] = DataLoader(ds_tr, batch_size=64, shuffle=True)
        test_loaders[c_id] = DataLoader(ds_te, batch_size=128, shuffle=False)

        client_labels[c_id] = y_tr
        counts = [int((y_tr == i).sum()) for i in range(4)]
        client_counts.append(counts)

    matrices = {}

    # ---------------------------------------------------------
    # 1. Local-Only 6x6 Matrix (Model i trained on C_i_train, tested on C_j_test)
    # ---------------------------------------------------------
    logger.info("Training Local-Only Models (No FL)...")
    local_models = {}
    for c_id in range(1, 7):
        m = CharCNN(num_classes=4).to(DEVICE)
        opt = torch.optim.Adam(m.parameters(), lr=1e-3)
        crit = nn.CrossEntropyLoss()

        m.train()
        for epoch in range(3):
            for bx, by in train_loaders[c_id]:
                bx, by = bx.to(DEVICE), by.to(DEVICE)
                opt.zero_grad()
                loss = crit(m(bx), by)
                loss.backward()
                opt.step()
        local_models[c_id] = m

    mat_local = np.zeros((6, 6))
    for i in range(6):
        for j in range(6):
            mat_local[i, j] = eval_on_loader(local_models[i+1], test_loaders[j+1])
    matrices["Local-Only"] = mat_local.tolist()

    # ---------------------------------------------------------
    # 2. FL Algorithms (FedAvg, FedProx, FedLC, FedPayload-DAFL)
    # ---------------------------------------------------------
    fl_global_performance = {}

    for algo in ["FedAvg", "FedProx", "FedLC", "FedPayload-DAFL"]:
        logger.info(f"Simulating FL Algorithm: {algo} ({rounds} rounds)...")
        global_m = CharCNN(num_classes=4).to(DEVICE)

        client_models_post_fl = {}

        for r in range(rounds):
            client_weights = []
            for i in range(6):
                c_id = i + 1
                local_m = CharCNN(num_classes=4).to(DEVICE)
                local_m.load_state_dict(global_m.state_dict())
                opt = torch.optim.Adam(local_m.parameters(), lr=1e-3)

                if algo == "FedLC" or algo == "FedPayload-DAFL":
                    counts_t = torch.tensor(client_counts[i], dtype=torch.float32)
                    crit = FedLCCalibratedLoss(counts_t, tau=0.5)
                else:
                    crit = nn.CrossEntropyLoss()

                local_m.train()
                for bx, by in train_loaders[c_id]:
                    bx, by = bx.to(DEVICE), by.to(DEVICE)
                    opt.zero_grad()
                    loss = crit(local_m(bx), by)
                    if algo == "FedProx":
                        prox = 0.0
                        for p, pg in zip(local_m.parameters(), global_m.parameters()):
                            prox += (p - pg).pow(2).sum()
                        loss += 0.01 * prox
                    loss.backward()
                    opt.step()

                weights = [p.detach().cpu().numpy() for p in local_m.parameters()]
                client_weights.append(weights)
                client_models_post_fl[c_id] = local_m

            fl_results = []
            for i in range(6):
                fl_results.append((client_weights[i], len(client_labels[i+1]), {"class_counts": client_counts[i]}))

            if algo == "FedPayload-DAFL":
                new_weights = aggregate_dafl(fl_results)
            else:
                new_weights = aggregate_fedavg(fl_results)

            state_dict = global_m.state_dict()
            for key, val in zip(state_dict.keys(), new_weights):
                state_dict[key] = torch.tensor(val).to(DEVICE)
            global_m.load_state_dict(state_dict)

        # 6x6 Matrix (Client i model evaluated on Client j Test Data)
        mat_algo = np.zeros((6, 6))
        for i in range(6):
            for j in range(6):
                mat_algo[i, j] = eval_on_loader(client_models_post_fl[i+1], test_loaders[j+1])
        matrices[algo] = mat_algo.tolist()

        # Global Model Evaluation across Client Test Sets
        c_f1s = [eval_on_loader(global_m, test_loaders[j+1]) for j in range(6)]
        fl_global_performance[algo] = {
            "client_f1s": c_f1s,
            "worst_client_f1": float(np.min(c_f1s)),
            "mean_f1": float(np.mean(c_f1s)),
            "variance": float(np.var(c_f1s))
        }

    # Save outputs
    report_file = os.path.join(REPORTING_DIR, "client_cross_evaluation_matrix.json")
    with open(report_file, "w") as f:
        json.dump({"matrices": matrices, "global_fl_performance": fl_global_performance}, f, indent=2)

    logger.info("=== EVALUATION COMPLETE: MATRICES SAVED ===")
    return matrices, fl_global_performance


if __name__ == "__main__":
    run_client_matrix_evaluation()
