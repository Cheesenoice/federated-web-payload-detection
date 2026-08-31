import os
import sys
import json
import logging
import importlib.util
import torch
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, accuracy_score, classification_report
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def dynamic_import(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

CURRENT_DIR = os.path.dirname(__file__)
ds_mod = dynamic_import("dataset_tokenizer", os.path.join(CURRENT_DIR, "3.1_dataset_and_char_tokenizer.py"))
arch_mod = dynamic_import("neural_archs", os.path.join(CURRENT_DIR, "3.2_neural_architectures.py"))

get_dataloader = ds_mod.get_dataloader
LABEL_MAP = ds_mod.LABEL_MAP
INV_LABEL_MAP = ds_mod.INV_LABEL_MAP
PayloadDataset = ds_mod.PayloadDataset
get_neural_model = arch_mod.get_neural_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
CLIENTS_DIR = os.path.join(PROCESSED_DIR, "clients")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_03_neural")
LOCAL_MODELS_DIR = os.path.join(MODELS_DIR, "local_silos")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "stage_03_neural")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")

os.makedirs(FIGURES_DIR, exist_ok=True)

W_BASE_PATH = os.path.join(MODELS_DIR, "W_base.pt")
OUT_MATRIX_CSV = os.path.join(REPORTS_DIR, "local_silo_cross_evaluation_matrix.csv")
OUT_SUMMARY_CSV = os.path.join(REPORTS_DIR, "neural_models_benchmark_summary.csv")
OUT_JSON = os.path.join(REPORTS_DIR, "metrics_neural_foundation.json")

def evaluate_model_on_loader(model, loader, device):
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
    macro_f1 = f1_score(all_trues, all_preds, average="macro", zero_division=0)
    rep = classification_report(all_trues, all_preds, target_names=[INV_LABEL_MAP[i] for i in range(4)], output_dict=True, zero_division=0)
    return acc, macro_f1, rep

