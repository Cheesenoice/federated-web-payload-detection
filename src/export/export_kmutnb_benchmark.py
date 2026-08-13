"""
KMUTNB WebPayload Benchmark Export Engine (`src/export/export_kmutnb_benchmark.py`)

Packages and exports the sanitized feature-level dataset artifact:
`KMUTNB-WebPayload-FL-Benchmark`

Contains:
  - `sanitized_payload` (Cookies, session IDs, internal IPs 100% masked)
  - `label_binary` (0: Benign, 1: Malicious)
  - `label_multiclass` (benign, sqli, xss, pathtrav)
  - `client_partition_id` (Client 1 to Client 6 for Non-IID FL research)
  - `dedup_cluster_id` (SHA256 Lineage Cluster ID for zero-leakage split verification)
"""

import os
import sys
import json
import logging
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
EXPORT_DIR = os.path.join(DATA_DIR, "export", "KMUTNB-WebPayload-FL-Benchmark")

os.makedirs(EXPORT_DIR, exist_ok=True)


def run_kmutnb_benchmark_export():
    logger.info("=== STARTING KMUTNB-WEBPAYLOAD-FL-BENCHMARK ARTIFACT EXPORT ===")

    all_dfs = []
    
    # 1. Load Client Partition Datasets
    for i in range(1, 7):
        df_c = pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{i}_train.parquet"))
        df_c["fl_partition"] = f"client_{i}_silo"
        all_dfs.append(df_c)

    # 2. Load Global In-Domain Test & Validation Sets
    df_val = pd.read_parquet(os.path.join(SPLITS_DIR, "val_global.parquet"))
    df_val["fl_partition"] = "global_validation"
    all_dfs.append(df_val)

    df_test = pd.read_parquet(os.path.join(SPLITS_DIR, "test_indomain.parquet"))
    df_test["fl_partition"] = "global_test_indomain"
    all_dfs.append(df_test)

    # 3. Combine into unified Benchmark Artifact
    df_benchmark = pd.concat(all_dfs, ignore_index=True)

    # Select & sanitize export columns
    export_cols = ["sanitized_payload", "label_binary", "label_multiclass", "fl_partition", "dedup_cluster_id"]
    for col in export_cols:
        if col not in df_benchmark.columns:
            df_benchmark[col] = "N/A"

    df_export = df_benchmark[export_cols].copy()

    # Save Parquet & CSV formats for public repository release
    parquet_path = os.path.join(EXPORT_DIR, "KMUTNB-WebPayload-FL-Benchmark.parquet")
    csv_path = os.path.join(EXPORT_DIR, "KMUTNB-WebPayload-FL-Benchmark.csv")

    df_export.to_parquet(parquet_path, index=False)
    df_export.to_csv(csv_path, index=False)

    metadata = {
        "dataset_name": "KMUTNB-WebPayload-FL-Benchmark",
        "description": "Sanitized multi-family web attack payload dataset with Non-IID client partitions for Federated Learning research.",
        "author": "KMUTNB Cybersecurity Research Team",
        "total_records": len(df_export),
        "class_distribution": df_export["label_multiclass"].value_counts().to_dict(),
        "fl_partitions": df_export["fl_partition"].value_counts().to_dict(),
        "exported_files": [
            "KMUTNB-WebPayload-FL-Benchmark.parquet",
            "KMUTNB-WebPayload-FL-Benchmark.csv"
        ]
    }

    meta_path = os.path.join(EXPORT_DIR, "dataset_card.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("=== KMUTNB ARTIFACT EXPORT COMPLETE ===")
    print("\n" + "="*85)
    print("KMUTNB-WEBPAYLOAD-FL-BENCHMARK PUBLISHED ARTIFACT SUMMARY")
    print("="*85)
    print(f"Total Benchmark Records Saved : {len(df_export)} rows")
    print(f"Parquet Artifact Location    : {parquet_path}")
    print(f"CSV Artifact Location        : {csv_path}")
    print(f"Dataset Card Metadata        : {meta_path}")
    print("-" * 85)
    print("Class Distribution:")
    for k, v in metadata["class_distribution"].items():
        print(f"  - {k:<10}: {v} rows")
    print("="*85 + "\n")


if __name__ == "__main__":
    run_kmutnb_benchmark_export()
