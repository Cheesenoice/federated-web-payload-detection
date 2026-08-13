"""
Feature Extraction Engine (`src/features/build_features.py`)

Reads split parquet files from `data/splits/`, extracts TF-IDF matrices (10,000 dimensions)
and PyTorch CharTokenizer tensors for:
  - client_1_train to client_6_train
  - client_1_test to client_6_test
  - client_1_val to client_6_val
  - global_test & global_val
"""

import os
import sys
import pickle
import logging
import pandas as pd
import numpy as np
from scipy.sparse import save_npz

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.features.tfidf import fit_and_transform_tfidf
from src.features.tokenizer import CharTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SPLITS_DIR = os.path.join(DATA_DIR, "splits")
FEATURES_DIR = os.path.join(DATA_DIR, "features")
os.makedirs(FEATURES_DIR, exist_ok=True)


def run_build_features():
    logger.info("=== STARTING FEATURE EXTRACTION PIPELINE (DISJOINT HELD-OUT SPLITS) ===")

    client_train_dfs = [pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{i+1}_train.parquet")) for i in range(6)]
    client_val_dfs = [pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{i+1}_val.parquet")) for i in range(6)]
    client_test_dfs = [pd.read_parquet(os.path.join(SPLITS_DIR, f"client_{i+1}_test.parquet")) for i in range(6)]

    df_val_global = pd.read_parquet(os.path.join(SPLITS_DIR, "val_global.parquet"))
    df_test_indomain = pd.read_parquet(os.path.join(SPLITS_DIR, "test_indomain.parquet"))

    train_texts = pd.concat([df["sanitized_payload"] for df in client_train_dfs], ignore_index=True).tolist()
    val_texts = df_val_global["sanitized_payload"].tolist()
    test_texts = df_test_indomain["sanitized_payload"].tolist()

    # 1. Fit TF-IDF Vectorizer
    vectorizer, X_train_tfidf, X_val_tfidf, X_test_tfidf = fit_and_transform_tfidf(
        train_texts, val_texts, test_texts, max_features=10000
    )

    vec_path = os.path.join(FEATURES_DIR, "tfidf_vectorizer.pkl")
    with open(vec_path, "wb") as f:
        pickle.dump(vectorizer, f)

    # Save Client TF-IDF matrices
    for i in range(6):
        c_tr_tfidf = vectorizer.transform(client_train_dfs[i]["sanitized_payload"])
        c_te_tfidf = vectorizer.transform(client_test_dfs[i]["sanitized_payload"])

        save_npz(os.path.join(FEATURES_DIR, f"client_{i+1}_train_tfidf.npz"), c_tr_tfidf)
        save_npz(os.path.join(FEATURES_DIR, f"client_{i+1}_test_tfidf.npz"), c_te_tfidf)
        # Legacy compatibility
        save_npz(os.path.join(FEATURES_DIR, f"client_{i+1}_tfidf.npz"), c_tr_tfidf)

    save_npz(os.path.join(FEATURES_DIR, "test_indomain_tfidf.npz"), X_test_tfidf)
    save_npz(os.path.join(FEATURES_DIR, "val_global_tfidf.npz"), X_val_tfidf)

    # 2. Tokenize for PyTorch CharCNN
    tokenizer = CharTokenizer(max_length=256)

    for i in range(6):
        c_tr_tokens = tokenizer.batch_encode(client_train_dfs[i]["sanitized_payload"].tolist())
        c_va_tokens = tokenizer.batch_encode(client_val_dfs[i]["sanitized_payload"].tolist())
        c_te_tokens = tokenizer.batch_encode(client_test_dfs[i]["sanitized_payload"].tolist())

        np.save(os.path.join(FEATURES_DIR, f"client_{i+1}_train_tokens.npy"), c_tr_tokens)
        np.save(os.path.join(FEATURES_DIR, f"client_{i+1}_val_tokens.npy"), c_va_tokens)
        np.save(os.path.join(FEATURES_DIR, f"client_{i+1}_test_tokens.npy"), c_te_tokens)
        # Legacy compatibility
        np.save(os.path.join(FEATURES_DIR, f"client_{i+1}_tokens.npy"), c_tr_tokens)

    np.save(os.path.join(FEATURES_DIR, "test_indomain_tokens.npy"), tokenizer.batch_encode(test_texts))
    np.save(os.path.join(FEATURES_DIR, "val_global_tokens.npy"), tokenizer.batch_encode(val_texts))

    logger.info("=== FEATURE EXTRACTION COMPLETE ===")


if __name__ == "__main__":
    run_build_features()
