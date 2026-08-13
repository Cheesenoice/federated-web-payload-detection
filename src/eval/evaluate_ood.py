"""
Out-of-Domain (OOD) External Benchmark Evaluation Engine (`src/eval/evaluate_ood.py`)

Parses CSIC 2010 External WAF HTTP Request Dumps (`data/raw/SRC_02_csic2010/`),
sanitizes and tokenizes payloads, evaluates all global FL models (FedAvg, FedProx, FedLC, FedPayload-DAFL),
and compiles the Master Paper Report (`data/reporting/paper_master_report.json`).

Outputs:
  - `data/splits/test_ood_csic2010.parquet`
  - `data/reporting/ood_evaluation_matrix.json`
  - `data/reporting/paper_master_report.json`
"""

import os
import sys
import json
import logging
import urllib.parse
import torch
import numpy as np
import pandas as pd
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.models.charcnn import CharCNN
from src.features.tokenizer import CharTokenizer
from src.training.trainer import evaluate_model_pytorch, LABEL_MAP
from src.training.losses import FedLCCalibratedLoss
from src.federated.client import PayloadFlowerClient, set_model_parameters, get_model_parameters
from src.federated.aggregate import aggregate_fedavg, aggregate_dafl
from src.data.label_signatures import verify_payload_label

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
RAW_CSIC_DIR = os.path.join(DATA_DIR, "raw", "SRC_02_csic2010")
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
FEATURES_DIR = os.path.join(DATA_DIR, "features")
REPORTING_DIR = os.path.join(DATA_DIR, "reporting")

os.makedirs(REPORTING_DIR, exist_ok=True)


def parse_csic_file(file_path: str, is_anomalous: bool = False) -> list[dict]:
    """Parses CSIC 2010 raw HTTP request file into structured parameter payload rows."""
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        blocks = f.read().split("\n\n")

    rows = []
    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        first_line = lines[0]
        if first_line.startswith("GET ") or first_line.startswith("POST "):
            parts = first_line.split(" ")
            url_str = parts[1] if len(parts) >= 2 else ""
            parsed = urllib.parse.urlparse(url_str)
            query = parsed.query
            body = lines[-1] if len(lines) > 1 and "=" in lines[-1] and not lines[-1].startswith(("Host:", "User-Agent:", "Accept:", "Cookie:", "Content-")) else ""
            
            param_payload = (query + " " + body).strip() if (query or body) else parsed.path
            if len(param_payload) >= 2:
                if not is_anomalous:
                    multiclass_label = "benign"
                    binary_label = 0
                else:
                    mc, _ = verify_payload_label(param_payload, "malicious")
                    if mc in {"xss", "sqli", "pathtrav"}:
                        multiclass_label = mc
                    else:
                        multiclass_label = "other"
                    binary_label = 1

                rows.append({
                    "raw_payload": param_payload,
                    "label_binary": binary_label,
                    "label_multiclass": multiclass_label,
                    "source": "SRC_02_csic2010"
                })

    return rows


from src.data.decode import normalize_payload_text

def build_csic2010_ood_split() -> pd.DataFrame:
    """Builds and saves clean verified test_ood_csic2010.parquet dataset."""
    logger.info("Parsing CSIC 2010 Normal & Anomalous raw HTTP request dumps...")
    normal_path = os.path.join(RAW_CSIC_DIR, "csic2010_normal_raw.txt")
    anom_path = os.path.join(RAW_CSIC_DIR, "csic2010_anomalous_raw.txt")

    rows_normal = parse_csic_file(normal_path, is_anomalous=False)
    rows_anom = parse_csic_file(anom_path, is_anomalous=True)

    # Retain verified benign and verified attack payloads (XSS, SQLi, PathTrav)
    rows_anom_verified = [r for r in rows_anom if r["label_multiclass"] in {"xss", "sqli", "pathtrav"}]
    logger.info(f"Parsed CSIC 2010: {len(rows_normal)} Benign, {len(rows_anom_verified)} Verified Attack Payloads (XSS/SQLi/PathTrav)")

    all_rows = rows_normal[:len(rows_anom_verified)] + rows_anom_verified
    
    # Normalize payloads via Stage 2 Pipeline decoder
    for r in all_rows:
        decoded_text, _ = normalize_payload_text(r["raw_payload"])
        r["raw_payload"] = decoded_text if decoded_text else r["raw_payload"]

    df_ood = pd.DataFrame(all_rows)
    
    out_parquet = os.path.join(SPLITS_DIR, "test_ood_csic2010.parquet")
    df_ood.to_parquet(out_parquet, index=False)
    logger.info(f"Saved Clean Verified CSIC 2010 OOD dataset ({len(df_ood)} rows) to {out_parquet}")
    return df_ood


