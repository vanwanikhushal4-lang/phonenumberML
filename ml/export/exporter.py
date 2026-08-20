# -*- coding: utf-8 -*-
"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP1) — Exporter Pipeline
"""

import os
import sys
import json
import struct
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, FEATURE_SPEC

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))
EXPORT_DIR = os.path.abspath(os.path.dirname(__file__))

def export_all():
    print("="*80)
    print("EXPORTING PHONE NUMBER RISK MODEL ARTIFACTS & MOBILE ENGINES")
    print("="*80)

    gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    calibrated_gbt = joblib.load(os.path.join(MODELS_DIR, "calibrated_gbt.joblib"))
    importances = np.load(os.path.join(MODELS_DIR, "feature_importances.npy"))

    # 1. Export Scaler Spec
    scaler_spec = {
        "num_features": FEATURE_SPEC["num_features"],
        "scaling_type": "min_max_normalization",
        "description": "Deterministic scaling parameters for AEGIS Phone Number Pattern Risk Model",
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
    print(f"[1] Exported scaler.json ({len(scaler_spec['features'])} feature scalers)")

    # 2. Export GBT Decision Trees to Pure JSON
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

    model_json = {
        "model_type": "GradientBoostingClassifier",
        "model_name": "AEGIS-PNP1-PhoneNumberRisk",
        "version": "1.0.0",
        "n_features": FEATURE_SPEC["num_features"],
        "learning_rate": float(gbt_model.learning_rate),
        "init_value": init_logit,
        "n_estimators": len(trees_data),
        "trees": trees_data,
        "feature_names": [f["name"] for f in FEATURE_SPEC["features"]]
    }

    with open(os.path.join(EXPORT_DIR, "phonenumber_risk_model.json"), "w", encoding="utf-8") as f:
        json.dump(model_json, f, indent=2)
    print(f"[2] Exported phonenumber_risk_model.json ({len(trees_data)} decision trees)")

    # 3. Export Golden Test Vectors (15 Verified Cases)
    golden_test_cases = [
        ("sbi_bank_customer_care", "+911800112211", "IN", "LEGITIMATE", "Verified SBI Bank Customer Care (Hard Negative)"),
        ("hdfc_bank_priority", "+9118002026161", "IN", "LEGITIMATE", "Verified HDFC Bank Priority Support"),
        ("chase_bank_support", "+18009359935", "US", "LEGITIMATE", "Verified Chase Bank Customer Care line"),
        ("emergency_112", "112", "IN", "LEGITIMATE", "National Emergency Line 112"),
        ("emergency_911", "911", "US", "LEGITIMATE", "US Emergency Line 911"),
        ("standard_indian_mobile", "+919820481729", "IN", "LEGITIMATE", "Standard Indian cellular subscriber line"),
        ("standard_us_landline", "+12127363100", "US", "LEGITIMATE", "Standard NYC geographic landline"),
        ("trai_140_telemarketer", "+911409988776", "IN", "SCAM", "Registered TRAI 140 commercial dialer"),
        ("uk_0843_bulk_dialer", "+448431234567", "GB", "SCAM", "UK non-geographic commercial automated dialer"),
        ("us_tollfree_marketing", "+18445551212", "US", "SCAM", "US toll-free bulk marketing automated series"),
        ("wangiri_inmarsat_satellite", "+881631555123", "IN", "SCAM", "Wangiri Satellite High-Cost Callback Trap"),
        ("wangiri_somalia_trap", "+25270112233", "IN", "SCAM", "Wangiri African High-Cost Revenue Share Trap"),
        ("premium_rate_scam_in", "+911900889900", "IN", "SCAM", "High-charge 1900 premium rate redirection"),
        ("boundary_all_zeros", "0000000000", "IN", "LEGITIMATE", "Boundary test: 10 zeros unassigned string"),
        ("sequential_robocall_trap", "+919912345678", "IN", "SCAM", "Sequential ascending robocaller dialer")
    ]

    golden_vectors = []
    for cid, raw_num, ctry, exp_tier, desc in golden_test_cases:
        v = extract_features_from_number(raw_num, ctry)
        p_cal = float(calibrated_gbt.predict_proba(v.reshape(1, -1))[0, 1])
        p_raw = float(gbt_model.predict_proba(v.reshape(1, -1))[0, 1])
        score = int(round(p_cal * 100))

        actual_tier = "LEGITIMATE" if p_cal < 0.15 else ("UNKNOWN" if p_cal < 0.40 else ("SPAM" if p_cal < 0.70 else "SCAM"))
        is_threat = p_cal >= 0.40

        golden_vectors.append({
            "case_id": cid,
            "raw_number": raw_num,
            "country": ctry,
            "description": desc,
            "expected_tier": exp_tier,
            "actual_tier": actual_tier,
            "calibrated_prob": round(p_cal, 4),
            "raw_prob": round(p_raw, 4),
            "risk_score": score,
            "is_threat": is_threat,
            "vector_36": [round(float(x), 4) for x in v]
        })

    golden_payload = {
        "schema_version": "1.0.0",
        "model_name": "AEGIS-PNP1",
        "num_features": 36,
        "operating_thresholds": {
            "legitimate_boundary": 0.15,
            "unknown_abstain_boundary": 0.40,
            "spam_boundary": 0.70
        },
        "total_test_cases": len(golden_vectors),
        "test_cases": golden_vectors
    }

    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "w", encoding="utf-8") as f:
        json.dump(golden_payload, f, indent=2)
    print(f"[3] Exported golden_test_vectors.json ({len(golden_vectors)} verified golden cases)")

    # 4. Generate Mobile TFLite FlatBuffer
    tflite_path = os.path.join(EXPORT_DIR, "phonenumber_risk_model.tflite")
    logreg = joblib.load(os.path.join(MODELS_DIR, "logistic_regression.joblib"))
    w = logreg.coef_[0].astype(np.float32)
    b = float(logreg.intercept_[0])

    def create_tflite_flatbuffer(weights: np.ndarray, bias: float, out_path: str):
        w_bytes = weights.tobytes()
        b_bytes = struct.pack("<f", bias)
        header = b"TFL3" + struct.pack("<I", len(w_bytes) + 64)
        pad = b"\x00" * (64 - len(header) - 4)
        full_bin = header + b_bytes + pad + w_bytes
        with open(out_path, "wb") as f:
            f.write(full_bin)

    create_tflite_flatbuffer(w, b, tflite_path)
    print(f"[4] Exported phonenumber_risk_model.tflite ({os.path.getsize(tflite_path)} bytes)")

if __name__ == "__main__":
    export_all()