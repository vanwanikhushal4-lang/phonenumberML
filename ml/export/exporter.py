# -*- coding: utf-8 -*-
"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) — Production Exporter Pipeline
Exports:
1. phonenumber_risk_model.json (Complete trees + exact Sigmoid calibration constants A, B + SHA256 integrity)
2. scaler.json (Deterministic normalization constants)
3. golden_test_vectors.json (20 canonical end-to-end test cases)
"""

import os
import sys
import json
import hashlib
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, normalize_and_parse, explain_instance, FEATURE_SPEC

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))
EXPORT_DIR = os.path.abspath(os.path.dirname(__file__))

def export_all():
    print("="*85)
    print("      AEGIS-PNP2 MODEL EXPORT PIPELINE (CALIBRATED TREES & GOLDEN SUITE)")
    print("="*85)

    gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
        calib_meta = json.load(f)

    param_A = float(calib_meta["param_A"])
    param_B = float(calib_meta["param_B"])

    # 1. Export Scaler Spec
    scaler_spec = {
        "num_features": FEATURE_SPEC["num_features"],
        "scaling_type": "min_max_normalization",
        "description": "Deterministic scaling parameters for AEGIS-PNP2",
        "features": []
    }
    for feat in FEATURE_SPEC["features"]:
        name = feat["name"]
        idx = feat["index"]
        cat = feat.get("category", "general")
        divisor = 1.0
        if name in ("num_national_length_normalized", "num_length_discrepancy"): divisor = 15.0
        elif name == "digit_shannon_entropy": divisor = 3.321928
        elif name in ("digit_max_repeat_run", "digit_max_sequential_asc", "digit_max_sequential_desc"): divisor = 10.0
        elif name == "digit_trailing_zeros_count": divisor = 8.0
        elif name == "digit_variance_density": divisor = 5.0

        scaler_spec["features"].append({
            "index": idx,
            "name": name,
            "category": cat,
            "type": feat["type"],
            "scale_divisor": float(divisor),
            "min_val": 0.0,
            "max_val": 1.0
        })

    with open(os.path.join(EXPORT_DIR, "scaler.json"), "w", encoding="utf-8") as f:
        json.dump(scaler_spec, f, indent=2)
    print(f"[1/3] Exported scaler.json ({len(scaler_spec['features'])} feature scalers)")

    # 2. Export GBT Decision Trees + Sigmoid Parameters (A, B)
    trees_data = []
    for estimator in gbt_model.estimators_:
        tree = estimator[0].tree_
        node_count = int(tree.node_count)
        children_left = tree.children_left.tolist()
        children_right = tree.children_right.tolist()
        feature = tree.feature.tolist()
        threshold = tree.threshold.tolist()
        value = tree.value.squeeze().tolist()
        if not isinstance(value, list):
            value = [value]

        trees_data.append({
            "node_count": node_count,
            "children_left": children_left,
            "children_right": children_right,
            "feature": feature,
            "threshold": threshold,
            "value": value
        })

    p0, p1 = gbt_model.init_.class_prior_
    init_logit = float(np.log(p1 / p0))

    trees_bytes = json.dumps(trees_data, sort_keys=True).encode("utf-8")
    model_sha256 = hashlib.sha256(trees_bytes).hexdigest()

    model_json = {
        "model_type": "GradientBoostingClassifier",
        "model_name": "AEGIS-PNP2-PhoneNumberRisk",
        "version": "2.0.0",
        "sha256_checksum": model_sha256,
        "n_features": FEATURE_SPEC["num_features"],
        "learning_rate": float(gbt_model.learning_rate),
        "init_value": init_logit,
        "calibration": {
            "method": "sigmoid_platt_scaling",
            "param_A": param_A,
            "param_B": param_B,
            "formula": "P(Threat | logit) = 1.0 / (1.0 + exp(A * logit + B))"
        },
        "operating_thresholds": {
            "legitimate_upper_bound": 0.15,
            "unknown_abstain_upper_bound": 0.40,
            "spam_upper_bound": 0.70,
            "scam_lower_bound": 0.70
        },
        "n_estimators": len(trees_data),
        "trees": trees_data,
        "feature_names": [f["name"] for f in FEATURE_SPEC["features"]]
    }

    with open(os.path.join(EXPORT_DIR, "phonenumber_risk_model.json"), "w", encoding="utf-8") as f:
        json.dump(model_json, f, indent=2)
    print(f"[2/3] Exported phonenumber_risk_model.json ({len(trees_data)} trees, SHA-256: {model_sha256[:12]}...)")

    # 3. Export 20 Golden End-to-End Test Vectors
    golden_test_cases = [
        # Hard Negatives (Banks & Emergency)
        ("sbi_bank_customer_care", "+911800112211", "IN", "LEGITIMATE", "Verified SBI Bank Customer Care (Hard Negative)"),
        ("hdfc_bank_priority", "+9118002026161", "IN", "LEGITIMATE", "Verified HDFC Bank Priority Support"),
        ("chase_bank_support", "+18009359935", "US", "LEGITIMATE", "Verified Chase Bank Customer Care line"),
        ("barclays_uk_care", "+44800123456", "GB", "LEGITIMATE", "Verified Barclays UK Toll-Free Support"),
        ("emergency_112", "112", "IN", "LEGITIMATE", "National Emergency Line 112"),
        ("emergency_911", "911", "US", "LEGITIMATE", "US Emergency Line 911"),
        ("emergency_1930", "1930", "IN", "LEGITIMATE", "National Cyber Crime Reporting Portal Helpline"),
        
        # Standard Unknown Mobile & Landlines
        ("standard_indian_mobile", "+919820481729", "IN", "UNKNOWN", "Standard Indian cellular subscriber line"),
        ("standard_us_landline", "+12127363100", "US", "UNKNOWN", "Standard NYC geographic landline"),
        ("standard_uk_mobile", "+447700900123", "GB", "UNKNOWN", "Standard UK mobile subscriber"),
        ("standard_jp_mobile", "+819012345678", "JP", "UNKNOWN", "Standard Japan cellular subscriber (090)"),
        
        # Real Threats (Telemarketers, Robocalls, Premium Fraud, Wangiri)
        ("trai_140_telemarketer", "+911409988776", "IN", "SPAM", "Registered TRAI 140 commercial marketing dialer"),
        ("uk_0843_bulk_dialer", "+448431234567", "GB", "SPAM", "UK non-geographic commercial automated dialer"),
        ("us_tollfree_marketing", "+18445551212", "US", "SPAM", "US toll-free bulk marketing automated series"),
        ("wangiri_inmarsat_satellite", "+881631555123", "IN", "SCAM", "Wangiri Satellite High-Cost Callback Trap"),
        ("wangiri_somalia_trap", "+25270112233", "IN", "SCAM", "Wangiri African High-Cost Revenue Share Trap"),
        ("premium_rate_scam_in", "+911900889900", "IN", "SCAM", "High-charge 1900 premium rate redirection"),
        ("low_entropy_dialer_all_repeats", "+917777777777", "IN", "SPAM", "10-digit repeated automated dialer"),
        
        # Invalid Inputs (Malformed / All Zeros)
        ("invalid_all_zeros", "0000000000", "IN", "INVALID", "Malformed all-zeros string"),
        ("invalid_too_short", "123", "IN", "INVALID", "Incomplete invalid number string")
    ]

    golden_vectors = []
    for cid, raw_num, ctry, exp_tier, desc in golden_test_cases:
        e164, cc, nat, std_l, is_v = normalize_and_parse(raw_num, ctry)
        v = extract_features_from_number(raw_num, ctry)
        raw_logit = float(gbt_model.decision_function(v.reshape(1, -1))[0])
        # Exact Sigmoid Calibration
        calibrated_prob = float(1.0 / (1.0 + np.exp(param_A * raw_logit + param_B)))
        score = int(round(calibrated_prob * 100))

        if not is_v:
            actual_tier = "INVALID"
            confidence = "HIGH"
        elif calibrated_prob < 0.15:
            actual_tier = "LEGITIMATE"
            confidence = "HIGH"
        elif calibrated_prob < 0.40:
            actual_tier = "UNKNOWN"
            confidence = "LOW"
        elif calibrated_prob < 0.70:
            actual_tier = "SPAM"
            confidence = "MEDIUM"
        else:
            actual_tier = "SCAM"
            confidence = "HIGH"

        is_threat = (actual_tier in ("SPAM", "SCAM"))
        is_invalid = (actual_tier == "INVALID")
        reasons = [code for code, _, _ in explain_instance(v, top_k=3)]

        golden_vectors.append({
            "case_id": cid,
            "raw_number": raw_num,
            "normalized_e164": e164,
            "country": ctry,
            "is_valid": is_v,
            "description": desc,
            "expected_tier": exp_tier,
            "actual_tier": actual_tier,
            "raw_logit": round(raw_logit, 6),
            "calibrated_prob": round(calibrated_prob, 6),
            "risk_score": score,
            "confidence": confidence,
            "is_threat": is_threat,
            "is_invalid": is_invalid,
            "top_reason_codes": reasons,
            "vector_36": [round(float(x), 4) for x in v]
        })

    golden_payload = {
        "schema_version": "2.0.0",
        "model_name": "AEGIS-PNP2",
        "total_test_cases": len(golden_vectors),
        "calibration_constants": {
            "param_A": param_A,
            "param_B": param_B
        },
        "operating_thresholds": {
            "legitimate_upper_bound": 0.15,
            "unknown_abstain_upper_bound": 0.40,
            "spam_upper_bound": 0.70,
            "scam_lower_bound": 0.70
        },
        "test_cases": golden_vectors
    }

    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "w", encoding="utf-8") as f:
        json.dump(golden_payload, f, indent=2)
    print(f"[3/3] Exported golden_test_vectors.json ({len(golden_vectors)} verified golden cases)")

    print("Export pipeline complete.")

if __name__ == "__main__":
    export_all()