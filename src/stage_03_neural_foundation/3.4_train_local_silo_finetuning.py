import os
import sys
import time
import copy
import logging
import importlib.util
import torch
import torch.nn as nn
import pandas as pd
from sklearn.metrics import f1_score, accuracy_score

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
get_neural_model = arch_mod.get_neural_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
CLIENTS_DIR = os.path.join(PROCESSED_DIR, "clients")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_03_neural")
LOCAL_MODELS_DIR = os.path.join(MODELS_DIR, "local_silos")

os.makedirs(LOCAL_MODELS_DIR, exist_ok=True)

W_BASE_PATH = os.path.join(MODELS_DIR, "W_base.pt")

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
    return acc, macro_f1

def train_local_silos():
    logger.info("=== STARTING STAGE 3.4: 6-CLIENT LOCAL SILO FINE-TUNING (STARTING FROM W_base) ===")
    
    if not os.path.exists(W_BASE_PATH):
        logger.error(f"Base model W_base not found at {W_BASE_PATH}. Run Stage 3.3.4 first.")
        return
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using Computing Device: [{device}] ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    
    # 1. Load Pre-trained Base Model Weights
    base_checkpoint = torch.load(W_BASE_PATH, map_location=device)
    base_state_dict = base_checkpoint["model_state_dict"]
    model_type = base_checkpoint.get("model_type", "char_cnn")
    champion_name = base_checkpoint.get("champion_name", "CharCNN")
    logger.info(f"Loaded foundational W_base weights: [{champion_name}] (Type: {model_type})")
    
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    
    # 2. Iterate through each of the 6 Client Silos
    for i in range(1, 7):
        client_id = f"client_{i}"
        logger.info(f"\n--- FINE-TUNING LOCAL MODEL: [{client_id.upper()}] ({champion_name}) ---")
        
        train_path = os.path.join(CLIENTS_DIR, f"{client_id}_train.parquet")
        val_path = os.path.join(CLIENTS_DIR, f"{client_id}_val.parquet")
        
        train_loader = get_dataloader(train_path, batch_size=256, shuffle=True)
        val_loader = get_dataloader(val_path, batch_size=256, shuffle=False)
        
        logger.info(f"{client_id} Train samples: {len(train_loader.dataset):,} | Val samples: {len(val_loader.dataset):,}")
        
        # Instantiate fresh model of the champion architecture and load W_base weights
        local_model = get_neural_model(model_type, num_classes=4).to(device)
        local_model.load_state_dict(copy.deepcopy(base_state_dict))
        
        optimizer = torch.optim.AdamW(local_model.parameters(), lr=3e-4, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-5)
        scaler = torch.amp.GradScaler(enabled=torch.cuda.is_available())
        
        epochs = 10
        patience = 3
        best_local_f1 = 0.0
        patience_counter = 0
        best_state = None
        
        start_client_time = time.time()
        
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
            
            val_acc, val_f1 = evaluate_loader(local_model, val_loader, device)
            logger.info(f"[{client_id}] Epoch {epoch:02d}/{epochs:02d} - Loss: {avg_loss:.4f} | Val Acc: {val_acc:.4f} | Val Macro F1: {val_f1:.4f}")
            
            if val_f1 > best_local_f1:
                best_local_f1 = val_f1
                best_state = copy.deepcopy(local_model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"[{client_id}] Early stopping at epoch {epoch}. Best Val F1: {best_local_f1:.4f}")
                    break
                    
        elapsed = time.time() - start_client_time
        logger.info(f"[{client_id}] Fine-tuning completed in {elapsed:.2f}s. Best Val Macro F1: {best_local_f1:.4f}")
        
        out_ckpt_path = os.path.join(LOCAL_MODELS_DIR, f"W_local_{client_id}.pt")
        torch.save({
            "client_id": client_id,
            "model_type": model_type,
            "model_state_dict": best_state if best_state is not None else local_model.state_dict(),
            "best_val_f1": best_local_f1,
            "base_checkpoint_used": W_BASE_PATH
        }, out_ckpt_path)
        logger.info(f"Saved local model checkpoint to: {out_ckpt_path}")
        
    logger.info("STAGE 3.4 COMPLETE: All 6 client local models fine-tuned and saved.")

if __name__ == "__main__":
    train_local_silos()
