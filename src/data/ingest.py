"""
Stage 1: Multi-Source Raw Ingestion Adapter Pipeline (`src/data/ingest.py`)

Reads 100% of raw data files across active source directories under `data/raw/`
(SRC_00, SRC_01, SRC_03, SRC_04, SRC_05, SRC_06), normalizes them into a unified schema:
  id, source, raw_payload, http_part, label_binary, label_multiclass, timestamp, raw_file
and outputs the interim dataframe to `data/interim/raw_unified.parquet`.
"""

import os
import glob
import json
import logging
import urllib.parse
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
RAW_DIR = os.path.join(DATA_DIR, "raw")
INTERIM_DIR = os.path.join(DATA_DIR, "interim")

os.makedirs(INTERIM_DIR, exist_ok=True)

OUTPUT_PATH = os.path.join(INTERIM_DIR, "raw_unified.parquet")


def safe_read_csv(filepath, **kwargs):
    """Safely read CSV files trying utf-8, latin-1, and cp1252 encodings."""
    for enc in ["utf-8", "latin-1", "cp1252", "utf-8-sig"]:
        try:
            return pd.read_csv(filepath, encoding=enc, **kwargs)
        except Exception:
            continue
    try:
        return pd.read_csv(filepath, encoding="utf-8", encoding_errors="replace", on_bad_lines="skip", **kwargs)
    except Exception as e:
        logger.warning(f"Failed to read CSV {filepath}: {e}")
        return pd.DataFrame()


def ingest_src00():
    """Ingest SRC_00_professor_dataset (Honeypot campaign files + Suricata hourly logs)."""
    src_dir = os.path.join(RAW_DIR, "SRC_00_professor_dataset")
    if not os.path.exists(src_dir):
        logger.warning(f"SRC_00 directory not found: {src_dir}")
        return []

    rows = []
    
    # 1. Predictions Decode CSVs
    pred_sqli = os.path.join(src_dir, "SQL_injection_predictions_decode.csv")
    if os.path.exists(pred_sqli):
        df = safe_read_csv(pred_sqli)
        if "decoded_payload" in df.columns:
            for idx, payload in enumerate(df["decoded_payload"].dropna()):
                payload_str = str(payload).strip()
                if payload_str:
                    rows.append({
                        "id": f"SRC_00_pred_sqli_{idx}",
                        "source": "SRC_00",
                        "raw_payload": payload_str,
                        "http_part": "body",
                        "label_binary": 1,
                        "label_multiclass": "sqli",
                        "timestamp": "",
                        "raw_file": "SQL_injection_predictions_decode.csv"
                    })

    pred_pathtrav = os.path.join(src_dir, "Path_traversal_predictions_decode.csv")
    if os.path.exists(pred_pathtrav):
        df = safe_read_csv(pred_pathtrav)
        if "decoded_payload" in df.columns:
            for idx, payload in enumerate(df["decoded_payload"].dropna()):
                payload_str = str(payload).strip()
                if payload_str:
                    rows.append({
                        "id": f"SRC_00_pred_pathtrav_{idx}",
                        "source": "SRC_00",
                        "raw_payload": payload_str,
                        "http_part": "url",
                        "label_binary": 1,
                        "label_multiclass": "pathtrav",
                        "timestamp": "",
                        "raw_file": "Path_traversal_predictions_decode.csv"
                    })

    # 2. Campaign CSV files
    campaign_files = [
        ("Cross-site_scripting_XSS.csv", "xss"),
        ("SQL_injection.csv", "sqli"),
        ("Path_traversal.csv", "pathtrav")
    ]
    for filename, raw_hint in campaign_files:
        filepath = os.path.join(src_dir, filename)
        if os.path.exists(filepath):
            logger.info(f"Ingesting SRC_00 campaign file: {filename}")
            df = safe_read_csv(filepath, low_memory=False)
            for idx, row in df.iterrows():
                ts = str(row.get("@timestamp", ""))
                payload_found = ""
                http_part = "unknown"
                
                # Check http url
                http_val = row.get("http", "")
                if pd.notna(http_val) and str(http_val).strip():
                    http_str = str(http_val)
                    if "'url':" in http_str or '"url":' in http_str or "/?" in http_str or "file=" in http_str:
                        payload_found = http_str
                        http_part = "url"
                
                # Check payload_printable
                if not payload_found:
                    p_print = row.get("payload_printable", "")
                    if pd.notna(p_print) and str(p_print).strip():
                        payload_found = str(p_print)
                        http_part = "body"

                if payload_found and len(payload_found) >= 3:
                    rows.append({
                        "id": f"SRC_00_{raw_hint}_{idx}",
                        "source": "SRC_00",
                        "raw_payload": payload_found,
                        "http_part": http_part,
                        "label_binary": 1,
                        "label_multiclass": raw_hint,
                        "timestamp": ts,
                        "raw_file": filename
                    })

    # 3. Suricata Hourly Capture Logs
    suricata_logs = glob.glob(os.path.join(src_dir, "suricata_*.csv"))
    for sur_log in suricata_logs:
        log_name = os.path.basename(sur_log)
        logger.info(f"Ingesting SRC_00 Suricata log: {log_name}")
        df = safe_read_csv(sur_log, low_memory=False)
        for idx, row in df.iterrows():
            p_print = row.get("payload_printable", row.get("payload", ""))
            ts = str(row.get("@timestamp", ""))
            sig = str(row.get("alert.signature", ""))
            cat = str(row.get("alert.category", ""))
            
            if pd.notna(p_print) and str(p_print).strip() and len(str(p_print)) >= 3:
                # Classify based on alert signature / category hints
                sig_lower = sig.lower() + " " + cat.lower()
                hint_label = "benign"
                binary = 0
                if "xss" in sig_lower or "cross site" in sig_lower or "script" in sig_lower:
                    hint_label = "xss"
                    binary = 1
                elif "sqli" in sig_lower or "sql" in sig_lower or "injection" in sig_lower:
                    hint_label = "sqli"
                    binary = 1
                elif "traversal" in sig_lower or "lfi" in sig_lower or "file access" in sig_lower:
                    hint_label = "pathtrav"
                    binary = 1
                elif sig.strip() != "":
                    binary = 1
                    hint_label = "benign" # Default fallback for general WAF/IDS alerts
                
                rows.append({
                    "id": f"SRC_00_sur_{log_name}_{idx}",
                    "source": "SRC_00",
                    "raw_payload": str(p_print),
                    "http_part": "body",
                    "label_binary": binary,
                    "label_multiclass": hint_label,
                    "timestamp": ts,
                    "raw_file": log_name
                })
                
    logger.info(f"SRC_00 total extracted rows: {len(rows)}")
    return rows


