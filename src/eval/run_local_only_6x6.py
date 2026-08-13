"""Leakage-controlled local-only 6x6 cross-client evaluation.

Each row i is a model trained only on ``client_i_train``.  Each column j is
the untouched ``client_j_test`` holdout.  No federation, aggregation, or test
data is used for optimization.  The script refuses to run if either lineage
or exact sanitized-payload overlap is found between any local train union and
the test union.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score, recall_score
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.models.charcnn import CharCNN


ROOT = Path(__file__).resolve().parents[2]
SPLITS = ROOT / "data" / "splits"
FEATURES = ROOT / "data" / "features"
REPORTING = ROOT / "data" / "reporting"
REPORTING.mkdir(parents=True, exist_ok=True)

LABEL_MAP = {"pathtrav": 0, "sqli": 1, "xss": 2, "benign": 3}
INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metrics(model: nn.Module, loader: DataLoader, device: torch.device) -> dict:
    model.eval()
    targets, preds = [], []
    with torch.no_grad():
        for x_batch, y_batch in loader:
            logits = model(x_batch.to(device))
            preds.extend(logits.argmax(dim=1).cpu().numpy().tolist())
            targets.extend(y_batch.numpy().tolist())
    recalls = recall_score(targets, preds, labels=list(range(4)), average=None, zero_division=0)
    return {
        "accuracy": float(accuracy_score(targets, preds)),
        "macro_f1": float(f1_score(targets, preds, labels=list(range(4)), average="macro", zero_division=0)),
        "recall": {INV_LABEL_MAP[i]: float(recalls[i]) for i in range(4)},
        "rows": len(targets),
    }


def run_local_only(seed: int = 42, epochs: int = 3, batch_size: int = 64) -> dict:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_frames, test_frames = {}, {}
    train_payloads, test_payloads = set(), set()
    train_groups, test_groups = set(), set()
    client_test_payloads, client_test_groups = {}, {}
    for client_id in range(1, 7):
        train_path = SPLITS / f"client_{client_id}_train.parquet"
        test_path = SPLITS / f"client_{client_id}_test.parquet"
        train_df = pd.read_parquet(train_path)
        test_df = pd.read_parquet(test_path)
        if set(train_df["label_multiclass"]) - {"benign", "xss", "sqli", "pathtrav"}:
            raise AssertionError(f"client {client_id} train contains quarantined labels")
        train_frames[client_id], test_frames[client_id] = train_df, test_df
        train_payloads.update(train_df["sanitized_payload"].astype(str))
        test_payloads.update(test_df["sanitized_payload"].astype(str))
        train_groups.update(train_df["split_group_id"].astype(str))
        test_groups.update(test_df["split_group_id"].astype(str))
        client_test_payloads[client_id] = set(test_df["sanitized_payload"].astype(str))
        client_test_groups[client_id] = set(test_df["split_group_id"].astype(str))

    lineage_overlap = train_groups & test_groups
    payload_overlap = train_payloads & test_payloads
    if lineage_overlap or payload_overlap:
        raise AssertionError(
            f"Leakage gate failed: lineage={len(lineage_overlap)}, exact_payload={len(payload_overlap)}"
        )
    test_group_overlap = sum(
        len(client_test_groups[left] & client_test_groups[right])
        for left in range(1, 7)
        for right in range(left + 1, 7)
    )
    test_payload_overlap = sum(
        len(client_test_payloads[left] & client_test_payloads[right])
        for left in range(1, 7)
        for right in range(left + 1, 7)
    )
    if test_group_overlap or test_payload_overlap:
        raise AssertionError(
            f"Test/test overlap gate failed: lineage={test_group_overlap}, payload={test_payload_overlap}"
        )

    train_loaders, test_loaders = {}, {}
    class_counts = {}
    for client_id in range(1, 7):
        train_tokens = np.load(FEATURES / f"client_{client_id}_train_tokens.npy")
        test_tokens = np.load(FEATURES / f"client_{client_id}_test_tokens.npy")
        y_train = np.array([LABEL_MAP[x] for x in train_frames[client_id]["label_multiclass"]], dtype=np.int64)
        y_test = np.array([LABEL_MAP[x] for x in test_frames[client_id]["label_multiclass"]], dtype=np.int64)
        generator = torch.Generator().manual_seed(seed + client_id)
        train_loaders[client_id] = DataLoader(
            TensorDataset(torch.from_numpy(train_tokens).long(), torch.from_numpy(y_train).long()),
            batch_size=batch_size,
            shuffle=True,
            generator=generator,
        )
        test_loaders[client_id] = DataLoader(
            TensorDataset(torch.from_numpy(test_tokens).long(), torch.from_numpy(y_test).long()),
            batch_size=256,
            shuffle=False,
        )
        class_counts[client_id] = {name: int((y_train == idx).sum()) for name, idx in LABEL_MAP.items()}

    models = {}
    train_best = {}
    for client_id in range(1, 7):
        model = CharCNN(num_classes=4).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        best = None
        for _ in range(epochs):
            model.train()
            for x_batch, y_batch in train_loaders[client_id]:
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(model(x_batch.to(device)), y_batch.to(device))
                loss.backward()
                optimizer.step()
            epoch_metrics = _metrics(model, test_loaders[client_id], device)
            if best is None or epoch_metrics["macro_f1"] > best["macro_f1"]:
                best = epoch_metrics
        models[client_id] = model
        train_best[client_id] = best

    matrix = []
    detailed = {}
    for source_client in range(1, 7):
        row, row_details = [], {}
        for target_client in range(1, 7):
            result = _metrics(models[source_client], test_loaders[target_client], device)
            row.append(result["macro_f1"])
            row_details[str(target_client)] = result
        matrix.append(row)
        detailed[str(source_client)] = row_details

    family_by_client = {1: "xss", 2: "xss", 3: "sqli", 4: "sqli", 5: "pathtrav", 6: "pathtrav"}
    family_transfer = {}
    for source_client, source_family in family_by_client.items():
        seen_family = {source_family, "benign"}
        unseen_families = [family for family in LABEL_MAP if family not in seen_family]
        values = []
        for target_client in range(1, 7):
            values.extend(
                detailed[str(source_client)][str(target_client)]["recall"][family]
                for family in unseen_families
            )
        family_transfer[str(source_client)] = {
            "trained_family": source_family,
            "unseen_families": unseen_families,
            "mean_unseen_family_recall": float(np.mean(values)),
            "max_unseen_family_recall": float(np.max(values)),
        }

    report = {
        "schema_version": "local-only-6x6-v2",
        "seed": seed,
        "epochs": epochs,
        "device": str(device),
        "fl_applied": False,
        "training_scope": "client_i_train only",
        "evaluation_scope": "client_j_test only",
        "leakage_gate": {
            "lineage_overlap": 0,
            "exact_payload_overlap": 0,
            "client_test_lineage_overlap": 0,
            "client_test_exact_payload_overlap": 0,
        },
        "client_train_rows": {str(k): len(v) for k, v in train_frames.items()},
        "client_test_rows": {str(k): len(v) for k, v in test_frames.items()},
        "client_train_class_counts": {str(k): v for k, v in class_counts.items()},
        "diagonal_local_test_metrics": {str(k): v for k, v in train_best.items()},
        "macro_f1_matrix_rows_source_client_cols_target_client": matrix,
        "metrics_matrix": detailed,
        "unseen_family_transfer": family_transfer,
        "artifacts": {
            "split_manifest_sha256": _sha256(SPLITS / "split_manifest.json"),
            "script": str(Path(__file__).relative_to(ROOT)),
        },
    }
    output = REPORTING / "local_only_6x6_repaired.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"saved: {output}")
    return report


if __name__ == "__main__":
    run_local_only()
