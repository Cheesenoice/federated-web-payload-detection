import os
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
MANIFEST_PATH = os.path.join(PROCESSED_DIR, "sample_manifest.parquet")

def run_pipeline():
    logger.info("=== STARTING STAGE 1.5: POOL SPLIT (15% POOL A / 85% POOL B / OOD) ===")
    
    if not os.path.exists(MANIFEST_PATH):
        logger.error(f"Manifest not found at {MANIFEST_PATH}")
        return
        
    df = pd.read_parquet(MANIFEST_PATH)
    logger.info(f"Loaded manifest with {len(df)} records.")
    
    primary_df = df[df["is_primary_in_cluster"] == True].copy()
    logger.info(f"Primary unique clusters: {len(primary_df)}")
    
    # 1. Isolate OOD (CSIC 2010 -> SRC_02)
    ood_mask = primary_df["source_id"] == "SRC_02_csic2010"
    ood_cids = set(primary_df[ood_mask]["exact_cluster_id"].unique())
    logger.info(f"OOD CSIC 2010 clusters: {len(ood_cids)}")
    
    # 2. Stratified Split 15% Pool A / 85% Pool B across each class and label_status
    remaining_df = primary_df[~ood_mask]
    
    pool_map = {}
    for cid in ood_cids:
        pool_map[cid] = "OOD"
        
    for (lbl, status), group in remaining_df.groupby(["final_label", "label_status"]):
        # Deterministic shuffle
        cids = group.sample(frac=1.0, random_state=42)["exact_cluster_id"].values
        n = len(cids)
        idx_a = int(n * 0.15) # Exactly 15% Pool A
        
        for cid in cids[:idx_a]:
            pool_map[cid] = "Pool_A"
        for cid in cids[idx_a:]:
            pool_map[cid] = "Pool_B"
            
    df["pool_id"] = df["exact_cluster_id"].map(pool_map).fillna("Unknown")
    
    logger.info(f"Saving updated manifest with pool_id to {MANIFEST_PATH}")
    df.to_parquet(MANIFEST_PATH, index=False)
    
    # Print summary
    primary_updated = df[df["is_primary_in_cluster"] == True]
    print("\n" + "="*70)
    print("STAGE 1.5 POOL SPLIT DISTRIBUTION (PRIMARY CLUSTERS)")
    print("="*70)
    print(pd.crosstab(primary_updated["pool_id"], primary_updated["final_label"], margins=True))
    print("="*70 + "\n")
    logger.info("STAGE 1.5 COMPLETE.")

if __name__ == "__main__":
    run_pipeline()
