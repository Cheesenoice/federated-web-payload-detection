"""
Strict Family-Disjoint Client Partitioning Engine (`src/splits/build_splits.py`)

Adapted from C:\\Users\\huynh\\Desktop\\thailand\\project\\fedwebpayload architecture.

Guarantees:
  1. Local Client Silos (Train, Val, Test):
     - Client 1 & 2 (XSS Specialist): Local Train, Val, AND Test contain XSS + Benign ONLY.
     - Client 3 & 4 (SQLi Specialist): Local Train, Val, AND Test contain SQLi + Benign ONLY.
     - Client 5 & 6 (PathTrav Specialist): Local Train, Val, AND Test contain PathTrav + Benign ONLY.
  2. Global Held-Out Test Set (test_indomain.parquet):
     - Contains ALL 4 CLASSES from disjoint lineage clusters to evaluate post-FL Global Model generalization!
  3. Zero Lineage Overlap: Train Lineages ∩ Test Lineages = ∅ (Hard SHA256 Cluster Isolation).
"""

import os
import sys
import json
import hashlib
import logging
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
os.makedirs(SPLITS_DIR, exist_ok=True)

INPUT_CORPUS_PATH = os.path.join(PROCESSED_DIR, "trainable_corpus.parquet")
DEFAULT_SEED = 42


def stable_hash_score(value: str, seed: int, namespace: str) -> str:
    """Returns SHA256 deterministic hash for stable, seed-independent sorting."""
    return hashlib.sha256(f"{seed}\0{namespace}\0{value}".encode("utf-8")).hexdigest()


