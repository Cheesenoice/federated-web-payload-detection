import os
import logging
import pandas as pd
import numpy as np
import importlib.util
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
INTERIM_DIR = os.path.join(DATA_DIR, "interim")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

INPUT_PATH = os.path.join(INTERIM_DIR, "manifest_stage2.parquet")
OUTPUT_PATH = os.path.join(PROCESSED_DIR, "sample_manifest.parquet")

# Dynamically import OWASP Regex Signatures
try:
    sig_path = os.path.join(os.path.dirname(__file__), "1.3.1_label_signatures.py")
    spec = importlib.util.spec_from_file_location("label_signatures", sig_path)
    label_signatures = importlib.util.module_from_spec(spec)
    sys.modules["label_signatures"] = label_signatures
    spec.loader.exec_module(label_signatures)
    verify_payload_label = label_signatures.verify_payload_label
except Exception as e:
    logger.warning(f"Could not import label_signatures: {e}. Using fallback labeling.")
    def verify_payload_label(payload, current_label, source=""):
        return current_label, 1 if current_label != "benign" else 0

def run_pipeline():
    logger.info("=== STARTING STAGE 1.3: OWASP CONSENSUS & LABEL AUDIT ===")
    
    if not os.path.exists(INPUT_PATH):
        logger.error(f"Input file not found: {INPUT_PATH}")
        return
        
    df = pd.read_parquet(INPUT_PATH)
    logger.info(f"Loaded {len(df)} total records from Stage 1.2.")
    
    # 1. Isolate primary unique clusters for fast verification
    primary_df = df[df["is_primary_in_cluster"] == True].copy()
    logger.info(f"Auditing {len(primary_df)} unique primary clusters against OWASP CRS v4...")
    
    # Fast C-level zip iteration over unique payloads
    owasp_labels = []
    for p, lbl in zip(primary_df["sanitized_payload"], primary_df["original_source_label"]):
        v_mclass, _ = verify_payload_label(str(p), str(lbl))
        owasp_labels.append(v_mclass)
        
    primary_df["OWASP_label"] = owasp_labels
    
    # Determine Consensus Status
    # - confirmed: Original label strictly matches OWASP detection
    # - ambiguous: Disagreement between source annotation and OWASP
    # - rejected: Multi-match attack signature conflict
    conditions = [
        (primary_df["OWASP_label"] == "other") & (primary_df["original_source_label"] != "other"),
        (primary_df["original_source_label"] == primary_df["OWASP_label"]),
        (primary_df["original_source_label"] != primary_df["OWASP_label"])
    ]
    choices = ["rejected", "confirmed", "ambiguous"]
    
    primary_df["label_status"] = np.select(conditions, choices, default="ambiguous")
    primary_df["final_label"] = primary_df["OWASP_label"]
    
    # SPECIAL RULE FOR CSIC 2010 (SRC_02):
    # CSIC 2010 only provides 'normal' (benign) and 'anomalous' (ingested as 'other').
    # If OWASP detects a specific attack pattern (xss, sqli, pathtrav) in an 'anomalous' request,
    # we promote it to 'confirmed'.
    csic_anomalous_mask = (primary_df["source_id"] == "SRC_02_csic2010") & (primary_df["original_source_label"] == "other")
    mapped_mask = csic_anomalous_mask & (primary_df["OWASP_label"].isin(["xss", "sqli", "pathtrav"]))
    primary_df.loc[mapped_mask, "label_status"] = "confirmed"
    
    logger.info("Broadcasting audited labels back to all 5.3M records in manifest...")
    cluster_to_owasp = dict(zip(primary_df["exact_cluster_id"], primary_df["OWASP_label"]))
    cluster_to_status = dict(zip(primary_df["exact_cluster_id"], primary_df["label_status"]))
    cluster_to_final = dict(zip(primary_df["exact_cluster_id"], primary_df["final_label"]))
    
    df["OWASP_label"] = df["exact_cluster_id"].map(cluster_to_owasp)
    df["label_status"] = df["exact_cluster_id"].map(cluster_to_status)
    df["final_label"] = df["exact_cluster_id"].map(cluster_to_final)
    
    logger.info(f"Saving audited manifest to {OUTPUT_PATH}")
    manifest_cols = [
        "sample_id", "source_id", "source_record_id", "raw_hash", "sanitized_hash", 
        "exact_cluster_id", "is_primary_in_cluster", "original_source_label", "OWASP_label", 
        "final_label", "label_status", "raw_payload", "sanitized_payload"
    ]
    df[manifest_cols].to_parquet(OUTPUT_PATH, index=False)
    logger.info("STAGE 1.3 COMPLETE (Audited manifest ready. Halting before pool splitting).")

if __name__ == "__main__":
    run_pipeline()
