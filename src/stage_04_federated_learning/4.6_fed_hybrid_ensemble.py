import os
import sys
import time
import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
import pandas as pd
from sklearn.metrics import f1_score, accuracy_score, classification_report, precision_score, recall_score

CURRENT_DIR = os.path.dirname(__file__)
sys.path.insert(0, CURRENT_DIR)

from fed_coordinator import (
    get_device, load_w_base, load_test_holdouts, evaluate_loader_metrics,
    MODELS_DIR, REPORTS_DIR, get_neural_model, INV_LABEL_MAP
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FEDAVG_CKPT = os.path.join(MODELS_DIR, "W_fedavg.pt")
OUT_CKPT = os.path.join(MODELS_DIR, "W_ensemble.pt")

ALPHA_BASE_WEIGHT = 0.3 # 30% Foundation Anchor + 70% Federated Consensus

class HybridEnsembleModel(nn.Module):
    """
    Hybrid Ensemble Model combining Pre-trained Foundation Intelligence (W_base)
    and Federated Consensus Intelligence (W_fed) via soft probability blending.
    """
    def __init__(self, base_model, fed_model, alpha=ALPHA_BASE_WEIGHT):
        super(HybridEnsembleModel, self).__init__()
        self.base_model = base_model
        self.fed_model = fed_model
        self.alpha = alpha

    def forward(self, x):
        logits_base = self.base_model(x)
        logits_fed = self.fed_model(x)
        
        prob_base = F.softmax(logits_base, dim=1)
        prob_fed = F.softmax(logits_fed, dim=1)
        
        blended_prob = self.alpha * prob_base + (1.0 - self.alpha) * prob_fed
        return blended_prob

def evaluate_ensemble_loader(ensemble_model, loader, device):
    ensemble_model.eval()
    all_preds, all_trues = [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=torch.cuda.is_available()):
                probs = ensemble_model(x)
            preds = torch.argmax(probs, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_trues.extend(y.numpy())
            
    acc = accuracy_score(all_trues, all_preds)
    macro_f1 = f1_score(all_trues, all_preds, average="macro", zero_division=0)
    macro_prec = precision_score(all_trues, all_preds, average="macro", zero_division=0)
    macro_rec = recall_score(all_trues, all_preds, average="macro", zero_division=0)
    rep = classification_report(all_trues, all_preds, target_names=[INV_LABEL_MAP[i] for i in range(4)], output_dict=True, zero_division=0)
    return acc, macro_f1, macro_prec, macro_rec, rep

def run_hybrid_ensemble():
    logger.info("=== STARTING STAGE 4.6: HYBRID ENSEMBLE INTELLIGENCE (W_base + W_fedavg) ===")
    if os.path.exists(OUT_CKPT):
        logger.info(f"--> [SKIP] Hybrid Ensemble checkpoint already exists at: {OUT_CKPT}. Skipping.")
        return
        
    device = get_device()
    logger.info(f"Computing Device: [{device}]")
    
    # 1. Load W_base Model
    base_model, model_type, _ = load_w_base(device)
    base_model.eval()
    
    # 2. Load FedAvg Global Model
    if not os.path.exists(FEDAVG_CKPT):
        logger.error(f"FedAvg Checkpoint not found at {FEDAVG_CKPT}. Run Stage 4.2 first.")
        return
        
    fed_ckpt = torch.load(FEDAVG_CKPT, map_location=device)
    fed_model = get_neural_model(model_type, num_classes=4).to(device)
    fed_model.load_state_dict(fed_ckpt["model_state_dict"])
    fed_model.eval()
    
    # 3. Instantiate Hybrid Ensemble
    ensemble = HybridEnsembleModel(base_model, fed_model, alpha=ALPHA_BASE_WEIGHT).to(device)
    logger.info(f"Hybrid Ensemble constructed: [{ALPHA_BASE_WEIGHT*100:.0f}% W_base + {(1-ALPHA_BASE_WEIGHT)*100:.0f}% W_fedavg]")
    
    # 4. Evaluate Ensemble on Test Holdouts
    client_test_loaders, global_b_loader, ood_loader = load_test_holdouts(batch_size=512)
    
    acc_b, f1_b, _, _, rep_b = evaluate_ensemble_loader(ensemble, global_b_loader, device)
    acc_ood, f1_ood, _, _, rep_ood = evaluate_ensemble_loader(ensemble, ood_loader, device)
    
    logger.info(f"[Hybrid Ensemble] Global Network Test B -> Acc: {acc_b*100:.2f}% | Macro F1: {f1_b:.4f}")
    logger.info(f"[Hybrid Ensemble] External OOD CSIC     -> Acc: {acc_ood*100:.2f}% | Macro F1: {f1_ood:.4f}")
    
    # 5. Save Checkpoint
    torch.save({
        "algorithm": "Hybrid_Ensemble",
        "model_type": model_type,
        "alpha_base_weight": ALPHA_BASE_WEIGHT,
        "base_model_state_dict": base_model.state_dict(),
        "fed_model_state_dict": fed_model.state_dict(),
        "global_test_b_macro_f1": f1_b,
        "ood_csic_macro_f1": f1_ood
    }, OUT_CKPT)
    logger.info(f"Saved Hybrid Ensemble Checkpoint to: {OUT_CKPT}")

if __name__ == "__main__":
    run_hybrid_ensemble()
