import os
import sys
import time
import copy
import logging
import torch
import torch.nn as nn
import pandas as pd

CURRENT_DIR = os.path.dirname(__file__)
sys.path.insert(0, CURRENT_DIR)

from fed_coordinator_fast import (
    get_device, load_w_base, load_client_loaders, load_test_holdouts,
    aggregate_weighted_parameters, evaluate_loader_metrics, save_round_checkpoint,
    MODELS_DIR, REPORTS_DIR, get_neural_model
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_CKPT = os.path.join(MODELS_DIR, "W_fedavg.pt")
OUT_HISTORY_CSV = os.path.join(REPORTS_DIR, "history_fedavg.csv")

def train_client_local(client_id, global_state, train_loader, val_loader, model_type, device, epochs=2, lr=3e-4):
    local_model = get_neural_model(model_type, num_classes=4).to(device)
    local_model.load_state_dict(copy.deepcopy(global_state))
    
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(local_model.parameters(), lr=lr, weight_decay=1e-4)
    scaler = torch.amp.GradScaler(enabled=torch.cuda.is_available())
    
    local_model.train()
    for epoch in range(epochs):
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                logits = local_model(x)
                loss = criterion(logits, y)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            
    val_acc, val_f1, _, _, _ = evaluate_loader_metrics(local_model, val_loader, device)
    return local_model.state_dict(), val_f1

def run_fedavg():
    logger.info("=== STARTING STAGE 4.2: STANDARD FEDERATED AVERAGING (FedAvg) [FAST TRACK] ===")
    if os.path.exists(OUT_CKPT) and os.path.exists(OUT_HISTORY_CSV):
        logger.info(f"--> [SKIP] FedAvg checkpoint already exists at: {OUT_CKPT}. Skipping training.")
        return
        
    device = get_device()
    logger.info(f"Computing Device: [{device}] ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    
    global_model, model_type, global_state = load_w_base(device)
    train_loaders, val_loaders, client_sample_counts = load_client_loaders(batch_size=256)
    _, global_b_loader, _ = load_test_holdouts(batch_size=512)
    
    rounds = 10
    local_epochs = 2
    round_history = []
    
    start_total_time = time.time()
    for r in range(1, rounds + 1):
        round_start_t = time.time()
        logger.info(f"\n--- [FedAvg Fast] COMMUNICATION ROUND {r:02d}/{rounds:02d} ---")
        
        client_states = {}
        client_val_f1s = {}
        
        for i in range(1, 7):
            cid = f"client_{i}"
            c_state, c_val_f1 = train_client_local(
                cid, global_state, train_loaders[cid], val_loaders[cid],
                model_type, device, epochs=local_epochs, lr=3e-4
            )
            client_states[cid] = c_state
            client_val_f1s[cid] = c_val_f1
            logger.info(f"[{cid}] Local Val F1: {c_val_f1:.4f}")
            
        global_state = aggregate_weighted_parameters(client_states, client_sample_counts)
        global_model.load_state_dict(global_state)
        
        test_b_acc, test_b_f1, _, _, _ = evaluate_loader_metrics(global_model, global_b_loader, device)
        round_time = time.time() - round_start_t
        
        logger.info(f"[FedAvg Fast] Round {r:02d} Complete ({round_time:.1f}s) -> Global Test B Macro F1: {test_b_f1:.4f}")
        
        log_entry = {
            "Algorithm": "FedAvg",
            "Round": r,
            "Global_Test_B_Acc": round(test_b_acc, 4),
            "Global_Test_B_Macro_F1": round(test_b_f1, 4),
            "Round_Time_s": round(round_time, 2)
        }
        for cid, val_f1 in client_val_f1s.items():
            log_entry[f"{cid}_Val_F1"] = round(val_f1, 4)
            
        round_history.append(log_entry)
        save_round_checkpoint("FedAvg", r, global_state, model_type, log_entry)
        
    total_time = time.time() - start_total_time
    logger.info(f"\n[FedAvg Fast] All {rounds} Rounds Completed in {total_time:.2f}s.")
    
    df_history = pd.DataFrame(round_history)
    df_history.to_csv(OUT_HISTORY_CSV, index=False)
    
    torch.save({
        "algorithm": "FedAvg",
        "model_type": model_type,
        "model_state_dict": global_state,
        "final_global_test_b_f1": round_history[-1]["Global_Test_B_Macro_F1"],
        "total_training_time_s": total_time
    }, OUT_CKPT)
    logger.info(f"Saved FedAvg Checkpoint to: {OUT_CKPT}")

if __name__ == "__main__":
    run_fedavg()
