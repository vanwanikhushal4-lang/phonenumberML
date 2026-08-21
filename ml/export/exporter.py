"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) — Production Model Exporter
Exports:
1. phonenumber_risk_model.json with 150 trees, init_value, Platt parameters, SHA-256 integrity hash
2. scaler.json
3. golden_test_vectors.json containing immutable independently authored semantic expectations + reference numeric predictions
"""

import os
import sys
import json
import hashlib
import numpy as np
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import FEATURE_SPEC, extract_features_from_number, normalize_and_parse

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))
EXPORT_DIR = os.path.dirname(__file__)
ANDROID_ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../android/src/main/assets"))
FIXTURES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../evaluation/fixtures/canonical_semantic_expectations.json"))

def export_all():
    print("="*85)
    print("      AEGIS-PNP2 PRODUCTION MODEL EXPORT PIPELINE")
    print("="*85)

    gbt = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
    with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
        calib_meta = json.load(f)

    param_a = float(calib_meta["param_A"])
    param_b = float(calib_meta["param_B"])

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
            "param_a": round(float(param_a), 6),
            "param_b": round(float(param_b), 6),
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

    # 3. Load Independent Canonical Semantic Fixture and Assert Non-Circular Compliance
    if not os.path.exists(FIXTURES_PATH):
        raise FileNotFoundError(f"Independent semantic fixture missing at {FIXTURES_PATH}")

    with open(FIXTURES_PATH, "r", encoding="utf-8-sig") as f:
        fixtures_data = json.load(f)

    canonical_cases = fixtures_data["canonical_cases"]
    enriched_vectors = []

    for case in canonical_cases:
        raw_num = case["raw_number"]
        country = case["country"]
        e164, cc, nat, std_len, is_v = normalize_and_parse(raw_num, country)

        if not is_v:
            feats = [0.0] * 36
            raw_l = 0.0
            prob = 0.0
            score = 0
            pred_tier = "INVALID"
            pred_threat = False
            is_abstain = False
            is_invalid = True
        else:
            v_py = extract_features_from_number(raw_num, country)
            feats = [round(float(x), 6) for x in v_py]
            raw_l = float(gbt.predict(v_py.reshape(1, -1))[0])
            prob = float(1.0 / (1.0 + np.exp(-(param_a * raw_l + param_b))))
            score = int(round(max(0.0, min(1.0, raw_l)) * 100.0))

            if prob >= 0.98:
                pred_tier = "SCAM"
                pred_threat = True
                is_abstain = False
            elif prob >= 0.60:
                pred_tier = "SPAM"
                pred_threat = True
                is_abstain = False
            elif prob >= 0.10:
                pred_tier = "UNKNOWN"
                pred_threat = False
                is_abstain = True
            else:
                pred_tier = "LEGITIMATE"
                pred_threat = False
                is_abstain = False

            is_invalid = False

        # STRICT NON-CIRCULAR ASSERTIONS: Model predictions MUST agree with independently authored expectations
        if pred_tier != case["expected_tier"]:
            raise ValueError(
                f"FATAL SEMANTIC REGRESSION: Case '{case['case_id']}' predicted '{pred_tier}', "
                f"but independently authored expectation is '{case['expected_tier']}'!"
            )
        if pred_threat != case["expected_is_threat"]:
            raise ValueError(
                f"FATAL SEMANTIC REGRESSION: Case '{case['case_id']}' predicted isThreat={pred_threat}, "
                f"but independently authored expectation is isThreat={case['expected_is_threat']}!"
            )
        if is_v != case["expected_is_valid"]:
            raise ValueError(
                f"FATAL NORMALIZATION REGRESSION: Case '{case['case_id']}' isValid={is_v}, "
                f"expected={case['expected_is_valid']}!"
            )
        if is_abstain != case["expected_is_abstain"]:
            raise ValueError(
                f"FATAL ABSTENTION REGRESSION: Case '{case['case_id']}' isAbstain={is_abstain}, "
                f"expected={case['expected_is_abstain']}!"
            )
        if is_invalid != case["expected_is_invalid"]:
            raise ValueError(
                f"FATAL INVALID STATE REGRESSION: Case '{case['case_id']}' isInvalid={is_invalid}, "
                f"expected={case['expected_is_invalid']}!"
            )
        if e164 != case["expected_normalized_e164"]:
            raise ValueError(
                f"FATAL E.164 REGRESSION: Case '{case['case_id']}' normalized to '{e164}', "
                f"expected '{case['expected_normalized_e164']}'!"
            )

        enriched_vectors.append({
            "case_id": case["case_id"],
            "raw_number": raw_num,
            "country": country,
            "category": case["category"],
            "provenance": case["provenance"],
            "expected_normalized_e164": case["expected_normalized_e164"],
            "expected_tier": case["expected_tier"],
            "expected_is_threat": case["expected_is_threat"],
            "expected_is_valid": case["expected_is_valid"],
            "expected_is_abstain": case["expected_is_abstain"],
            "expected_is_invalid": case["expected_is_invalid"],
            "reference_raw_logit": round(raw_l, 6),
            "reference_calibrated_probability": round(prob, 6),
            "reference_score": score,
            "reference_features": feats,
            "expected_reason_codes": case.get("expected_reason_codes", []),
            "expected_explanations": case.get("expected_explanations", [])
        })

    golden_suite = {
        "version": "2.1.0",
        "description": f"{len(enriched_vectors)} Canonical Golden Test Vectors with Reference Python Outputs",
        "fixture_provenance": "ml/evaluation/fixtures/canonical_semantic_expectations.json",
        "operating_thresholds": {
            "legitimate_upper": 0.10,
            "unknown_upper": 0.60,
            "spam_upper": 0.98,
            "scam_lower": 0.98
        },
        "test_cases": enriched_vectors
    }
    with open(os.path.join(EXPORT_DIR, "golden_test_vectors.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(golden_suite, f, indent=2)
    print(f"[3/3] Exported golden_test_vectors.json ({len(enriched_vectors)} canonical test cases asserted non-circularly)")

    # 4. Copy to Android assets
    os.makedirs(ANDROID_ASSETS_DIR, exist_ok=True)
    with open(os.path.join(ANDROID_ASSETS_DIR, "phonenumber_risk_model.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(model_export_dict, f, indent=2)
    print(f"[+] Copied phonenumber_risk_model.json to Android assets ({ANDROID_ASSETS_DIR})")

if __name__ == "__main__":
    export_all()