import os
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
CLIENTS_DIR = os.path.join(PROCESSED_DIR, "clients")
os.makedirs(CLIENTS_DIR, exist_ok=True)

MANIFEST_PATH = os.path.join(PROCESSED_DIR, "sample_manifest.parquet")

OUT_GLOBAL_TEST = os.path.join(PROCESSED_DIR, "pool_b_global_test.parquet")
OUT_GLOBAL_VAL = os.path.join(PROCESSED_DIR, "pool_b_global_val.parquet")

def run_pipeline():
    logger.info("=== STARTING STAGE 1.7: PARTITION POOL B INTO 6 NON-IID CLIENT SILOS & GLOBAL HOLDOUTS ===")
    
    df = pd.read_parquet(MANIFEST_PATH)
    
    # 1. Filter Pool B Confirmed Primary Clusters
    pool_b_mask = (df["pool_id"] == "Pool_B") & (df["is_primary_in_cluster"] == True) & (df["label_status"] == "confirmed")
    pool_b_df = df[pool_b_mask].copy()
    logger.info(f"Total confirmed primary clusters in Pool B: {len(pool_b_df)}")
    
    # 2. Extract Stratified Global Test (15%) and Global Val (15%)
    global_test_cids = []
    global_val_cids = []
    train_reservoir_cids = []
    
    for lbl, group in pool_b_df.groupby("final_label"):
        shuffled = group.sample(frac=1.0, random_state=42)["exact_cluster_id"].values
        n = len(shuffled)
        idx_train = int(n * 0.70)
        idx_val = int(n * 0.85)
        
        train_reservoir_cids.extend(shuffled[:idx_train])
        global_val_cids.extend(shuffled[idx_train:idx_val])
        global_test_cids.extend(shuffled[idx_val:])
        
    global_test_df = pool_b_df[pool_b_df["exact_cluster_id"].isin(global_test_cids)].copy()
    global_val_df = pool_b_df[pool_b_df["exact_cluster_id"].isin(global_val_cids)].copy()
    train_reservoir_df = pool_b_df[pool_b_df["exact_cluster_id"].isin(train_reservoir_cids)].copy()
    
    logger.info(f"Pool B Partitioning -> Train Reservoir: {len(train_reservoir_df)}, Global Val: {len(global_val_df)}, Global Test: {len(global_test_df)}")
    
    # Save Global Holdouts (The Straight Ruler)
    global_test_df.to_parquet(OUT_GLOBAL_TEST, index=False)
    global_val_df.to_parquet(OUT_GLOBAL_VAL, index=False)
    logger.info(f"Saved Global Test ({len(global_test_df)}) to {OUT_GLOBAL_TEST}")
    logger.info(f"Saved Global Val ({len(global_val_df)}) to {OUT_GLOBAL_VAL}")
    
    # 3. Partition Train Reservoir into 6 Non-IID Client Silos (Paired Specialization)
    logger.info("Executing Paired Extreme Non-IID Silo Partitioning...")
    client_records = {f"client_{i}": [] for i in range(1, 7)}
    
    for lbl, group in train_reservoir_df.groupby("final_label"):
        shuffled = group.sample(frac=1.0, random_state=42)
        cids = shuffled.to_dict("records")
        n = len(cids)
        
        if lbl == "xss":
            # 80% to C1/C2 (40% each), 20% to C3-C6 (5% each)
            chunks = [
                cids[:int(n*0.4)], cids[int(n*0.4):int(n*0.8)],
                cids[int(n*0.8):int(n*0.85)], cids[int(n*0.85):int(n*0.9)],
                cids[int(n*0.9):int(n*0.95)], cids[int(n*0.95):]
            ]
        elif lbl == "sqli":
            # 80% to C3/C4 (40% each)
            chunks = [
                cids[:int(n*0.05)], cids[int(n*0.05):int(n*0.1)],
                cids[int(n*0.1):int(n*0.5)], cids[int(n*0.5):int(n*0.9)],
                cids[int(n*0.9):int(n*0.95)], cids[int(n*0.95):]
            ]
        elif lbl == "pathtrav":
            # 80% to C5/C6 (40% each)
            chunks = [
                cids[:int(n*0.05)], cids[int(n*0.05):int(n*0.1)],
                cids[int(n*0.1):int(n*0.15)], cids[int(n*0.15):int(n*0.2)],
                cids[int(n*0.2):int(n*0.6)], cids[int(n*0.6):]
            ]
        else:
            # Benign & Other: Uniform 1/6th
            cs = n // 6
            chunks = [
                cids[0:cs], cids[cs:cs*2], cids[cs*2:cs*3],
                cids[cs*3:cs*4], cids[cs*4:cs*5], cids[cs*5:]
            ]
            
        for i in range(6):
            client_records[f"client_{i+1}"].extend(chunks[i])
            
    # 4. For each Client, split into Local Train (80%), Local Val (10%), Local Test (10%)
    client_summary = []
    
    for client_id, rows in client_records.items():
        c_df = pd.DataFrame(rows)
        
        c_train_list, c_val_list, c_test_list = [], [], []
        for lbl, group in c_df.groupby("final_label"):
            shuffled = group.sample(frac=1.0, random_state=42)
            n_c = len(shuffled)
            i_tr = int(n_c * 0.80)
            i_v = int(n_c * 0.90)
            
            c_train_list.append(shuffled.iloc[:i_tr])
            c_val_list.append(shuffled.iloc[i_tr:i_v])
            c_test_list.append(shuffled.iloc[i_v:])
            
        c_train_df = pd.concat(c_train_list, ignore_index=True)
        c_val_df = pd.concat(c_val_list, ignore_index=True)
        c_test_df = pd.concat(c_test_list, ignore_index=True)
        
        # Save individual client partitions
        c_train_df.to_parquet(os.path.join(CLIENTS_DIR, f"{client_id}_train.parquet"), index=False)
        c_val_df.to_parquet(os.path.join(CLIENTS_DIR, f"{client_id}_val.parquet"), index=False)
        c_test_df.to_parquet(os.path.join(CLIENTS_DIR, f"{client_id}_test.parquet"), index=False)
        
        c_counts = c_df["final_label"].value_counts().to_dict()
        client_summary.append({
            "Client_ID": client_id,
            "Total_Samples": len(c_df),
            "Train_Samples": len(c_train_df),
            "Val_Samples": len(c_val_df),
            "Test_Samples": len(c_test_df),
            "Benign": c_counts.get("benign", 0),
            "XSS": c_counts.get("xss", 0),
            "SQLi": c_counts.get("sqli", 0),
            "PathTrav": c_counts.get("pathtrav", 0)
        })
        
    df_summary = pd.DataFrame(client_summary)
    print("\n" + "="*80)
    print("STAGE 1.7 6-CLIENT NON-IID SILO ALLOCATION SUMMARY")
    print("="*80)
    print(df_summary.to_string(index=False))
    print("="*80 + "\n")
    logger.info("STAGE 1.7 COMPLETE.")

if __name__ == "__main__":
    run_pipeline()
