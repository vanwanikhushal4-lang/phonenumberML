"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) — Model Training Pipeline
Trains:
1. Production Gradient Boosted Trees Ensemble (150 Estimators, max depth 4)
2. Calibrated Sigmoid Parameters (A, B) fit on dedicated validation split
3. Multi-Class Random Forest Model (5 Classes: BENIGN, UNKNOWN, SPAM, SCAM, INVALID)

Saves explicit calibration constants (A, B) into metadata for 100% Android runtime parity.
"""

import os
import sys
import json
import numpy as np
import joblib
from scipy.optimize import minimize
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, FEATURE_SPEC

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "saved_models"))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
os.makedirs(MODELS_DIR, exist_ok=True)

def train_production_models():
    print("="*85)
    print("      AEGIS-PNP2 PRODUCTION MODEL TRAINING & SIGMOID CALIBRATION PIPELINE")
    print("="*85)

    # 1. Load Training Data
    with open(os.path.join(DATA_DIR, "train_dataset.json"), "r", encoding="utf-8-sig") as f:
        train_samples = json.load(f)

    # 2. Load Validation Data (for calibration & parameter tuning)
    with open(os.path.join(DATA_DIR, "val_dataset.json"), "r", encoding="utf-8-sig") as f:
        val_samples = json.load(f)

    n_features = FEATURE_SPEC["num_features"]

    X_train = np.zeros((len(train_samples), n_features), dtype=np.float32)
    y_binary_train = np.zeros(len(train_samples), dtype=np.int32)
    y_multi_train = np.zeros(len(train_samples), dtype=np.int32)

    for i, s in enumerate(train_samples):
        X_train[i] = extract_features_from_number(s["raw_number"], s.get("country", "IN"))
        y_binary_train[i] = s["is_threat"]
        y_multi_train[i] = s["label"]

    X_val = np.zeros((len(val_samples), n_features), dtype=np.float32)
    y_binary_val = np.zeros(len(val_samples), dtype=np.int32)
    y_multi_val = np.zeros(len(val_samples), dtype=np.int32)

    for i, s in enumerate(val_samples):
        X_val[i] = extract_features_from_number(s["raw_number"], s.get("country", "IN"))
        y_binary_val[i] = s["is_threat"]
        y_multi_val[i] = s["label"]

    print(f"[*] Training Data:   X={X_train.shape}, Threats={np.sum(y_binary_train == 1)} ({np.mean(y_binary_train)*100:.1f}%)")
    print(f"[*] Validation Data: X={X_val.shape}, Threats={np.sum(y_binary_val == 1)} ({np.mean(y_binary_val)*100:.1f}%)")

    # 3. Train Production Gradient Boosted Trees
    print("\n[1/3] Training Production Gradient Boosted Decision Tree Ensemble (150 Estimators)...")
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

    # 4. Compute Raw Logits on Validation Split & Fit Explicit Sigmoid Calibration (A, B)
    print("[2/3] Fitting Explicit Sigmoid Calibration Parameters (A, B) on Validation Set...")
    val_raw_logits = gbt.decision_function(X_val)

    # Logistic calibration: P = 1 / (1 + exp(A * logit + B))
    # We fit A and B via Logistic Regression on validation logits
    cal_lr = LogisticRegression(C=10.0, solver="lbfgs", max_iter=1000)
    # Feature is -logit so standard logistic regression P = 1 / (1 + exp(-(coef*(-logit) + intercept)))
    cal_lr.fit(val_raw_logits.reshape(-1, 1), y_binary_val)

    # In standard form P(y=1) = 1 / (1 + exp(- (w * x + b)))
    # With x = logit, P(y=1) = 1 / (1 + exp(A * logit + B)) where A = -w, B = -b
    param_A = float(-cal_lr.coef_[0][0])
    param_B = float(-cal_lr.intercept_[0])

    val_calibrated_probs = 1.0 / (1.0 + np.exp(param_A * val_raw_logits + param_B))
    val_brier = brier_score_loss(y_binary_val, val_calibrated_probs)
    val_roc = roc_auc_score(y_binary_val, val_calibrated_probs)
    val_prauc = average_precision_score(y_binary_val, val_calibrated_probs)

    print(f"  * Fitted Calibration Parameters: A = {param_A:.6f}, B = {param_B:.6f}")
    print(f"  * Validation Brier Loss:         {val_brier:.6f} (Ideal < 0.05)")
    print(f"  * Validation ROC-AUC:            {val_roc:.4f}")
    print(f"  * Validation PR-AUC:             {val_prauc:.4f}")

    # 5. Train Multi-Class Random Forest Model
    print("[3/3] Training Multiclass Random Forest Classifier (5 Classes)...")
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

    # 7. Save Model Binaries & Calibration Constants
    print(f"\nSaving model binaries and calibration constants to {MODELS_DIR}...")
    joblib.dump(gbt, os.path.join(MODELS_DIR, "gbt_model.joblib"))
    joblib.dump(rf_multi, os.path.join(MODELS_DIR, "rf_multi_model.joblib"))
    np.save(os.path.join(MODELS_DIR, "feature_importances.npy"), importances)

    calibration_metadata = {
        "model_name": "AEGIS-PNP2",
        "version": "2.0.0",
        "method": "sigmoid_platt_scaling",
        "formula": "P(Threat | logit) = 1.0 / (1.0 + exp(A * logit + B))",
        "param_A": param_A,
        "param_B": param_B,
        "val_brier_score": float(val_brier),
        "val_roc_auc": float(val_roc),
        "val_pr_auc": float(val_prauc),
        "operating_thresholds": {
            "legitimate_upper_bound": 0.15,
            "unknown_abstain_upper_bound": 0.40,
            "spam_upper_bound": 0.70,
            "scam_lower_bound": 0.70
        }
    }
    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(calibration_metadata, f, indent=2)

    print("Model training & calibration complete.")

if __name__ == "__main__":
    train_production_models()