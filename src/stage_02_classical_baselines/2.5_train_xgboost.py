import os
import time
import logging
import joblib
import numpy as np
import torch
from scipy import sparse
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, f1_score, accuracy_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FEATURES_DIR = os.path.join(ROOT_DIR, "data", "interim", "stage_02_features")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_02_baselines")

CORE_CLASSES = ["benign", "pathtrav", "sqli", "xss"]

def train_xgb():
    logger.info("=== STARTING STAGE 2.5: GPU-ACCELERATED XGBOOST TRAINING ===")
    
    # 1. Hardware Detection
    use_cuda = torch.cuda.is_available()
    device = "cuda" if use_cuda else "cpu"
    device_name = torch.cuda.get_device_name(0) if use_cuda else "CPU Multi-Core"
    logger.info(f"Target Computing Device: [{device.upper()}] ({device_name})")
    
    # 2. Load Pre-extracted Features
    logger.info("Loading cached feature matrices...")
    X_train = sparse.load_npz(os.path.join(FEATURES_DIR, "X_train.npz"))
    y_train_raw = np.load(os.path.join(FEATURES_DIR, "y_train.npy"), allow_pickle=True)
    
    X_val = sparse.load_npz(os.path.join(FEATURES_DIR, "X_val.npz"))
    y_val_raw = np.load(os.path.join(FEATURES_DIR, "y_val.npy"), allow_pickle=True)
    
    # 3. Encode Class Labels
    label_encoder = LabelEncoder()
    label_encoder.fit(CORE_CLASSES)
    y_train = label_encoder.transform(y_train_raw)
    y_val = label_encoder.transform(y_val_raw)
    logger.info(f"Classes Mapped: {dict(zip(label_encoder.classes_, range(len(label_encoder.classes_))))}")
    
    # 4. Configure XGBoost
    xgb_params = {
        "n_estimators": 500,
        "max_depth": 8,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "objective": "multi:softprob",
        "eval_metric": ["mlogloss", "merror"],
        "early_stopping_rounds": 30,
        "random_state": 42,
        "tree_method": "hist",
        "device": device
    }
    
    if not use_cuda:
        xgb_params["n_jobs"] = -1
        
    clf = XGBClassifier(**xgb_params)
    
    # 5. Fit Model with Early Stopping
    logger.info("Training XGBoost (Histogram tree method on GPU, early stopping on Val)...")
    start_time = time.time()
    clf.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=50
    )
    train_time = time.time() - start_time
    logger.info(f"Training completed in {train_time:.2f} seconds. (Best Iteration: {clf.best_iteration})")
    
    # 6. Evaluate on Validation Set
    y_pred_val = clf.predict(X_val)
    val_acc = accuracy_score(y_val, y_pred_val)
    val_f1 = f1_score(y_val, y_pred_val, average="macro")
    
    logger.info(f"Validation Accuracy: {val_acc:.4f} | Validation Macro F1: {val_f1:.4f}")
    print("\n" + "="*60)
    print("XGBOOST VALIDATION PERFORMANCE")
    print("="*60)
    print(classification_report(y_val, y_pred_val, target_names=label_encoder.classes_, digits=4))
    print("="*60 + "\n")
    
    # 7. Save Artifacts
    model_path = os.path.join(MODELS_DIR, "model_xgboost.joblib")
    joblib.dump({"model": clf, "label_encoder": label_encoder}, model_path)
    logger.info(f"Model checkpoint saved to: {model_path}")
    logger.info("STAGE 2.5 COMPLETE.")

if __name__ == "__main__":
    train_xgb()