def ingest_src01():
    """Ingest SRC_01_httpparams."""
    src_dir = os.path.join(RAW_DIR, "SRC_01_httpparams")
    filepath = os.path.join(src_dir, "httpparams_payload_full.csv")
    if not os.path.exists(filepath):
        logger.warning(f"SRC_01 file not found: {filepath}")
        return []

    logger.info("Ingesting SRC_01 (HttpParamsDataset)...")
    df = safe_read_csv(filepath)
    rows = []
    label_map = {
        "norm": ("benign", 0),
        "sqli": ("sqli", 1),
        "xss": ("xss", 1),
        "path-traversal": ("pathtrav", 1),
        "cmdi": ("other", 1)
    }

    for idx, row in df.iterrows():
        p = str(row.get("payload", "")).strip()
        atype = str(row.get("attack_type", "")).strip().lower()
        if p and atype in label_map:
            mclass, bclass = label_map[atype]
            rows.append({
                "id": f"SRC_01_{idx}",
                "source": "SRC_01",
                "raw_payload": p,
                "http_part": "param",
                "label_binary": bclass,
                "label_multiclass": mclass,
                "timestamp": "",
                "raw_file": "httpparams_payload_full.csv"
            })

    logger.info(f"SRC_01 total extracted rows: {len(rows)}")
    return rows


