"""
Automated Security, Authentication, Input Validation & Rate Limiting Tests for AEGIS Backend Server
Tests:
1. Missing Authentication (401 Unauthorized)
2. Invalid Authentication (401 Unauthorized)
3. Valid Authentication (200 OK)
4. Input Payload Validation (422 Unprocessable Entity for oversized/malformed payloads)
5. In-memory Rate Limiting (429 Too Many Requests after 120 calls)
6. Pattern assessment with valid & invalid dial strings
7. Structured IPQS proxy UNAVAILABLE handling without secret leakage
8. Production Startup Credential Validation (Fails closed on missing or weak secrets)
"""

import os
import sys
import unittest
import importlib
from fastapi.testclient import TestClient

os.environ["AEGIS_TEST_MODE"] = "1"
os.environ["AEGIS_SERVER_API_KEY"] = "aegis-test-mode-secure-key-32-chars-long-abcdef"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import ml.api.server as server_module
from ml.api.server import app, AEGIS_SERVER_API_KEY, RATE_LIMIT_BUCKET

class ApiServerSecurityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.valid_headers = {"X-AEGIS-API-KEY": AEGIS_SERVER_API_KEY}
        cls.invalid_headers = {"X-AEGIS-API-KEY": "invalid-bogus-token-12345"}

    def setUp(self):
        # Reset rate limit bucket before each test
        RATE_LIMIT_BUCKET.clear()

    def test_health_endpoint_public(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["service"], "AEGIS-PNP2")
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["objective"], "PATTERN_RISK")

    def test_missing_authentication_token_returns_401(self):
        resp = self.client.post(
            "/assess/number",
            json={"raw_number": "+911409988776", "default_country": "IN"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid or missing X-AEGIS-API-KEY header", resp.json()["detail"])

    def test_invalid_authentication_token_returns_401(self):
        resp = self.client.post(
            "/assess/number",
            json={"raw_number": "+911409988776", "default_country": "IN"},
            headers=self.invalid_headers
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid or missing X-AEGIS-API-KEY header", resp.json()["detail"])

    def test_input_payload_bounds_validation_returns_422(self):
        # Oversized number (> 30 chars)
        resp_too_long = self.client.post(
            "/assess/number",
            json={"raw_number": "+91" + "9" * 40, "default_country": "IN"},
            headers=self.valid_headers
        )
        self.assertEqual(resp_too_long.status_code, 422)

        # Invalid country code (> 2 chars or non-alpha)
        resp_bad_cc = self.client.post(
            "/assess/number",
            json={"raw_number": "+919820481729", "default_country": "IND"},
            headers=self.valid_headers
        )
        self.assertEqual(resp_bad_cc.status_code, 422)

    def test_assessment_valid_telemarketer(self):
        resp = self.client.post(
            "/assess/number",
            json={"raw_number": "+911409988776", "default_country": "IN"},
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_valid"])
        self.assertTrue(data["is_threat"])
        self.assertIn(data["threat_tier"], ["SPAM", "SCAM"])
        self.assertGreaterEqual(data["pattern_risk_score"], 40)
        self.assertIn("risk_telemarketing_series", data["top_reason_codes"])

    def test_assessment_counterexample_gb_high_calibrated_scam(self):
        # Reviewer counterexample +448453722722 (GB) -> cal_prob >= 0.98 -> SCAM
        resp = self.client.post(
            "/assess/number",
            json={"raw_number": "+448453722722", "default_country": "GB"},
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_valid"])
        self.assertTrue(data["is_threat"])
        self.assertEqual(data["threat_tier"], "SCAM")
        self.assertFalse(data["is_abstain"])

    def test_assessment_counterexample_in_medium_calibrated_spam(self):
        # Reviewer counterexample +919472476956 (IN) -> cal_prob >= 0.60 -> SPAM
        resp = self.client.post(
            "/assess/number",
            json={"raw_number": "+919472476956", "default_country": "IN"},
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_valid"])
        self.assertTrue(data["is_threat"])
        self.assertEqual(data["threat_tier"], "SPAM")
        self.assertFalse(data["is_abstain"])

    def test_assessment_invalid_all_zeros(self):
        resp = self.client.post(
            "/assess/number",
            json={"raw_number": "0000000000", "default_country": "IN"},
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["is_valid"])
        self.assertTrue(data["is_invalid"])
        self.assertEqual(data["threat_tier"], "INVALID")
        self.assertEqual(data["pattern_risk_score"], 0)

    def test_rate_limiting_enforcement(self):
        for _ in range(120):
            resp = self.client.post(
                "/assess/number",
                json={"raw_number": "112", "default_country": "IN"},
                headers=self.valid_headers
            )
            self.assertEqual(resp.status_code, 200)

        # 121st request MUST return 429 Too Many Requests
        resp_429 = self.client.post(
            "/assess/number",
            json={"raw_number": "112", "default_country": "IN"},
            headers=self.valid_headers
        )
        self.assertEqual(resp_429.status_code, 429)
        self.assertIn("Rate limit exceeded", resp_429.json()["detail"])

    def test_ipqs_proxy_returns_unavailable_when_unconfigured(self):
        resp = self.client.post(
            "/reputation/ipqs",
            json={"normalized_e164": "+919820481729", "country": "IN"},
            headers=self.valid_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "UNAVAILABLE")
        self.assertIsNone(data["fraud_score"])
        self.assertIsNone(data["is_risky"])

    def test_production_mode_missing_secret_fails_startup(self):
        saved_test_mode = os.environ.get("AEGIS_TEST_MODE")
        saved_key = os.environ.get("AEGIS_SERVER_API_KEY")
        try:
            os.environ["AEGIS_TEST_MODE"] = "0"
            os.environ["AEGIS_SERVER_API_KEY"] = ""
            with self.assertRaises(RuntimeError) as ctx:
                importlib.reload(server_module)
            self.assertIn("AEGIS_SERVER_API_KEY environment variable is mandatory", str(ctx.exception))
        finally:
            if saved_test_mode is not None:
                os.environ["AEGIS_TEST_MODE"] = saved_test_mode
            if saved_key is not None:
                os.environ["AEGIS_SERVER_API_KEY"] = saved_key
            importlib.reload(server_module)

    def test_production_mode_weak_secret_fails_startup(self):
        saved_test_mode = os.environ.get("AEGIS_TEST_MODE")
        saved_key = os.environ.get("AEGIS_SERVER_API_KEY")
        try:
            os.environ["AEGIS_TEST_MODE"] = "0"
            os.environ["AEGIS_SERVER_API_KEY"] = "short-secret"
            with self.assertRaises(RuntimeError) as ctx:
                importlib.reload(server_module)
            self.assertIn("AEGIS_SERVER_API_KEY environment variable is mandatory", str(ctx.exception))
        finally:
            if saved_test_mode is not None:
                os.environ["AEGIS_TEST_MODE"] = saved_test_mode
            if saved_key is not None:
                os.environ["AEGIS_SERVER_API_KEY"] = saved_key
            importlib.reload(server_module)

if __name__ == "__main__":
    unittest.main()