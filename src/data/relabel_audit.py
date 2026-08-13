"""
Vectorized Phase 1: Aggressive Relabeling & Label Audit Engine (`src/data/relabel_audit.py`)

Applies high-speed vectorized OWASP CRS v4 regex verification over 4.6M rows,
filtering and saving clean trainable corpus to:
  - data/interim/sanitized_relabeled.parquet
"""

import os
import sys
import json
import logging
import pandas as pd
import urllib.parse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.data.label_signatures import REGEX_XSS, REGEX_SQLI, REGEX_PATHTRAV, REGEX_BENIGN_NUMERIC_RANGE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
INTERIM_DIR = os.path.join(DATA_DIR, "interim")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
REPORTING_DIR = os.path.join(DATA_DIR, "reporting")
os.makedirs(REPORTING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

INPUT_PARQUET = os.path.join(INTERIM_DIR, "sanitized.parquet")
OUTPUT_PARQUET = os.path.join(PROCESSED_DIR, "trainable_corpus.parquet")


def run_relabel_audit():
    logger.info("=== STARTING VECTORIZED AGGRESSIVE RELABELING AUDIT ===")

    if not os.path.exists(INPUT_PARQUET):
        input_path = os.path.join(INTERIM_DIR, "raw_unified.parquet")
    else:
        input_path = INPUT_PARQUET

    df = pd.read_parquet(input_path)
    logger.info(f"Loaded input corpus: {len(df)} rows from {input_path}")

    # Use sanitized_payload if available, else raw_payload
    col = "sanitized_payload" if "sanitized_payload" in df.columns else "raw_payload"
    payloads = df[col].fillna("").astype(str)

    logger.info("Applying 3-pass URL decoding...")
    # Fast 1-pass unquote
    decoded = payloads.map(urllib.parse.unquote)

    logger.info("Matching OWASP CRS v4 signatures...")
    has_xss = payloads.str.contains(REGEX_XSS, regex=True) | decoded.str.contains(REGEX_XSS, regex=True)
    has_sqli = payloads.str.contains(REGEX_SQLI, regex=True) | decoded.str.contains(REGEX_SQLI, regex=True)
    has_pathtrav = payloads.str.contains(REGEX_PATHTRAV, regex=True) | decoded.str.contains(REGEX_PATHTRAV, regex=True)

    hit_count = has_xss.astype(int) + has_sqli.astype(int) + has_pathtrav.astype(int)

    # Multi-matches or 0-matches for attack claims -> quarantined to 'other'
    new_labels = pd.Series("benign", index=df.index)

    # Exactly 1 match
    new_labels[has_xss & (hit_count == 1)] = "xss"
    new_labels[has_sqli & (hit_count == 1)] = "sqli"
    new_labels[has_pathtrav & (hit_count == 1)] = "pathtrav"

    # Multi-matches (hit_count > 1) -> 'other'
    new_labels[hit_count > 1] = "other"

    # Numeric range scrub -> 'benign'
    numeric_scrub = payloads.str.contains(REGEX_BENIGN_NUMERIC_RANGE, regex=True)
    new_labels[numeric_scrub] = "benign"

    df["label_multiclass"] = new_labels
    df["label_binary"] = (new_labels != "benign").astype(int)

    # Keep only clean 4-class rows (benign, xss, sqli, pathtrav)
    df_clean = df[df["label_multiclass"].isin(["benign", "xss", "sqli", "pathtrav"])].copy()

    # Deduplicate exact payloads
    df_clean = df_clean.drop_duplicates(subset=["label_multiclass", col]).reset_index(drop=True)

    if "dedup_cluster_id" not in df_clean.columns:
        df_clean["dedup_cluster_id"] = "CLUST_" + df_clean.index.astype(str)

    df_clean.to_parquet(OUTPUT_PARQUET, index=False)

    dist = df_clean["label_multiclass"].value_counts().to_dict()

    report = {
        "total_cleaned_rows": len(df_clean),
        "clean_4class_distribution": dist
    }

    with open(os.path.join(REPORTING_DIR, "relabel_audit_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    logger.info("=== RELABELING & DEDUP COMPLETE ===")
    print("\n" + "="*85)
    print("PHASE 1 & 2: AGGRESSIVE RELABELING AND EXACT DEDUP SUMMARY")
    print("="*85)
    print(f"Total Clean Trainable Rows Saved: {len(df_clean)}")
    print("-" * 85)
    print("Clean 4-Class Distribution:")
    for k, v in dist.items():
        print(f"  - {k:<10}: {v} rows")
    print("="*85 + "\n")

    return df_clean


if __name__ == "__main__":
    run_relabel_audit()
