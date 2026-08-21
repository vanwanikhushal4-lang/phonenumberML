"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) — Model Training Pipeline
Trains:
1. Production Continuous Pattern Risk Estimator (150 GBT Estimators)
2. True Platt Sigmoid Calibrator on Binary Threat Detection
3. Multi-Class Random Forest Model (5 Classes)
"""

import os
import sys
import json
import numpy as np
import joblib
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import mean_squared_error, roc_auc_score, average_precision_score, brier_score_loss

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, FEATURE_SPEC

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "saved_models"))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
os.makedirs(MODELS_DIR, exist_ok=True)

TARGET_MAP = {
    "BENIGN": 0.00,
    "UNKNOWN": 0.25,
    "TELEMARKETING_SPAM": 0.55,
    "CONFIRMED_SCAM": 0.98,
    "INVALID": 0.00
}

def train_production_models():
    print("="*85)
    print("      AEGIS-PNP2 CONTINUOUS PATTERN RISK TRAINING & PLATT CALIBRATION")
    print("="*85)

    with open(os.path.join(DATA_DIR, "train_dataset.json"), "r", encoding="utf-8-sig") as f:
        train_samples = json.load(f)
    with open(os.path.join(DATA_DIR, "calib_dataset.json"), "r", encoding="utf-8-sig") as f:
        calib_samples = json.load(f)
    with open(os.path.join(DATA_DIR, "val_dataset.json"), "r", encoding="utf-8-sig") as f:
        val_samples = json.load(f)

    n_features = FEATURE_SPEC["num_features"]

    X_train = np.zeros((len(train_samples), n_features), dtype=np.float32)
    y_train = np.zeros(len(train_samples), dtype=np.float32)
    y_binary_train = np.zeros(len(train_samples), dtype=np.int32)
    y_multi_train = np.zeros(len(train_samples), dtype=np.int32)

    for i, s in enumerate(train_samples):
        X_train[i] = extract_features_from_number(s["raw_number"], s.get("country", "IN"))
        y_train[i] = TARGET_MAP.get(s["label_name"], 0.25)
        y_binary_train[i] = s["is_threat"]
        y_multi_train[i] = s["label_code"]

    X_calib = np.zeros((len(calib_samples), n_features), dtype=np.float32)
    y_binary_calib = np.zeros(len(calib_samples), dtype=np.int32)
    for i, s in enumerate(calib_samples):
        X_calib[i] = extract_features_from_number(s["raw_number"], s.get("country", "IN"))
        y_binary_calib[i] = s["is_threat"]

    X_val = np.zeros((len(val_samples), n_features), dtype=np.float32)
    y_val = np.zeros(len(val_samples), dtype=np.float32)
    y_binary_val = np.zeros(len(val_samples), dtype=np.int32)
    y_multi_val = np.zeros(len(val_samples), dtype=np.int32)

    for i, s in enumerate(val_samples):
        X_val[i] = extract_features_from_number(s["raw_number"], s.get("country", "IN"))
        y_val[i] = TARGET_MAP.get(s["label_name"], 0.25)
        y_binary_val[i] = s["is_threat"]
        y_multi_val[i] = s["label_code"]

    print(f"[*] Training Data:   X={X_train.shape}, Threats={np.sum(y_binary_train == 1)} ({np.mean(y_binary_train)*100:.1f}%)")
    print(f"[*] Calib Data:      X={X_calib.shape}, Threats={np.sum(y_binary_calib == 1)} ({np.mean(y_binary_calib)*100:.1f}%)")
    print(f"[*] Validation Data: X={X_val.shape}, Threats={np.sum(y_binary_val == 1)} ({np.mean(y_binary_val)*100:.1f}%)")

    # 1. Train Production Continuous GBT Pattern Risk Regressor
    print("\n[1/3] Training Production Continuous GBT Pattern Risk Model (150 Estimators)...")
    gbt = GradientBoostingRegressor(
        n_estimators=150,
        learning_rate=0.10,
        max_depth=5,
        min_samples_leaf=4,
        subsample=0.85,
        random_state=42
    )
    gbt.fit(X_train, y_train)

    val_logits = gbt.predict(X_val)
    val_ordinal_preds = np.clip(val_logits, 0.0, 1.0)
    val_mse = mean_squared_error(y_val, val_ordinal_preds)

    # 2. Fit True Platt Sigmoid Calibrator on Dedicated Disjoint Calibration Split
    print("[2/3] Fitting Platt Sigmoid Calibrator on Dedicated Disjoint Split...")
    calib_logits = gbt.predict(X_calib).reshape(-1, 1)
    platt_model = LogisticRegression(C=10.0, solver="lbfgs", random_state=42)
    platt_model.fit(calib_logits, y_binary_calib)

    param_A = float(platt_model.coef_[0][0])
    param_B = float(platt_model.intercept_[0])

    val_prob_threat = 1.0 / (1.0 + np.exp(-(param_A * val_logits + param_B)))
    val_brier = brier_score_loss(y_binary_val, val_prob_threat)
    val_roc = roc_auc_score(y_binary_val, val_prob_threat)
    val_prauc = average_precision_score(y_binary_val, val_prob_threat)

    print(f"  * Validation Ordinal MSE:        {val_mse:.6f}")
    print(f"  * Platt Calibrator Params:       A = {param_A:.4f}, B = {param_B:.4f}")
    print(f"  * Validation Brier Loss:         {val_brier:.6f}")
    print(f"  * Validation ROC-AUC:            {val_roc:.4f}")
    print(f"  * Validation PR-AUC:             {val_prauc:.4f}")

    assert val_roc >= 0.85, f"FATAL GATE FAILURE: Validation ROC-AUC {val_roc:.4f} < 0.85!"
    assert val_prauc >= 0.85, f"FATAL GATE FAILURE: Validation PR-AUC {val_prauc:.4f} < 0.85!"

    # 3. Train Multi-Class Random Forest Model
    print("[3/3] Training Multiclass Random Forest Classifier (5 Classes)...")
    rf_multi = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1, class_weight="balanced")
    rf_multi.fit(X_train, y_multi_train)

    # 4. Feature Importances
    importances = gbt.feature_importances_
    indices = np.argsort(importances)[::-1]
    print("\nTop 12 Most Discriminative Phone Number Structural Features:")
    for rank in range(min(12, len(indices))):
        idx = indices[rank]
        f_name = FEATURE_SPEC["features"][idx]["name"]
        f_desc = FEATURE_SPEC["features"][idx]["description"]
        print(f"  {rank+1:>2}. [{idx:02d}] {f_name:<35}: {importances[idx]:.4f} ({f_desc})")

    # 5. Save Models & Calibration Metadata
    print(f"\nSaving model binaries and calibration constants to {MODELS_DIR}...")
    joblib.dump(gbt, os.path.join(MODELS_DIR, "gbt_model.joblib"))
    joblib.dump(rf_multi, os.path.join(MODELS_DIR, "rf_multi_model.joblib"))
    np.save(os.path.join(MODELS_DIR, "feature_importances.npy"), importances)

    calibration_metadata = {
        "model_name": "AEGIS-PNP2",
        "version": "2.1.0",
        "objective": "PATTERN_RISK",
        "method": "continuous_calibrated_regression_with_platt_scaling",
        "formula": "P(Threat | features) = 1 / (1 + exp(-(param_A * raw_logit + param_B)))",
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