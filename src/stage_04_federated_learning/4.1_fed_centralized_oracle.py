import os
import sys
import time
import logging
import torch
import torch.nn as nn
import pandas as pd
from torch.utils.data import ConcatDataset, DataLoader

CURRENT_DIR = os.path.dirname(__file__)
sys.path.insert(0, CURRENT_DIR)

from fed_coordinator import (
    get_device, load_w_base, load_client_loaders, evaluate_loader_metrics,
    MODELS_DIR, get_neural_model
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_CKPT = os.path.join(MODELS_DIR, "W_centralized.pt")

def train_centralized():
    logger.info("=== STARTING STAGE 4.1: CENTRALIZED LEARNING ORACLE (HIGH-SPEED) ===")
    if os.path.exists(OUT_CKPT):
        logger.info(f"--> [SKIP] Centralized checkpoint already exists at: {OUT_CKPT}. Skipping training.")
        return
        
    device = get_device()
    logger.info(f"Computing Device: [{device}] ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    
    # 1. Load W_base initialization
    model, model_type, base_state = load_w_base(device)
    logger.info(f"Initialized Centralized Model from W_base ({model_type.upper()})")
    
    # 2. Pool all 6 pre-tokenized client datasets
    train_loaders, val_loaders, _ = load_client_loaders(batch_size=512)
    
    pooled_train_ds = ConcatDataset([loader.dataset for loader in train_loaders.values()])
    pooled_val_ds = ConcatDataset([loader.dataset for loader in val_loaders.values()])
    
    logger.info(f"Pooled Centralized Training Samples:   {len(pooled_train_ds):,}")
    logger.info(f"Pooled Centralized Validation Samples: {len(pooled_val_ds):,}")
    
    central_train_loader = DataLoader(pooled_train_ds, batch_size=512, shuffle=True, pin_memory=torch.cuda.is_available())
    central_val_loader = DataLoader(pooled_val_ds, batch_size=512, shuffle=False, pin_memory=torch.cuda.is_available())
    
    # 3. Setup Optimizer & Scheduler
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10, eta_min=1e-5)
    scaler = torch.amp.GradScaler(enabled=torch.cuda.is_available())
    
    epochs = 10
    patience = 3
    best_val_f1 = 0.0
    patience_counter = 0
    best_state = None
    
    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        
        for x, y in central_train_loader:
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
        avg_loss = total_loss / len(central_train_loader)
        val_acc, val_f1, _, _, _ = evaluate_loader_metrics(model, central_val_loader, device)
        logger.info(f"[Centralized Oracle] Epoch {epoch:02d}/{epochs:02d} - Loss: {avg_loss:.4f} | Val Acc: {val_acc:.4f} | Val Macro F1: {val_f1:.4f}")
        
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = model.state_dict().copy()
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch}. Best Val F1: {best_val_f1:.4f}")
                break
                
    elapsed = time.time() - start_time
    logger.info(f"Centralized Training completed in {elapsed:.2f}s. Best Val Macro F1: {best_val_f1:.4f}")
    
    torch.save({
        "algorithm": "Centralized_Oracle",
        "model_type": model_type,
        "model_state_dict": best_state if best_state is not None else model.state_dict(),
        "best_val_f1": best_val_f1,
        "training_time_s": elapsed
    }, OUT_CKPT)
    logger.info(f"Saved Centralized Oracle checkpoint to: {OUT_CKPT}")

if __name__ == "__main__":
    train_centralized()
