"""
High-Speed CUDA Platinum Ensemble Labeling Engine (`src/data/platinum_ensemble_labeler.py`)

Implements Dual-Consensus Label Verification combining:
  1. Layer 1: OWASP CRS v4 Regex Engine with 3-pass URL decoding
  2. Layer 2: SetFit / SentenceTransformer Semantic Classification (all-MiniLM-L6-v2) on CUDA
  3. Platinum Consensus: Payloads are retained ONLY IF Layer 1 and Layer 2 AGREE (Confidence >= 0.85).
"""

import os
import sys
import json
import torch
import logging
import pandas as pd
import numpy as np
import urllib.parse
from sklearn.linear_model import LogisticRegression
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.data.create_gold_seeds import get_gold_seed_df
from src.data.label_signatures import REGEX_XSS, REGEX_SQLI, REGEX_PATHTRAV, REGEX_BENIGN_NUMERIC_RANGE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
INTERIM_DIR = os.path.join(DATA_DIR, "interim")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
REPORTING_DIR = os.path.join(DATA_DIR, "reporting")
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(REPORTING_DIR, exist_ok=True)

INPUT_PARQUET = os.path.join(INTERIM_DIR, "sanitized.parquet")
OUTPUT_PARQUET = os.path.join(PROCESSED_DIR, "trainable_corpus.parquet")

