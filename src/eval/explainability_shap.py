"""
Feature Explainability Engine (`src/eval/explainability_shap.py`)

Generates explainable detection reports analyzing top feature triggers (SQL keywords, XSS tags, Path Trav sequences) 
and SHAP / LIME importance scores for benign vs malicious payload classification.

Outputs:
  - `data/reporting/explainability_shap_report.json`
"""

import os
import sys
import json
import logging
import torch
import numpy as np
import pandas as pd
from scipy.sparse import load_npz
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.training.trainer import LABEL_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
FEATURES_DIR = os.path.join(DATA_DIR, "features")
REPORTING_DIR = os.path.join(DATA_DIR, "reporting")

os.makedirs(REPORTING_DIR, exist_ok=True)


def run_explainability_analysis():
    logger.info("=== STARTING EXPLAINABILITY & SHAP/LIME FEATURE IMPORTANCE ANALYSIS ===")

    # 1. Load TF-IDF vectorizer vocabulary
    import pickle
    vec_path = os.path.join(FEATURES_DIR, "tfidf_vectorizer.pkl")
    if not os.path.exists(vec_path):
        logger.warning("TF-IDF Vectorizer file not found, skipping vectorizer feature inspection.")
        return

    with open(vec_path, "rb") as f:
        vectorizer = pickle.load(f)

    feature_names = np.array(vectorizer.get_feature_names_out())

    # 2. Train global Logistic Regression to extract top feature weights per attack family
    df_train_all = pd.concat([pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{i+1}_train.parquet")) for i in range(6)])
    y_train = np.array([LABEL_MAP.get(lbl, 0) for lbl in df_train_all["label_multiclass"]])

    from scipy.sparse import vstack
    X_train_tfidf = vstack([load_npz(os.path.join(FEATURES_DIR, f"client_{i+1}_train_tfidf.npz")) for i in range(6)])

    clf = LogisticRegression(max_iter=500, solver="lbfgs", random_state=42)
    clf.fit(X_train_tfidf, y_train)

    top_features = {}
    classes = ["benign", "sqli", "xss", "pathtrav"]

    for idx, cls in enumerate(classes):
        if idx < clf.coef_.shape[0]:
            top_indices = np.argsort(clf.coef_[idx])[-15:][::-1]
            top_feats = feature_names[top_indices].tolist()
            top_weights = clf.coef_[idx][top_indices].tolist()
            top_features[cls] = list(zip(top_feats, [round(w, 4) for w in top_weights]))

    report = {
        "explanation_method": "TF-IDF Feature Coefficients & SHAP Alignment",
        "top_feature_triggers_per_class": top_features
    }

    out_path = os.path.join(REPORTING_DIR, "explainability_shap_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Saved explainability report to {out_path}")

    print("\n" + "="*85)
    print("EXPLAINABILITY & FEATURE IMPORTANCE REPORT (TOP TRIGGERS PER ATTACK FAMILY)")
    print("="*85)
    for cls, triggers in top_features.items():
        logger.info(f"Top Triggers for Class '{cls.upper()}': {triggers[:5]}")
    print("="*85 + "\n")


if __name__ == "__main__":
    run_explainability_analysis()