def run_ood_evaluation():
    logger.info("=== STARTING PHASE 6: OUT-OF-DOMAIN (OOD) BENCHMARK EVALUATION ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Hardware Accelerator: {device}")

    # 1. Build & Tokenize CSIC 2010 OOD Dataset
    df_ood = build_csic2010_ood_split()
    tokenizer = CharTokenizer(max_length=256)
    
    tokens_ood = np.array([tokenizer.encode(str(p)) for p in df_ood["raw_payload"]])
    y_ood = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_ood["label_multiclass"]])

    ds_ood = TensorDataset(torch.from_numpy(tokens_ood).long(), torch.from_numpy(y_ood).long())
    loader_ood = DataLoader(ds_ood, batch_size=128, shuffle=False)

    # 2. Train Global Models for all 4 FL Algorithms over 5 Rounds
    client_datasets = []
    client_class_counts = []
    for c_id in range(1, 7):
        df_c = pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}.parquet"))
        y_c = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_c["label_multiclass"]])
        c_tokens = np.load(os.path.join(FEATURES_DIR, f"client_{c_id}_tokens.npy"))
        ds = TensorDataset(torch.from_numpy(c_tokens).long(), torch.from_numpy(y_c).long())
        client_datasets.append(ds)
        counts = [int((y_c == i).sum()) for i in range(4)]
        client_class_counts.append(torch.tensor(counts, dtype=torch.float32))

    algorithms = ["FedAvg", "FedProx", "FedLC", "FedPayload-DAFL"]
    ood_results = {}

    for algo in algorithms:
        logger.info(f"\nTraining Global Model for {algo} (10 rounds)...")
        global_model = CharCNN(vocab_size=128, num_classes=4).to(device)
        w_gen_path = os.path.join(DATA_DIR, "models", "w_general_charcnn.pt")
        if os.path.exists(w_gen_path):
            global_model.load_state_dict(torch.load(w_gen_path, map_location=device))
        global_params = get_model_parameters(global_model)

        for r in range(1, 11):
            client_results = []
            for c_idx in range(6):
                c_model = CharCNN(vocab_size=128, num_classes=4)
                c_loader = DataLoader(client_datasets[c_idx], batch_size=64, shuffle=True)
                fl_client = PayloadFlowerClient(
                    client_id=c_idx + 1,
                    model=c_model,
                    train_loader=c_loader,
                    val_loader=loader_ood,
                    class_counts=client_class_counts[c_idx],
                    device=device,
                    strategy_name=algo,
                    epochs=2
                )
                updated_params, n_k, metrics = fl_client.fit(global_params, config={})
                client_results.append((updated_params, n_k, metrics))

            if algo == "FedPayload-DAFL":
                global_params = aggregate_dafl(client_results, alpha=1.0, beta=0.5, gamma=1.5)
            else:
                global_params = aggregate_fedavg(client_results)

        set_model_parameters(global_model, global_params)
        
        # Multi-class Evaluation
        eval_metrics = evaluate_model_pytorch(global_model, loader_ood, device)
        
        # Binary WAF Detection Evaluation (0: Benign, 1: Malicious)
        global_model.eval()
        all_preds = []
        with torch.no_grad():
            for x_b, _ in loader_ood:
                x_b = x_b.to(device)
                logits = global_model(x_b)
                preds = torch.argmax(logits, dim=1).cpu().numpy()
                all_preds.extend(preds)
        
        y_true_binary = df_ood["label_binary"].values
        y_pred_binary = (np.array(all_preds) > 0).astype(int)
        
        bin_acc = float(accuracy_score(y_true_binary, y_pred_binary))
        bin_rec = float(recall_score(y_true_binary, y_pred_binary, zero_division=0))
        bin_f1 = float(f1_score(y_true_binary, y_pred_binary, zero_division=0))

        eval_metrics["binary_waf_accuracy"] = bin_acc
        eval_metrics["binary_waf_recall"] = bin_rec
        eval_metrics["binary_waf_f1"] = bin_f1

        ood_results[algo] = eval_metrics
        logger.info(f"[{algo}] CSIC 2010 OOD -> Binary WAF Acc: {bin_acc*100:.2f}% | Malicious Recall: {bin_rec*100:.2f}% | Binary F1: {bin_f1:.4f}")

    # 3. Save OOD Evaluation Matrix JSON
    ood_json_path = os.path.join(REPORTING_DIR, "ood_evaluation_matrix.json")
    with open(ood_json_path, "w") as f:
        json.dump(ood_results, f, indent=2)
    logger.info(f"Saved OOD Evaluation Matrix to {ood_json_path}")

    # 4. Generate Master Paper Report
    master_report = {
        "project_name": "fedwebpayload",
        "conference_target": "SCIN-2026",
        "total_trainable_samples": len(df_ood),
        "in_domain_test_samples": 1439,
        "csic2010_ood_samples": len(df_ood),
        "ood_benchmark_results": ood_results
    }
    master_path = os.path.join(REPORTING_DIR, "paper_master_report.json")
    with open(master_path, "w") as f:
        json.dump(master_report, f, indent=2)
    logger.info(f"Saved Master Paper Report to {master_path}")

    # 5. Print Summary Table
    print("\n" + "="*95)
    print("PHASE 6 OUT-OF-DOMAIN (CSIC 2010 EXTERNAL WAF BENCHMARK) EVALUATION REPORT")
    print("="*95)
    print(f"{'FL Algorithm':<18} | {'Binary WAF Acc':<16} | {'Malicious Recall':<18} | {'Binary F1':<12} | {'Paper Status':<10}")
    print("-" * 95)
    for algo in algorithms:
        m = ood_results[algo]
        status = "PROPOSED" if algo == "FedPayload-DAFL" else "Baseline"
        print(f"{algo:<18} | {m['binary_waf_accuracy']*100:<15.2f}% | {m['binary_waf_recall']*100:<17.2f}% | {m['binary_waf_f1']:<12.4f} | {status:<10}")
    print("="*95 + "\n")


if __name__ == "__main__":
    run_ood_evaluation()
