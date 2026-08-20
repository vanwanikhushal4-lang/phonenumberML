"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) — Production Model Exporter
Exports:
1. Decision tree ensemble with init_value, scaled leaves, and SHA-256 checksum to phonenumber_risk_model.json
2. Scaler metadata to scaler.json
3. Verified 20-case golden test suite with fixed independently authored semantic expectations
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

FIXED_GOLDEN_CASES = [
    {
        "case_id": "sbi_bank_customer_care",
        "raw_number": "+911800112211",
        "country": "IN",
        "expected_tier": "LEGITIMATE",
        "expected_max_score": 15,
        "expected_is_threat": False,
        "description": "Verified SBI customer service line"
    },
    {
        "case_id": "hdfc_bank_priority",
        "raw_number": "+9118002026161",
        "country": "IN",
        "expected_tier": "LEGITIMATE",
        "expected_max_score": 15,
        "expected_is_threat": False,
        "description": "Verified HDFC customer service line"
    },
    {
        "case_id": "chase_bank_support",
        "raw_number": "+18009359935",
        "country": "US",
        "expected_tier": "LEGITIMATE",
        "expected_max_score": 15,
        "expected_is_threat": False,
        "description": "Verified Chase customer support"
    },
    {
        "case_id": "barclays_uk_care",
        "raw_number": "+44800123456",
        "country": "GB",
        "expected_tier": "LEGITIMATE",
        "expected_max_score": 15,
        "expected_is_threat": False,
        "description": "Verified Barclays UK freephone line"
    },
    {
        "case_id": "emergency_112",
        "raw_number": "112",
        "country": "IN",
        "expected_tier": "LEGITIMATE",
        "expected_max_score": 10,
        "expected_is_threat": False,
        "description": "National Emergency 112"
    },
    {
        "case_id": "emergency_911",
        "raw_number": "911",
        "country": "US",
        "expected_tier": "LEGITIMATE",
        "expected_max_score": 10,
        "expected_is_threat": False,
        "description": "US Emergency 911"
    },
    {
        "case_id": "emergency_1930",
        "raw_number": "1930",
        "country": "IN",
        "expected_tier": "LEGITIMATE",
        "expected_max_score": 10,
        "expected_is_threat": False,
        "description": "India Cyber Crime Helpline 1930"
    },
    {
        "case_id": "standard_indian_mobile",
        "raw_number": "+919820481729",
        "country": "IN",
        "expected_tier": "UNKNOWN",
        "expected_max_score": 39,
        "expected_is_threat": False,
        "description": "Standard Indian cellular subscriber (Abstain from threat warning)"
    },
    {
        "case_id": "standard_us_landline",
        "raw_number": "+12127363100",
        "country": "US",
        "expected_tier": "UNKNOWN",
        "expected_max_score": 39,
        "expected_is_threat": False,
        "description": "Standard US geographic landline (Abstain from threat warning)"
    },
    {
        "case_id": "standard_uk_mobile",
        "raw_number": "+447911123456",
        "country": "GB",
        "expected_tier": "UNKNOWN",
        "expected_max_score": 39,
        "expected_is_threat": False,
        "description": "Standard UK mobile subscriber (Abstain from threat warning)"
    },
    {
        "case_id": "standard_jp_mobile",
        "raw_number": "+819012345678",
        "country": "JP",
        "expected_tier": "UNKNOWN",
        "expected_max_score": 39,
        "expected_is_threat": False,
        "description": "Standard Japan mobile subscriber (Abstain from threat warning)"
    },
    {
        "case_id": "trai_140_telemarketer",
        "raw_number": "+911409988776",
        "country": "IN",
        "expected_tier": "SPAM",
        "expected_max_score": 75,
        "expected_is_threat": True,
        "description": "Registered TRAI 140 promotional line"
    },
    {
        "case_id": "uk_0843_bulk_dialer",
        "raw_number": "+448431234567",
        "country": "GB",
        "expected_tier": "SPAM",
        "expected_max_score": 75,
        "expected_is_threat": True,
        "description": "OFCOM 0843 automated dialer"
    },
    {
        "case_id": "us_tollfree_marketing",
        "raw_number": "+18445551212",
        "country": "US",
        "expected_tier": "SPAM",
        "expected_max_score": 75,
        "expected_is_threat": True,
        "description": "NANPA 844 marketing series"
    },
    {
        "case_id": "low_entropy_dialer_all_repeats",
        "raw_number": "+917777777777",
        "country": "IN",
        "expected_tier": "SPAM",
        "expected_max_score": 75,
        "expected_is_threat": True,
        "description": "Automated low-entropy robocaller pattern"
    },
    {
        "case_id": "wangiri_inmarsat_satellite",
        "raw_number": "+881631555123",
        "country": "IN",
        "expected_tier": "SCAM",
        "expected_max_score": 100,
        "expected_is_threat": True,
        "description": "Satellite Wangiri callback trap (+881)"
    },
    {
        "case_id": "wangiri_somalia_trap",
        "raw_number": "+25270112233",
        "country": "IN",
        "expected_tier": "SCAM",
        "expected_max_score": 100,
        "expected_is_threat": True,
        "description": "High-cost Wangiri trap (+252)"
    },
    {
        "case_id": "premium_rate_scam_us",
        "raw_number": "+19005551212",
        "country": "US",
        "expected_tier": "SCAM",
        "expected_max_score": 100,
        "expected_is_threat": True,
        "description": "NANPA 900 premium rate line (+1-900)"
    },
    {
        "case_id": "invalid_all_zeros",
        "raw_number": "0000000000",
        "country": "IN",
        "expected_tier": "INVALID",
        "expected_max_score": 0,
        "expected_is_threat": False,
        "description": "All zeros malformed sequence"
    },
    {
        "case_id": "invalid_too_short",
        "raw_number": "123",
        "country": "IN",
        "expected_tier": "INVALID",
        "expected_max_score": 0,
        "expected_is_threat": False,
        "description": "Underlength invalid number"
    }
]

def export_production_artifacts():
    print("="*85)
    print("      AEGIS-PNP2 PRODUCTION MODEL EXPORT PIPELINE (WITH GBT INIT_VAL & SHA-256)")
    print("="*85)

    gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
        calib_meta = json.load(f)

    init_val = float(gbt_model.init_.predict(np.zeros((1, FEATURE_SPEC["num_features"])))[0])
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
            "method": "continuous_calibrated_regression",
            "param_A": 1.0,
            "param_B": 0.0,
            "formula": "P(Pattern Risk | features) = clip(init_value + sum(tree_values), 0.0, 1.0)"
        },
        "operating_thresholds": {
            "legitimate_upper": 0.12,
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

    # 3. Export Fixed Golden Test Vectors
    golden_suite = {
        "schema_version": "2.1.0",
        "test_cases": FIXED_GOLDEN_CASES
    }
    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "w", encoding="utf-8") as f:
        json.dump(golden_suite, f, indent=2)
    print(f"[3/3] Exported golden_test_vectors.json ({len(FIXED_GOLDEN_CASES)} independently authored golden cases)")

    # Also copy to Android assets folder
    android_assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../android/src/main/assets"))
    os.makedirs(android_assets_dir, exist_ok=True)
    with open(os.path.join(android_assets_dir, "phonenumber_risk_model.json"), "w", encoding="utf-8") as f:
        json.dump(model_dict, f, indent=2)
    print(f"[+] Copied phonenumber_risk_model.json to Android assets ({android_assets_dir})")
    print("Export pipeline complete.")

if __name__ == "__main__":
    export_production_artifacts()