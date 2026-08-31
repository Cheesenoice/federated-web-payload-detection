import os
import glob
import json
import logging
import hashlib
import re
import html
import unicodedata
import urllib.parse
import pandas as pd
import numpy as np
import uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
RAW_DIR = os.path.join(DATA_DIR, "raw")
INTERIM_DIR = os.path.join(DATA_DIR, "interim")
os.makedirs(INTERIM_DIR, exist_ok=True)

OUTPUT_PATH = os.path.join(INTERIM_DIR, "manifest_stage1.parquet")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

REGEX_PATTERNS = [
    (re.compile(r"(?i)(phpsessid|jsessionid|sessionid|sess_id|token)=([a-z0-9\-_]+)", re.I), r"\1=MASKED_SESS_TOKEN"),
    (re.compile(r"(?i)\b(bearer\s+[a-z0-9\-\._~\+\/]+=*)", re.I), "bearer MASKED_AUTH_TOKEN"),
    (re.compile(r"\b(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3})\b"), "MASKED_INTERNAL_IP"),
    (re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", re.I), "MASKED_UUID"),
]

def decode_payload(text: str) -> str:
    if not isinstance(text, str) or not text.strip(): return ""
    cur = text.strip()
    for _ in range(3):
        decoded = urllib.parse.unquote(cur)
        if decoded == cur: break
        cur = decoded
    return unicodedata.normalize("NFKC", html.unescape(cur))

def sanitize_payload(text: str) -> str:
    if not text: return ""
    cur = text
    for pattern, repl in REGEX_PATTERNS: cur = pattern.sub(repl, cur)
    return cur

def compute_sha256(text: str) -> str:
    if not text: return ""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

def safe_read_csv(filepath, **kwargs):
    try: return pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip", **kwargs)
    except UnicodeDecodeError:
        try: return pd.read_csv(filepath, encoding="latin1", on_bad_lines="skip", **kwargs)
        except: return pd.DataFrame()
    except Exception: return pd.DataFrame()

# ==========================================
# VECTORIZED EXTRACTION ADAPTERS (C-LEVEL SPEED)
# ==========================================

def process_src00(filepath):
    df = safe_read_csv(filepath, low_memory=False)
    if df.empty: return pd.DataFrame()
    
    p_print = df.get("payload_printable", df.get("payload", pd.Series([""]*len(df)))).fillna("").astype(str).str.strip()
    http_val = df.get("http", pd.Series([""]*len(df))).fillna("").astype(str).str.strip()
    
    raw_p = np.where(http_val.str.len() > 2, http_val, p_print)
    
    lbl_col = df.get("alert.signature", df.get("alert.category", pd.Series(["other"]*len(df)))).fillna("other").astype(str).str.lower()
    
    hint = np.where(lbl_col.str.contains("xss"), "xss",
           np.where(lbl_col.str.contains("sql"), "sqli",
           np.where(lbl_col.str.contains("traversal|lfi"), "pathtrav", "other")))
           
    valid_mask = pd.Series(raw_p).str.len() > 2
    return pd.DataFrame({"raw_payload": raw_p[valid_mask], "original_source_label": hint[valid_mask]})

def process_src01(filepath):
    df = safe_read_csv(filepath, low_memory=False)
    if df.empty or "payload" not in df.columns: return pd.DataFrame()
    
    p = df["payload"].fillna("").astype(str).str.strip()
    atype = df.get("attack_type", pd.Series([""]*len(df))).fillna("").astype(str).str.lower().str.strip()
    
    label_map = {"norm": "benign", "sqli": "sqli", "xss": "xss", "path-traversal": "pathtrav"}
    hint = atype.map(label_map).fillna("other")
    
    valid_mask = (p.str.len() > 0) & (hint != "other")
    return pd.DataFrame({"raw_payload": p[valid_mask], "original_source_label": hint[valid_mask]})

def process_src02(filepath):
    extracted = []
    lbl = "benign" if "normal" in filepath.lower() else "other"
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("GET ") or line.startswith("POST ") or line.startswith("PUT "):
                    extracted.append(line.strip())
    except: pass
    return pd.DataFrame({"raw_payload": extracted, "original_source_label": lbl})

def process_src03(filepath):
    extracted = []
    labels = []
    if filepath.endswith(".log"):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f: content = f.read()
            entries = re.split(r"(?=--[0-9A-Za-z]+-A--)", content)
            for entry in entries:
                entry_lower = entry.lower()
                hint = "other"
                if any(t in entry_lower for t in ["930", "web_attack/file_injection", "path traversal", "lfi"]): hint = "pathtrav"
                elif any(t in entry_lower for t in ["941", "web_attack/xss", "cross-site scripting"]): hint = "xss"
                elif any(t in entry_lower for t in ["942", "web_attack/sqli", "sql injection"]): hint = "sqli"
                for line in entry.splitlines():
                    if line.startswith("GET ") or line.startswith("POST "):
                        extracted.append(line.strip())
                        labels.append(hint)
        except: pass
    elif filepath.endswith(".json"):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f: data = json.load(f)
            if isinstance(data, list):
                lbl = "sqli" if "sqli" in filepath.lower() else "benign" if "legitimate" in filepath.lower() else "other"
                for item in data:
                    if isinstance(item, dict):
                        p = item.get("payload", item.get("data", item.get("uri", "")))
                        if p:
                            extracted.append(str(p).strip())
                            labels.append(lbl)
        except: pass
    return pd.DataFrame({"raw_payload": extracted, "original_source_label": labels})

def process_src04(filepath):
    df = safe_read_csv(filepath, low_memory=False)
    if df.empty: return pd.DataFrame()
    p_col = "Payloads" if "Payloads" in df.columns else "Query" if "Query" in df.columns else df.columns[0]
    c_col = "Class" if "Class" in df.columns else "Label" if "Label" in df.columns else df.columns[-1]
    
    p = df[p_col].fillna("").astype(str).str.strip()
    c = df[c_col].fillna("").astype(str).str.strip()
    hint = np.where(c.isin(["1", "1.0", "attack"]), "xss", "benign")
    
    valid_mask = p.str.len() > 0
    return pd.DataFrame({"raw_payload": p[valid_mask], "original_source_label": hint[valid_mask]})

def process_src05(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f if l.strip()]
        return pd.DataFrame({"raw_payload": lines, "original_source_label": "pathtrav"})
    except: return pd.DataFrame()

def process_src06(filepath):
    fn = os.path.basename(filepath).lower()
    lbl_fallback = "benign" if "norm" in fn or "good" in fn else "sqli" if "sql" in fn else "other"
    if filepath.endswith(".txt"):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = [l.strip() for l in f if len(l.strip()) > 2]
            return pd.DataFrame({"raw_payload": lines, "original_source_label": lbl_fallback})
        except: return pd.DataFrame()
    elif filepath.endswith(".csv"):
        df = safe_read_csv(filepath, low_memory=False)
        if df.empty: return pd.DataFrame()
        for col in ["Input", "Sentence", "payload", "Query", "Payload", "request"]:
            if col in df.columns:
                p = df[col].fillna("").astype(str).str.strip()
                valid_mask = p.str.len() > 2
                return pd.DataFrame({"raw_payload": p[valid_mask], "original_source_label": lbl_fallback})
    return pd.DataFrame()

def process_src07(filepath):
    parts = filepath.split(os.sep)
    lbl = "other"
    for expected in ["benign", "pathtrav", "sqli", "xss"]:
        if expected in parts: lbl = expected
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f if len(l.strip()) > 1]
        return pd.DataFrame({"raw_payload": lines, "original_source_label": lbl})
    except: return pd.DataFrame()

