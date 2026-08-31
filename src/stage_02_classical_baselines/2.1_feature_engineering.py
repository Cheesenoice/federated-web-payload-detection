import os
import sys
import math
import logging
import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
FEATURES_DIR = os.path.join(DATA_DIR, "interim", "stage_02_features")
MODELS_DIR = os.path.join(ROOT_DIR, "models", "stage_02_baselines")

os.makedirs(FEATURES_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# Datasets
PATH_TRAIN = os.path.join(PROCESSED_DIR, "pool_a_train_balanced_40k.parquet")
PATH_VAL = os.path.join(PROCESSED_DIR, "pool_a_val.parquet")
PATH_TEST_A = os.path.join(PROCESSED_DIR, "pool_a_test.parquet")
PATH_TEST_B = os.path.join(PROCESSED_DIR, "pool_b_global_test.parquet")
PATH_MANIFEST = os.path.join(PROCESSED_DIR, "sample_manifest.parquet")

CORE_CLASSES = ["benign", "xss", "sqli", "pathtrav"]
SPECIAL_CHARS = ["<", ">", "'", '"', "/", "\\", ";", "(", ")", "=", "%", "-"]

def calculate_shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    prob = [float(s.count(c)) / len(s) for c in set(s)]
    return -sum(p * math.log2(p) for p in prob)

def extract_lexical_features(payload_series: pd.Series) -> np.ndarray:
    features = []
    for text in payload_series.fillna("").astype(str):
        n = len(text)
        if n == 0:
            features.append([0.0] * 16)
            continue
            
        ent = calculate_shannon_entropy(text)
        char_counts = [text.count(c) / n for c in SPECIAL_CHARS]
        digit_ratio = sum(c.isdigit() for c in text) / n
        upper_ratio = sum(c.isupper() for c in text) / n
        
        features.append([float(n), ent] + char_counts + [digit_ratio, upper_ratio])
        
    return np.array(features, dtype=np.float32)

def run_pipeline():
    logger.info("=== STARTING STAGE 2.1: FEATURE ENGINEERING PIPELINE (4 CORE CLASSES) ===")
    
    # 1. Load Datasets and Filter strictly for the 4 Core Attack Families
    df_train = pd.read_parquet(PATH_TRAIN)
    df_train = df_train[df_train["final_label"].isin(CORE_CLASSES)].copy()
    
    df_val = pd.read_parquet(PATH_VAL)
    df_val = df_val[df_val["final_label"].isin(CORE_CLASSES)].copy()
    
    df_test_a = pd.read_parquet(PATH_TEST_A)
    df_test_a = df_test_a[df_test_a["final_label"].isin(CORE_CLASSES)].copy()
    
    df_test_b = pd.read_parquet(PATH_TEST_B)
    df_test_b = df_test_b[df_test_b["final_label"].isin(CORE_CLASSES)].copy()
    
    manifest_df = pd.read_parquet(PATH_MANIFEST)
    df_ood = manifest_df[(manifest_df["pool_id"] == "OOD") & (manifest_df["final_label"].isin(CORE_CLASSES))].copy()
    
    logger.info(f"Train samples (Pool A Balanced): {len(df_train)}")
    logger.info(f"Val samples (Pool A Natural):    {len(df_val)}")
    logger.info(f"Test A samples (In-Domain):      {len(df_test_a)}")
    logger.info(f"Test B samples (Global Network): {len(df_test_b)}")
    logger.info(f"OOD CSIC samples (4 Classes):    {len(df_ood)}")
    
    # 2. Fit Feature Extractors on Train Set
    logger.info("Fitting Character n-gram TF-IDF (1-3 grams, top 10,000 features)...")
    tfidf_char = TfidfVectorizer(
        analyzer="char",
        ngram_range=(1, 3),
        max_features=10000,
        sublinear_tf=True
    )
    X_train_char = tfidf_char.fit_transform(df_train["sanitized_payload"].fillna("").astype(str))
    
    logger.info("Fitting Word n-gram TF-IDF (1-2 grams, top 5,000 features)...")
    tfidf_word = TfidfVectorizer(
        analyzer="word",
        token_pattern=r"\S+",
        ngram_range=(1, 2),
        max_features=5000,
        sublinear_tf=True
    )
    X_train_word = tfidf_word.fit_transform(df_train["sanitized_payload"].fillna("").astype(str))
    
    logger.info("Extracting and Scaling Lexical Features (16 dimensions)...")
    X_train_lex = extract_lexical_features(df_train["sanitized_payload"])
    scaler = StandardScaler(with_mean=False)
    X_train_lex_scaled = scaler.fit_transform(sparse.csr_matrix(X_train_lex))
    
    X_train_combined = sparse.hstack([X_train_lex_scaled, X_train_char, X_train_word]).tocsr()
    logger.info(f"Train Feature Matrix Shape: {X_train_combined.shape}")
    
    # 3. Transform Validation, Test A, Test B, and OOD sets
    def transform_dataset(df_sub, name):
        logger.info(f"Transforming {name} ({len(df_sub)} samples)...")
        p = df_sub["sanitized_payload"].fillna("").astype(str)
        c = tfidf_char.transform(p)
        w = tfidf_word.transform(p)
        lex = scaler.transform(sparse.csr_matrix(extract_lexical_features(p)))
        return sparse.hstack([lex, c, w]).tocsr()
        
    X_val_combined = transform_dataset(df_val, "Validation Set A")
    X_test_a_combined = transform_dataset(df_test_a, "Test Set A")
    X_test_b_combined = transform_dataset(df_test_b, "Global Test Set B")
    X_ood_combined = transform_dataset(df_ood, "External OOD Set")
    
    # 4. Save Extractor Pipelines
    logger.info(f"Saving feature extractors to {MODELS_DIR}...")
    joblib.dump({
        "tfidf_char": tfidf_char,
        "tfidf_word": tfidf_word,
        "scaler": scaler
    }, os.path.join(MODELS_DIR, "feature_pipeline.joblib"))
    
    # 5. Cache Sparse Feature Matrices & Labels to Disk
    logger.info(f"Caching sparse feature matrices to {FEATURES_DIR}...")
    sparse.save_npz(os.path.join(FEATURES_DIR, "X_train.npz"), X_train_combined)
    sparse.save_npz(os.path.join(FEATURES_DIR, "X_val.npz"), X_val_combined)
    sparse.save_npz(os.path.join(FEATURES_DIR, "X_test_a.npz"), X_test_a_combined)
    sparse.save_npz(os.path.join(FEATURES_DIR, "X_test_b.npz"), X_test_b_combined)
    sparse.save_npz(os.path.join(FEATURES_DIR, "X_ood.npz"), X_ood_combined)
    
    np.save(os.path.join(FEATURES_DIR, "y_train.npy"), df_train["final_label"].values)
    np.save(os.path.join(FEATURES_DIR, "y_val.npy"), df_val["final_label"].values)
    np.save(os.path.join(FEATURES_DIR, "y_test_a.npy"), df_test_a["final_label"].values)
    np.save(os.path.join(FEATURES_DIR, "y_test_b.npy"), df_test_b["final_label"].values)
    np.save(os.path.join(FEATURES_DIR, "y_ood.npy"), df_ood["final_label"].values)
    
    logger.info("STAGE 2.1 COMPLETE: Feature engineering and caching finished successfully.")

if __name__ == "__main__":
    run_pipeline()
