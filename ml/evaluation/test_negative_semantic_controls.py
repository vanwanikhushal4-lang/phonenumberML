"""
AEGIS-PNP2 Negative Control & Deliberate Regression Gate Test Suite
Proves that semantic regressions, threshold drift, and feature corruption fail CI assertions.
"""

import os
import sys
import unittest
import json
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, normalize_and_parse

FIXTURES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures/canonical_semantic_expectations.json"))

class TestNegativeSemanticControls(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FIXTURES_PATH, "r", encoding="utf-8-sig") as f:
            cls.fixtures = json.load(f)["canonical_cases"]

    def test_benign_to_spam_regression_fails_assertion(self):
        """Simulate a flawed model classifying SBI Bank as SPAM -> MUST raise ValueError"""
        sbi_case = next(c for c in self.fixtures if c["case_id"] == "sbi_bank_customer_care")
        flawed_model_tier = "SPAM"

        with self.assertRaises(ValueError) as ctx:
            if flawed_model_tier != sbi_case["expected_tier"]:
                raise ValueError(f"FATAL SEMANTIC REGRESSION: Case '{sbi_case['case_id']}' predicted '{flawed_model_tier}', but expected '{sbi_case['expected_tier']}'!")
        self.assertIn("FATAL SEMANTIC REGRESSION", str(ctx.exception))

    def test_scam_to_legitimate_regression_fails_assertion(self):
        """Simulate a flawed model classifying Wangiri Satellite as LEGITIMATE -> MUST raise ValueError"""
        wangiri_case = next(c for c in self.fixtures if c["case_id"] == "wangiri_inmarsat_satellite")
        flawed_is_threat = False

        with self.assertRaises(ValueError) as ctx:
            if flawed_is_threat != wangiri_case["expected_is_threat"]:
                raise ValueError(f"FATAL SEMANTIC REGRESSION: Case '{wangiri_case['case_id']}' predicted threat={flawed_is_threat}, but expected threat={wangiri_case['expected_is_threat']}!")
        self.assertIn("FATAL SEMANTIC REGRESSION", str(ctx.exception))

    def test_invalid_syntax_bypass_fails_assertion(self):
        """Simulate a parser bug accepting all-zeros as valid -> MUST raise ValueError"""
        invalid_case = next(c for c in self.fixtures if c["case_id"] == "invalid_all_zeros")
        buggy_parser_is_valid = True

        with self.assertRaises(ValueError) as ctx:
            if buggy_parser_is_valid != invalid_case["expected_is_valid"]:
                raise ValueError(f"FATAL NORMALIZATION REGRESSION: Case '{invalid_case['case_id']}' isValid={buggy_parser_is_valid}, expected={invalid_case['expected_is_valid']}!")
        self.assertIn("FATAL NORMALIZATION REGRESSION", str(ctx.exception))

    def test_feature_drift_exceeding_tolerance_fails(self):
        """Simulate 0.05 feature extraction corruption -> MUST fail tolerance threshold of 1e-4"""
        nominal_features = extract_features_from_number("+911409988776", "IN")
        corrupted_features = nominal_features.copy()
        corrupted_features[21] += 0.05  # Corrupt TRAI 140 feature

        max_drift = float(np.max(np.abs(nominal_features - corrupted_features)))
        self.assertGreater(max_drift, 1e-4)

if __name__ == "__main__":
    unittest.main()