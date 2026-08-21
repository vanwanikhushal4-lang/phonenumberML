"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2)
End-to-End Prediction Parity Suite with Independent Golden Vectors
[Python Model] vs [Pure JVM Engine] vs [FastAPI Backend] vs [Canonical Reference Expectations]
"""

import os
import sys
import json
import subprocess
import numpy as np
import joblib
from fastapi.testclient import TestClient

os.environ["AEGIS_TEST_MODE"] = "1"
os.environ["AEGIS_SERVER_API_KEY"] = "aegis-test-mode-secure-key-32-chars-long-abcdef"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, normalize_and_parse
from ml.api.server import app, AEGIS_SERVER_API_KEY

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
    print("="*115)
    print("      AEGIS-PNP2 COMPLETE TRAIN / SERVE PARITY & SEMANTIC VERIFICATION SUITE")
    print("       [Python Scikit-Learn] vs [JVM Tree Engine] vs [FastAPI Backend] vs [Golden Expectations]")
    print("="*115)

    compile_jvm_evaluator()
    client = TestClient(app)
    api_headers = {"X-AEGIS-API-KEY": AEGIS_SERVER_API_KEY}

    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "r", encoding="utf-8-sig") as f:
        golden_data = json.load(f)

    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
        calib_meta = json.load(f)

    gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    param_a = calib_meta["param_A"]
    param_b = calib_meta["param_B"]

    test_cases = golden_data["test_cases"]
    passed_count = 0

    print(f"\n{'Case ID':<30} | {'Py Tier':<10} | {'JVM Tier':<10} | {'API Tier':<10} | {'Exp Tier':<10} | {'Prob Diff':<10} | {'Status'}")
    print("-" * 115)

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
            if prob_py >= 0.98: tier_py = "SCAM"
            elif prob_py >= 0.60: tier_py = "SPAM"
            elif prob_py >= 0.10: tier_py = "UNKNOWN"
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

        # 3. FastAPI Endpoint
        api_resp = client.post("/assess/number", json={"raw_number": raw_num, "default_country": country}, headers=api_headers)
        if api_resp.status_code != 200:
            raise RuntimeError(f"FastAPI call failed for {raw_num}: {api_resp.text}")
        api_data = api_resp.json()
        tier_api = api_data["threat_tier"]
        prob_api = float(api_data["calibrated_probability"])

        feat_diff = float(np.max(np.abs(v_py - v_jvm)))
        prob_diff = max(abs(prob_py - prob_jvm), abs(prob_py - prob_api))
        logit_diff = abs(raw_l_py - raw_l_jvm)

        norm_match = (e164_py == e164_jvm == api_data["normalized_e164"]) and (is_v_py == is_v_jvm == api_data["is_valid"])
        feat_match = (feat_diff < 1e-3)
        prob_match = (prob_diff < 1e-3) and (logit_diff < 0.05)
        tier_match = (tier_py == tier_jvm == tier_api == expected_tier)
        score_match = (abs(score_py - score_jvm) <= 1) and (abs(score_py - api_data["pattern_risk_score"]) <= 1)

        passed = norm_match and feat_match and prob_match and tier_match and score_match
        if passed: passed_count += 1
        status = "[PARITY OK]" if passed else f"[FAIL - Diff (P:{prob_diff:.4f}, T:{tier_py}/{tier_jvm}/{tier_api}/{expected_tier})]"

        print(f"{cid:<30} | {tier_py:<10} | {tier_jvm:<10} | {tier_api:<10} | {expected_tier:<10} | {prob_diff:<10.6f} | {status}")

    print("-" * 115)
    print(f"End-to-End Parity & Semantic Result: {passed_count} / {len(test_cases)} PASSED ({passed_count/len(test_cases)*100:.1f}%)")
    return passed_count == len(test_cases)

if __name__ == "__main__":
    success = verify_end_to_end_parity()
    if not success: sys.exit(1)