"""
Automated Security, Authentication & Rate Limiting Tests for AEGIS Backend Server
Tests:
1. Missing Authentication (401 Unauthorized)
2. Invalid Authentication (401 Unauthorized)
3. Valid Authentication (200 OK)
4. In-memory Rate Limiting (429 Too Many Requests after 120 calls)
5. Pattern assessment with valid & invalid dial strings
6. Structured IPQS proxy UNAVAILABLE handling
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
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
        # 120 allowed requests
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

if __name__ == "__main__":
    unittest.main()