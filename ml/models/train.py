"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP1) — Model Training Pipeline
Trains:
1. Baseline 1: Deterministic Pattern & Numbering Plan Rules
2. Baseline 2: Calibrated L2 Logistic Regression
3. Production Model: Calibrated Gradient Boosted Trees (GBT - 150 Estimators)
4. Reference Model: Random Forest Classifier

Features: 36 Privacy-Preserving Structural Dimensions
Outputs: Calibrated Malice Probability [0.0 - 1.0], Confidence Level, 4-Class Tiers
"""

import os
import sys
import json
import numpy as np
import joblib
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, FEATURE_SPEC

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "saved_models"))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
os.makedirs(MODELS_DIR, exist_ok=True)

def train_pipeline():
    print("="*80)
    print("AEGIS PHONE NUMBER PATTERN RISK MODEL (36 FEATURES) — TRAINING PIPELINE")
    print("="*80)

    # 1. Load Training Data
    with open(os.path.join(DATA_DIR, "train_dataset.json"), "r", encoding="utf-8-sig") as f:
        train_samples = json.load(f)

    X_train = np.zeros((len(train_samples), FEATURE_SPEC["num_features"]), dtype=np.float32)
    # Binary threat label: 1 if (SPAM or SCAM), 0 if (LEGITIMATE or UNKNOWN)
    y_binary_train = np.zeros(len(train_samples), dtype=np.int32)
    y_multi_train = np.zeros(len(train_samples), dtype=np.int32)

    for i, s in enumerate(train_samples):
        X_train[i] = extract_features_from_number(s["raw_number"], s.get("country", "IN"))
        y_multi_train[i] = s["label"]
        # SPAM (2) or SCAM (3) are threats; LEGITIMATE (0) and UNKNOWN (1) are non-threats
        y_binary_train[i] = 1 if s["label"] in (2, 3) else 0

    print(f"Train Shape: X={X_train.shape}, y={y_binary_train.shape}")
    print(f"  * Threat (SPAM/SCAM):    {np.sum(y_binary_train == 1)} ({np.mean(y_binary_train)*100:.1f}%)")
    print(f"  * Non-Threat (LEGIT/UNK): {np.sum(y_binary_train == 0)} ({(1-np.mean(y_binary_train))*100:.1f}%)")

    # 2. Train Baseline 2: Logistic Regression
    print("\nTraining Baseline 2: L2 Logistic Regression...")
    logreg = LogisticRegression(C=1.0, max_iter=1000, random_state=42, class_weight="balanced")
    logreg.fit(X_train, y_binary_train)

    # 3. Train Production Model: Gradient Boosted Trees (GBT)
    print("Training Production Model: Gradient Boosted Trees (GBT - 150 Estimators)...")
    gbt = GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=4,
        subsample=0.85,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42
    )
    gbt.fit(X_train, y_binary_train)

    # 4. Probability Calibration (5-fold Sigmoid Calibration)
    print("Calibrating GBT model output probabilities (5-fold CV)...")
    calibrated_gbt = CalibratedClassifierCV(estimator=gbt, method="sigmoid", cv=5)
    calibrated_gbt.fit(X_train, y_binary_train)

    # 5. Train Random Forest (Multi-Class 4-Tier Reference)
    print("Training Multi-Class Random Forest Model (4-Class Tiers)...")
    rf_multi = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1, class_weight="balanced")
    rf_multi.fit(X_train, y_multi_train)

    # 6. Feature Importances
    importances = gbt.feature_importances_
    indices = np.argsort(importances)[::-1]
    print("\nTop 12 Most Discriminative Phone Number Structural Features:")
    for rank in range(min(12, len(indices))):
        idx = indices[rank]
        f_name = FEATURE_SPEC["features"][idx]["name"]
        f_desc = FEATURE_SPEC["features"][idx]["description"]
        print(f"  {rank+1:>2}. [{idx:02d}] {f_name:<35}: {importances[idx]:.4f} ({f_desc})")

    # 7. Save Models
    print(f"\nSaving model binaries to {MODELS_DIR}...")
    joblib.dump(logreg, os.path.join(MODELS_DIR, "logistic_regression.joblib"))
    joblib.dump(gbt, os.path.join(MODELS_DIR, "gbt_model.joblib"))
    joblib.dump(calibrated_gbt, os.path.join(MODELS_DIR, "calibrated_gbt.joblib"))
    joblib.dump(rf_multi, os.path.join(MODELS_DIR, "rf_multi_model.joblib"))
    np.save(os.path.join(MODELS_DIR, "feature_importances.npy"), importances)

    print("Training pipeline complete.")

if __name__ == "__main__":
    train_pipeline()