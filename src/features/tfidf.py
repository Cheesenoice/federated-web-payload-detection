"""
Feature Extraction Module: Character n-gram TF-IDF Vectorizer (`src/features/tfidf.py`)

Extracts sub-word character 3-gram to 5-gram TF-IDF feature matrices for ML baselines
(XGBoost, LightGBM, Random Forest, Logistic Regression).

Strict Fitting Rule:
  TF-IDF vectorizer is fitted ONLY on local client training data to prevent feature-level test leakage.
"""

import os
import pickle
import logging
import pandas as pd
import numpy as np
from scipy.sparse import save_npz, load_npz
from sklearn.feature_extraction.text import TfidfVectorizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def build_char_tfidf_vectorizer(max_features: int = 10000, ngram_range: tuple = (3, 5)) -> TfidfVectorizer:
    """Instantiates a character n-gram TF-IDF vectorizer."""
    return TfidfVectorizer(
        analyzer="char",
        ngram_range=ngram_range,
        max_features=max_features,
        sublinear_tf=True,
        lowercase=False
    )


def fit_and_transform_tfidf(
    train_texts: list[str],
    val_texts: list[str],
    test_texts: list[str],
    max_features: int = 10000
) -> tuple[TfidfVectorizer, any, any, any]:
    """Fits TF-IDF vectorizer on train_texts ONLY, then transforms train, val, test."""
    logger.info(f"Fitting Char TF-IDF Vectorizer (max_features={max_features}) on {len(train_texts)} train payloads...")
    vectorizer = build_char_tfidf_vectorizer(max_features=max_features)
    X_train = vectorizer.fit_transform(train_texts)
    logger.info(f"Fitted vocabulary size: {len(vectorizer.vocabulary_)}")

    X_val = vectorizer.transform(val_texts) if val_texts else None
    X_test = vectorizer.transform(test_texts) if test_texts else None

    return vectorizer, X_train, X_val, X_test
