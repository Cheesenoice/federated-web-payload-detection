import os
import sys
import time
import json
import logging
import importlib.util
import torch
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, accuracy_score

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

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_03_neural")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "stage_03_neural")
os.makedirs(REPORTS_DIR, exist_ok=True)

PATH_TEST_A = os.path.join(PROCESSED_DIR, "pool_a_test.parquet")
PATH_TEST_B = os.path.join(PROCESSED_DIR, "pool_b_global_test.parquet")
PATH_MANIFEST = os.path.join(PROCESSED_DIR, "sample_manifest.parquet")

OUT_TOURNAMENT_CSV = os.path.join(REPORTS_DIR, "neural_architectures_tournament_summary.csv")
OUT_W_BASE = os.path.join(MODELS_DIR, "W_base.pt")
OUT_W_BASE_META = os.path.join(MODELS_DIR, "W_base_metadata.json")

def evaluate_model_on_loader(model, loader, device):
    model.eval()
    all_preds, all_trues = [], []
    start_t = time.time()
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                logits = model(x)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_trues.extend(y.numpy())
            
    latency_ms = ((time.time() - start_t) / len(all_trues)) * 1000.0
    acc = accuracy_score(all_trues, all_preds)
    macro_f1 = f1_score(all_trues, all_preds, average="macro", zero_division=0)
    macro_prec = precision_score(all_trues, all_preds, average="macro", zero_division=0)
    macro_rec = recall_score(all_trues, all_preds, average="macro", zero_division=0)
    rep = classification_report(all_trues, all_preds, target_names=[INV_LABEL_MAP[i] for i in range(4)], output_dict=True, zero_division=0)
    return acc, macro_f1, macro_prec, macro_rec, latency_ms, rep

def run_tournament():
    logger.info("=== STARTING STAGE 3.3.4: NEURAL TOURNAMENT (CharCNN vs Bi-LSTM vs Transformer) ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using Computing Device: [{device}]")
    
    # 1. Load DataLoaders
    logger.info("Loading Test DataLoaders...")
    test_a_loader = get_dataloader(PATH_TEST_A, batch_size=256, shuffle=False)
    test_b_loader = get_dataloader(PATH_TEST_B, batch_size=256, shuffle=False)
    
    manifest_df = pd.read_parquet(PATH_MANIFEST)
    ood_df = manifest_df[(manifest_df["pool_id"] == "OOD") & (manifest_df["final_label"].isin(LABEL_MAP.keys()))]
    from torch.utils.data import DataLoader
    ood_loader = DataLoader(PayloadDataset(ood_df), batch_size=256, shuffle=False)
    
    # 2. Candidate Models
    candidates = [
        ("CharCNN (Multi-Scale 1D)", "char_cnn", os.path.join(MODELS_DIR, "model_char_cnn.pt")),
        ("Bi-LSTM with Attention", "bilstm", os.path.join(MODELS_DIR, "model_bilstm.pt")),
        ("Transformer Encoder", "transformer", os.path.join(MODELS_DIR, "model_transformer.pt"))
    ]
    
    tournament_rows = []
    best_overall_score = -1.0
    champion_info = {}
    
    datasets = [
        ("In-Domain Test A", test_a_loader, len(test_a_loader.dataset)),
        ("Global Network Test B", test_b_loader, len(test_b_loader.dataset)),
        ("External OOD (CSIC 2010)", ood_loader, len(ood_loader.dataset))
    ]
    
    # 3. Evaluate each architecture
    for model_title, arch_type, ckpt_path in candidates:
        if not os.path.exists(ckpt_path):
            logger.warning(f"Checkpoint not found for {model_title} at {ckpt_path}. Skipping.")
            continue
            
        logger.info(f"\n--- EVALUATING ARCHITECTURE: [{model_title}] ---")
        model = get_neural_model(arch_type, num_classes=4).to(device)
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        
        composite_score = 0.0
        
        for d_name, loader, n_samples in datasets:
            acc, macro_f1, prec, rec, lat_ms, rep = evaluate_model_on_loader(model, loader, device)
            logger.info(f"[{model_title}] on [{d_name}] -> Acc: {acc*100:.2f}% | Macro F1: {macro_f1:.4f} | Latency: {lat_ms:.4f} ms/sample")
            
            tournament_rows.append({
                "Architecture": model_title,
                "Model_Type": arch_type,
                "Dataset": d_name,
                "Samples": n_samples,
                "Accuracy": round(acc, 4),
                "Macro_Precision": round(prec, 4),
                "Macro_Recall": round(rec, 4),
                "Macro_F1": round(macro_f1, 4),
                "Benign_F1": round(rep.get("benign", {}).get("f1-score", 0.0), 4),
                "XSS_F1": round(rep.get("xss", {}).get("f1-score", 0.0), 4),
                "SQLi_F1": round(rep.get("sqli", {}).get("f1-score", 0.0), 4),
                "PathTrav_F1": round(rep.get("pathtrav", {}).get("f1-score", 0.0), 4),
                "Latency_ms_per_sample": round(lat_ms, 4)
            })
            
            if d_name == "Global Network Test B":
                composite_score += macro_f1 * 0.6
            elif d_name == "External OOD (CSIC 2010)":
                composite_score += macro_f1 * 0.4
                
        # Tournament scoring
        if composite_score > best_overall_score:
            best_overall_score = composite_score
            champion_info = {
                "model_title": model_title,
                "arch_type": arch_type,
                "ckpt_path": ckpt_path,
                "composite_score": composite_score,
                "state_dict": ckpt["model_state_dict"]
            }
            
    # 4. Save Tournament Summary
    df_tournament = pd.DataFrame(tournament_rows)
    df_tournament.to_csv(OUT_TOURNAMENT_CSV, index=False)
    logger.info(f"Saved Neural Tournament Comparison Table to: {OUT_TOURNAMENT_CSV}")
    
    # 5. Declare Champion and Freeze W_base
    logger.info(f"\n==========================================================================")
    logger.info(f"👑 THE TOURNAMENT CHAMPION IS: [{champion_info['model_title']}]")
    logger.info(f"Freezing and saving as canonical foundation anchor: {OUT_W_BASE}")
    logger.info(f"==========================================================================\n")
    
    torch.save({
        "champion_name": champion_info["model_title"],
        "model_type": champion_info["arch_type"],
        "model_state_dict": champion_info["state_dict"],
        "composite_tournament_score": champion_info["composite_score"]
    }, OUT_W_BASE)
    
    with open(OUT_W_BASE_META, "w") as f:
        json.dump({
            "champion_architecture": champion_info["model_title"],
            "model_type": champion_info["arch_type"],
            "source_checkpoint": champion_info["ckpt_path"],
            "composite_score": champion_info["composite_score"]
        }, f, indent=4)
        
    print("\n" + "="*140)
    print("STAGE 3: NEURAL ARCHITECTURES TOURNAMENT SUMMARY (TABLE 2 FOR PUBLICATION)")
    print("="*140)
    print(df_tournament.to_string(index=False))
    print("="*140 + "\n")
    logger.info("STAGE 3.3.4 COMPLETE.")

if __name__ == "__main__":
    run_tournament()