# ==========================================
# MASTER RUNNER
# ==========================================

def run_pipeline():
    logger.info("=== STARTING STAGE 1.1: BLAZING FAST VECTORIZED INGESTION ===")
    all_dfs = []
    
    tasks = [
        ("SRC_00_professor_dataset", "*.csv", process_src00),
        ("SRC_01_httpparams", "*.csv", process_src01),
        ("SRC_02_csic2010", "*.txt", process_src02),
        ("SRC_03_modsecurity_waf", "*.*", process_src03),
        ("SRC_04_xss_collections", "*.csv", process_src04),
        ("SRC_05_pathtrav_collections", "*.txt", process_src05),
        ("SRC_06_sqli_collections", "*.*", process_src06),
        ("SRC_07_extended_diverse_payloads", "*.txt", process_src07)
    ]
    
    for src_id, glob_p, func in tasks:
        logger.info(f"Extracting {src_id}...")
        files = glob.glob(os.path.join(RAW_DIR, src_id, "**", glob_p), recursive=True)
        for fp in files:
            if "extracted" in fp.lower(): continue
            try:
                df_ext = func(fp)
                if not df_ext.empty:
                    df_ext["source_id"] = src_id
                    df_ext["raw_file"] = os.path.basename(fp)
                    all_dfs.append(df_ext)
            except Exception as ex:
                logger.warning(f"Error on {fp}: {ex}")
                
    if not all_dfs:
        logger.error("NO DATA EXTRACTED! Check your data/raw folder.")
        return
        
    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df["source_record_id"] = master_df["raw_file"] + "_" + master_df.index.astype(str)
    
    logger.info(f"Total extracted records: {len(master_df)}")
    
    logger.info("Decoding payloads (Vectorized Apply)...")
    master_df["decoded_payload"] = master_df["raw_payload"].apply(decode_payload)
    
    logger.info("Sanitizing payloads (Vectorized Apply)...")
    master_df["sanitized_payload"] = master_df["decoded_payload"].apply(sanitize_payload)
    
    logger.info("Computing Hashes...")
    master_df["raw_hash"] = master_df["raw_payload"].apply(compute_sha256)
    master_df["sanitized_hash"] = master_df["sanitized_payload"].apply(compute_sha256)
    
    logger.info("Generating UUIDs...")
    master_df["sample_id"] = [str(uuid.uuid4()) for _ in range(len(master_df))]
    
    logger.info(f"Saving {len(master_df)} rows to {OUTPUT_PATH}")
    master_df.to_parquet(OUTPUT_PATH, index=False)
    logger.info("STAGE 1.1 COMPLETE.")

if __name__ == "__main__":
    run_pipeline()
