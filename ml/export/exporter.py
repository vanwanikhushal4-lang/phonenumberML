"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) — Production Model Exporter
Exports:
1. phonenumber_risk_model.json with 150 trees, init_value, Platt parameters, SHA-256 integrity hash
2. scaler.json
3. golden_test_vectors.json with 25 independently authored golden test cases
"""

import os
import sys
import json
import hashlib
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import FEATURE_SPEC

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))
EXPORT_DIR = os.path.dirname(__file__)
ANDROID_ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../android/src/main/assets"))

INDEPENDENT_GOLDEN_VECTORS = [
    # 1. HARD NEGATIVES (Certified Banks & Emergency Helplines -> LEGITIMATE)
    {"case_id": "sbi_bank_customer_care", "raw_number": "+911800112211", "country": "IN", "expected_tier": "LEGITIMATE", "expected_is_threat": False, "category": "Bank Helpline"},
    {"case_id": "hdfc_bank_priority", "raw_number": "+9118002026161", "country": "IN", "expected_tier": "LEGITIMATE", "expected_is_threat": False, "category": "Bank Helpline"},
    {"case_id": "chase_bank_support", "raw_number": "+18009359935", "country": "US", "expected_tier": "LEGITIMATE", "expected_is_threat": False, "category": "Bank Helpline"},
    {"case_id": "barclays_uk_care", "raw_number": "+44800123456", "country": "GB", "expected_tier": "LEGITIMATE", "expected_is_threat": False, "category": "Bank Helpline"},
    {"case_id": "us_tollfree_800_standard", "raw_number": "+18005550100", "country": "US", "expected_tier": "LEGITIMATE", "expected_is_threat": False, "category": "NANPA 800 Toll-Free Line"},
    {"case_id": "emergency_112", "raw_number": "112", "country": "IN", "expected_tier": "LEGITIMATE", "expected_is_threat": False, "category": "Emergency Shortcode"},
    {"case_id": "emergency_911", "raw_number": "911", "country": "US", "expected_tier": "LEGITIMATE", "expected_is_threat": False, "category": "Emergency Shortcode"},
    {"case_id": "emergency_1930", "raw_number": "1930", "country": "IN", "expected_tier": "LEGITIMATE", "expected_is_threat": False, "category": "Cyber Crime Helpline"},

    # 2. TOLL-FREE REGRESSION COUNTEREXAMPLES (US 833, 844, 855, 866, 877, 888 -> UNKNOWN / Abstain)
    {"case_id": "us_tollfree_833_standard", "raw_number": "+18335550101", "country": "US", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "NANPA 833 Toll-Free Line"},
    {"case_id": "us_tollfree_844_standard", "raw_number": "+18445550102", "country": "US", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "NANPA 844 Toll-Free Line"},
    {"case_id": "us_tollfree_855_standard", "raw_number": "+18555550103", "country": "US", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "NANPA 855 Toll-Free Line"},
    {"case_id": "us_tollfree_866_standard", "raw_number": "+18665550104", "country": "US", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "NANPA 866 Toll-Free Line"},
    {"case_id": "us_tollfree_877_standard", "raw_number": "+18775550105", "country": "US", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "NANPA 877 Toll-Free Line"},
    {"case_id": "us_tollfree_888_standard", "raw_number": "+18885550106", "country": "US", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "NANPA 888 Toll-Free Line"},

    # 3. SOVEREIGN COUNTRY MOBILE SUBSCRIBERS (Standard cellular subscribers -> UNKNOWN / Abstain)
    {"case_id": "somalia_standard_mobile", "raw_number": "+252615551234", "country": "SO", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "Somalia Cellular Subscriber"},
    {"case_id": "sierra_leone_standard_mobile", "raw_number": "+23276123456", "country": "SL", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "Sierra Leone Cellular Subscriber"},
    {"case_id": "standard_indian_mobile", "raw_number": "+919820481729", "country": "IN", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "India Cellular Subscriber"},
    {"case_id": "standard_us_landline", "raw_number": "+12127363100", "country": "US", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "US Fixed Landline"},
    {"case_id": "standard_uk_mobile", "raw_number": "+447911123456", "country": "GB", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "UK Cellular Subscriber"},
    {"case_id": "standard_jp_mobile", "raw_number": "+819012345678", "country": "JP", "expected_tier": "UNKNOWN", "expected_is_threat": False, "category": "Japan Cellular Subscriber"},

    # 4. TELEMARKETING & AUTOMATED ROBOCALLERS -> SPAM
    {"case_id": "trai_140_telemarketer", "raw_number": "+911409988776", "country": "IN", "expected_tier": "SPAM", "expected_is_threat": True, "category": "TRAI 140 Marketing"},
    {"case_id": "uk_0843_bulk_dialer", "raw_number": "+448431234567", "country": "GB", "expected_tier": "SPAM", "expected_is_threat": True, "category": "OFCOM Bulk Series"},
    {"case_id": "low_entropy_dialer_all_repeats", "raw_number": "+917777777777", "country": "IN", "expected_tier": "SPAM", "expected_is_threat": True, "category": "Repeated Robocall Pattern"},

    # 5. HIGH-CHARGE FRAUD & WANGIRI TRAPS -> SCAM
    {"case_id": "wangiri_inmarsat_satellite", "raw_number": "+881631555123", "country": "IN", "expected_tier": "SCAM", "expected_is_threat": True, "category": "Wangiri Satellite Trap"},
    {"case_id": "wangiri_thuraya_satellite", "raw_number": "+882165551234", "country": "IN", "expected_tier": "SCAM", "expected_is_threat": True, "category": "Wangiri Satellite Trap"},
    {"case_id": "premium_rate_scam_us", "raw_number": "+19005551212", "country": "US", "expected_tier": "SCAM", "expected_is_threat": True, "category": "NANPA Premium Rate Fraud"},

    # 6. SYNTAX & STRUCTURE VIOLATIONS -> INVALID
    {"case_id": "invalid_all_zeros", "raw_number": "00000", "country": "IN", "expected_tier": "INVALID", "expected_is_threat": False, "category": "Malformed Syntax"},
    {"case_id": "invalid_too_short", "raw_number": "123", "country": "IN", "expected_tier": "INVALID", "expected_is_threat": False, "category": "Length Below Minimum"},
    {"case_id": "invalid_malformed_somalia_fragment", "raw_number": "+2521", "country": "IN", "expected_tier": "INVALID", "expected_is_threat": False, "category": "Malformed Truncated Dial String"}
]

def export_all():
    print("="*85)
    print("      AEGIS-PNP2 PRODUCTION MODEL EXPORT PIPELINE")
    print("="*85)

    gbt = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
        calib_meta = json.load(f)

    # 1. Export Scaler
    scaler_dict = {
        "feature_names": [f["name"] for f in FEATURE_SPEC["features"]],
        "scale": [1.0] * FEATURE_SPEC["num_features"],
        "min": [0.0] * FEATURE_SPEC["num_features"]
    }
    with open(os.path.join(EXPORT_DIR, "scaler.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(scaler_dict, f, indent=2)
    print("[1/3] Exported scaler.json")

    # 2. Serialize Trees
    learning_rate = gbt.learning_rate
    init_val = float(gbt.init_.constant_[0][0])
    estimators = gbt.estimators_

    trees_list = []
    lines = []
    for tree_idx, est in enumerate(estimators):
        tree = est[0].tree_
        node_count = tree.node_count
        children_left = tree.children_left
        children_right = tree.children_right
        feature = tree.feature
        threshold = tree.threshold
        value = tree.value

        lines.append(f"T:{tree_idx}:{node_count}")
        nodes = []
        for i in range(node_count):
            is_leaf = bool(children_left[i] == children_right[i])
            if is_leaf:
                leaf_val = float(value[i][0][0] * learning_rate)
                lines.append(f"L:{i}:{leaf_val:.8f}")
                nodes.append({
                    "node_id": i,
                    "is_leaf": True,
                    "leaf_value": float(leaf_val)
                })
            else:
                lines.append(f"N:{i}:{int(feature[i])}:{float(threshold[i]):.8f}:{int(children_left[i])}:{int(children_right[i])}")
                nodes.append({
                    "node_id": i,
                    "is_leaf": False,
                    "feature_idx": int(feature[i]),
                    "threshold": float(threshold[i]),
                    "left_child": int(children_left[i]),
                    "right_child": int(children_right[i])
                })
        trees_list.append({
            "tree_id": tree_idx,
            "num_nodes": node_count,
            "nodes": nodes
        })

    # Compute SHA-256
    canonical_tree_str = "\n".join(lines)
    tree_sha256 = hashlib.sha256(canonical_tree_str.encode("utf-8")).hexdigest()

    model_export_dict = {
        "model_name": "AEGIS-PNP2-PhonePatternRiskModel",
        "schema_version": "2.1.0",
        "objective": "PATTERN_RISK",
        "num_features": FEATURE_SPEC["num_features"],
        "num_trees": len(trees_list),
        "init_value": float(init_val),
        "sha256_checksum": tree_sha256,
        "platt_calibrator": {
            "param_a": round(float(calib_meta["param_A"]), 6),
            "param_b": round(float(calib_meta["param_B"]), 6),
            "formula": "P(Threat | features) = 1 / (1 + exp(-(param_a * raw_logit + param_b)))"
        },
        "operating_thresholds": {
            "legitimate_upper": 0.10,
            "unknown_upper": 0.60,
            "spam_upper": 0.98,
            "scam_lower": 0.98
        },
        "trees": trees_list
    }

    model_export_path = os.path.join(EXPORT_DIR, "phonenumber_risk_model.json")
    with open(model_export_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(model_export_dict, f, indent=2)
    print(f"[2/3] Exported phonenumber_risk_model.json (150 trees, SHA-256: {tree_sha256[:12]}...)")

    # 3. Export Golden Test Vectors
    golden_suite = {
        "version": "2.1.0",
        "description": f"{len(INDEPENDENT_GOLDEN_VECTORS)} Independently Authored Golden Test Vectors for AEGIS-PNP2 Verification",
        "test_cases": INDEPENDENT_GOLDEN_VECTORS
    }
    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(golden_suite, f, indent=2)
    print(f"[3/3] Exported golden_test_vectors.json ({len(INDEPENDENT_GOLDEN_VECTORS)} independently authored golden cases)")

    # 4. Copy to Android assets
    os.makedirs(ANDROID_ASSETS_DIR, exist_ok=True)
    with open(os.path.join(ANDROID_ASSETS_DIR, "phonenumber_risk_model.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(model_export_dict, f, indent=2)
    print(f"[+] Copied phonenumber_risk_model.json to Android assets ({ANDROID_ASSETS_DIR})")

if __name__ == "__main__":
    export_all()