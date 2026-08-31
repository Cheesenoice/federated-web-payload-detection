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

from fed_coordinator import (
    get_device, load_w_base, load_client_loaders, load_test_holdouts,
    aggregate_weighted_parameters, evaluate_loader_metrics, save_round_checkpoint,
    MODELS_DIR, REPORTS_DIR, get_neural_model
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_CKPT = os.path.join(MODELS_DIR, "W_fedprox.pt")
OUT_HISTORY_CSV = os.path.join(REPORTS_DIR, "history_fedprox.csv")

MU_PROXIMAL = 0.01

def train_client_fedprox(client_id, global_state, train_loader, val_loader, model_type, device, epochs=3, lr=3e-4, mu=MU_PROXIMAL):
    """Executes local training with FedProx proximal regularization: L = L_ce + (mu/2) * ||w - w_global||^2."""
    local_model = get_neural_model(model_type, num_classes=4).to(device)
    local_model.load_state_dict(copy.deepcopy(global_state))
    
    global_tensors = {k: v.clone().detach().to(device) for k, v in global_state.items()}
    
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
                ce_loss = criterion(logits, y)
                
                prox_loss = 0.0
                for name, param in local_model.named_parameters():
                    if name in global_tensors:
                        prox_loss += torch.sum((param - global_tensors[name]) ** 2)
                        
                total_loss = ce_loss + (mu / 2.0) * prox_loss
                
            scaler.scale(total_loss).backward()
            scaler.step(optimizer)
            scaler.update()
            
    val_acc, val_f1, _, _, _ = evaluate_loader_metrics(local_model, val_loader, device)
    return local_model.state_dict(), val_f1

def run_fedprox():
    logger.info(f"=== STARTING STAGE 4.3: FEDPROX (Li et al., 2020) [mu={MU_PROXIMAL}] [TURBOCHARGED] ===")
    if os.path.exists(OUT_CKPT) and os.path.exists(OUT_HISTORY_CSV):
        logger.info(f"--> [SKIP] FedProx checkpoint already exists at: {OUT_CKPT}. Skipping training.")
        return
        
    device = get_device()
    logger.info(f"Computing Device: [{device}] ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    
    # 1. Initialize Global Model from W_base Anchor
    global_model, model_type, global_state = load_w_base(device)
    logger.info(f"Initialized FedProx Global Model from W_base ({model_type.upper()})")
    
    # 2. Load DataLoaders
    train_loaders, val_loaders, client_sample_counts = load_client_loaders(batch_size=512)
    _, global_b_loader, _ = load_test_holdouts(batch_size=512)
    
    rounds = 10
    local_epochs = 3
    round_history = []
    
    start_total_time = time.time()
    for r in range(1, rounds + 1):
        round_start_t = time.time()
        logger.info(f"\n--- [FedProx mu={MU_PROXIMAL}] COMMUNICATION ROUND {r:02d}/{rounds:02d} ---")
        
        client_states = {}
        client_val_f1s = {}
        
        # Local FedProx training across all 6 clients
        for i in range(1, 7):
            cid = f"client_{i}"
            c_state, c_val_f1 = train_client_fedprox(
                cid, global_state, train_loaders[cid], val_loaders[cid],
                model_type, device, epochs=local_epochs, lr=3e-4, mu=MU_PROXIMAL
            )
            client_states[cid] = c_state
            client_val_f1s[cid] = c_val_f1
            logger.info(f"[{cid}] Local FedProx {local_epochs} Epochs Done -> Local Val F1: {c_val_f1:.4f}")
            
        # Server Aggregation: Weighted Average
        global_state = aggregate_weighted_parameters(client_states, client_sample_counts)
        global_model.load_state_dict(global_state)
        
        # Evaluate Global Model on Global Test B holdout (354,808 samples)
        test_b_acc, test_b_f1, _, _, _ = evaluate_loader_metrics(global_model, global_b_loader, device)
        round_time = time.time() - round_start_t
        
        logger.info(f"[FedProx] Round {r:02d} Complete ({round_time:.1f}s) -> Global Test B Acc: {test_b_acc*100:.2f}% | Global Test B Macro F1: {test_b_f1:.4f}")
        
        log_entry = {
            "Algorithm": "FedProx",
            "Round": r,
            "Global_Test_B_Acc": round(test_b_acc, 4),
            "Global_Test_B_Macro_F1": round(test_b_f1, 4),
            "Round_Time_s": round(round_time, 2)
        }
        for cid, val_f1 in client_val_f1s.items():
            log_entry[f"{cid}_Val_F1"] = round(val_f1, 4)
            
        round_history.append(log_entry)
        
        # Save Round Checkpoint
        save_round_checkpoint("FedProx", r, global_state, model_type, log_entry)
        
    total_time = time.time() - start_total_time
    logger.info(f"\n[FedProx] All {rounds} Rounds Completed in {total_time:.2f}s.")
    
    # Save History CSV
    df_history = pd.DataFrame(round_history)
    df_history.to_csv(OUT_HISTORY_CSV, index=False)
    logger.info(f"Saved FedProx Round History to: {OUT_HISTORY_CSV}")
    
    # Save Final Checkpoint
    torch.save({
        "algorithm": "FedProx",
        "model_type": model_type,
        "mu": MU_PROXIMAL,
        "model_state_dict": global_state,
        "final_global_test_b_f1": round_history[-1]["Global_Test_B_Macro_F1"],
        "total_training_time_s": total_time
    }, OUT_CKPT)
    logger.info(f"Saved FedProx Global Checkpoint to: {OUT_CKPT}")

if __name__ == "__main__":
    run_fedprox()
