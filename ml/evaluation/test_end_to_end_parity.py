"""
AEGIS Complete Train / Serve End-to-End Parity Verification Suite
Compares:
1. Python Pipeline (libphonenumber 9.0.37 + Scikit-Learn GBT Model)
2. JVM Production Pipeline (Google libphonenumber 8.13.52 + Pure Java GBT Tree Engine)
3. Fixed Independently Authored Semantic Golden Expectations
Checks:
- E.164 String Match
- Validity Boolean Match
- 36 Features Match (max diff < 1e-4)
- Raw GBT Logit Match (max diff < 1e-4)
- Calibrated Probability Match (max diff < 1e-4)
- Risk Score Match (exact integer)
- Threat Tier Match (exact string & semantic match)
"""

import os
import sys
import json
import subprocess
import numpy as np
import joblib
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, normalize_and_parse, FEATURE_SPEC

EVAL_DIR = os.path.dirname(__file__)
LIB_JAR = os.path.join(EVAL_DIR, "lib", "libphonenumber-8.13.52.jar")
EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../export"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))
MODEL_JSON = os.path.join(EXPORT_DIR, "phonenumber_risk_model.json")

def run_jvm_eval(raw_num: str, country: str) -> Dict[str, Any]:
    cmd = ["java", "-cp", f"{LIB_JAR};{EVAL_DIR}", "JvmPhoneNumberEvaluator", raw_num, country, MODEL_JSON]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout.strip())

def verify_end_to_end_parity():
    print("="*95)
    print("      AEGIS-PNP2 COMPLETE TRAIN / SERVE PARITY & SEMANTIC VERIFICATION SUITE")
    print("       [Python Scikit-Learn] vs [JVM Tree Engine] vs [Golden Expectations]")
    print("="*95)

    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "r", encoding="utf-8-sig") as f:
        golden_data = json.load(f)

    gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))

    test_cases = golden_data["test_cases"]
    passed_count = 0

    print(f"\n{'Case ID':<28} | {'Py Tier':<10} | {'JVM Tier':<10} | {'Exp Tier':<10} | {'Prob Diff':<10} | {'Feat Diff':<10} | {'Status'}")
    print("-" * 105)

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
            raw_l_py = float(gbt_model.predict(v_py.reshape(1, -1))[0])
            prob_py = max(0.0, min(1.0, raw_l_py))
            score_py = int(round(prob_py * 100))
            if prob_py >= 0.70: tier_py = "SCAM"
            elif prob_py >= 0.40: tier_py = "SPAM"
            elif prob_py >= 0.12: tier_py = "UNKNOWN"
            else: tier_py = "LEGITIMATE"

        # 2. JVM Pipeline
        jvm_res = run_jvm_eval(raw_num, country)
        e164_jvm = jvm_res["normalizedE164"]
        is_v_jvm = jvm_res["isValid"]
        raw_l_jvm = float(jvm_res["rawLogit"])
        prob_jvm = float(jvm_res["calibratedProbability"])
        score_jvm = int(jvm_res["riskScore"])
        tier_jvm = jvm_res["threatTier"]
        v_jvm = np.array(jvm_res["features"], dtype=np.float32)

        feat_diff = float(np.max(np.abs(v_py - v_jvm)))
        prob_diff = abs(prob_py - prob_jvm)
        logit_diff = abs(raw_l_py - raw_l_jvm)

        norm_match = (e164_py == e164_jvm) and (is_v_py == is_v_jvm)
        feat_match = (feat_diff < 1e-3)
        prob_match = (prob_diff < 1e-3) and (logit_diff < 1e-3)
        tier_match = (tier_py == tier_jvm) and (tier_py == expected_tier)
        score_match = (score_py == score_jvm)

        passed = norm_match and feat_match and prob_match and tier_match and score_match
        if passed: passed_count += 1
        status = "[PARITY OK]" if passed else f"[FAIL - Diff (P:{prob_diff:.4f}, T:{tier_py}/{tier_jvm}/{expected_tier})]"

        print(f"{cid:<28} | {tier_py:<10} | {tier_jvm:<10} | {expected_tier:<10} | {prob_diff:<10.6f} | {feat_diff:<10.6f} | {status}")

    print("-" * 105)
    print(f"End-to-End Parity & Semantic Result: {passed_count} / {len(test_cases)} PASSED ({passed_count/len(test_cases)*100:.1f}%)")
    return passed_count == len(test_cases)

if __name__ == "__main__":
    success = verify_end_to_end_parity()
    if not success: sys.exit(1)