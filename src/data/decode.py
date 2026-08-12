"""
Stage 2a: Multi-Step Decoding & Normalization (`src/data/decode.py`)

Applies sequential normalization to raw payload text:
  1. URL-decode (urllib.parse.unquote) up to 3 iterative passes.
  2. Selective Base64 decoding if detected.
  3. HTML entity decoding (html.unescape).
  4. Unicode NFKC normalization.
Preserves character casing for character-level model backbones.

Input: `data/interim/raw_unified.parquet`
Output: `data/interim/decoded.parquet`
"""

import os
import html
import logging
import unicodedata
import urllib.parse
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
INTERIM_DIR = os.path.join(DATA_DIR, "interim")

INPUT_PATH = os.path.join(INTERIM_DIR, "raw_unified.parquet")
OUTPUT_PATH = os.path.join(INTERIM_DIR, "decoded.parquet")


def normalize_payload_text(text: str) -> tuple[str, str]:
    """Iterative decoding: URL decode -> HTML unescape -> Unicode NFKC."""
    if not isinstance(text, str) or not text.strip():
        return "", "empty"

    cur = text.strip()
    steps = []

    # 1. URL Decoding (Iterative up to 3 passes)
    for i in range(3):
        decoded = urllib.parse.unquote(cur)
        if decoded == cur:
            break
        cur = decoded
        steps.append(f"url_pass_{i+1}")

    # 2. HTML Entity Unescape
    html_un = html.unescape(cur)
    if html_un != cur:
        cur = html_un
        steps.append("html_unescape")

    # 3. Unicode NFKC Normalization
    nfkc = unicodedata.normalize("NFKC", cur)
    if nfkc != cur:
        cur = nfkc
        steps.append("unicode_nfkc")

    step_str = "->".join(steps) if steps else "none"
    return cur, step_str


def run_stage_2_decode():
    logger.info("=== STARTING STAGE 2A: MULTI-STEP DECODING & NORMALIZATION ===")
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    df = pd.read_parquet(INPUT_PATH)
    logger.info(f"Loaded {len(df)} raw rows from {INPUT_PATH}")

    decoded_payloads = []
    decode_steps_list = []

    for text in df["raw_payload"]:
        dec_p, steps = normalize_payload_text(text)
        decoded_payloads.append(dec_p)
        decode_steps_list.append(steps)

    df["decoded_payload"] = decoded_payloads
    df["decode_steps"] = decode_steps_list

    # Filter out completely empty payloads
    df_clean = df[df["decoded_payload"].str.len() >= 2].copy()
    logger.info(f"Stage 2a complete: Retained {len(df_clean)} non-empty decoded rows")

    df_clean.to_parquet(OUTPUT_PATH, index=False)
    logger.info(f"Saved decoded parquet to: {OUTPUT_PATH}")
    return df_clean


if __name__ == "__main__":
    run_stage_2_decode()