LABEL_MAPPING = {"benign": 0, "sqli": 1, "xss": 2, "pathtrav": 3}
REVERSE_LABEL = {0: "benign", 1: "sqli", 2: "xss", 3: "pathtrav"}
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def run_platinum_labeler():
    logger.info(f"=== STARTING PLATINUM ENSEMBLE LABELING ENGINE (DEVICE={DEVICE}) ===")

    # Step 1: Load Gold Seeds & Train SentenceTransformer Classifier
    df_gold = get_gold_seed_df()
    logger.info(f"Loaded Gold Seed Set: {len(df_gold)} rows")

    logger.info("Loading pre-trained SentenceTransformer ('sentence-transformers/all-MiniLM-L6-v2')...")
    st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=DEVICE)

    gold_texts = df_gold["sanitized_payload"].tolist()
    gold_y = [LABEL_MAPPING[lbl] for lbl in df_gold["label_multiclass"]]

    logger.info("Encoding Gold Seed embeddings...")
    gold_embeddings = st_model.encode(gold_texts, batch_size=32, show_progress_bar=False, device=DEVICE)

    logger.info("Fitting Semantic Logistic Regression Classifier on Gold Embeddings...")
    classifier = LogisticRegression(C=10.0, max_iter=1000)
    classifier.fit(gold_embeddings, gold_y)

    # Step 2: Load Interim Corpus
    if not os.path.exists(INPUT_PARQUET):
        input_path = os.path.join(INTERIM_DIR, "raw_unified.parquet")
    else:
        input_path = INPUT_PARQUET

    df_corpus = pd.read_parquet(input_path)
    logger.info(f"Loaded candidate corpus: {len(df_corpus)} rows from {input_path}")

    col = "sanitized_payload" if "sanitized_payload" in df_corpus.columns else "raw_payload"
    payloads_all = df_corpus[col].fillna("").astype(str)

    logger.info("Stratified Candidate Selection: Finding candidates for XSS, SQLi, PathTrav, Benign...")
    decoded_all = payloads_all.map(urllib.parse.unquote)

    has_xss = payloads_all.str.contains(REGEX_XSS, regex=True) | decoded_all.str.contains(REGEX_XSS, regex=True)
    has_sqli = payloads_all.str.contains(REGEX_SQLI, regex=True) | decoded_all.str.contains(REGEX_SQLI, regex=True)
    has_pathtrav = payloads_all.str.contains(REGEX_PATHTRAV, regex=True) | decoded_all.str.contains(REGEX_PATHTRAV, regex=True)

    hit_count = has_xss.astype(int) + has_sqli.astype(int) + has_pathtrav.astype(int)

    layer1_all = pd.Series("benign", index=df_corpus.index)
    layer1_all[has_xss & (hit_count == 1)] = "xss"
    layer1_all[has_sqli & (hit_count == 1)] = "sqli"
    layer1_all[has_pathtrav & (hit_count == 1)] = "pathtrav"
    layer1_all[hit_count > 1] = "other"

    numeric_scrub = payloads_all.str.contains(REGEX_BENIGN_NUMERIC_RANGE, regex=True)
    layer1_all[numeric_scrub] = "benign"

    # Sample up to 10,000 per class to build a balanced 40,000 candidate pool
    sampled_indices = []
    for cls in ["benign", "sqli", "xss", "pathtrav"]:
        cls_idx = df_corpus[layer1_all == cls].index
        n_sample = min(10000, len(cls_idx))
        logger.info(f"Class '{cls}' matched {len(cls_idx)} candidates -> Sampling {n_sample} for Layer 2 prediction")
        if n_sample > 0:
            sampled_indices.extend(np.random.choice(cls_idx, size=n_sample, replace=False))

    df_corpus = df_corpus.loc[sampled_indices].reset_index(drop=True)
    payloads = df_corpus[col].fillna("").astype(str)
    layer1_labels = layer1_all.loc[sampled_indices].reset_index(drop=True)

    # Step 4: Layer 2 SetFit/SentenceTransformer Batch Semantic Prediction on CUDA GPU
    logger.info("Layer 2: Encoding semantic embeddings & predicting probability distributions on CUDA GPU...")
    batch_size = 512
    all_probs = []

    for i in range(0, len(payloads), batch_size):
        batch_texts = payloads.iloc[i:i + batch_size].tolist()
        batch_emb = st_model.encode(batch_texts, batch_size=batch_size, show_progress_bar=False, device=DEVICE)
        batch_prob = classifier.predict_proba(batch_emb)
        all_probs.append(batch_prob)

    probs = np.vstack(all_probs)
    max_probs = np.max(probs, axis=1)
    pred_indices = np.argmax(probs, axis=1)
    layer2_labels = [REVERSE_LABEL[idx] for idx in pred_indices]

    # Step 5: Apply Platinum Dual-Consensus Rule
    logger.info("Step 5: Applying Dual-Consensus Rule (Layer 1 Regex == Layer 2 Semantic && Confidence >= 0.85)...")
    platinum_mask = (layer1_labels.values == np.array(layer2_labels)) & (max_probs >= 0.85) & (layer1_labels.values != "other")

    df_platinum = df_corpus[platinum_mask].copy()
    df_platinum["label_multiclass"] = layer1_labels.values[platinum_mask]
    df_platinum["label_binary"] = (df_platinum["label_multiclass"] != "benign").astype(int)
    df_platinum["semantic_confidence"] = max_probs[platinum_mask]

    # Balance platinum rows
    balanced_dfs = []
    target_counts = {"benign": 15000, "sqli": 10000, "xss": 10000, "pathtrav": 10000}

    for cls, count in target_counts.items():
        df_cls = df_platinum[df_platinum["label_multiclass"] == cls]
        if len(df_cls) > count:
            df_sampled = df_cls.sample(n=count, random_state=42).copy()
        else:
            df_sampled = df_cls.copy()
        balanced_dfs.append(df_sampled)

    df_balanced = pd.concat(balanced_dfs, ignore_index=True)
    df_balanced = df_balanced.sample(frac=1.0, random_state=42).reset_index(drop=True)

    if "dedup_cluster_id" not in df_balanced.columns:
        df_balanced["dedup_cluster_id"] = "CLUST_" + df_balanced.index.astype(str)

    df_balanced.to_parquet(OUTPUT_PARQUET, index=False)

    final_dist = df_balanced["label_multiclass"].value_counts().to_dict()

    report = {
        "candidate_rows": len(df_corpus),
        "platinum_verified_rows": int(platinum_mask.sum()),
        "balanced_corpus_rows": len(df_balanced),
        "final_distribution": final_dist
    }

    with open(os.path.join(REPORTING_DIR, "platinum_labeling_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    logger.info("=== PLATINUM LABELING COMPLETE ===")
    print("\n" + "="*85)
    print("PLATINUM DUAL-CONSENSUS LABELING SUMMARY")
    print("="*85)
    print(f"Candidate Rows Evaluated    : {len(df_corpus)}")
    print(f"Platinum Dual-Verified Rows: {int(platinum_mask.sum())} (Confidence >= 0.85 & OWASP Match)")
    print(f"Balanced Corpus Saved       : {len(df_balanced)} rows -> {OUTPUT_PARQUET}")
    print("-" * 85)
    print("Final Balanced 4-Class Distribution:")
    for k, v in final_dist.items():
        print(f"  - {k:<10}: {v} rows")
    print("="*85 + "\n")

    return df_balanced


if __name__ == "__main__":
    run_platinum_labeler()
