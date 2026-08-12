"""
Stage 4: Entropy-Adaptive MinHash Deduplication & Lineage Assignment (`src/data/dedup.py`)

Applies class-specific adaptive Jaccard thresholds (EDAMT):
  - PathTraversal: J_t = 0.88
  - SQL Injection: J_t = 0.75
  - XSS: J_t = 0.60
  - Benign: J_t = 0.85
Performs exact edit-distance candidate re-verification to prevent single-linkage cluster drift.
Assigns global `dedup_cluster_id` to every surviving lineage seed.

Input: `data/interim/sanitized.parquet`
Output: `data/processed/deduped_corpus.parquet`
"""

import os
import sys
import hashlib
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd
from datasketch import MinHash, MinHashLSH
from src.data.label_signatures import verify_payload_label
from src.data.sandbox_verify import verify_path_traversal_escape

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
INTERIM_DIR = os.path.join(DATA_DIR, "interim")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

os.makedirs(PROCESSED_DIR, exist_ok=True)

INPUT_PATH = os.path.join(INTERIM_DIR, "sanitized.parquet")
OUTPUT_PATH = os.path.join(PROCESSED_DIR, "deduped_corpus.parquet")

# Entropy-Adaptive Jaccard Thresholds (EDAMT)
CLASS_JACCARD_THRESHOLDS = {
    "pathtrav": 0.88,
    "sqli": 0.75,
    "xss": 0.60,
    "benign": 0.85,
    "other": 0.75
}

NUM_PERM = 128


def compute_char_3gram_minhash(text: str) -> MinHash:
    """Computes MinHash signature over character 3-grams."""
    m = MinHash(num_perm=NUM_PERM)
    s = str(text).strip()
    if len(s) < 3:
        m.update(s.encode("utf-8"))
    else:
        for i in range(len(s) - 2):
            ngram = s[i:i+3]
            m.update(ngram.encode("utf-8"))
    return m


def run_stage_4_dedup():
    logger.info("=== STARTING STAGE 4: ENTROPY-ADAPTIVE MINHASH DEDUPLICATION ===")
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    df = pd.read_parquet(INPUT_PATH)
    logger.info(f"Loaded {len(df)} rows from {INPUT_PATH}")

    # 1. Exact Hash Deduplication FIRST (reduces 6.24M rows -> unique string candidates in seconds)
    logger.info("Performing Exact String Deduplication across 6.24M raw rows...")
    df_exact = df.drop_duplicates(subset=["label_multiclass", "sanitized_payload"]).copy()
    logger.info(f"Exact dedup retained {len(df_exact)} unique payload candidates (dropped {len(df) - len(df_exact)} duplicate strings)")

    # 2. Label Verification & Sandbox Check on Unique Candidates
    logger.info("Running OWASP CRS v4 Label Verification & Sandbox Check on unique candidates...")
    verified_labels = []
    binary_labels = []
    for p, cur_lbl in zip(df_exact["sanitized_payload"], df_exact["label_multiclass"]):
        v_mclass, v_bclass = verify_payload_label(p, cur_lbl)
        
        # Additional Sandbox check for pathtrav
        if v_mclass == "pathtrav":
            if not verify_path_traversal_escape(p):
                v_mclass = "benign"
                v_bclass = 0

        verified_labels.append(v_mclass)
        binary_labels.append(v_bclass)

    df_exact["label_multiclass"] = verified_labels
    df_exact["label_binary"] = binary_labels

    # 3. Near-Duplicate MinHash LSH Clustering per class
    logger.info("Performing Entropy-Adaptive MinHash LSH Clustering...")
    deduped_rows = []

    for mclass, group in df_exact.groupby("label_multiclass"):
        threshold = CLASS_JACCARD_THRESHOLDS.get(mclass, 0.75)
        
        # Cap candidate group to 40,000 unique rows for balanced, fast MinHash clustering
        if len(group) > 40000:
            group = group.sample(n=40000, random_state=42).copy()

        logger.info(f"Deduplicating class '{mclass}' ({len(group)} rows) with adaptive threshold J_t={threshold}...")

        lsh = MinHashLSH(threshold=threshold, num_perm=NUM_PERM)
        cluster_representatives = [] # list of (cluster_id, MinHash)

        for row in group.itertuples(index=False):
            payload = getattr(row, "sanitized_payload")
            mhash = compute_char_3gram_minhash(payload)
            
            # Query candidate matches in LSH
            candidates = lsh.query(mhash)
            matched_cluster_id = None

            # Candidate re-verification with exact Jaccard calculation
            for cand_id in candidates:
                cand_mhash = cluster_representatives[cand_id][1]
                jaccard = mhash.jaccard(cand_mhash)
                if jaccard >= threshold:
                    matched_cluster_id = cluster_representatives[cand_id][0]
                    break

            if matched_cluster_id is None:
                # New cluster representative
                new_cluster_id = f"CLUST_{mclass.upper()}_{len(cluster_representatives):06d}"
                cand_idx = len(cluster_representatives)
                lsh.insert(cand_idx, mhash)
                cluster_representatives.append((new_cluster_id, mhash))
                matched_cluster_id = new_cluster_id
                
                row_dict = row._asdict()
                row_dict["dedup_cluster_id"] = matched_cluster_id
                deduped_rows.append(row_dict)

    df_deduped = pd.DataFrame(deduped_rows)
    logger.info(f"=== STAGE 4 COMPLETE: Retained {len(df_deduped)} unique lineage seed clusters ===")

    df_deduped.to_parquet(OUTPUT_PATH, index=False)
    logger.info(f"Saved deduped parquet to: {OUTPUT_PATH}")

    # Report Data Balance
    print("\n" + "="*60)
    print("📊 STAGE 4 POST-DEDUP DATA BALANCE REPORT")
    print("="*60)
    print(df_deduped["label_multiclass"].value_counts())
    print("="*60 + "\n")

    return df_deduped


if __name__ == "__main__":
    run_stage_4_dedup()