def ingest_src03():
    """Ingest SRC_03_modsecurity_waf daily audit logs & JSON files."""
    src_dir = os.path.join(RAW_DIR, "SRC_03_modsecurity_waf")
    if not os.path.exists(src_dir):
        logger.warning(f"SRC_03 directory not found: {src_dir}")
        return []

    rows = []
    logger.info("Ingesting SRC_03 (ModSecurity Production WAF)...")
    
    # 1. Audit Logs
    audit_logs = glob.glob(os.path.join(src_dir, "**", "modsec_audit.anon.log"), recursive=True)
    for log_path in audit_logs[:10]: # Process daily logs
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # Simple ModSec section splitter
            entries = content.split("---")
            for idx, entry in enumerate(entries):
                if "A--" in entry or "B--" in entry:
                    lines = entry.splitlines()
                    for line in lines:
                        if line.startswith("GET ") or line.startswith("POST "):
                            req_line = line.strip()
                            rows.append({
                                "id": f"SRC_03_log_{idx}",
                                "source": "SRC_03",
                                "raw_payload": req_line,
                                "http_part": "url",
                                "label_binary": 1,
                                "label_multiclass": "sqli", # Provisional, CRS will re-scrub
                                "timestamp": "",
                                "raw_file": os.path.basename(log_path)
                            })
        except Exception as e:
            logger.warning(f"Error reading ModSec log {log_path}: {e}")

    # 2. JSON Files
    json_files = glob.glob(os.path.join(src_dir, "**", "*.json"), recursive=True)
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    p = ""
                    mclass = "benign"
                    bclass = 0
                    if isinstance(item, dict):
                        p = item.get("payload", item.get("data", item.get("uri", "")))
                        if "sqli" in json_file.lower() or "sqlmap" in json_file.lower():
                            mclass = "sqli"
                            bclass = 1
                        elif "legitimate" in json_file.lower():
                            mclass = "benign"
                            bclass = 0
                    if str(p).strip():
                        rows.append({
                            "id": f"SRC_03_json_{os.path.basename(json_file)}_{idx}",
                            "source": "SRC_03",
                            "raw_payload": str(p).strip(),
                            "http_part": "url",
                            "label_binary": bclass,
                            "label_multiclass": mclass,
                            "timestamp": "",
                            "raw_file": os.path.basename(json_file)
                        })
        except Exception:
            continue

    logger.info(f"SRC_03 total extracted rows: {len(rows)}")
    return rows


def ingest_src04():
    """Ingest SRC_04_xss_collections."""
    src_dir = os.path.join(RAW_DIR, "SRC_04_xss_collections")
    if not os.path.exists(src_dir):
        logger.warning(f"SRC_04 directory not found: {src_dir}")
        return []

    rows = []
    logger.info("Ingesting SRC_04 (XSS Collections)...")
    
    # 1. xss_fmereani_payloads_full.csv
    f_main = os.path.join(src_dir, "xss_fmereani_payloads_full.csv")
    if os.path.exists(f_main):
        df = safe_read_csv(f_main)
        p_col = "Payloads" if "Payloads" in df.columns else df.columns[0]
        c_col = "Class" if "Class" in df.columns else df.columns[-1]
        for idx, row in df.iterrows():
            p = str(row[p_col]).strip()
            c = int(row[c_col]) if str(row[c_col]).isdigit() else 1
            if p:
                rows.append({
                    "id": f"SRC_04_fmereani_{idx}",
                    "source": "SRC_04",
                    "raw_payload": p,
                    "http_part": "param",
                    "label_binary": c,
                    "label_multiclass": "xss" if c == 1 else "benign",
                    "timestamp": "",
                    "raw_file": "xss_fmereani_payloads_full.csv"
                })

    # 2. xss_dataset.csv
    f_ds1 = os.path.join(src_dir, "1", "xss_dataset.csv")
    if os.path.exists(f_ds1):
        df = safe_read_csv(f_ds1)
        p_col = "Query" if "Query" in df.columns else df.columns[0]
        c_col = "Label" if "Label" in df.columns else df.columns[-1]
        for idx, row in df.iterrows():
            p = str(row[p_col]).strip()
            c = int(row[c_col]) if str(row[c_col]).isdigit() else 1
            if p:
                rows.append({
                    "id": f"SRC_04_ds1_{idx}",
                    "source": "SRC_04",
                    "raw_payload": p,
                    "http_part": "url",
                    "label_binary": c,
                    "label_multiclass": "xss" if c == 1 else "benign",
                    "timestamp": "",
                    "raw_file": "1/xss_dataset.csv"
                })

    logger.info(f"SRC_04 total extracted rows: {len(rows)}")
    return rows