def build_family_disjoint_splits(seed: int = DEFAULT_SEED, test_fraction: float = 0.15, val_fraction: float = 0.15):
    logger.info(f"=== BUILDING STRICT FAMILY-DISJOINT NON-IID SPLITS (SEED={seed}) ===")
    if not os.path.exists(INPUT_CORPUS_PATH):
        raise FileNotFoundError(f"Input corpus not found: {INPUT_CORPUS_PATH}")

    df_corpus = pd.read_parquet(INPUT_CORPUS_PATH)
    logger.info(f"Loaded clean corpus: {len(df_corpus)} rows")

    if "dedup_cluster_id" not in df_corpus.columns:
        df_corpus["dedup_cluster_id"] = "CLUST_" + df_corpus.index.astype(str)

    unique_clusters = df_corpus["dedup_cluster_id"].astype(str).drop_duplicates().tolist()
    logger.info(f"Total unique root lineage clusters (dedup_cluster_id): {len(unique_clusters)}")

    # 1. Freeze Global Test & Validation Clusters FIRST (Dedup Lineage Isolated)
    cluster_df = pd.DataFrame({"dedup_cluster_id": unique_clusters})
    cluster_df["_score"] = cluster_df["dedup_cluster_id"].map(
        lambda cid: stable_hash_score(cid, seed=seed, namespace="global_holdout")
    )
    cluster_df = cluster_df.sort_values(["_score", "dedup_cluster_id"], kind="stable").reset_index(drop=True)

    n_total = len(cluster_df)
    n_test = int(n_total * test_fraction)
    n_val = int(n_total * val_fraction)

    test_cluster_set = set(cluster_df.iloc[:n_test]["dedup_cluster_id"])
    val_cluster_set = set(cluster_df.iloc[n_test:n_test + n_val]["dedup_cluster_id"])
    train_cluster_set = set(cluster_df.iloc[n_test + n_val:]["dedup_cluster_id"])

    # HARD LEAKAGE ASSERTIONS
    assert len(train_cluster_set & test_cluster_set) == 0, "CRITICAL: Train and Test cluster overlap detected!"
    assert len(train_cluster_set & val_cluster_set) == 0, "CRITICAL: Train and Val cluster overlap detected!"
    assert len(val_cluster_set & test_cluster_set) == 0, "CRITICAL: Val and Test cluster overlap detected!"

    df_test_indomain = df_corpus[df_corpus["dedup_cluster_id"].astype(str).isin(test_cluster_set)].copy()
    df_val_global = df_corpus[df_corpus["dedup_cluster_id"].astype(str).isin(val_cluster_set)].copy()
    df_train_pool = df_corpus[df_corpus["dedup_cluster_id"].astype(str).isin(train_cluster_set)].copy()

    df_test_indomain.to_parquet(os.path.join(SPLITS_DIR, "test_indomain.parquet"), index=False)
    df_val_global.to_parquet(os.path.join(SPLITS_DIR, "val_global.parquet"), index=False)

    # 2. Build Family-Disjoint Client Silos
    client_family_specs = {
        1: "xss",
        2: "xss",
        3: "sqli",
        4: "sqli",
        5: "pathtrav",
        6: "pathtrav"
    }

    # Partition Benign Clusters evenly across all 6 clients
    benign_pool = df_train_pool[df_train_pool["label_multiclass"].eq("benign")]
    benign_clusters = benign_pool["dedup_cluster_id"].astype(str).drop_duplicates().tolist()
    benign_clusters_sorted = sorted(
        benign_clusters,
        key=lambda cid: stable_hash_score(cid, seed=seed, namespace="benign_partition")
    )

    client_benign_clusters = [[] for _ in range(6)]
    for idx, cid in enumerate(benign_clusters_sorted):
        client_benign_clusters[idx % 6].append(cid)

    # Partition Attack Clusters strictly by designated Family
    client_attack_clusters = [[] for _ in range(6)]

    for family in ["xss", "sqli", "pathtrav"]:
        f_pool = df_train_pool[df_train_pool["label_multiclass"].eq(family)]
        f_clusters = f_pool["dedup_cluster_id"].astype(str).drop_duplicates().tolist()
        f_clusters_sorted = sorted(
            f_clusters,
            key=lambda cid: stable_hash_score(cid, seed=seed, namespace=f"attack_partition:{family}")
        )
        target_clients = [c_id for c_id, fam in client_family_specs.items() if fam == family]
        for idx, cid in enumerate(f_clusters_sorted):
            assigned_client = target_clients[idx % len(target_clients)]
            client_attack_clusters[assigned_client - 1].append(cid)

    manifest = {"seed": seed, "total_clusters": n_total, "splits": {}}

    for c_id in range(1, 7):
        designated_family = client_family_specs[c_id]
        c_benign_set = set(client_benign_clusters[c_id - 1])
        c_attack_set = set(client_attack_clusters[c_id - 1])

        c_full_cluster_set = c_benign_set | c_attack_set
        df_c_full = df_train_pool[df_train_pool["dedup_cluster_id"].astype(str).isin(c_full_cluster_set)].copy()

        # Split client pool into 70% Train, 15% Val, and 15% Test NATIVE TO THIS CLIENT'S SILO
        c_clusters_sorted = sorted(
            list(c_full_cluster_set),
            key=lambda cid: stable_hash_score(cid, seed=seed, namespace=f"client_{c_id}_subsplit")
        )
        nc = len(c_clusters_sorted)
        nc_val = max(1, int(nc * 0.15))
        nc_test = max(1, int(nc * 0.15))

        c_test_clusters = set(c_clusters_sorted[:nc_test])
        c_val_clusters = set(c_clusters_sorted[nc_test:nc_test + nc_val])
        c_train_clusters = set(c_clusters_sorted[nc_test + nc_val:])

        df_c_train = df_c_full[df_c_full["dedup_cluster_id"].astype(str).isin(c_train_clusters)].copy()
        df_c_val = df_c_full[df_c_full["dedup_cluster_id"].astype(str).isin(c_val_clusters)].copy()
        df_c_test = df_c_full[df_c_full["dedup_cluster_id"].astype(str).isin(c_test_clusters)].copy()

        df_c_train.to_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}_train.parquet"), index=False)
        df_c_val.to_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}_val.parquet"), index=False)
        df_c_test.to_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}_test.parquet"), index=False)

        # Legacy compatibility alias
        df_c_train.to_parquet(os.path.join(SPLITS_DIR, f"client_{c_id}.parquet"), index=False)

        manifest["splits"][f"client_{c_id}"] = {
            "designated_family": designated_family,
            "train_rows": len(df_c_train),
            "val_rows": len(df_c_val),
            "test_rows": len(df_c_test),
            "train_class_dist": df_c_train["label_multiclass"].value_counts().to_dict(),
            "test_class_dist": df_c_test["label_multiclass"].value_counts().to_dict()
        }

    with open(os.path.join(SPLITS_DIR, "split_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info("=== FAMILY-DISJOINT NON-IID SPLITTING COMPLETE ===")
    print("\n" + "="*85)
    print(f"STRICT FAMILY-DISJOINT DATASET PARTITIONING SUMMARY (SEED={seed})")
    print("="*85)
    print(f"Global In-Domain Test: {len(df_test_indomain)} rows ({len(test_cluster_set)} Clusters)")
    print("-" * 85)
    for i in range(1, 7):
        c_info = manifest["splits"][f"client_{i}"]
        print(f"Client {i} ({c_info['designated_family'].upper():<8}): Train={c_info['train_rows']:<5} | Test={c_info['test_rows']:<4} | Test Classes: {list(c_info['test_class_dist'].keys())}")
    print("="*85 + "\n")


if __name__ == "__main__":
    build_family_disjoint_splits(seed=42)
