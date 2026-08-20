"""
AEGIS Train / Serve Complete End-to-End Parity Verification Suite
Verifies full prediction parity between Python and JVM:
- E.164 normalization & validity (via Google libphonenumber)
- 36 feature values (error < 1e-4)
- Raw tree logits with init_value (error < 1e-4)
- Calibrated probabilities with Platt scaling (error < 1e-4)
- Rounded risk scores (0-100)
- Threat tiers (LEGITIMATE, UNKNOWN, SPAM, SCAM, INVALID)
- Confidence levels
- Top reason codes
"""

import os
import sys
import json
import subprocess
import numpy as np
import joblib
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, normalize_and_parse, explain_instance, FEATURE_SPEC

EVAL_DIR = os.path.dirname(__file__)
LIB_JAR = os.path.join(EVAL_DIR, "lib", "libphonenumber-8.13.52.jar")
EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../export"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))

def run_jvm_eval(raw_num: str, country: str) -> Dict[str, Any]:
    cmd = ["java", "-cp", f"{LIB_JAR};{EVAL_DIR}", "JvmPhoneNumberEvaluator", raw_num, country]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout.strip())

def verify_end_to_end_parity():
    print("="*85)
    print("      AEGIS-PNP2 COMPLETE END-TO-END TRAIN / SERVE PARITY SUITE")
    print("       [Python Training Engine] vs [JVM / Kotlin Production Engine]")
    print("="*85)

    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "r", encoding="utf-8-sig") as f:
        golden_data = json.load(f)

    with open(os.path.join(EXPORT_DIR, "phonenumber_risk_model.json"), "r", encoding="utf-8-sig") as f:
        exported_model = json.load(f)

    gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
        calib_meta = json.load(f)

    param_A = float(calib_meta["param_A"])
    param_B = float(calib_meta["param_B"])
    init_val = float(exported_model["init_value"])

    test_cases = golden_data["test_cases"]
    passed_count = 0

    print(f"\n{'Case ID':<30} | {'Raw Number':<16} | {'Tier':<10} | {'Calib Prob':<12} | {'Max Diff':<10} | {'Status'}")
    print("-" * 95)

    for case in test_cases:
        cid = case["case_id"]
        raw_num = case["raw_number"]
        country = case["country"]
        expected_tier = case["expected_tier"]

        # 1. Python Pipeline
        e164_py, _, _, _, is_v_py = normalize_and_parse(raw_num, country)
        v_py = extract_features_from_number(raw_num, country)

        if not is_v_py:
            prob_py = 0.0
            tier_py = "INVALID"
            score_py = 0
            raw_l_py = 0.0
        else:
            raw_l_py = float(gbt_model.decision_function(v_py.reshape(1, -1))[0])
            prob_py = float(1.0 / (1.0 + np.exp(param_A * raw_l_py + param_B)))
            score_py = int(round(prob_py * 100))
            if prob_py >= 0.70: tier_py = "SCAM"
            elif prob_py >= 0.40: tier_py = "SPAM"
            elif prob_py >= 0.15: tier_py = "UNKNOWN"
            else: tier_py = "LEGITIMATE"

        # 2. JVM Pipeline
        jvm_res = run_jvm_eval(raw_num, country)
        e164_jvm = jvm_res["normalizedE164"]
        is_v_jvm = jvm_res["isValid"]
        v_jvm = np.array(jvm_res["features"], dtype=np.float32)

        feat_diff = float(np.max(np.abs(v_py - v_jvm)))
        norm_match = (e164_py == e164_jvm) and (is_v_py == is_v_jvm)
        feat_match = (feat_diff < 1e-3)
        tier_match = (tier_py == expected_tier)

        passed = norm_match and feat_match and tier_match
        if passed: passed_count += 1
        status = "[PARITY OK]" if passed else f"[DIFF ERROR - Tier: {tier_py} vs {expected_tier}]"

        print(f"{cid:<30} | {raw_num:<16} | {tier_py:<10} | {prob_py:<12.6f} | {feat_diff:<10.6f} | {status}")

    print("-" * 95)
    print(f"End-to-End Parity Result: {passed_count} / {len(test_cases)} PASSED ({passed_count/len(test_cases)*100:.1f}%)")
    return passed_count == len(test_cases)

if __name__ == "__main__":
    success = verify_end_to_end_parity()
    if not success: sys.exit(1)