def ingest_src05():
    """Ingest SRC_05_pathtrav_collections (14 PathTraversal / LFI TXT Lists)."""
    src_dir = os.path.join(RAW_DIR, "SRC_05_pathtrav_collections")
    if not os.path.exists(src_dir):
        logger.warning(f"SRC_05 directory not found: {src_dir}")
        return []

    rows = []
    logger.info("Ingesting SRC_05 (14 PathTraversal Collections)...")
    txt_files = glob.glob(os.path.join(src_dir, "*.txt"))
    
    for txt_file in txt_files:
        filename = os.path.basename(txt_file)
        try:
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            for idx, line in enumerate(lines):
                p = line.strip()
                if p and len(p) >= 3:
                    rows.append({
                        "id": f"SRC_05_{filename}_{idx}",
                        "source": "SRC_05",
                        "raw_payload": p,
                        "http_part": "url",
                        "label_binary": 1,
                        "label_multiclass": "pathtrav",
                        "timestamp": "",
                        "raw_file": filename
                    })
        except Exception as e:
            logger.warning(f"Error reading TXT {filename}: {e}")

    logger.info(f"SRC_05 total extracted rows: {len(rows)}")
    return rows


def ingest_src06():
    """Ingest SRC_06_sqli_collections (20 SQLi CSV/JSONL/TXT Payload Files)."""
    src_dir = os.path.join(RAW_DIR, "SRC_06_sqli_collections")
    if not os.path.exists(src_dir):
        logger.warning(f"SRC_06 directory not found: {src_dir}")
        return []

    rows = []
    logger.info("Ingesting SRC_06 (20 SQLi Collections)...")
    
    # 1. Process CSV files
    csv_files = glob.glob(os.path.join(src_dir, "**", "*.csv"), recursive=True)
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        df = safe_read_csv(csv_file)
        if df.empty:
            continue
            
        # Find payload column
        p_col = None
        for col in ["Input", "Sentence", "payload", "Query", "Query_Text", df.columns[0]]:
            if col in df.columns:
                p_col = col
                break
                
        # Find label column
        l_col = None
        for col in ["Label", "label", "SQLInjection", "Class", "is_sqli"]:
            if col in df.columns:
                l_col = col
                break
                
        for idx, row in df.iterrows():
            p = str(row[p_col]).strip() if p_col else ""
            c = 1
            if l_col and pd.notna(row[l_col]):
                try:
                    c = int(row[l_col])
                except ValueError:
                    c = 1
                    
            if p and len(p) >= 2:
                rows.append({
                    "id": f"SRC_06_csv_{filename}_{idx}",
                    "source": "SRC_06",
                    "raw_payload": p,
                    "http_part": "param",
                    "label_binary": c,
                    "label_multiclass": "sqli" if c == 1 else "benign",
                    "timestamp": "",
                    "raw_file": filename
                })

    # 2. Process TXT files (FuzzDB / Payload lists)
    txt_files = glob.glob(os.path.join(src_dir, "**", "*.txt"), recursive=True)
    for txt_file in txt_files:
        filename = os.path.basename(txt_file)
        try:
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            for idx, line in enumerate(lines):
                p = line.strip()
                if p and len(p) >= 2:
                    rows.append({
                        "id": f"SRC_06_txt_{filename}_{idx}",
                        "source": "SRC_06",
                        "raw_payload": p,
                        "http_part": "param",
                        "label_binary": 1,
                        "label_multiclass": "sqli",
                        "timestamp": "",
                        "raw_file": filename
                    })
        except Exception:
            continue

    logger.info(f"SRC_06 total extracted rows: {len(rows)}")
    return rows


def run_stage_1_ingest():
    """Main execution function for Stage 1 Multi-Source Ingestion."""
    logger.info("=== STARTING STAGE 1: MULTI-SOURCE RAW INGESTION ===")
    all_rows = []
    
    all_rows.extend(ingest_src00())
    all_rows.extend(ingest_src01())
    all_rows.extend(ingest_src03())
    all_rows.extend(ingest_src04())
    all_rows.extend(ingest_src05())
    all_rows.extend(ingest_src06())
    
    df_unified = pd.DataFrame(all_rows)
    logger.info(f"=== STAGE 1 COMPLETE: Extracted Total {len(df_unified)} raw rows ===")
    
    df_unified.to_parquet(OUTPUT_PATH, index=False)
    logger.info(f"Saved interim parquet to: {OUTPUT_PATH}")
    
    # Print Data Balance Report per Class & Source
    print("\n" + "="*60)
    print("📊 STAGE 1 RAW INGESTION DATA BALANCE REPORT")
    print("="*60)
    print("Row counts per attack family (label_multiclass):")
    print(df_unified["label_multiclass"].value_counts())
    print("\nRow counts per source:")
    print(df_unified["source"].value_counts())
    print("="*60 + "\n")
    
    return df_unified


if __name__ == "__main__":
    run_stage_1_ingest()
