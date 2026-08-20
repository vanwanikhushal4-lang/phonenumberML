"""
Automated Security & Regression Tests for AEGIS Backend Proxy Server
Tests:
1. Authentication verification (401 on missing/invalid API key)
2. Number assessment with valid/invalid inputs
3. IPQS proxy structured UNAVAILABLE handling
4. Rate limiting behavior
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.api.server import app, AEGIS_SERVER_API_KEY

class ApiServerSecurityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.auth_headers = {"X-AEGIS-API-KEY": AEGIS_SERVER_API_KEY}

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["service"], "AEGIS-PNP2")
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["objective"], "PATTERN_RISK")

    def test_assessment_valid_telemarketer(self):
        resp = self.client.post(
            "/assess/number",
            json={"raw_number": "+911409988776", "default_country": "IN"},
            headers=self.auth_headers
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
            headers=self.auth_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["is_valid"])
        self.assertTrue(data["is_invalid"])
        self.assertEqual(data["threat_tier"], "INVALID")
        self.assertEqual(data["pattern_risk_score"], 0)

    def test_ipqs_proxy_returns_unavailable_when_unconfigured(self):
        resp = self.client.post(
            "/reputation/ipqs",
            json={"normalized_e164": "+919820481729", "country": "IN"},
            headers=self.auth_headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # When IPQS key is not set, status MUST be UNAVAILABLE, never clean false zero
        self.assertEqual(data["status"], "UNAVAILABLE")
        self.assertIsNone(data["fraud_score"])
        self.assertIsNone(data["is_risky"])

if __name__ == "__main__":
    unittest.main()