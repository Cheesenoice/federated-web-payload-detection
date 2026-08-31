import os
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

MANIFEST_PATH = os.path.join(PROCESSED_DIR, "sample_manifest.parquet")
ACCOUNTING_PATH = os.path.join(PROCESSED_DIR, "data_accounting.csv")
SOURCE_ACCOUNTING_PATH = os.path.join(PROCESSED_DIR, "source_label_accounting.csv")

def get_stats_row(sub_df, stage_name):
    total = len(sub_df)
    if total == 0:
        return {
            "Stage": stage_name, "Total_Count": 0,
            "Orig_Benign": 0, "Orig_XSS": 0, "Orig_SQLi": 0, "Orig_PathTrav": 0, "Orig_Other": 0,
            "Final_Benign": 0, "Final_XSS": 0, "Final_SQLi": 0, "Final_PathTrav": 0, "Final_Other": 0,
            "Confirmed": 0, "Ambiguous": 0, "Rejected": 0
        }
        
    orig_counts = sub_df["original_source_label"].value_counts().to_dict() if "original_source_label" in sub_df.columns else {}
    final_counts = sub_df["final_label"].value_counts().to_dict() if "final_label" in sub_df.columns else {}
    status_counts = sub_df["label_status"].value_counts().to_dict() if "label_status" in sub_df.columns else {}
    
    return {
        "Stage": stage_name,
        "Total_Count": total,
        "Orig_Benign": orig_counts.get("benign", 0),
        "Orig_XSS": orig_counts.get("xss", 0),
        "Orig_SQLi": orig_counts.get("sqli", 0),
        "Orig_PathTrav": orig_counts.get("pathtrav", 0),
        "Orig_Other": orig_counts.get("other", 0),
        "Final_Benign": final_counts.get("benign", 0),
        "Final_XSS": final_counts.get("xss", 0),
        "Final_SQLi": final_counts.get("sqli", 0),
        "Final_PathTrav": final_counts.get("pathtrav", 0),
        "Final_Other": final_counts.get("other", 0),
        "Confirmed": status_counts.get("confirmed", 0),
        "Ambiguous": status_counts.get("ambiguous", 0),
        "Rejected": status_counts.get("rejected", 0)
    }

def run_pipeline():
    logger.info("=== STARTING STAGE 1.4: COMPREHENSIVE DATA ACCOUNTING & SOURCE STATS ===")
    
    if not os.path.exists(MANIFEST_PATH):
        logger.error(f"Audited manifest not found at: {MANIFEST_PATH}")
        return
        
    df = pd.read_parquet(MANIFEST_PATH)
    logger.info(f"Loaded {len(df)} total records.")
    
    primary_df = df[df["is_primary_in_cluster"] == True]
    confirmed_df = df[df["label_status"] == "confirmed"]
    
    # -------------------------------------------------------------
    # 1. OVERALL DATA ACCOUNTING FUNNEL
    # -------------------------------------------------------------
    report = []
    report.append(get_stats_row(df, "1. Raw records collected"))
    report.append(get_stats_row(df, "2. Text payloads extracted"))
    report.append(get_stats_row(df, "3. Payloads decoded (3-pass unquote)"))
    report.append(get_stats_row(df, "4. Payloads sanitized (Masked IPs, Tokens, UUIDs)"))
    report.append(get_stats_row(primary_df, "5. Exact unique payloads (Primary Clusters)"))
    report.append(get_stats_row(confirmed_df, "6. High-confidence OWASP consensus confirmed (All Rows)"))
    report.append(get_stats_row(primary_df[primary_df["label_status"] == "confirmed"], "7. High-confidence OWASP consensus confirmed (Unique Clusters)"))
    
    accounting_df = pd.DataFrame(report)
    accounting_df.to_csv(ACCOUNTING_PATH, index=False)
    logger.info(f"Saved global accounting report to: {ACCOUNTING_PATH}")
    
    # -------------------------------------------------------------
    # 2. PER-SOURCE LABEL ACCOUNTING MATRIX
    # -------------------------------------------------------------
    source_stats = []
    all_sources = sorted(df["source_id"].unique().tolist())
    
    for src in all_sources:
        src_df = df[df["source_id"] == src]
        src_primary = src_df[src_df["is_primary_in_cluster"] == True]
        
        orig_counts = src_df["original_source_label"].value_counts().to_dict()
        owasp_counts = src_df["OWASP_label"].value_counts().to_dict()
        final_counts = src_df["final_label"].value_counts().to_dict()
        status_counts = src_df["label_status"].value_counts().to_dict()
        
        total_raw = len(src_df)
        total_clusters = len(src_primary)
        confirmed_count = status_counts.get("confirmed", 0)
        ambiguous_count = status_counts.get("ambiguous", 0)
        rejected_count = status_counts.get("rejected", 0)
        
        agreement_rate = round((confirmed_count / total_raw * 100), 2) if total_raw > 0 else 0.0
        
        source_stats.append({
            "Source_ID": src,
            "Total_Raw_Records": total_raw,
            "Unique_Clusters": total_clusters,
            "Orig_Benign": orig_counts.get("benign", 0),
            "Orig_XSS": orig_counts.get("xss", 0),
            "Orig_SQLi": orig_counts.get("sqli", 0),
            "Orig_PathTrav": orig_counts.get("pathtrav", 0),
            "Orig_Other": orig_counts.get("other", 0),
            "OWASP_Benign": owasp_counts.get("benign", 0),
            "OWASP_XSS": owasp_counts.get("xss", 0),
            "OWASP_SQLi": owasp_counts.get("sqli", 0),
            "OWASP_PathTrav": owasp_counts.get("pathtrav", 0),
            "Confirmed_Benign": sum((src_df["final_label"] == "benign") & (src_df["label_status"] == "confirmed")),
            "Confirmed_XSS": sum((src_df["final_label"] == "xss") & (src_df["label_status"] == "confirmed")),
            "Confirmed_SQLi": sum((src_df["final_label"] == "sqli") & (src_df["label_status"] == "confirmed")),
            "Confirmed_PathTrav": sum((src_df["final_label"] == "pathtrav") & (src_df["label_status"] == "confirmed")),
            "Ambiguous_Count": ambiguous_count,
            "Rejected_Count": rejected_count,
            "Consensus_Rate_%": agreement_rate
        })
        
    src_df_out = pd.DataFrame(source_stats)
    src_df_out.to_csv(SOURCE_ACCOUNTING_PATH, index=False)
    logger.info(f"Saved per-source accounting matrix to: {SOURCE_ACCOUNTING_PATH}")
    
    print("\n" + "="*140)
    print("STAGE 1 SUMMARY: PER-SOURCE LABEL ACCOUNTING & CONSENSUS MATRIX")
    print("="*140)
    print(src_df_out.to_string(index=False))
    print("="*140 + "\n")
    
    print("\n" + "="*140)
    print("STAGE 1 OVERALL ACCOUNTING FUNNEL (UP TO CONSENSUS AUDIT)")
    print("="*140)
    print(accounting_df.to_string(index=False))
    print("="*140 + "\n")

if __name__ == "__main__":
    run_pipeline()
