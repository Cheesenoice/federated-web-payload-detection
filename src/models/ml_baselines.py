"""
Machine Learning Baseline Classifiers (`src/models/ml_baselines.py`)

Wrappers for traditional ML baselines operating on 10,000-dimensional TF-IDF sparse matrices:
  - Logistic Regression (L2 / Saga)
  - XGBoost Classifier (Multi-class gbtree)
  - LightGBM / Random Forest Classifier
"""

import logging
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MappedClassifier:
    """Wrapper that encodes client labels to 0..K-1 for training, then maps predictions back to global labels."""
    def __init__(self, base_clf, encoder):
        self.base_clf = base_clf
        self.encoder = encoder

    def predict(self, X):
        raw_preds = self.base_clf.predict(X)
        if hasattr(raw_preds, "ndim") and raw_preds.ndim > 1:
            raw_preds = np.argmax(raw_preds, axis=1)
        # Map local contiguous predictions back to global class IDs
        return self.encoder.inverse_transform(raw_preds)


def train_logistic_regression(X_train, y_train, max_iter: int = 500, seed: int = 42):
    """Trains a multi-class Logistic Regression classifier with class mapping."""
    logger.info(f"Training LogisticRegression on matrix {X_train.shape}...")
    le = LabelEncoder()
    y_enc = le.fit_transform(y_train)
    clf = LogisticRegression(
        max_iter=max_iter,
        solver="lbfgs",
        random_state=seed
    )
    clf.fit(X_train, y_enc)
    return MappedClassifier(clf, le)


def train_xgboost(X_train, y_train, n_estimators: int = 50, max_depth: int = 5, seed: int = 42):
    """Trains an XGBoost multi-class classifier with class mapping."""
    logger.info(f"Training XGBoost (n_estimators={n_estimators}, max_depth={max_depth}) on matrix {X_train.shape}...")
    le = LabelEncoder()
    y_enc = le.fit_transform(y_train)
    num_classes = len(le.classes_)
    
    if num_classes > 2:
        clf = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=0.1,
            tree_method="hist",
            objective="multi:softprob",
            num_class=num_classes,
            random_state=seed,
            n_jobs=-1
        )
    else:
        clf = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=0.1,
            tree_method="hist",
            objective="binary:logistic",
            random_state=seed,
            n_jobs=-1
        )
    clf.fit(X_train, y_enc)
    return MappedClassifier(clf, le)


def train_random_forest(X_train, y_train, n_estimators: int = 100, seed: int = 42):
    """Trains a Random Forest multi-class classifier with class mapping."""
    logger.info(f"Training RandomForest (n_estimators={n_estimators}) on matrix {X_train.shape}...")
    le = LabelEncoder()
    y_enc = le.fit_transform(y_train)
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=seed,
        n_jobs=-1
    )
    clf.fit(X_train, y_enc)
    return MappedClassifier(clf, le)
