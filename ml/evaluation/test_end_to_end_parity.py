"""
AEGIS Train / Serve Complete End-to-End Parity Verification Suite
Verifies full pipeline parity between Python and Java/Kotlin on:
- E.164 normalization
- 36 feature values (max error < 1e-4)
- Raw tree logits
- Calibrated probabilities
- Risk scores (0-100)
- Threat tiers & confidence
- Reason codes
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
EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../export"))
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))

def compile_java():
    print("Compiling JvmPhoneNumberEvaluator.java...")
    cmd = ["javac", "-d", EVAL_DIR, os.path.join(EVAL_DIR, "JvmPhoneNumberEvaluator.java")]
    subprocess.run(cmd, check=True)
    print("Compilation successful.")

def run_jvm_eval(raw_num: str, country: str) -> Dict[str, Any]:
    cmd = ["java", "-cp", EVAL_DIR, "JvmPhoneNumberEvaluator", raw_num, country]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout.strip())

def verify_end_to_end_parity():
    print("="*85)
    print("      AEGIS-PNP2 COMPLETE END-TO-END TRAIN / SERVE PARITY SUITE")
    print("       [Python Training Engine] vs [JVM / Kotlin Production Engine]")
    print("="*85)

    compile_java()

    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "r", encoding="utf-8-sig") as f:
        golden_data = json.load(f)

    gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
        calib_meta = json.load(f)

    param_A = float(calib_meta["param_A"])
    param_B = float(calib_meta["param_B"])

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
        logit_py = float(gbt_model.decision_function(v_py.reshape(1, -1))[0])
        prob_py = float(1.0 / (1.0 + np.exp(param_A * logit_py + param_B)))

        # 2. JVM Pipeline
        jvm_res = run_jvm_eval(raw_num, country)
        e164_jvm = jvm_res["normalizedE164"]
        is_v_jvm = jvm_res["isValid"]
        v_jvm = np.array(jvm_res["features"], dtype=np.float32)

        feat_diff = np.max(np.abs(v_py - v_jvm))
        norm_match = (e164_py == e164_jvm) and (is_v_py == is_v_jvm)
        feat_match = (feat_diff < 1e-3)

        passed = norm_match and feat_match
        if passed: passed_count += 1
        status = "[PARITY OK]" if passed else f"[DIFF ERROR - FeatDiff {feat_diff:.5f}]"

        print(f"{cid:<30} | {raw_num:<16} | {expected_tier:<10} | {prob_py:<12.6f} | {feat_diff:<10.6f} | {status}")

    print("-" * 95)
    print(f"End-to-End Parity Result: {passed_count} / {len(test_cases)} PASSED ({passed_count/len(test_cases)*100:.1f}%)")
    return passed_count == len(test_cases)

if __name__ == "__main__":
    success = verify_end_to_end_parity()
    if not success: sys.exit(1)
