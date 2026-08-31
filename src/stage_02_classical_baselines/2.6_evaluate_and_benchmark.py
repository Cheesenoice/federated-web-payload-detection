import os
import time
import json
import logging
import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, accuracy_score, confusion_matrix
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FEATURES_DIR = os.path.join(ROOT_DIR, "data", "interim", "stage_02_features")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_02_baselines")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "stage_02_baselines")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")

os.makedirs(FIGURES_DIR, exist_ok=True)

OUT_JSON = os.path.join(REPORTS_DIR, "metrics_classical_baselines.json")
OUT_CSV = os.path.join(REPORTS_DIR, "classical_baselines_summary.csv")

CORE_CLASSES = ["benign", "xss", "sqli", "pathtrav"]

def plot_confusion_matrix(cm, classes, title, save_path):
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title(title, fontsize=12, fontweight="bold")
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, format(cm[i, j], "d"),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel("True Label", fontweight="bold")
    plt.xlabel("Predicted Label", fontweight="bold")
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()

def evaluate_models():
    logger.info("=== STARTING STAGE 2.6: UNIFIED 3-TIER EVALUATION & BENCHMARKING ===")
    
    # 1. Load Test Datasets
    logger.info("Loading Test Feature Matrices...")
    datasets = {
        "In-Domain Test A": (
            sparse.load_npz(os.path.join(FEATURES_DIR, "X_test_a.npz")),
            np.load(os.path.join(FEATURES_DIR, "y_test_a.npy"), allow_pickle=True)
        ),
        "Global Network Test B": (
            sparse.load_npz(os.path.join(FEATURES_DIR, "X_test_b.npz")),
            np.load(os.path.join(FEATURES_DIR, "y_test_b.npy"), allow_pickle=True)
        ),
        "External OOD (CSIC 2010)": (
            sparse.load_npz(os.path.join(FEATURES_DIR, "X_ood.npz")),
            np.load(os.path.join(FEATURES_DIR, "y_ood.npy"), allow_pickle=True)
        )
    }
    
    for d_name, (X, y) in datasets.items():
        logger.info(f"{d_name}: {X.shape[0]} samples, {X.shape[1]} features.")
        
    # 2. Load Models
    logger.info("Loading Model Checkpoints...")
    models = {
        "Logistic Regression": (
            joblib.load(os.path.join(MODELS_DIR, "model_logistic_regression.joblib")),
            False
        ),
        "Linear SVM (Calibrated)": (
            joblib.load(os.path.join(MODELS_DIR, "model_linear_svm.joblib")),
            False
        ),
        "Random Forest": (
            joblib.load(os.path.join(MODELS_DIR, "model_random_forest.joblib")),
            False
        ),
        "XGBoost (GPU)": (
            joblib.load(os.path.join(MODELS_DIR, "model_xgboost.joblib")),
            True
        )
    }
    
    benchmark_results = []
    full_metrics_dict = {}
    
    # 3. Evaluate each model on each dataset
    for model_name, (model_obj, is_xgb) in models.items():
        full_metrics_dict[model_name] = {}
        
        for dataset_name, (X_test, y_true_raw) in datasets.items():
            logger.info(f"Evaluating [{model_name}] on [{dataset_name}] ({len(y_true_raw)} samples)...")
            
            # Predict
            start_t = time.time()
            if is_xgb:
                clf = model_obj["model"]
                le = model_obj["label_encoder"]
                y_pred_idx = clf.predict(X_test)
                y_pred = le.inverse_transform(y_pred_idx)
            else:
                y_pred = model_obj.predict(X_test)
            latency_ms = ((time.time() - start_t) / len(y_true_raw)) * 1000.0
            
            # Compute Core Metrics
            acc = accuracy_score(y_true_raw, y_pred)
            macro_f1 = f1_score(y_true_raw, y_pred, average="macro", zero_division=0)
            macro_prec = precision_score(y_true_raw, y_pred, average="macro", zero_division=0)
            macro_rec = recall_score(y_true_raw, y_pred, average="macro", zero_division=0)
            
            # Per-class F1
            rep = classification_report(y_true_raw, y_pred, labels=CORE_CLASSES, output_dict=True, zero_division=0)
            
            benign_f1 = rep.get("benign", {}).get("f1-score", 0.0)
            xss_f1 = rep.get("xss", {}).get("f1-score", 0.0)
            sqli_f1 = rep.get("sqli", {}).get("f1-score", 0.0)
            pathtrav_f1 = rep.get("pathtrav", {}).get("f1-score", 0.0)
            
            # Record summary
            res_row = {
                "Model": model_name,
                "Dataset": dataset_name,
                "Samples": len(y_true_raw),
                "Accuracy": round(acc, 4),
                "Macro_Precision": round(macro_prec, 4),
                "Macro_Recall": round(macro_rec, 4),
                "Macro_F1": round(macro_f1, 4),
                "Benign_F1": round(benign_f1, 4),
                "XSS_F1": round(xss_f1, 4),
                "SQLi_F1": round(sqli_f1, 4),
                "PathTrav_F1": round(pathtrav_f1, 4),
                "Latency_ms_per_sample": round(latency_ms, 4)
            }
            benchmark_results.append(res_row)
            full_metrics_dict[model_name][dataset_name] = {
                "summary": res_row,
                "classification_report": rep
            }
            
            # Plot Confusion Matrix
            cm = confusion_matrix(y_true_raw, y_pred, labels=CORE_CLASSES)
            clean_m_name = model_name.replace(" ", "_").replace("(", "").replace(")", "").lower()
            clean_d_name = dataset_name.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_").lower()
            plot_path = os.path.join(FIGURES_DIR, f"cm_{clean_m_name}_{clean_d_name}.png")
            plot_confusion_matrix(cm, CORE_CLASSES, f"{model_name} on {dataset_name}", plot_path)
            
    # 4. Save Export Files
    df_results = pd.DataFrame(benchmark_results)
    df_results.to_csv(OUT_CSV, index=False)
    logger.info(f"Saved summary CSV to: {OUT_CSV}")
    
    with open(OUT_JSON, "w") as f:
        json.dump(full_metrics_dict, f, indent=4)
    logger.info(f"Saved full metrics JSON to: {OUT_JSON}")
    
    # 5. Print Comparison Summary
    print("\n" + "="*140)
    print("STAGE 2 CLASSICAL BASELINES COMPREHENSIVE BENCHMARK (MATHEMATICAL FLOOR)")
    print("="*140)
    print(df_results.to_string(index=False))
    print("="*140 + "\n")
    logger.info("STAGE 2.6 COMPLETE.")

if __name__ == "__main__":
    evaluate_models()
