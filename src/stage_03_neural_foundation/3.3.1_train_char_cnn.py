import os
import sys
import time
import logging
import importlib.util
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, f1_score, accuracy_score

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

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_03_neural")
os.makedirs(MODELS_DIR, exist_ok=True)

PATH_TRAIN = os.path.join(PROCESSED_DIR, "pool_a_train_balanced_40k.parquet")
PATH_VAL = os.path.join(PROCESSED_DIR, "pool_a_val.parquet")
OUT_CKPT = os.path.join(MODELS_DIR, "model_char_cnn.pt")

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

def train():
    logger.info("=== STARTING STAGE 3.3.1: TRAIN MULTI-SCALE 1D CharCNN ===")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Computing Device: [{device}] ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    
    train_loader = get_dataloader(PATH_TRAIN, batch_size=128, shuffle=True)
    val_loader = get_dataloader(PATH_VAL, batch_size=256, shuffle=False)
    
    model = get_neural_model("char_cnn", num_classes=4).to(device)
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"CharCNN Trainable parameters: {total_params:,}")
    
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=20, eta_min=1e-5)
    scaler = torch.amp.GradScaler(enabled=torch.cuda.is_available())
    
    epochs = 20
    patience = 5
    best_val_f1 = 0.0
    patience_counter = 0
    best_state = None
    
    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                logits = model(x)
                loss = criterion(logits, y)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            total_loss += loss.item()
            
        scheduler.step()
        avg_loss = total_loss / len(train_loader)
        val_acc, val_f1 = evaluate_loader(model, val_loader, device)
        logger.info(f"[CharCNN] Epoch {epoch:02d}/{epochs:02d} - Loss: {avg_loss:.4f} | Val Acc: {val_acc:.4f} | Val Macro F1: {val_f1:.4f}")
        
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = model.state_dict().copy()
            patience_counter = 0
            torch.save({
                "model_name": "CharCNN",
                "model_type": "char_cnn",
                "model_state_dict": model.state_dict(),
                "best_val_f1": best_val_f1,
                "val_acc": val_acc
            }, OUT_CKPT)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch}. Best Val F1: {best_val_f1:.4f}")
                break
                
    elapsed = time.time() - start_time
    logger.info(f"CharCNN Training finished in {elapsed:.2f}s. Saved checkpoint to {OUT_CKPT}")

if __name__ == "__main__":
    train()
