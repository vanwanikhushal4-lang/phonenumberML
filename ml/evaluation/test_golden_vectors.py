"""
AEGIS Phone Number Pattern Risk Model — Golden Test Vectors Verification
Validates 15 golden cases against expected probabilities, tiers, and threat thresholds.
"""

import os
import sys
import json
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, FEATURE_SPEC

EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../export"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))

def run_golden_tests():
    print("="*80)
    print("RUNNING AEGIS GOLDEN TEST VECTORS REGRESSION SUITE (15 CASES)")
    print("="*80)

    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "r", encoding="utf-8-sig") as f:
        golden_data = json.load(f)

    calibrated_gbt = joblib.load(os.path.join(MODELS_DIR, "calibrated_gbt.joblib"))
    test_cases = golden_data["test_cases"]
    passed_count = 0

    print(f"\n{'Case ID':<28} | {'Raw Number':<16} | {'Expected':<10} | {'Actual Prob':<12} | {'Score':<6} | {'Status'}")
    print("-" * 90)

    for case in test_cases:
        cid = case["case_id"]
        raw_num = case["raw_number"]
        country = case["country"]
        expected_tier = case["expected_tier"]
        expected_prob = case["calibrated_prob"]

        v = extract_features_from_number(raw_num, country)
        prob = float(calibrated_gbt.predict_proba(v.reshape(1, -1))[0, 1])
        score = int(round(prob * 100))

        actual_tier = "LEGITIMATE" if prob < 0.15 else ("UNKNOWN" if prob < 0.40 else ("SPAM" if prob < 0.70 else "SCAM"))
        
        prob_match = abs(prob - expected_prob) < 0.05
        tier_match = (actual_tier == expected_tier)

        passed = prob_match and tier_match
        if passed: passed_count += 1
        status = "[PASS]" if passed else f"[FAIL - Expected {expected_tier}]"

        print(f"{cid:<28} | {raw_num:<16} | {expected_tier:<10} | {prob:<12.4f} | {score:<6} | {status}")

    print("-" * 90)
    print(f"Golden Vector Verification: {passed_count} / {len(test_cases)} PASSED ({passed_count/len(test_cases)*100:.1f}%)")
    return passed_count == len(test_cases)

if __name__ == "__main__":
    success = run_golden_tests()
    if not success: sys.exit(1)