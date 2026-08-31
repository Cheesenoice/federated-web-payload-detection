import os
import sys
import time
import copy
import logging
import importlib.util
import torch
import torch.nn as nn
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
CHARCNN_LOCAL_DIR = os.path.join(MODELS_DIR, "local_silos_charcnn")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "stage_03_neural")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")

os.makedirs(CHARCNN_LOCAL_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

CHARCNN_BASE_PATH = os.path.join(MODELS_DIR, "model_char_cnn.pt")
OUT_MATRIX_CSV = os.path.join(REPORTS_DIR, "local_silo_charcnn_cross_evaluation_matrix.csv")
OUT_SUMMARY_CSV = os.path.join(REPORTS_DIR, "neural_charcnn_benchmark_summary.csv")

def evaluate_loader(model, loader, device):
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

def run_charcnn_silos():
    logger.info("=== STARTING STAGE 3.4.1: FINE-TUNE & BENCHMARK CharCNN ON 6 LOCAL SILOS ===")
    
    if not os.path.exists(CHARCNN_BASE_PATH):
        logger.error(f"Base CharCNN checkpoint not found at {CHARCNN_BASE_PATH}.")
        return
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using Computing Device: [{device}] ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    
    # 1. Load Pre-trained Base CharCNN Weights
    base_checkpoint = torch.load(CHARCNN_BASE_PATH, map_location=device)
    base_state_dict = base_checkpoint["model_state_dict"]
    logger.info(f"Loaded foundational CharCNN base weights (Pretrain Val F1: {base_checkpoint.get('best_val_f1', 0.0):.4f})")
    
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    charcnn_models = {}
    
    # 2. Fine-tune CharCNN for each of the 6 Client Silos
    for i in range(1, 7):
        client_id = f"client_{i}"
        logger.info(f"\n--- FINE-TUNING CharCNN ON [{client_id.upper()}] ---")
        
        train_path = os.path.join(CLIENTS_DIR, f"{client_id}_train.parquet")
        val_path = os.path.join(CLIENTS_DIR, f"{client_id}_val.parquet")
        
        train_loader = get_dataloader(train_path, batch_size=256, shuffle=True)
        val_loader = get_dataloader(val_path, batch_size=256, shuffle=False)
        
        local_model = get_neural_model("char_cnn", num_classes=4).to(device)
        local_model.load_state_dict(copy.deepcopy(base_state_dict))
        
        optimizer = torch.optim.AdamW(local_model.parameters(), lr=3e-4, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-5)
        scaler = torch.amp.GradScaler(enabled=torch.cuda.is_available())
        
        epochs = 10
        patience = 3
        best_local_f1 = 0.0
        patience_counter = 0
        best_state = None
        
        start_time = time.time()
        for epoch in range(1, epochs + 1):
            local_model.train()
            total_loss = 0.0
            
            for x, y in train_loader:
                x, y = x.to(device), y.to(device)
                optimizer.zero_grad()
                with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                    logits = local_model(x)
                    loss = criterion(logits, y)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
                total_loss += loss.item()
                
            scheduler.step()
            avg_loss = total_loss / len(train_loader)
            val_acc, val_f1, _ = evaluate_loader(local_model, val_loader, device)
            logger.info(f"[CharCNN - {client_id}] Epoch {epoch:02d}/{epochs:02d} - Loss: {avg_loss:.4f} | Val Acc: {val_acc:.4f} | Val Macro F1: {val_f1:.4f}")
            
            if val_f1 > best_local_f1:
                best_local_f1 = val_f1
                best_state = copy.deepcopy(local_model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"[CharCNN - {client_id}] Early stopping at epoch {epoch}. Best Val F1: {best_local_f1:.4f}")
                    break
                    
        elapsed = time.time() - start_time
        logger.info(f"[CharCNN - {client_id}] Fine-tuning completed in {elapsed:.2f}s.")
        
        # Save to dedicated local_silos_charcnn folder
        out_ckpt_path = os.path.join(CHARCNN_LOCAL_DIR, f"W_local_{client_id}.pt")
        final_state = best_state if best_state is not None else local_model.state_dict()
        torch.save({
            "client_id": client_id,
            "model_type": "char_cnn",
            "model_state_dict": final_state,
            "best_val_f1": best_local_f1,
            "base_checkpoint_used": CHARCNN_BASE_PATH
        }, out_ckpt_path)
        logger.info(f"Saved CharCNN checkpoint to: {out_ckpt_path}")
        
        saved_m = get_neural_model("char_cnn", num_classes=4).to(device)
        saved_m.load_state_dict(final_state)
        charcnn_models[f"W_local_charcnn_{client_id}"] = saved_m

    # 3. Cross-Evaluation Matrix for CharCNN
    logger.info("Computing 6x6 Cross-Evaluation Matrix for CharCNN...")
    client_test_loaders = {}
    for i in range(1, 7):
        cid = f"client_{i}"
        path = os.path.join(CLIENTS_DIR, f"{cid}_test.parquet")
        client_test_loaders[cid] = get_dataloader(path, batch_size=256, shuffle=False)
        
    matrix_6x6 = np.zeros((6, 6))
    client_names = [f"Client {i}" for i in range(1, 7)]
    for i in range(6):
        m = charcnn_models[f"W_local_charcnn_client_{i+1}"]
        for j in range(6):
            test_cid = f"client_{j+1}"
            loader = client_test_loaders[test_cid]
            acc, f1, _ = evaluate_loader(m, loader, device)
            matrix_6x6[i, j] = f1
            
    df_matrix = pd.DataFrame(matrix_6x6, index=client_names, columns=client_names)
    df_matrix.to_csv(OUT_MATRIX_CSV)
    logger.info(f"Saved CharCNN 6x6 Matrix to: {OUT_MATRIX_CSV}")
    
    # 4. Multi-Tier Benchmark for CharCNN
    logger.info("Evaluating CharCNN models on Global Test B and OOD CSIC...")
    global_test_b_loader = get_dataloader(os.path.join(PROCESSED_DIR, "pool_b_global_test.parquet"), batch_size=256, shuffle=False)
    
    manifest_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "sample_manifest.parquet"))
    ood_df = manifest_df[(manifest_df["pool_id"] == "OOD") & (manifest_df["final_label"].isin(LABEL_MAP.keys()))]
    from torch.utils.data import DataLoader
    ood_loader = DataLoader(PayloadDataset(ood_df), batch_size=256, shuffle=False)
    
    summary_rows = []
    for m_label, m in charcnn_models.items():
        acc_b, f1_b, rep_b = evaluate_loader(m, global_test_b_loader, device)
        acc_ood, f1_ood, rep_ood = evaluate_loader(m, ood_loader, device)
        
        c_idx = int(m_label.split("_")[-1]) - 1
        in_silo_f1 = matrix_6x6[c_idx, c_idx]
        off_diag = [matrix_6x6[c_idx, k] for k in range(6) if k != c_idx]
        cross_silo_f1 = np.mean(off_diag)
        
        summary_rows.append({
            "Model": m_label,
            "Architecture": "CharCNN",
            "In_Silo_Local_F1": round(in_silo_f1, 4),
            "Avg_Cross_Silo_F1": round(cross_silo_f1, 4),
            "Global_Test_B_Acc": round(acc_b, 4),
            "Global_Test_B_Macro_F1": round(f1_b, 4),
            "OOD_CSIC_Acc": round(acc_ood, 4),
            "OOD_CSIC_Macro_F1": round(f1_ood, 4),
            "OOD_Benign_F1": round(rep_ood.get("benign", {}).get("f1-score", 0.0), 4),
            "OOD_XSS_F1": round(rep_ood.get("xss", {}).get("f1-score", 0.0), 4),
            "OOD_SQLi_F1": round(rep_ood.get("sqli", {}).get("f1-score", 0.0), 4),
            "OOD_PathTrav_F1": round(rep_ood.get("pathtrav", {}).get("f1-score", 0.0), 4)
        })
        
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(OUT_SUMMARY_CSV, index=False)
    logger.info(f"Saved CharCNN Benchmark Summary to: {OUT_SUMMARY_CSV}")
    
    print("\n" + "="*120)
    print("CharCNN 6x6 LOCAL SILO CROSS-EVALUATION MATRIX")
    print("="*120)
    print(df_matrix.to_string())
    print("="*120 + "\n")
    
    print("\n" + "="*120)
    print("CharCNN MULTI-TIER BENCHMARK SUMMARY")
    print("="*120)
    print(df_summary.to_string(index=False))
    print("="*120 + "\n")
    logger.info("STAGE 3.4.1 COMPLETE.")

if __name__ == "__main__":
    run_charcnn_silos()