def plot_heatmap(matrix, client_labels, save_path):
    plt.figure(figsize=(7, 6))
    plt.imshow(matrix, cmap="RdYlGn", interpolation="nearest", vmin=0.4, vmax=1.0)
    plt.title("6x6 Local Silo Cross-Evaluation Matrix (Macro F1)\nEvidence of Catastrophic Forgetting", fontsize=12, fontweight="bold")
    plt.colorbar(label="Macro F1-Score")
    
    ticks = np.arange(len(client_labels))
    plt.xticks(ticks, client_labels, rotation=45)
    plt.yticks(ticks, client_labels)
    
    for i in range(len(client_labels)):
        for j in range(len(client_labels)):
            val = matrix[i, j]
            color = "white" if (val < 0.65 or val > 0.85) else "black"
            plt.text(j, i, f"{val*100:.1f}%", ha="center", va="center", color=color, fontweight="bold", fontsize=10)
            
    plt.ylabel("Trained Model Silo (W_local)", fontweight="bold")
    plt.xlabel("Evaluated Test Silo (Test Set)", fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()

def run_benchmark():
    logger.info("=== STARTING STAGE 3.5: MASTER 6x6 CROSS-EVALUATION & MULTI-TIER BENCHMARK ===")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using Computing Device: [{device}]")
    
    # 1. Load DataLoaders
    logger.info("Loading 6 Local Test Silos...")
    client_test_loaders = {}
    for i in range(1, 7):
        cid = f"client_{i}"
        path = os.path.join(CLIENTS_DIR, f"{cid}_test.parquet")
        client_test_loaders[cid] = get_dataloader(path, batch_size=256, shuffle=False)
        
    logger.info("Loading Global Holdouts (Global Test B & OOD CSIC)...")
    global_test_b_loader = get_dataloader(os.path.join(PROCESSED_DIR, "pool_b_global_test.parquet"), batch_size=256, shuffle=False)
    
    manifest_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "sample_manifest.parquet"))
    ood_df = manifest_df[(manifest_df["pool_id"] == "OOD") & (manifest_df["final_label"].isin(LABEL_MAP.keys()))]
    from torch.utils.data import DataLoader
    ood_loader = DataLoader(PayloadDataset(ood_df), batch_size=256, shuffle=False)
    
    # 2. Load Models
    models = {}
    
    # W_base
    base_ckpt = torch.load(W_BASE_PATH, map_location=device)
    model_type = base_ckpt.get("model_type", "char_cnn")
    base_model = get_neural_model(model_type, num_classes=4).to(device)
    base_model.load_state_dict(base_ckpt["model_state_dict"])
    models["W_base (Foundation)"] = base_model
    
    # 6 Local Client Models
    for i in range(1, 7):
        cid = f"client_{i}"
        m = get_neural_model(model_type, num_classes=4).to(device)
        ckpt = torch.load(os.path.join(LOCAL_MODELS_DIR, f"W_local_{cid}.pt"), map_location=device)
        m.load_state_dict(ckpt["model_state_dict"])
        models[f"W_local_{cid}"] = m
        
    # 3. Compute 6x6 Cross-Evaluation Matrix
    logger.info("Computing 6x6 Cross-Evaluation Heatmap Matrix...")
    matrix_6x6 = np.zeros((6, 6))
    client_names = [f"Client {i}" for i in range(1, 7)]
    
    for i in range(6):
        model_name = f"W_local_client_{i+1}"
        m = models[model_name]
        for j in range(6):
            test_cid = f"client_{j+1}"
            loader = client_test_loaders[test_cid]
            acc, f1, _ = evaluate_model_on_loader(m, loader, device)
            matrix_6x6[i, j] = f1
            logger.info(f"Model [{model_name}] on Test [{test_cid}] -> Macro F1: {f1*100:.2f}%")
            
    df_matrix = pd.DataFrame(matrix_6x6, index=client_names, columns=client_names)
    df_matrix.to_csv(OUT_MATRIX_CSV)
    logger.info(f"Saved 6x6 Cross-Evaluation Matrix to: {OUT_MATRIX_CSV}")
    
    heatmap_path = os.path.join(FIGURES_DIR, "heatmap_6x6_local_cross_evaluation.png")
    plot_heatmap(matrix_6x6, client_names, heatmap_path)
    logger.info(f"Saved 6x6 Heatmap figure to: {heatmap_path}")
    
    # 4. Comprehensive Benchmark Table
    logger.info("Computing Multi-Tier Benchmark Table across all models...")
    summary_rows = []
    full_json = {}
    
    for m_label, m in models.items():
        # Global Test B
        acc_b, f1_b, rep_b = evaluate_model_on_loader(m, global_test_b_loader, device)
        # OOD CSIC
        acc_ood, f1_ood, rep_ood = evaluate_model_on_loader(m, ood_loader, device)
        
        # In-silo vs Cross-silo calculation for local models
        if m_label.startswith("W_local_client_"):
            c_idx = int(m_label.split("_")[-1]) - 1
            in_silo_f1 = matrix_6x6[c_idx, c_idx]
            off_diag = [matrix_6x6[c_idx, k] for k in range(6) if k != c_idx]
            cross_silo_f1 = np.mean(off_diag)
        else:
            in_silo_f1 = np.nan
            cross_silo_f1 = np.nan
            
        row = {
            "Model": m_label,
            "In_Silo_Local_F1": round(in_silo_f1, 4) if not np.isnan(in_silo_f1) else "N/A",
            "Avg_Cross_Silo_F1": round(cross_silo_f1, 4) if not np.isnan(cross_silo_f1) else "N/A",
            "Global_Test_B_Acc": round(acc_b, 4),
            "Global_Test_B_Macro_F1": round(f1_b, 4),
            "OOD_CSIC_Acc": round(acc_ood, 4),
            "OOD_CSIC_Macro_F1": round(f1_ood, 4),
            "OOD_Benign_F1": round(rep_ood.get("benign", {}).get("f1-score", 0.0), 4),
            "OOD_XSS_F1": round(rep_ood.get("xss", {}).get("f1-score", 0.0), 4),
            "OOD_SQLi_F1": round(rep_ood.get("sqli", {}).get("f1-score", 0.0), 4),
            "OOD_PathTrav_F1": round(rep_ood.get("pathtrav", {}).get("f1-score", 0.0), 4)
        }
        summary_rows.append(row)
        full_json[m_label] = {
            "global_test_b_report": rep_b,
            "ood_csic_report": rep_ood
        }
        
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(OUT_SUMMARY_CSV, index=False)
    logger.info(f"Saved master benchmark summary CSV to: {OUT_SUMMARY_CSV}")
    
    with open(OUT_JSON, "w") as f:
        json.dump(full_json, f, indent=4)
    logger.info(f"Saved detailed metrics JSON to: {OUT_JSON}")
    
    # 5. Print Comparison Summary
    print("\n" + "="*140)
    print("STAGE 3: 6x6 LOCAL SILO CROSS-EVALUATION MATRIX (CATASTROPHIC FORGETTING PROOF)")
    print("="*140)
    print(df_matrix.to_string())
    print("="*140 + "\n")
    
    print("\n" + "="*140)
    print("STAGE 3: NEURAL FOUNDATION & LOCAL SILOS MULTI-TIER BENCHMARK SUMMARY")
    print("="*140)
    print(df_summary.to_string(index=False))
    print("="*140 + "\n")
    logger.info("STAGE 3.5 COMPLETE.")

if __name__ == "__main__":
    run_benchmark()
