"""
Stage 5: Fast Deterministic Semantic Augmentation (`src/data/augment.py`)

Applies 8 deterministic mutation rules (M1–M8) to expand minority attack classes
(PathTraversal & SQL Injection) to ~10,000–12,000 rows each in seconds:
  - M1: Case Toggling
  - M2: Single URL Encoding
  - M3: Double URL Encoding
  - M4: Space-to-Comment Injection
  - M5: Logical Operator Swap
  - M6: Null-Byte Injection
  - M7: Path Depth Extension
  - M8: Path Separator Obfuscation

Lineage Constraint: Every augmented variant inherits its parent seed's `dedup_cluster_id`.

Input: `data/processed/deduped_corpus.parquet`
Output: `data/processed/trainable_corpus.parquet`
"""

import os
import sys
import re
import urllib.parse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

INPUT_PATH = os.path.join(PROCESSED_DIR, "deduped_corpus.parquet")
OUTPUT_PATH = os.path.join(PROCESSED_DIR, "trainable_corpus.parquet")


def apply_sqli_mutations(payload: str) -> list[str]:
    """Generates 2–3 deterministic semantic variants for SQLi seeds."""
    variants = [payload]
    
    # Rule M1: Case Toggling
    toggled = "".join(c.upper() if idx % 2 == 0 else c.lower() for idx, c in enumerate(payload))
    variants.append(toggled)

    # Rule M4: Space-to-Comment Injection
    if " " in payload:
        variants.append(re.sub(r"\s+", "/**/", payload))

    # Rule M5: Logical Operator Swap
    if " OR " in payload.upper():
        variants.append(re.sub(r"\bOR\b", "||", payload, flags=re.IGNORECASE))

    # Rule M2: Single URL Encoding
    if "'" in payload or "=" in payload:
        variants.append(urllib.parse.quote(payload, safe=""))

    return list(set(variants))


def apply_pathtrav_mutations(payload: str) -> list[str]:
    """Generates 3–4 deterministic semantic variants for PathTrav seeds."""
    variants = [payload]

    # Rule M2: Single URL Encoding
    if "../" in payload or "..\\" in payload:
        v_url = payload.replace("../", "%2e%2e%2f").replace("..\\", "%2e%2e%5c")
        variants.append(v_url)
        # Rule M3: Double URL Encoding
        variants.append(v_url.replace("%2e", "%252e").replace("%2f", "%252f"))

    # Rule M7: Path Depth Extension
    if "../" in payload:
        variants.append(payload.replace("../", "../../"))
        variants.append(payload.replace("../", "../../../"))

    # Rule M8: Path Separator Obfuscation
    if "../" in payload:
        variants.append(payload.replace("../", "....//"))
        variants.append(payload.replace("../", "..\\/"))

    # Rule M6: Null Byte Injection
    if "passwd" in payload or "win.ini" in payload:
        variants.append(payload + "%00")

    return list(set(variants))


def run_stage_5_augment():
    logger.info("=== STARTING STAGE 5: FAST DETERMINISTIC SEMANTIC AUGMENTATION ===")
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    df_seeds = pd.read_parquet(INPUT_PATH)
    logger.info(f"Loaded {len(df_seeds)} seed rows from {INPUT_PATH}")

def run_stage_5_augment():
    logger.info("=== STARTING STAGE 5: FAST DETERMINISTIC SEMANTIC AUGMENTATION ===")
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    df_seeds = pd.read_parquet(INPUT_PATH)
    logger.info(f"Loaded {len(df_seeds)} seed rows from {INPUT_PATH}")

    # Subsample majority classes (benign, sqli, xss) to ~25,000 seeds each for ideal 1:1 balance
    balanced_seeds = []
    for mclass, group in df_seeds.groupby("label_multiclass"):
        if mclass in ["benign", "sqli", "xss"] and len(group) > 25000:
            group = group.sample(n=25000, random_state=42)
        balanced_seeds.append(group)

    df_balanced_seeds = pd.concat(balanced_seeds, ignore_index=True)
    logger.info(f"Balanced seed corpus: {len(df_balanced_seeds)} rows")

    augmented_rows = []

    sqli_seed_count = len(df_seeds[df_seeds["label_multiclass"] == "sqli"])

    for row in df_balanced_seeds.itertuples(index=False):
        row_dict = row._asdict()
        p = getattr(row, "sanitized_payload")
        mclass = getattr(row, "label_multiclass")
        row_id = getattr(row, "id")

        # Keep original seed row
        seed_dict = dict(row_dict)
        seed_dict["is_augmented"] = False
        augmented_rows.append(seed_dict)

        # Apply fast deterministic mutations to PathTrav & SQLi
        if mclass == "pathtrav":
            variants = apply_pathtrav_mutations(p)
            for v_idx, v_p in enumerate(variants):
                if v_p != p:
                    aug_dict = dict(row_dict)
                    aug_dict["id"] = f"{row_id}_aug_pathtrav_{v_idx}"
                    aug_dict["sanitized_payload"] = v_p
                    aug_dict["is_augmented"] = True
                    # CRITICAL: Retain exact parent lineage ID (dedup_cluster_id)
                    augmented_rows.append(aug_dict)

        elif mclass == "sqli" and sqli_seed_count < 10000:
            variants = apply_sqli_mutations(p)
            for v_idx, v_p in enumerate(variants):
                if v_p != p:
                    aug_dict = dict(row_dict)
                    aug_dict["id"] = f"{row_id}_aug_sqli_{v_idx}"
                    aug_dict["sanitized_payload"] = v_p
                    aug_dict["is_augmented"] = True
                    # CRITICAL: Retain exact parent lineage ID (dedup_cluster_id)
                    augmented_rows.append(aug_dict)

    df_trainable = pd.DataFrame(augmented_rows)
    logger.info(f"=== STAGE 5 COMPLETE: Generated {len(df_trainable)} trainable payload rows ===")

    df_trainable.to_parquet(OUTPUT_PATH, index=False)
    logger.info(f"Saved final trainable corpus to: {OUTPUT_PATH}")

    # Print Final Data Balance Report
    print("\n" + "="*60)
    print("STAGE 5 FINAL TRAINABLE CORPUS DATA BALANCE REPORT")
    print("="*60)
    print("Row counts per attack class (label_multiclass):")
    print(df_trainable["label_multiclass"].value_counts())
    print("\nAugmented status breakdown:")
    print(df_trainable["is_augmented"].value_counts())
    print("="*60 + "\n")

    return df_trainable


if __name__ == "__main__":
    run_stage_5_augment()
