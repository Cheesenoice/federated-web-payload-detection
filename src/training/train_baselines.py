"""
Baseline Training & Evaluation Matrix Orchestrator (`src/training/train_baselines.py`)

Trains local client baselines (XGBoost, RandomForest, LogisticRegression, PyTorch CharCNN)
across all 6 client datasets and evaluates performance on Global In-Domain Test & Validation sets.

Outputs:
  - Báo cáo Ma trận Đánh giá Baseline (Accuracy, Macro-F1, Recall SQLi, Recall PathTrav, Recall XSS, Recall Benign)
  - `data/reporting/baseline_evaluation_matrix.json`
"""

import os
import sys
import json
import logging
import torch
import numpy as np
import pandas as pd
from scipy.sparse import load_npz
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, f1_score, recall_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.models.charcnn import CharCNN
from src.models.ml_baselines import train_logistic_regression, train_xgboost, train_random_forest
from src.training.trainer import train_pytorch_model, evaluate_model_pytorch, LABEL_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
FEATURES_DIR = os.path.join(DATA_DIR, "features")
REPORTING_DIR = os.path.join(DATA_DIR, "reporting")

os.makedirs(REPORTING_DIR, exist_ok=True)


def evaluate_sklearn_model(clf, X_test, y_test) -> dict:
    """Evaluates sklearn / xgboost model and returns classification metrics."""
    preds = clf.predict(X_test)
    if hasattr(preds, "ndim") and preds.ndim > 1:
        preds = np.argmax(preds, axis=1)
    acc = accuracy_score(y_test, preds)
    macro_f1 = f1_score(y_test, preds, average="macro", zero_division=0)
    per_class_rec = recall_score(y_test, preds, average=None, labels=[0, 1, 2, 3], zero_division=0)

    return {
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "recall_benign": float(per_class_rec[0]),
        "recall_xss": float(per_class_rec[1]),
        "recall_sqli": float(per_class_rec[2]),
        "recall_pathtrav": float(per_class_rec[3]),
    }


def run_baseline_training_matrix():
    logger.info("=== STARTING PHASE 4: LOCAL BASELINE TRAINING & EVALUATION MATRIX ===")

    # 1. Load Global Validation & Test Sets
    df_val = pd.read_parquet(os.path.join(SPLITS_DIR, "val_global.parquet"))
    df_test = pd.read_parquet(os.path.join(SPLITS_DIR, "test_indomain.parquet"))

    y_val = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_val["label_multiclass"]])
    y_test = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_test["label_multiclass"]])

    X_val_tfidf = load_npz(os.path.join(FEATURES_DIR, "val_global_tfidf.npz"))
    X_test_tfidf = load_npz(os.path.join(FEATURES_DIR, "test_indomain_tfidf.npz"))

    val_tokens = np.load(os.path.join(FEATURES_DIR, "val_global_tokens.npy"))
    test_tokens = np.load(os.path.join(FEATURES_DIR, "test_indomain_tokens.npy"))

    val_dataset = TensorDataset(torch.from_numpy(val_tokens).long(), torch.from_numpy(y_val).long())
    test_dataset = TensorDataset(torch.from_numpy(test_tokens).long(), torch.from_numpy(y_test).long())

    val_loader = DataLoader(val_dataset, batch_size=128, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False)

    results_matrix = {}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training hardware accelerator: {device}")

    # 2. Train Local Models per Client (Client 1 to Client 6)
    for c_id in range(1, 7):
        logger.info(f"\n--- Training Local Models on Client {c_id} ---")
        df_client = pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}.parquet"))
        y_c = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_client["label_multiclass"]])
        X_c_tfidf = load_npz(os.path.join(FEATURES_DIR, f"client_{c_id}_tfidf.npz"))
        c_tokens = np.load(os.path.join(FEATURES_DIR, f"client_{c_id}_tokens.npy"))

        c_dataset = TensorDataset(torch.from_numpy(c_tokens).long(), torch.from_numpy(y_c).long())
        c_loader = DataLoader(c_dataset, batch_size=64, shuffle=True)

        results_matrix[f"client_{c_id}"] = {}

        # a. Logistic Regression Baseline
        logger.info(f"Client {c_id} -> Training LogisticRegression...")
        clf_lr = train_logistic_regression(X_c_tfidf, y_c, seed=42)
        metrics_lr = evaluate_sklearn_model(clf_lr, X_test_tfidf, y_test)
        results_matrix[f"client_{c_id}"]["LogisticRegression"] = metrics_lr

        # b. XGBoost Baseline
        logger.info(f"Client {c_id} -> Training XGBoost...")
        clf_xgb = train_xgboost(X_c_tfidf, y_c, n_estimators=50, max_depth=5, seed=42)
        metrics_xgb = evaluate_sklearn_model(clf_xgb, X_test_tfidf, y_test)
        results_matrix[f"client_{c_id}"]["XGBoost"] = metrics_xgb

        # c. PyTorch CharCNN Baseline
        logger.info(f"Client {c_id} -> Training PyTorch CharCNN...")
        model_cnn = CharCNN(vocab_size=128, num_classes=4)
        model_cnn, _ = train_pytorch_model(model_cnn, c_loader, val_loader, epochs=5, lr=1e-3, device=device)
        metrics_cnn = evaluate_model_pytorch(model_cnn, test_loader, device)
        results_matrix[f"client_{c_id}"]["CharCNN"] = metrics_cnn

    # 3. Save Matrix JSON Report
    report_path = os.path.join(REPORTING_DIR, "baseline_evaluation_matrix.json")
    with open(report_path, "w") as f:
        json.dump(results_matrix, f, indent=2)
    logger.info(f"Saved baseline evaluation matrix to {report_path}")

    # 4. Print Summary Table
    print("\n" + "="*80)
    print("PHASE 4 BASELINE EVALUATION MATRIX REPORT (TEST IN-DOMAIN)")
    print("="*80)
    print(f"{'Client ID':<10} | {'Model':<18} | {'Macro-F1':<10} | {'Recall-SQLi':<12} | {'Recall-Path':<12} | {'Recall-XSS':<10}")
    print("-" * 80)
    for c_id in range(1, 7):
        client_key = f"client_{c_id}"
        for model_name, m in results_matrix[client_key].items():
            print(f"{client_key:<10} | {model_name:<18} | {m['macro_f1']:<10.4f} | {m['recall_sqli']:<12.4f} | {m['recall_pathtrav']:<12.4f} | {m['recall_xss']:<10.4f}")
        print("-" * 80)
    print("="*80 + "\n")


if __name__ == "__main__":
    run_baseline_training_matrix()
