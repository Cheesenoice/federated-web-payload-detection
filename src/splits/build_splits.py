"""
Strict Family-Disjoint Non-IID Dataset Partitioning Engine (`src/splits/build_splits.py`)

Adapted from C:\\Users\\huynh\\Desktop\\thailand\\project\\fedwebpayload architecture.

Guarantees:
  1. Family-Disjoint Local Silos:
     - Client 1 & Client 2: Train ONLY on XSS + Benign (Unseen: SQLi, PathTrav)
     - Client 3 & Client 4: Train ONLY on SQLi + Benign (Unseen: XSS, PathTrav)
     - Client 5 & Client 6: Train ONLY on PathTrav + Benign (Unseen: XSS, SQLi)
  2. Complete 4-Class Test Evaluation:
     - Each client_i_test.parquet contains ALL 4 CLASSES (pathtrav, sqli, xss, benign) to measure Unseen-Family Recall!
  3. Zero Lineage Overlap: Train Lineages ∩ Test Lineages = ∅ (Hard SHA256 Cluster Isolation).
"""

import os
import sys
import json
import hashlib
import logging
import numpy as np
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
    logger.info(f"Loaded trainable corpus: {len(df_corpus)} rows")

    # ``other`` is a quarantine class for protocol/PHP/command-injection
    # records whose family is not one of the preregistered four classes.  It
    # must not be silently coerced into a 4-class target index.
    allowed_labels = {"benign", "xss", "sqli", "pathtrav"}
    before_quarantine = len(df_corpus)
    df_corpus = df_corpus[df_corpus["label_multiclass"].isin(allowed_labels)].copy()
    logger.info(
        "Excluded %d quarantined 'other' rows from the 4-class split",
        before_quarantine - len(df_corpus),
    )

    if "dedup_cluster_id" not in df_corpus.columns:
        df_corpus["dedup_cluster_id"] = df_corpus["id"].astype(str)

    # Augmentation can make two different parent seeds produce the same
    # exact payload. Union those parents before assigning a split.
    parent = {str(cid): str(cid) for cid in df_corpus["dedup_cluster_id"].astype(str).unique()}

    def find(cid):
        while parent[cid] != cid:
            parent[cid] = parent[parent[cid]]
            cid = parent[cid]
        return cid

    def union(left, right):
        l_root, r_root = find(left), find(right)
        if l_root != r_root:
            parent[r_root] = l_root

    for _, payload_group in df_corpus.groupby("sanitized_payload", sort=False):
        ids = payload_group["dedup_cluster_id"].astype(str).drop_duplicates().tolist()
        for cid in ids[1:]:
            union(ids[0], cid)
    df_corpus["split_group_id"] = df_corpus["dedup_cluster_id"].astype(str).map(find)

    unique_clusters = df_corpus["split_group_id"].drop_duplicates().tolist()
    logger.info(f"Total split groups after exact-payload union: {len(unique_clusters)}")

    # 1. Freeze Global Test & Validation Clusters FIRST (Dedup Lineage Isolated)
    cluster_df = pd.DataFrame({"split_group_id": unique_clusters})
    cluster_df["_score"] = cluster_df["split_group_id"].map(
        lambda cid: stable_hash_score(cid, seed=seed, namespace="global_holdout")
    )
    cluster_df = cluster_df.sort_values(["_score", "split_group_id"], kind="stable").reset_index(drop=True)

    n_total = len(cluster_df)
    n_test = int(n_total * test_fraction)
    n_val = int(n_total * val_fraction)

    test_cluster_set = set(cluster_df.iloc[:n_test]["split_group_id"])
    val_cluster_set = set(cluster_df.iloc[n_test:n_test + n_val]["split_group_id"])
    train_cluster_set = set(cluster_df.iloc[n_test + n_val:]["split_group_id"])

    # HARD LEAKAGE ASSERTIONS
    assert len(train_cluster_set & test_cluster_set) == 0, "CRITICAL: Train and Test cluster overlap detected!"
    assert len(train_cluster_set & val_cluster_set) == 0, "CRITICAL: Train and Val cluster overlap detected!"
    assert len(val_cluster_set & test_cluster_set) == 0, "CRITICAL: Val and Test cluster overlap detected!"

    df_test_indomain = df_corpus[df_corpus["split_group_id"].isin(test_cluster_set)].copy()
    df_val_global = df_corpus[df_corpus["split_group_id"].isin(val_cluster_set)].copy()
    df_train_pool = df_corpus[df_corpus["split_group_id"].isin(train_cluster_set)].copy()

    df_test_indomain.to_parquet(os.path.join(SPLITS_DIR, "test_indomain.parquet"), index=False)
    df_val_global.to_parquet(os.path.join(SPLITS_DIR, "val_global.parquet"), index=False)

    # Give every target client an independent holdout.  The previous
    # implementation sampled 16.6% from the same global table six times,
    # causing substantial test/test overlap and correlated matrix columns.
    test_client_groups = {client_id: set() for client_id in range(1, 7)}
    for label in sorted(allowed_labels):
        label_groups = df_test_indomain.loc[
            df_test_indomain["label_multiclass"].eq(label), "split_group_id"
        ].drop_duplicates().tolist()
        label_groups = sorted(
            label_groups,
            key=lambda gid: stable_hash_score(gid, seed=seed, namespace=f"test_client:{label}"),
        )
        for idx, group_id in enumerate(label_groups):
            test_client_groups[(idx % 6) + 1].add(group_id)

    # 2. Build Family-Disjoint Client Silos
    # Client Specifications (Matching C:\Users\huynh\Desktop\thailand\project\fedwebpayload)
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
    benign_clusters = benign_pool["split_group_id"].drop_duplicates().tolist()
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
        f_clusters = f_pool["split_group_id"].drop_duplicates().tolist()
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

        # Training clusters for Client c_id: Benign + Designated Attack Family ONLY
        c_train_cluster_set = c_benign_set | c_attack_set

        df_c_train_full = df_train_pool[df_train_pool["split_group_id"].isin(c_train_cluster_set)].copy()

        # Split client pool into 70% Train, 15% Val, and 15% Test
        # Test set contains ALL 4 CLASSES from df_train_pool to measure Unseen-Family Recall!
        c_clusters_sorted = sorted(
            list(c_train_cluster_set),
            key=lambda cid: stable_hash_score(cid, seed=seed, namespace=f"client_{c_id}_subsplit")
        )
        nc = len(c_clusters_sorted)
        nc_val = max(1, int(nc * 0.15))
        nc_test = max(1, int(nc * 0.15))

        c_test_clusters = set(c_clusters_sorted[:nc_test])
        c_val_clusters = set(c_clusters_sorted[nc_test:nc_test + nc_val])
        c_train_clusters = set(c_clusters_sorted[nc_test + nc_val:])

        df_c_train = df_c_train_full[df_c_train_full["split_group_id"].isin(c_train_clusters)].copy()
        df_c_val = df_c_train_full[df_c_train_full["split_group_id"].isin(c_val_clusters)].copy()

        # Build an independent, label-stratified target test set from global
        # held-out groups. No client test group is reused by another client.
        df_c_test = df_test_indomain[
            df_test_indomain["split_group_id"].isin(test_client_groups[c_id])
        ].copy()

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

    train_payloads = set(df_train_pool["sanitized_payload"].astype(str))
    test_payloads = set(df_test_indomain["sanitized_payload"].astype(str))
    exact_payload_overlap = train_payloads & test_payloads
    if exact_payload_overlap:
        raise AssertionError(
            f"CRITICAL: exact sanitized payload overlap train/test: {len(exact_payload_overlap)}"
        )
    for left in range(1, 7):
        for right in range(left + 1, 7):
            if test_client_groups[left] & test_client_groups[right]:
                raise AssertionError("CRITICAL: client test lineage overlap detected")
    manifest["integrity"] = {
        "lineage_overlap": 0,
        "exact_payload_overlap": 0,
        "client_test_lineage_overlap": 0,
        "split_group_column": "split_group_id",
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
        print(f"Client {i} ({c_info['designated_family'].upper():<8}): Train={c_info['train_rows']:<5} | Test={c_info['test_rows']:<4} | Local Train Classes: {list(c_info['train_class_dist'].keys())}")
    print("="*85 + "\n")


if __name__ == "__main__":
    build_family_disjoint_splits(seed=42)
