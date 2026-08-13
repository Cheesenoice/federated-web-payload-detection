"""
PyTorch Model Trainer & Evaluator (`src/training/trainer.py`)

Manages PyTorch model training loops, validation evaluation, early stopping, and metric calculation
(Accuracy, Macro-F1, Per-Class Recall for SQLi, PathTrav, XSS, Benign).
"""

import os
import logging
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, f1_score, recall_score, classification_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LABEL_MAP = {"benign": 0, "xss": 1, "sqli": 2, "pathtrav": 3}
INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}


def evaluate_model_pytorch(model: nn.Module, data_loader: DataLoader, device: torch.device) -> dict:
    """Evaluates PyTorch model on data_loader and computes classification metrics."""
    model.eval()
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for x_batch, y_batch in data_loader:
            x_batch = x_batch.to(device)
            logits = model(x_batch)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(y_batch.numpy())

    acc = accuracy_score(all_targets, all_preds)
    macro_f1 = f1_score(all_targets, all_preds, average="macro")
    per_class_rec = recall_score(all_targets, all_preds, average=None, labels=[0, 1, 2, 3])

    metrics = {
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "recall_benign": float(per_class_rec[0]),
        "recall_xss": float(per_class_rec[1]),
        "recall_sqli": float(per_class_rec[2]),
        "recall_pathtrav": float(per_class_rec[3]),
    }
    return metrics


def train_pytorch_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int = 10,
    lr: float = 1e-3,
    device: torch.device = torch.device("cpu"),
    loss_fn: nn.Module = None
) -> tuple[nn.Module, dict]:
    """Trains PyTorch model with early stopping on validation Macro-F1."""
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    if loss_fn is None:
        loss_fn = nn.CrossEntropyLoss()

    best_val_f1 = -1.0
    best_metrics = {}

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for x_batch, y_batch in train_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            logits = model(x_batch)
            loss = loss_fn(logits, y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        val_metrics = evaluate_model_pytorch(model, val_loader, device)
        val_f1 = val_metrics["macro_f1"]

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_metrics = val_metrics

    return model, best_metrics
