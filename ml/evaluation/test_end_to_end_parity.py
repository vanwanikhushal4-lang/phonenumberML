"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2)
End-to-End Prediction Parity Suite with Independent Golden Vectors
[Python Model] vs [Pure JVM Engine] vs [Independently Authored Expectations]
"""

import os
import sys
import json
import subprocess
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, normalize_and_parse

EVAL_DIR = os.path.dirname(__file__)
EXPORT_DIR = os.path.abspath(os.path.join(EVAL_DIR, "../export"))
MODELS_DIR = os.path.abspath(os.path.join(EVAL_DIR, "../models/saved_models"))
LIB_JAR = os.path.join(EVAL_DIR, "lib/libphonenumber-8.13.52.jar")

def compile_jvm_evaluator():
    cp = f"{LIB_JAR}{os.pathsep}{EVAL_DIR}"
    cmd = ["javac", "-cp", cp, "-d", EVAL_DIR, os.path.join(EVAL_DIR, "JvmPhoneNumberEvaluator.java")]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print("[-] Failed to compile JvmPhoneNumberEvaluator.java:\n", res.stderr)
        sys.exit(1)

def run_jvm_eval(raw_number: str, country: str = "IN") -> dict:
    model_json = os.path.join(EXPORT_DIR, "phonenumber_risk_model.json")
    cp = f"{LIB_JAR}{os.pathsep}{EVAL_DIR}"
    cmd = ["java", "-cp", cp, "JvmPhoneNumberEvaluator", raw_number, country, model_json]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"JVM execution failed: {res.stderr}")
    return json.loads(res.stdout.strip())

def verify_end_to_end_parity():
    print("="*105)
    print("      AEGIS-PNP2 COMPLETE TRAIN / SERVE PARITY & SEMANTIC VERIFICATION SUITE")
    print("       [Python Scikit-Learn] vs [JVM Tree Engine] vs [Golden Expectations]")
    print("="*105)

    compile_jvm_evaluator()

    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "r", encoding="utf-8-sig") as f:
        golden_data = json.load(f)

    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
        calib_meta = json.load(f)

    gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    param_a = calib_meta["param_A"]
    param_b = calib_meta["param_B"]

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
            prob_py = 1.0 / (1.0 + np.exp(-(param_a * raw_l_py + param_b)))
            score_py = int(round(max(0.0, min(1.0, raw_l_py)) * 100))
            if raw_l_py >= 0.70: tier_py = "SCAM"
            elif raw_l_py >= 0.40: tier_py = "SPAM"
            elif raw_l_py >= 0.15: tier_py = "UNKNOWN"
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
        prob_match = (prob_diff < 1e-3) and (logit_diff < 0.05)
        tier_match = (tier_py == tier_jvm) and (tier_py == expected_tier)
        score_match = (abs(score_py - score_jvm) <= 1)

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