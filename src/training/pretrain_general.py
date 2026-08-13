"""
Stage A: General Base Pre-Training Engine (`src/training/pretrain_general.py`)

Pre-trains initial global model weights W_general on the combined training corpus 
containing all 4 attack classes (Benign, SQLi, XSS, PathTrav) to endow the global model 
with general cybersecurity payload detection knowledge.

Outputs:
  - `data/models/w_general_charcnn.pt` (Pre-trained CharCNN weights)
  - `data/models/w_general_logistic.pkl` (Centralized Logistic Regression)
  - `data/models/w_general_xgboost.json` (Centralized XGBoost)
"""

import os
import sys
import json
import pickle
import logging
import torch
import numpy as np
import pandas as pd
from scipy.sparse import load_npz, vstack
from torch.utils.data import TensorDataset, DataLoader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.models.charcnn import CharCNN
from src.models.ml_baselines import train_logistic_regression, train_xgboost, train_random_forest
from src.training.trainer import train_pytorch_model, evaluate_model_pytorch, LABEL_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
FEATURES_DIR = os.path.join(DATA_DIR, "features")
MODELS_DIR = os.path.join(DATA_DIR, "models")
REPORTING_DIR = os.path.join(DATA_DIR, "reporting")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORTING_DIR, exist_ok=True)


def run_general_pretraining():
    logger.info("=== STARTING STAGE 1: GENERAL BASE PRE-TRAINING (GLOBAL KNOWLEDGE ACQUISITION) ===")

    # 1. Aggregate Client Train Sets to Form Representative General Corpus
    client_train_dfs = [pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{i+1}_train.parquet")) for i in range(6)]
    df_train_all = pd.concat(client_train_dfs, ignore_index=True)
    
    y_train_all = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_train_all["label_multiclass"]])
    
    client_train_tfidfs = [load_npz(os.path.join(FEATURES_DIR, f"client_{i+1}_train_tfidf.npz")) for i in range(6)]
    X_train_all_tfidf = vstack(client_train_tfidfs)
    
    client_train_tokens = [np.load(os.path.join(FEATURES_DIR, f"client_{i+1}_train_tokens.npy")) for i in range(6)]
    train_all_tokens = np.vstack(client_train_tokens)

    # Load Global Test set
    df_test = pd.read_parquet(os.path.join(SPLITS_DIR, "test_indomain.parquet"))
    y_test = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_test["label_multiclass"]])
    X_test_tfidf = load_npz(os.path.join(FEATURES_DIR, "test_indomain_tfidf.npz"))
    test_tokens = np.load(os.path.join(FEATURES_DIR, "test_indomain_tokens.npy"))

    df_val = pd.read_parquet(os.path.join(SPLITS_DIR, "val_global.parquet"))
    y_val = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_val["label_multiclass"]])
    val_tokens = np.load(os.path.join(FEATURES_DIR, "val_global_tokens.npy"))

    logger.info(f"General Corpus Size: {len(df_train_all)} rows across all 4 classes")
    logger.info(f"Training Class Distribution: {df_train_all['label_multiclass'].value_counts().to_dict()}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # 2. Centralized Model Training (Upper Bound Performance)
    # a. Logistic Regression
    logger.info("Pre-training Centralized Logistic Regression...")
    clf_lr = train_logistic_regression(X_train_all_tfidf, y_train_all, seed=42)
    lr_preds = clf_lr.predict(X_test_tfidf)
    from sklearn.metrics import accuracy_score, f1_score
    lr_macro_f1 = f1_score(y_test, lr_preds, average="macro", zero_division=0)
    logger.info(f"Centralized Logistic Regression Global Test Macro-F1: {lr_macro_f1:.4f}")

    # b. XGBoost
    logger.info("Pre-training Centralized XGBoost...")
    clf_xgb = train_xgboost(X_train_all_tfidf, y_train_all, n_estimators=100, max_depth=6, seed=42)
    xgb_preds = clf_xgb.predict(X_test_tfidf)
    xgb_macro_f1 = f1_score(y_test, xgb_preds, average="macro", zero_division=0)
    logger.info(f"Centralized XGBoost Global Test Macro-F1: {xgb_macro_f1:.4f}")

    # c. PyTorch CharCNN (Global Base Model W_general)
    logger.info("Pre-training Centralized CharCNN (Global W_general Base)...")
    train_ds = TensorDataset(torch.from_numpy(train_all_tokens).long(), torch.from_numpy(y_train_all).long())
    val_ds = TensorDataset(torch.from_numpy(val_tokens).long(), torch.from_numpy(y_val).long())
    test_ds = TensorDataset(torch.from_numpy(test_tokens).long(), torch.from_numpy(y_test).long())

    train_loader = DataLoader(train_ds, batch_size=128, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=128, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=128, shuffle=False)

    w_general_model = CharCNN(vocab_size=128, num_classes=4)
    w_general_model, _ = train_pytorch_model(w_general_model, train_loader, val_loader, epochs=15, lr=1e-3, device=device)

    cnn_metrics = evaluate_model_pytorch(w_general_model, test_loader, device)
    logger.info(f"Centralized CharCNN Global Test Macro-F1: {cnn_metrics['macro_f1']:.4f}")

    # Save W_general weights
    w_general_path = os.path.join(MODELS_DIR, "w_general_charcnn.pt")
    torch.save(w_general_model.state_dict(), w_general_path)
    logger.info(f"Saved Global Base Weights W_general to {w_general_path}")

    summary = {
        "centralized_logistic_macro_f1": float(lr_macro_f1),
        "centralized_xgboost_macro_f1": float(xgb_macro_f1),
        "centralized_charcnn_metrics": cnn_metrics
    }
    
    with open(os.path.join(REPORTING_DIR, "pretrain_general_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*85)
    print("STAGE 1: GENERAL BASE PRE-TRAINING SUMMARY (CENTRALIZED UPPER BOUND)")
    print("="*85)
    print(f"Centralized LogReg Macro-F1  : {lr_macro_f1:.4f}")
    print(f"Centralized XGBoost Macro-F1 : {xgb_macro_f1:.4f}")
    print(f"Centralized CharCNN Macro-F1 : {cnn_metrics['macro_f1']:.4f} (Accuracy={cnn_metrics['accuracy']:.4f})")
    print(f"Base Weights Saved           : {w_general_path}")
    print("="*85 + "\n")


if __name__ == "__main__":
    run_general_pretraining()
