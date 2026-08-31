import os
import sys
import json
import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, accuracy_score, classification_report
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CURRENT_DIR = os.path.dirname(__file__)
sys.path.insert(0, CURRENT_DIR)

from fed_coordinator_fast import (
    get_device, load_w_base, load_test_holdouts, evaluate_loader_metrics,
    MODELS_DIR, STAGE_03_MODELS_DIR, REPORTS_DIR, FIGURES_DIR,
    get_neural_model, INV_LABEL_MAP
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_MASTER_CSV = os.path.join(REPORTS_DIR, "federated_algorithms_master_benchmark.csv")
OUT_JSON = os.path.join(REPORTS_DIR, "metrics_federated.json")
OUT_CONVERGENCE_MASTER_CSV = os.path.join(REPORTS_DIR, "round_convergence_history_master.csv")

class HybridEnsembleEvaluator(nn.Module):
    def __init__(self, base_m, fed_m, alpha=0.3):
        super(HybridEnsembleEvaluator, self).__init__()
        self.base_m = base_m
        self.fed_m = fed_m
        self.alpha = alpha
    def forward(self, x):
        p_base = F.softmax(self.base_m(x), dim=1)
        p_fed = F.softmax(self.fed_m(x), dim=1)
        return self.alpha * p_base + (1.0 - self.alpha) * p_fed

def evaluate_model_on_loader(model, loader, device, is_ensemble=False):
    model.eval()
    all_preds, all_trues = [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                out = model(x)
            preds = torch.argmax(out, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_trues.extend(y.numpy())
            
    acc = accuracy_score(all_trues, all_preds)
    macro_f1 = f1_score(all_trues, all_preds, labels=[0, 1, 2, 3], average="macro", zero_division=0)
    rep = classification_report(all_trues, all_preds, labels=[0, 1, 2, 3], target_names=[INV_LABEL_MAP[i] for i in range(4)], output_dict=True, zero_division=0)
    return acc, macro_f1, rep

def plot_convergence_curves():
    history_files = {
        "FedAvg": os.path.join(REPORTS_DIR, "history_fedavg.csv"),
        "FedProx": os.path.join(REPORTS_DIR, "history_fedprox.csv"),
        "FedAvgM": os.path.join(REPORTS_DIR, "history_fedavgm.csv"),
        "DAFL (Ours)": os.path.join(REPORTS_DIR, "history_dafl.csv")
    }
    
    plt.figure(figsize=(10, 6))
    merged_dfs = []
    
    colors = {"FedAvg": "blue", "FedProx": "orange", "FedAvgM": "green", "DAFL (Ours)": "purple"}
    markers = {"FedAvg": "o-", "FedProx": "s-", "FedAvgM": "^-", "DAFL (Ours)": "D-"}
    
    for name, path in history_files.items():
        if os.path.exists(path):
            df = pd.read_csv(path)
            df["Algorithm"] = name
            merged_dfs.append(df)
            plt.plot(df["Round"], df["Global_Test_B_Macro_F1"] * 100, markers[name], color=colors[name], label=name, linewidth=2)
            
    plt.title("Federated Convergence on Global Test B across 10 Communication Rounds (Fast 60k Track)", fontsize=12, fontweight="bold")
    plt.xlabel("Communication Round (R)", fontsize=11, fontweight="bold")
    plt.ylabel("Global Network Test B Macro F1 (%)", fontsize=11, fontweight="bold")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()
    
    plot_path = os.path.join(FIGURES_DIR, "convergence_comparison_rounds.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()
    logger.info(f"Saved convergence plot to: {plot_path}")
    
    if merged_dfs:
        df_merged = pd.concat(merged_dfs, ignore_index=True)
        df_merged.to_csv(OUT_CONVERGENCE_MASTER_CSV, index=False)
        logger.info(f"Saved master round convergence CSV to: {OUT_CONVERGENCE_MASTER_CSV}")

def plot_ood_bar_chart(summary_df):
    plt.figure(figsize=(11, 5))
    algos = summary_df["Method"].values
    ood_f1s = summary_df["OOD_CSIC_Macro_F1"].values * 100
    
    bars = plt.bar(algos, ood_f1s, color=["gray", "silver", "steelblue", "skyblue", "lightcoral", "darkseagreen", "mediumorchid"])
    plt.title("Zero-Shot OOD Robustness Comparison (External CSIC 2010 Benchmark)", fontsize=12, fontweight="bold")
    plt.ylabel("OOD Macro F1-Score (%)", fontsize=11, fontweight="bold")
    plt.xticks(rotation=30, ha="right", fontweight="bold")
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.5, f"{height:.2f}%", ha="center", va="bottom", fontweight="bold")
        
    plt.tight_layout()
    plot_path = os.path.join(FIGURES_DIR, "ood_robustness_comparison.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()
    logger.info(f"Saved OOD comparison figure to: {plot_path}")

def run_master_benchmark():
    logger.info("=== STARTING STAGE 4.7: MASTER BENCHMARK [FAST 60k TRACK] ===")
    device = get_device()
    logger.info(f"Computing Device: [{device}]")
    
    client_test_loaders, global_b_loader, ood_loader = load_test_holdouts(batch_size=512)
    
    models_to_eval = [
        ("Foundation W_base", os.path.join(STAGE_03_MODELS_DIR, "W_base.pt"), "single"),
        ("Centralized Oracle", os.path.join(MODELS_DIR, "W_centralized.pt"), "single"),
        ("Standard FedAvg", os.path.join(MODELS_DIR, "W_fedavg.pt"), "single"),
        ("FedProx (mu=0.01)", os.path.join(MODELS_DIR, "W_fedprox.pt"), "single"),
        ("FedAvgM (beta=0.9)", os.path.join(MODELS_DIR, "W_fedavgm.pt"), "single"),
        ("DAFL (Ours, lambda=0.02)", os.path.join(MODELS_DIR, "W_dafl.pt"), "single"),
        ("Hybrid Ensemble (W_base+W_fed)", os.path.join(MODELS_DIR, "W_ensemble.pt"), "ensemble")
    ]
    
    summary_rows = []
    full_json = {}
    
    for name, ckpt_path, eval_mode in models_to_eval:
        if not os.path.exists(ckpt_path):
            logger.warning(f"Checkpoint for {name} not found at {ckpt_path}. Skipping.")
            continue
            
        logger.info(f"\n--- BENCHMARKING: [{name}] ---")
        ckpt = torch.load(ckpt_path, map_location=device)
        model_type = ckpt.get("model_type", "transformer")
        
        if eval_mode == "single":
            m = get_neural_model(model_type, num_classes=4).to(device)
            m.load_state_dict(ckpt["model_state_dict"])
            is_ens = False
        elif eval_mode == "ensemble":
            base_m, _, _ = load_w_base(device)
            fed_m = get_neural_model(model_type, num_classes=4).to(device)
            fed_m.load_state_dict(ckpt["fed_model_state_dict"])
            m = HybridEnsembleEvaluator(base_m, fed_m, alpha=ckpt.get("alpha_base_weight", 0.3)).to(device)
            is_ens = True
            
        client_f1s = []
        for i in range(1, 7):
            cid = f"client_{i}"
            loader = client_test_loaders[cid]
            acc_c, f1_c, _ = evaluate_model_on_loader(m, loader, device, is_ensemble=is_ens)
            client_f1s.append(f1_c)
            
        avg_local_test_f1 = np.mean(client_f1s)
        acc_b, f1_b, rep_b = evaluate_model_on_loader(m, global_b_loader, device, is_ensemble=is_ens)
        acc_ood, f1_ood, rep_ood = evaluate_model_on_loader(m, ood_loader, device, is_ensemble=is_ens)
        
        logger.info(f"[{name}] -> Avg Local Test F1: {avg_local_test_f1*100:.2f}% | Global Test B F1: {f1_b*100:.2f}% | OOD CSIC F1: {f1_ood*100:.2f}%")
        
        row = {
            "Method": name,
            "Avg_Local_Test_F1": round(avg_local_test_f1, 4),
            "Client_1_Test_F1": round(client_f1s[0], 4),
            "Client_3_Test_F1": round(client_f1s[2], 4),
            "Client_5_Test_F1": round(client_f1s[4], 4),
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
        full_json[name] = {
            "global_test_b_report": rep_b,
            "ood_csic_report": rep_ood,
            "client_test_f1s": client_f1s
        }
        
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(OUT_MASTER_CSV, index=False)
    logger.info(f"Saved Master Federated Benchmark to: {OUT_MASTER_CSV}")
    
    with open(OUT_JSON, "w") as f:
        json.dump(full_json, f, indent=4)
    logger.info(f"Saved detailed metrics JSON to: {OUT_JSON}")
    
    plot_convergence_curves()
    plot_ood_bar_chart(df_summary)
    
    print("\n" + "="*140)
    print("STAGE 4: FEDERATED LEARNING ALGORITHMS MASTER BENCHMARK (PUBLICATION TABLE 4 - FAST 60k TRACK)")
    print("="*140)
    print(df_summary.to_string(index=False))
    print("="*140 + "\n")
    logger.info("STAGE 4.7 FAST COMPLETE.")

if __name__ == "__main__":
    run_master_benchmark()
