import os
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
INTERIM_DIR = os.path.join(DATA_DIR, "interim")

INPUT_PATH = os.path.join(INTERIM_DIR, "manifest_stage1.parquet")
OUTPUT_PATH = os.path.join(INTERIM_DIR, "manifest_stage2.parquet")

def run_pipeline():
    logger.info("=== STARTING STAGE 2: GLOBAL EXACT DEDUPLICATION ===")
    
    if not os.path.exists(INPUT_PATH):
        logger.error(f"Input file not found: {INPUT_PATH}")
        return
        
    df = pd.read_parquet(INPUT_PATH)
    logger.info(f"Loaded {len(df)} records from stage 1.")
    
    # EXACT DEDUPLICATION (Step 9 requirement)
    # We assign an exact_cluster_id based on the sanitized_hash.
    # All raw payloads that sanitize to the same string will share this cluster ID.
    logger.info("Assigning exact_cluster_id based on sanitized_hash...")
    
    # Map each unique sanitized_hash to a unique cluster ID
    unique_hashes = df["sanitized_hash"].unique()
    hash_to_cluster = {h: f"EXACT_CLUST_{i:07d}" for i, h in enumerate(unique_hashes)}
    
    df["exact_cluster_id"] = df["sanitized_hash"].map(hash_to_cluster)
    
    logger.info(f"Found {len(unique_hashes)} unique exact clusters out of {len(df)} records.")
    
    # We will keep ALL records in the manifest (for accounting), but we will flag them
    # as 'is_duplicate' if they are not the primary representative of their cluster.
    # The first one seen will be the primary.
    df["is_primary_in_cluster"] = ~df.duplicated(subset=["exact_cluster_id"], keep="first")
    
    primary_count = df["is_primary_in_cluster"].sum()
    duplicate_count = len(df) - primary_count
    logger.info(f"Primary records: {primary_count}, Duplicates: {duplicate_count}")
    
    logger.info(f"Saving manifest with deduplication tracking to {OUTPUT_PATH}")
    df.to_parquet(OUTPUT_PATH, index=False)

if __name__ == "__main__":
    run_pipeline()
