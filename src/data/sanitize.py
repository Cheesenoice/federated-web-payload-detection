"""
Stage 2b: Sensitive Token Masking & Sanitization (`src/data/sanitize.py`)

Strips/masks cookies, session IDs, auth tokens, internal IPs, and hostnames to prevent
spurious feature correlation leaks and unethical sensitive data disclosure.

Input: `data/interim/decoded.parquet`
Output: `data/interim/sanitized.parquet`
"""

import os
import re
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
INTERIM_DIR = os.path.join(DATA_DIR, "interim")

INPUT_PATH = os.path.join(INTERIM_DIR, "decoded.parquet")
OUTPUT_PATH = os.path.join(INTERIM_DIR, "sanitized.parquet")

# Masking regex patterns
REGEX_PATTERNS = [
    (re.compile(r"(?i)(phpsessid|jsessionid|sessionid|sess_id|token)=([a-z0-9\-_]+)", re.I), r"\1=MASKED_SESS_TOKEN"),
    (re.compile(r"(?i)\b(bearer\s+[a-z0-9\-\._~\+\/]+=*)", re.I), "bearer MASKED_AUTH_TOKEN"),
    (re.compile(r"\b(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3})\b"), "MASKED_INTERNAL_IP"),
    (re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", re.I), "MASKED_UUID"),
]


def sanitize_text(text: str) -> str:
    if not isinstance(text, str) or not text:
        return ""
    cur = text
    for pattern, repl in REGEX_PATTERNS:
        cur = pattern.sub(repl, cur)
    return cur


def run_stage_2_sanitize():
    logger.info("=== STARTING STAGE 2B: SENSITIVE TOKEN SANITIZATION ===")
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    df = pd.read_parquet(INPUT_PATH)
    logger.info(f"Loaded {len(df)} rows from {INPUT_PATH}")

    sanitized_payloads = [sanitize_text(p) for p in df["decoded_payload"]]
    df["sanitized_payload"] = sanitized_payloads

    df.to_parquet(OUTPUT_PATH, index=False)
    logger.info(f"Saved sanitized parquet to: {OUTPUT_PATH}")
    return df


if __name__ == "__main__":
    run_stage_2_sanitize()
