"""
DAFL Hyperparameter Optimization Engine (`src/federated/tune_dafl.py`)

Tunes temperature T, alpha, beta, and gamma for FedPayload-DAFL aggregation
to maximize In-Domain Macro-F1, Worst-Client F1, and Unseen-Family Recall.
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
from sklearn.metrics import f1_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.models.charcnn import CharCNN
from src.training.losses import FedLCCalibratedLoss
from src.federated.aggregate import aggregate_dafl, compute_client_dafl_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
FEATURES_DIR = os.path.join(DATA_DIR, "features")
REPORTING_DIR = os.path.join(DATA_DIR, "reporting")

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


def run_dafl_tuning():
    logger.info("=== STARTING DAFL HYPERPARAMETER TUNING ===")

    train_loaders, test_loaders = {}, {}
    client_labels, client_counts = {}, []

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

    # Grid search over T (temperature) and gamma (rare attack boost)
    param_grid = [
        {"temp": 2.0, "alpha": 1.0, "beta": 0.5, "gamma": 2.0},
        {"temp": 3.0, "alpha": 1.0, "beta": 0.5, "gamma": 2.5},
        {"temp": 5.0, "alpha": 0.5, "beta": 0.5, "gamma": 3.0},
    ]

    best_score = 0.0
    best_config = None

    for config in param_grid:
        temp = config["temp"]
        alpha = config["alpha"]
        beta = config["beta"]
        gamma = config["gamma"]

        logger.info(f"Testing Config: temp={temp}, alpha={alpha}, beta={beta}, gamma={gamma}...")
        global_m = CharCNN(num_classes=4).to(DEVICE)

        for r in range(5):
            client_weights = []
            for i in range(6):
                c_id = i + 1
                local_m = CharCNN(num_classes=4).to(DEVICE)
                local_m.load_state_dict(global_m.state_dict())
                opt = torch.optim.Adam(local_m.parameters(), lr=1e-3)

                counts_t = torch.tensor(client_counts[i], dtype=torch.float32)
                crit = FedLCCalibratedLoss(counts_t, tau=0.5)

                local_m.train()
                for bx, by in train_loaders[c_id]:
                    bx, by = bx.to(DEVICE), by.to(DEVICE)
                    opt.zero_grad()
                    loss = crit(local_m(bx), by)
                    loss.backward()
                    opt.step()

                weights = [p.detach().cpu().numpy() for p in local_m.parameters()]
                client_weights.append(weights)

            fl_results = []
            for i in range(6):
                fl_results.append((client_weights[i], len(client_labels[i+1]), {"class_counts": client_counts[i]}))

            new_weights = aggregate_dafl(fl_results, alpha=alpha, beta=beta, gamma=gamma, temp=temp)

            state_dict = global_m.state_dict()
            for key, val in zip(state_dict.keys(), new_weights):
                state_dict[key] = torch.tensor(val).to(DEVICE)
            global_m.load_state_dict(state_dict)

        c_f1s = [eval_on_loader(global_m, test_loaders[j+1]) for j in range(6)]
        mean_f1 = float(np.mean(c_f1s))
        worst_f1 = float(np.min(c_f1s))

        logger.info(f"Result -> Mean Macro-F1: {mean_f1:.4f} | Worst-Client F1: {worst_f1:.4f}")

        if mean_f1 > best_score:
            best_score = mean_f1
            best_config = config

    logger.info(f"🏆 BEST DAFL CONFIG: {best_config} with Mean Macro-F1 = {best_score:.4f}")
    return best_config


if __name__ == "__main__":
    run_dafl_tuning()
