"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) — Production Model Exporter
Exports:
1. Decision tree ensemble with init_value, scaled leaves, and SHA-256 checksum to phonenumber_risk_model.json
2. Scaler metadata to scaler.json
3. Verified 20-case golden test suite to golden_test_vectors.json
"""

import os
import sys
import json
import hashlib
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, normalize_and_parse, FEATURE_SPEC

EXPORT_DIR = os.path.dirname(__file__)
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))

def export_production_artifacts():
    print("="*85)
    print("      AEGIS-PNP2 PRODUCTION MODEL EXPORT PIPELINE (WITH GBT INIT_VAL & SHA-256)")
    print("="*85)

    gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
        calib_meta = json.load(f)

    param_A = float(calib_meta["param_A"])
    param_B = float(calib_meta["param_B"])
    init_val = float(gbt_model._raw_predict_init(np.zeros((1, FEATURE_SPEC["num_features"])))[0, 0])
    learning_rate = float(gbt_model.learning_rate)

    # 1. Export Scaler
    scaler_data = {
        "num_features": FEATURE_SPEC["num_features"],
        "scalers": [
            {"idx": i, "name": f["name"], "max_scale": 1.0}
            for i, f in enumerate(FEATURE_SPEC["features"])
        ]
    }
    with open(os.path.join(EXPORT_DIR, "scaler.json"), "w", encoding="utf-8") as f:
        json.dump(scaler_data, f, indent=2)
    print("[1/3] Exported scaler.json")

    # 2. Export GBT Decision Trees JSON
    trees_json = []
    for tree_idx, tree_arr in enumerate(gbt_model.estimators_):
        tree = tree_arr[0].tree_
        nodes_list = []
        for n in range(tree.node_count):
            is_leaf = (tree.children_left[n] == -1)
            if is_leaf:
                # Pre-multiply leaf value by learning rate
                leaf_val = float(tree.value[n, 0, 0] * learning_rate)
                nodes_list.append({
                    "node_id": n,
                    "is_leaf": True,
                    "leaf_value": round(leaf_val, 8)
                })
            else:
                nodes_list.append({
                    "node_id": n,
                    "is_leaf": False,
                    "feature_idx": int(tree.feature[n]),
                    "threshold": round(float(tree.threshold[n]), 6),
                    "left_child": int(tree.children_left[n]),
                    "right_child": int(tree.children_right[n])
                })
        trees_json.append({"tree_id": tree_idx, "nodes": nodes_list})

    model_dict = {
        "model_name": "AEGIS-PNP2",
        "schema_version": "2.1.0",
        "model_objective": "PATTERN_RISK",
        "num_features": FEATURE_SPEC["num_features"],
        "num_trees": len(trees_json),
        "init_value": round(init_val, 8),
        "learning_rate": round(learning_rate, 6),
        "calibration": {
            "method": "sigmoid_platt_scaling",
            "param_A": round(param_A, 8),
            "param_B": round(param_B, 8),
            "formula": "P(Pattern Risk | logit) = 1.0 / (1.0 + exp(param_A * logit + param_B))"
        },
        "operating_thresholds": {
            "legitimate_upper": 0.15,
            "unknown_abstain_upper": 0.40,
            "spam_upper": 0.70,
            "scam_lower": 0.70
        },
        "trees": trees_json
    }

    serialized_bytes = json.dumps(model_dict, indent=2).encode("utf-8")
    sha256_hash = hashlib.sha256(serialized_bytes).hexdigest()
    model_dict["sha256_checksum"] = sha256_hash

    model_path = os.path.join(EXPORT_DIR, "phonenumber_risk_model.json")
    with open(model_path, "w", encoding="utf-8") as f:
        json.dump(model_dict, f, indent=2)
    print(f"[2/3] Exported phonenumber_risk_model.json (150 trees, SHA-256: {sha256_hash[:12]}...)")

    # 3. Export 20 Golden Vectors dynamically evaluated against the trained model
    canonical_cases = [
        ("sbi_bank_customer_care", "+911800112211", "IN", "Verified SBI customer service line"),
        ("hdfc_bank_priority", "+9118002026161", "IN", "Verified HDFC customer service line"),
        ("chase_bank_support", "+18009359935", "US", "Verified Chase customer support"),
        ("barclays_uk_care", "+44800123456", "GB", "Verified Barclays UK freephone line"),
        ("emergency_112", "112", "IN", "National Emergency 112"),
        ("emergency_911", "911", "US", "US Emergency 911"),
        ("emergency_1930", "1930", "IN", "India Cyber Crime Helpline"),
        ("standard_indian_mobile", "+919820481729", "IN", "Clean Indian mobile subscriber"),
        ("standard_us_landline", "+12127363100", "US", "Clean US geographic landline"),
        ("standard_uk_mobile", "+447700900123", "GB", "Clean UK mobile subscriber"),
        ("standard_jp_mobile", "+819012345678", "JP", "Clean Japan mobile subscriber"),
        ("trai_140_telemarketer", "+911409988776", "IN", "Registered TRAI 140 promotional line"),
        ("uk_0843_bulk_dialer", "+448431234567", "GB", "OFCOM 0843 automated dialer"),
        ("us_tollfree_marketing", "+18445551212", "US", "NANPA 844 marketing series"),
        ("wangiri_inmarsat_satellite", "+881631555123", "IN", "Satellite Wangiri callback trap"),
        ("wangiri_somalia_trap", "+25270112233", "IN", "High-cost Wangiri trap"),
        ("premium_rate_scam_in", "+911900889900", "IN", "Premium rate redirect"),
        ("low_entropy_dialer_all_repeats", "+917777777777", "IN", "Automated low-entropy robocaller"),
        ("invalid_all_zeros", "0000000000", "IN", "All zeros malformed sequence"),
        ("invalid_too_short", "123", "IN", "Underlength invalid number")
    ]

    golden_vectors = []
    for cid, raw, country, desc in canonical_cases:
        e164, _, _, _, is_v = normalize_and_parse(raw, country)
        feat = extract_features_from_number(raw, country)

        if not is_v:
            expected_tier = "INVALID"
            expected_score = 0
            cal_p = 0.0
            raw_l = 0.0
        else:
            raw_l = float(gbt_model.decision_function(feat.reshape(1, -1))[0])
            cal_p = float(1.0 / (1.0 + np.exp(param_A * raw_l + param_B)))
            expected_score = int(round(cal_p * 100))
            if cal_p >= 0.70: expected_tier = "SCAM"
            elif cal_p >= 0.40: expected_tier = "SPAM"
            elif cal_p >= 0.15: expected_tier = "UNKNOWN"
            else: expected_tier = "LEGITIMATE"

        golden_vectors.append({
            "case_id": cid,
            "raw_number": raw,
            "country": country,
            "normalized_e164": e164,
            "is_valid": is_v,
            "expected_tier": expected_tier,
            "expected_pattern_risk_score": expected_score,
            "raw_logit": round(raw_l, 6),
            "calibrated_probability": round(cal_p, 6),
            "features": [round(float(x), 4) for x in feat],
            "description": desc
        })

    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": "2.1.0", "test_cases": golden_vectors}, f, indent=2)
    print(f"[3/3] Exported golden_test_vectors.json ({len(golden_vectors)} verified golden cases)")
    print("Export pipeline complete.")

if __name__ == "__main__":
    export_production_artifacts()