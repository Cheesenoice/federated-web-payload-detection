import os
import time
import logging
import joblib
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, accuracy_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FEATURES_DIR = os.path.join(ROOT_DIR, "data", "interim", "stage_02_features")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_02_baselines")

def train_lr():
    logger.info("=== STARTING STAGE 2.2: MULTINOMIAL LOGISTIC REGRESSION TRAINING ===")
    
    # 1. Load Pre-extracted Features
    logger.info("Loading cached feature matrices...")
    X_train = sparse.load_npz(os.path.join(FEATURES_DIR, "X_train.npz"))
    y_train = np.load(os.path.join(FEATURES_DIR, "y_train.npy"), allow_pickle=True)
    
    X_val = sparse.load_npz(os.path.join(FEATURES_DIR, "X_val.npz"))
    y_val = np.load(os.path.join(FEATURES_DIR, "y_val.npy"), allow_pickle=True)
    
    logger.info(f"Training Feature Matrix: {X_train.shape}, Labels: {len(y_train)}")
    logger.info(f"Validation Feature Matrix: {X_val.shape}, Labels: {len(y_val)}")
    
    # 2. Configure Model
    clf = LogisticRegression(
        solver="saga",
        penalty="l2",
        C=1.0,
        max_iter=2000,
        tol=1e-4,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    
    # 3. Fit Model
    logger.info("Training Logistic Regression (SAGA solver, L2 reg, balanced loss)...")
    start_time = time.time()
    clf.fit(X_train, y_train)
    train_time = time.time() - start_time
    logger.info(f"Training completed in {train_time:.2f} seconds. (Iterations: {clf.n_iter_[0]})")
    
    # 4. Evaluate on Validation Set
    y_pred_val = clf.predict(X_val)
    val_acc = accuracy_score(y_val, y_pred_val)
    val_f1 = f1_score(y_val, y_pred_val, average="macro")
    
    logger.info(f"Validation Accuracy: {val_acc:.4f} | Validation Macro F1: {val_f1:.4f}")
    print("\n" + "="*60)
    print("LOGISTIC REGRESSION VALIDATION PERFORMANCE")
    print("="*60)
    print(classification_report(y_val, y_pred_val, digits=4))
    print("="*60 + "\n")
    
    # 5. Save Artifact
    model_path = os.path.join(MODELS_DIR, "model_logistic_regression.joblib")
    joblib.dump(clf, model_path)
    logger.info(f"Model checkpoint saved to: {model_path}")
    logger.info("STAGE 2.2 COMPLETE.")

if __name__ == "__main__":
    train_lr()
