import os
import sys
import logging
import pandas as pd
import numpy as np
import importlib.util

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
MANIFEST_PATH = os.path.join(PROCESSED_DIR, "sample_manifest.parquet")

OUT_TRAIN = os.path.join(PROCESSED_DIR, "pool_a_train_balanced_40k.parquet")
OUT_VAL = os.path.join(PROCESSED_DIR, "pool_a_val.parquet")
OUT_TEST = os.path.join(PROCESSED_DIR, "pool_a_test.parquet")

# Dynamically import M1-M8 Mutation Engine
try:
    aug_path = os.path.join(os.path.dirname(__file__), "1.5.1_m1_m8_augment.py")
    spec = importlib.util.spec_from_file_location("m1_m8_augment", aug_path)
    m1_m8 = importlib.util.module_from_spec(spec)
    sys.modules["m1_m8_augment"] = m1_m8
    spec.loader.exec_module(m1_m8)
    apply_pathtrav_mutations = m1_m8.apply_pathtrav_mutations
    apply_sqli_mutations = m1_m8.apply_sqli_mutations
    apply_xss_mutations = m1_m8.apply_xss_mutations
except Exception as e:
    logger.error(f"Failed to import 1.5.1_m1_m8_augment: {e}")
    sys.exit(1)

TARGET_PER_CLASS = 10000 # 1:1:1:1 exact balanced pretraining corpus (40,000 samples)

def run_pipeline():
    logger.info("=== STARTING STAGE 1.6: BUILD POOL A BALANCED PRE-TRAINING CORPUS (1:1:1:1) ===")
    
    df = pd.read_parquet(MANIFEST_PATH)
    
    # 1. Filter Pool A Confirmed Primary Clusters
    pool_a_mask = (df["pool_id"] == "Pool_A") & (df["is_primary_in_cluster"] == True) & (df["label_status"] == "confirmed")
    pool_a_df = df[pool_a_mask].copy()
    
    logger.info(f"Total confirmed primary clusters in Pool A: {len(pool_a_df)}")
    
    # 2. Stratified Split Pool A into Train (70%), Val (15%), Test (15%)
    train_cids = []
    val_cids = []
    test_cids = []
    
    for lbl, group in pool_a_df.groupby("final_label"):
        shuffled = group.sample(frac=1.0, random_state=42)["exact_cluster_id"].values
        n = len(shuffled)
        idx_train = int(n * 0.70)
        idx_val = int(n * 0.85)
        
        train_cids.extend(shuffled[:idx_train])
        val_cids.extend(shuffled[idx_train:idx_val])
        test_cids.extend(shuffled[idx_val:])
        
    train_df = pool_a_df[pool_a_df["exact_cluster_id"].isin(train_cids)].copy()
    val_df = pool_a_df[pool_a_df["exact_cluster_id"].isin(val_cids)].copy()
    test_df = pool_a_df[pool_a_df["exact_cluster_id"].isin(test_cids)].copy()
    
    logger.info(f"Pool A raw split -> Train seeds: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # 3. Build Balanced 1:1:1:1 Train Corpus with M1-M8 Augmentation
    logger.info(f"Generating 1:1:1:1 balanced pre-training corpus ({TARGET_PER_CLASS} per class)...")
    balanced_rows = []
    
    for lbl in ["benign", "xss", "sqli", "pathtrav"]:
        class_df = train_df[train_df["final_label"] == lbl]
        seed_count = len(class_df)
        logger.info(f"Class '{lbl}': {seed_count} seed clusters available in Train A.")
        
        if seed_count >= TARGET_PER_CLASS:
            # Subsample down to TARGET_PER_CLASS
            sampled = class_df.sample(n=TARGET_PER_CLASS, random_state=42)
            for row in sampled.itertuples(index=False):
                r = row._asdict()
                r["is_augmented"] = False
                balanced_rows.append(r)
        else:
            # First, keep all original seed rows
            for row in class_df.itertuples(index=False):
                r = row._asdict()
                r["is_augmented"] = False
                balanced_rows.append(r)
                
            needed = TARGET_PER_CLASS - seed_count
            logger.info(f"Class '{lbl}': Expanding {seed_count} seeds by {needed} augmented variants using M1-M8...")
            
            aug_pool = []
            for row in class_df.itertuples(index=False):
                p = str(getattr(row, "sanitized_payload"))
                cid = getattr(row, "exact_cluster_id")
                
                if lbl == "pathtrav":
                    variants = apply_pathtrav_mutations(p)
                elif lbl == "sqli":
                    variants = apply_sqli_mutations(p)
                elif lbl == "xss":
                    variants = apply_xss_mutations(p)
                else:
                    variants = [p]
                    
                for v in variants:
                    if v != p:
                        r = row._asdict()
                        r["sanitized_payload"] = v
                        r["is_augmented"] = True
                        # Lineage constraint: inherits parent exact_cluster_id
                        r["exact_cluster_id"] = cid
                        aug_pool.append(r)
                        
            # Sample exactly what is needed to hit TARGET_PER_CLASS
            if len(aug_pool) >= needed:
                selected_aug = pd.DataFrame(aug_pool).sample(n=needed, random_state=42).to_dict("records")
            else:
                # If still under target, sample with replacement to hit exactly TARGET_PER_CLASS
                selected_aug = pd.DataFrame(aug_pool).sample(n=needed, replace=True, random_state=42).to_dict("records")
                
            balanced_rows.extend(selected_aug)
            
    df_balanced_train = pd.DataFrame(balanced_rows)
    logger.info(f"Balanced Train Corpus created: {len(df_balanced_train)} samples.")
    
    # Tag natural Val and Test sets
    val_df["is_augmented"] = False
    test_df["is_augmented"] = False
    
    # 4. Save Final Datasets
    logger.info(f"Saving balanced train corpus to: {OUT_TRAIN}")
    df_balanced_train.to_parquet(OUT_TRAIN, index=False)
    
    logger.info(f"Saving natural validation set to: {OUT_VAL}")
    val_df.to_parquet(OUT_VAL, index=False)
    
    logger.info(f"Saving natural test set to: {OUT_TEST}")
    test_df.to_parquet(OUT_TEST, index=False)
    
    print("\n" + "="*70)
    print("STAGE 1.6 POOL A PRE-TRAIN BALANCED CORPUS (1:1:1:1)")
    print("="*70)
    print("Train Class Distribution (40,000 samples):")
    print(df_balanced_train["final_label"].value_counts())
    print("\nAugmented Samples Breakdown:")
    print(df_balanced_train.groupby(["final_label", "is_augmented"]).size().unstack(fill_value=0))
    print("="*70 + "\n")
    logger.info("STAGE 1.6 COMPLETE.")

if __name__ == "__main__":
    run_pipeline()
