import os
import time
import logging
import joblib
import numpy as np
from scipy import sparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, f1_score, accuracy_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FEATURES_DIR = os.path.join(ROOT_DIR, "data", "interim", "stage_02_features")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_02_baselines")

def train_rf():
    logger.info("=== STARTING STAGE 2.4: RANDOM FOREST ENSEMBLE TRAINING ===")
    
    # 1. Load Pre-extracted Features
    logger.info("Loading cached feature matrices...")
    X_train = sparse.load_npz(os.path.join(FEATURES_DIR, "X_train.npz"))
    y_train = np.load(os.path.join(FEATURES_DIR, "y_train.npy"), allow_pickle=True)
    
    X_val = sparse.load_npz(os.path.join(FEATURES_DIR, "X_val.npz"))
    y_val = np.load(os.path.join(FEATURES_DIR, "y_val.npy"), allow_pickle=True)
    
    # 2. Configure Model
    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=30,
        min_samples_split=4,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        n_jobs=-1,
        random_state=42
    )
    
    # 3. Fit Model
    logger.info("Training Random Forest Classifier (300 trees, max_depth=30, multi-core)...")
    start_time = time.time()
    clf.fit(X_train, y_train)
    train_time = time.time() - start_time
    logger.info(f"Training completed in {train_time:.2f} seconds.")
    
    # 4. Evaluate on Validation Set
    y_pred_val = clf.predict(X_val)
    val_acc = accuracy_score(y_val, y_pred_val)
    val_f1 = f1_score(y_val, y_pred_val, average="macro")
    
    logger.info(f"Validation Accuracy: {val_acc:.4f} | Validation Macro F1: {val_f1:.4f}")
    print("\n" + "="*60)
    print("RANDOM FOREST VALIDATION PERFORMANCE")
    print("="*60)
    print(classification_report(y_val, y_pred_val, digits=4))
    print("="*60 + "\n")
    
    # 5. Save Artifact
    model_path = os.path.join(MODELS_DIR, "model_random_forest.joblib")
    joblib.dump(clf, model_path)
    logger.info(f"Model checkpoint saved to: {model_path}")
    logger.info("STAGE 2.4 COMPLETE.")

if __name__ == "__main__":
    train_rf()
