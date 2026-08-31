import os
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
SRC_CLIENTS_DIR = os.path.join(PROCESSED_DIR, "clients")
TGT_CLIENTS_DIR = os.path.join(PROCESSED_DIR, "clients_rep_60k")

os.makedirs(TGT_CLIENTS_DIR, exist_ok=True)

TARGET_TRAIN_SAMPLES_PER_CLIENT = 10000
TARGET_VAL_SAMPLES_PER_CLIENT = 2000
RANDOM_SEED = 42

def stratified_sample(df, target_n, label_col="final_label"):
    """Accurately draws a stratified sample of target_n rows preserving label distribution."""
    if len(df) <= target_n:
        return df.copy()
        
    sampled_dfs = []
    classes = df[label_col].value_counts()
    
    for cls, count in classes.items():
        prop = count / len(df)
        n_cls = int(round(prop * target_n))
        n_cls = max(1, min(n_cls, count))
        cls_df = df[df[label_col] == cls].sample(n_cls, random_state=RANDOM_SEED)
        sampled_dfs.append(cls_df)
        
    res = pd.concat(sampled_dfs, ignore_index=True)
    if len(res) > target_n:
        res = res.sample(target_n, random_state=RANDOM_SEED).reset_index(drop=True)
    elif len(res) < target_n:
        diff = target_n - len(res)
        remaining = df[~df["sample_id"].isin(res["sample_id"])]
        if len(remaining) > 0:
            extra = remaining.sample(min(diff, len(remaining)), random_state=RANDOM_SEED)
            res = pd.concat([res, extra], ignore_index=True)
            
    return res.sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)

def build_rep_silos():
    logger.info("=== STARTING 4.0: BUILD REPRESENTATIVE NON-IID CLIENT SILOS (60,000 SAMPLES) ===")
    
    total_train = 0
    total_val = 0
    
    for i in range(1, 7):
        cid = f"client_{i}"
        train_src = os.path.join(SRC_CLIENTS_DIR, f"{cid}_train.parquet")
        val_src = os.path.join(SRC_CLIENTS_DIR, f"{cid}_val.parquet")
        test_src = os.path.join(SRC_CLIENTS_DIR, f"{cid}_test.parquet")
        
        train_tgt = os.path.join(TGT_CLIENTS_DIR, f"{cid}_train.parquet")
        val_tgt = os.path.join(TGT_CLIENTS_DIR, f"{cid}_val.parquet")
        test_tgt = os.path.join(TGT_CLIENTS_DIR, f"{cid}_test.parquet")
        
        # 1. Stratified Sample for Training Set
        df_train = pd.read_parquet(train_src)
        df_rep_train = stratified_sample(df_train, TARGET_TRAIN_SAMPLES_PER_CLIENT)
        df_rep_train.to_parquet(train_tgt, index=False)
        total_train += len(df_rep_train)
        
        # 2. Stratified Sample for Validation Set
        df_val = pd.read_parquet(val_src)
        df_rep_val = stratified_sample(df_val, TARGET_VAL_SAMPLES_PER_CLIENT)
        df_rep_val.to_parquet(val_tgt, index=False)
        total_val += len(df_rep_val)
        
        # 3. Copy Local Test Set
        df_test = pd.read_parquet(test_src)
        df_test.to_parquet(test_tgt, index=False)
        
        counts_train = df_rep_train["final_label"].value_counts().to_dict()
        logger.info(f"[{cid.upper()}] Train: {len(df_rep_train):,} samples {counts_train} | Val: {len(df_rep_val):,} samples")
        
    logger.info(f"\nSuccessfully generated 60k Non-IID Representative Silos:")
    logger.info(f"Total Train Samples: {total_train:,} | Total Val Samples: {total_val:,}")
    logger.info(f"Saved to: {TGT_CLIENTS_DIR}")

if __name__ == "__main__":
    build_rep_silos()
