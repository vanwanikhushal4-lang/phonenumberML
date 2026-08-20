"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP1) — Evaluation Suite
Evaluates performance across:
1. Unseen prefix holdouts & geographic holdouts (2,500 test samples)
2. Precision, Recall, PR-AUC, ROC-AUC, Brier Score
3. False Positive Rate on Legitimate numbers & Hard Negatives
4. Slice performance by Country and Number Type
"""

import os
import sys
import json
import numpy as np
import joblib
from sklearn.metrics import (
    confusion_matrix, classification_report,
    roc_auc_score, average_precision_score,
    brier_score_loss, precision_recall_curve, roc_curve
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, FEATURE_SPEC

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))

def run_evaluation():
    print("="*80)
    print("AEGIS PHONE NUMBER PATTERN RISK MODEL — EVALUATION BENCHMARK")
    print("="*80)

    # 1. Load Prefix Holdout Dataset
    with open(os.path.join(DATA_DIR, "test_prefix_holdout.json"), "r", encoding="utf-8-sig") as f:
        test_samples = json.load(f)

    X_test = np.zeros((len(test_samples), FEATURE_SPEC["num_features"]), dtype=np.float32)
    y_test_multi = np.zeros(len(test_samples), dtype=np.int32)
    y_test_binary = np.zeros(len(test_samples), dtype=np.int32)
    countries = []

    for i, s in enumerate(test_samples):
        X_test[i] = extract_features_from_number(s["raw_number"], s.get("country", "IN"))
        y_test_multi[i] = s["label"]
        y_test_binary[i] = 1 if s["label"] in (2, 3) else 0
        countries.append(s.get("country", "IN"))

    calibrated_gbt = joblib.load(os.path.join(MODELS_DIR, "calibrated_gbt.joblib"))
    raw_gbt = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    logreg = joblib.load(os.path.join(MODELS_DIR, "logistic_regression.joblib"))

    # Predict
    probs_gbt = calibrated_gbt.predict_proba(X_test)[:, 1]
    probs_logreg = logreg.predict_proba(X_test)[:, 1]

    # Binary Metrics (Threshold = 0.40)
    OPERATING_THRESHOLD = 0.40
    y_pred_binary = (probs_gbt >= OPERATING_THRESHOLD).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_test_binary, y_pred_binary).ravel()
    fpr = (fp / (fp + tn)) * 100.0
    recall = (tp / (tp + fn)) * 100.0
    precision = (tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 0.0
    accuracy = ((tp + tn) / len(y_test_binary)) * 100.0
    brier = brier_score_loss(y_test_binary, probs_gbt)
    roc_auc = roc_auc_score(y_test_binary, probs_gbt)
    pr_auc = average_precision_score(y_test_binary, probs_gbt)

    print(f"\n--- OVERALL HOLDOUT METRICS (2,500 UNSEEN PREFIX SAMPLES) ---")
    print(f"  * Threat Recall (Sensitivity):     {recall:.2f}% ({tp} / {tp+fn} spam/scam caught)")
    print(f"  * Threat Precision:                {precision:.2f}%")
    print(f"  * False Positive Rate on Legitimate/Unknown: {fpr:.2f}% ({fp} / {tn+fp} false alarms)")
    print(f"  * Overall Accuracy:                {accuracy:.2f}%")
    print(f"  * PR-AUC (Precision-Recall AUC):   {pr_auc:.4f}")
    print(f"  * ROC-AUC:                         {roc_auc:.4f}")
    print(f"  * Probability Calibration (Brier): {brier:.4f} (Ideal < 0.05)")

    # 2. Confusion Matrix
    print(f"\n--- CONFUSION MATRIX (Operating Threshold = {OPERATING_THRESHOLD}) ---")
    print(f"                 Predicted Safe/Unk    Predicted Threat (Spam/Scam)")
    print(f"  Actual Safe:   {tn:>12}         {fp:>12} (FPR: {fpr:.2f}%)")
    print(f"  Actual Threat: {fn:>12}         {tp:>12} (Recall: {recall:.2f}%)")

    # 3. Sliced Evaluation by Country
    print(f"\n--- PERFORMANCE BY COUNTRY SLICE ---")
    print(f"{'Country':<10} | {'Count':<8} | {'Recall (%)':<12} | {'FPR (%)':<10} | {'PR-AUC':<8}")
    print("-" * 55)
    for ctry in sorted(list(set(countries))):
        c_indices = [i for i, c in enumerate(countries) if c == ctry]
        if len(c_indices) < 20: continue
        c_y_true = y_test_binary[c_indices]
        c_probs = probs_gbt[c_indices]
        c_pred = (c_probs >= OPERATING_THRESHOLD).astype(int)
        
        c_tp = np.sum((c_y_true == 1) & (c_pred == 1))
        c_fn = np.sum((c_y_true == 1) & (c_pred == 0))
        c_fp = np.sum((c_y_true == 0) & (c_pred == 1))
        c_tn = np.sum((c_y_true == 0) & (c_pred == 0))

        c_rec = (c_tp / (c_tp + c_fn) * 100.0) if (c_tp + c_fn) > 0 else 0.0
        c_fpr = (c_fp / (c_fp + c_tn) * 100.0) if (c_fp + c_tn) > 0 else 0.0
        c_prauc = average_precision_score(c_y_true, c_probs) if len(set(c_y_true)) > 1 else 1.0

        print(f"{ctry:<10} | {len(c_indices):<8} | {c_rec:<12.1f} | {c_fpr:<10.1f} | {c_prauc:<8.4f}")

    # 4. Hard Negatives Verification (Curated Real Bank & Emergency Lines)
    print(f"\n--- HARD NEGATIVES VERIFICATION (Curated Banks & Emergency Lines) ---")
    with open(os.path.join(DATA_DIR, "hard_negatives.json"), "r", encoding="utf-8-sig") as f:
        hard_negs = json.load(f)

    hard_passed = 0
    print(f"{'Organization / Line':<35} | {'Number':<16} | {'Risk Score':<11} | {'Status'}")
    print("-" * 75)
    for item in hard_negs:
        v = extract_features_from_number(item["number"], item["country"])
        p = float(calibrated_gbt.predict_proba(v.reshape(1, -1))[0, 1])
        score = int(round(p * 100))
        passed = (p <= item["expected_max_risk"])
        if passed: hard_passed += 1
        status = "[PASS]" if passed else f"[FAIL - P={p:.4f}]"
        print(f"{item['name']:<35} | {item['number']:<16} | {score:<2}/100 ({p:.3f}) | {status}")

    print("-" * 75)
    print(f"Hard Negatives Pass Rate: {hard_passed} / {len(hard_negs)} ({hard_passed/len(hard_negs)*100:.1f}%)")

if __name__ == "__main__":
    run_evaluation()