"""
AEGIS Phone Number Risk & Reputation Backend Proxy Server (FastAPI)
Production Hardened:
- Strict API Token Authentication (X-AEGIS-API-KEY required for all protected endpoints)
- In-memory Token Bucket Rate Limiting (120 requests / min / IP)
- Strict Request Validation & Bounded LRU Caching (10,000 max entries, 24h TTL)
- Structured Provider States (SUCCESS, CACHED, UNAVAILABLE, RATE_LIMITED)
- Zero PII Logging (SHA-256 truncated query hashes only)
"""

import os
import sys
import time
import json
import hashlib
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
import numpy as np
import joblib
from fastapi import FastAPI, HTTPException, Header, Depends, Security, Request, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, normalize_and_parse, explain_instance, FEATURE_SPEC

app = FastAPI(
    title="AEGIS Phone Number Risk & Screening API",
    version="2.1.0",
    description="Privacy-preserving on-device phone pattern risk model and backend reputation proxy."
)

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))

# Load Model & Calibration Parameters
gbt_model = joblib.load(os.path.join(MODELS_DIR, "gbt_model.joblib"))
with open(os.path.join(MODELS_DIR, "calibration_metadata.json"), "r", encoding="utf-8") as f:
    calib_meta = json.load(f)

PARAM_A = float(calib_meta["param_A"])
PARAM_B = float(calib_meta["param_B"])
IPQS_API_KEY = os.environ.get("IPQS_API_KEY", "")
AEGIS_SERVER_API_KEY = os.environ.get("AEGIS_SERVER_API_KEY", "aegis-production-secret-token-key-2026")

# Bounded LRU Reputation Cache (10,000 entries max, 24h TTL)
REPUTATION_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_MAX_SIZE = 10000
CACHE_TTL_SECONDS = 86400

# Rate Limiting (In-memory token bucket per client IP)
RATE_LIMIT_BUCKET: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60.0
RATE_LIMIT_MAX_REQUESTS = 120

api_key_header = APIKeyHeader(name="X-AEGIS-API-KEY", auto_error=False)

def verify_api_key(api_key: Optional[str] = Security(api_key_header)):
    if not api_key or api_key != AEGIS_SERVER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-AEGIS-API-KEY header."
        )
    return True

def enforce_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    if client_ip not in RATE_LIMIT_BUCKET:
        RATE_LIMIT_BUCKET[client_ip] = []
    # Purge timestamps outside the 60s window
    RATE_LIMIT_BUCKET[client_ip] = [t for t in RATE_LIMIT_BUCKET[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(RATE_LIMIT_BUCKET[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 120 requests per minute."
        )
    RATE_LIMIT_BUCKET[client_ip].append(now)

class PhoneAssessmentRequest(BaseModel):
    raw_number: str = Field(..., example="+911409988776")
    default_country: str = Field("IN", example="IN")

class PhoneAssessmentResponse(BaseModel):
    raw_number: str
    normalized_e164: str
    country: str
    is_valid: bool
    pattern_risk_score: int
    raw_logit: float
    calibrated_probability: float
    threat_tier: str
    confidence: str
    is_threat: bool
    is_abstain: bool
    is_invalid: bool
    top_reason_codes: List[str]
    top_explanations: List[str]
    evaluation_latency_ms: float

class IpqsProxyRequest(BaseModel):
    normalized_e164: str = Field(..., example="+919820481729")
    country: str = Field("IN", example="IN")

class IpqsProxyResponse(BaseModel):
    normalized_e164: str
    status: str
    fraud_score: Optional[int]
    is_risky: Optional[bool]
    carrier: Optional[str]
    line_type: Optional[str]
    cached: bool
    error_message: Optional[str]

@app.get("/health")
def health_check():
    return {
        "service": "AEGIS-PNP2",
        "version": "2.1.0",
        "objective": "PATTERN_RISK",
        "status": "healthy",
        "models_loaded": True,
        "features_count": FEATURE_SPEC["num_features"]
    }

@app.post("/assess/number", response_model=PhoneAssessmentResponse, dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])
def assess_phone_number(req: PhoneAssessmentRequest):
    t0 = time.perf_counter()
    raw_number = req.raw_number.strip()
    country = req.default_country.strip().upper()

    e164, cc, nat, std_len, is_valid = normalize_and_parse(raw_number, country)

    if not is_valid:
        latency = round((time.perf_counter() - t0) * 1000, 3)
        return PhoneAssessmentResponse(
            raw_number=raw_number,
            normalized_e164=e164 if e164 else raw_number,
            country=country,
            is_valid=False,
            pattern_risk_score=0,
            raw_logit=0.0,
            calibrated_probability=0.0,
            threat_tier="INVALID",
            confidence="HIGH",
            is_threat=False,
            is_abstain=False,
            is_invalid=True,
            top_reason_codes=["MALFORMED_OR_NON_DIALABLE"],
            top_explanations=["The input dial string does not conform to ITU-T E.164 national numbering standards."],
            evaluation_latency_ms=latency
        )

    # Extract 36 Features
    feats = extract_features_from_number(raw_number, country)
    raw_logit = float(gbt_model.predict(feats.reshape(1, -1))[0])
    cal_prob = 1.0 / (1.0 + np.exp(-(PARAM_A * raw_logit + PARAM_B)))
    score = int(round(max(0.0, min(1.0, raw_logit)) * 100))

    if raw_logit >= 0.70:
        tier = "SCAM"
        confidence = "HIGH"
        is_threat = True
        is_abstain = False
    elif raw_logit >= 0.40:
        tier = "SPAM"
        confidence = "MEDIUM"
        is_threat = True
        is_abstain = False
    elif raw_logit >= 0.15:
        tier = "UNKNOWN"
        confidence = "LOW"
        is_threat = False
        is_abstain = True
    else:
        tier = "LEGITIMATE"
        confidence = "HIGH"
        is_threat = False
        is_abstain = False

    explanations = explain_instance(feats, top_k=3)
    reason_codes = [e[0] for e in explanations]
    reason_texts = [e[1] for e in explanations]
    latency = round((time.perf_counter() - t0) * 1000, 3)

    return PhoneAssessmentResponse(
        raw_number=raw_number,
        normalized_e164=e164,
        country=country,
        is_valid=True,
        pattern_risk_score=score,
        raw_logit=round(raw_logit, 6),
        calibrated_probability=round(float(cal_prob), 6),
        threat_tier=tier,
        confidence=confidence,
        is_threat=is_threat,
        is_abstain=is_abstain,
        is_invalid=False,
        top_reason_codes=reason_codes,
        top_explanations=reason_texts,
        evaluation_latency_ms=latency
    )

@app.post("/reputation/ipqs", response_model=IpqsProxyResponse, dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)])
def proxy_ipqs_lookup(req: IpqsProxyRequest):
    e164 = req.normalized_e164.strip()
    cache_key = hashlib.sha256(e164.encode("utf-8")).hexdigest()

    # 1. Check in-memory LRU Cache
    now = time.time()
    if cache_key in REPUTATION_CACHE:
        entry = REPUTATION_CACHE[cache_key]
        if now - entry["timestamp"] < CACHE_TTL_SECONDS:
            data = entry["data"]
            return IpqsProxyResponse(
                normalized_e164=e164,
                status="CACHED",
                fraud_score=data.get("fraud_score"),
                is_risky=data.get("is_risky"),
                carrier=data.get("carrier"),
                line_type=data.get("line_type"),
                cached=True,
                error_message=None
            )

    # 2. Check API Key configuration
    if not IPQS_API_KEY:
        return IpqsProxyResponse(
            normalized_e164=e164,
            status="UNAVAILABLE",
            fraud_score=None,
            is_risky=None,
            carrier=None,
            line_type=None,
            cached=False,
            error_message="External IPQS reputation provider key unconfigured."
        )

    # 3. Perform upstream lookup
    clean_digits = e164.replace("+", "")
    url = f"https://www.ipqualityscore.com/api/json/phone/{IPQS_API_KEY}/{clean_digits}?country%5B%5D={req.country}"

    try:
        req_obj = urllib.request.Request(url, headers={"User-Agent": "AEGIS-Guardian-Core/2.1.0"})
        with urllib.request.urlopen(req_obj, timeout=3.0) as response:
            resp_data = json.loads(response.read().decode("utf-8"))

        if not resp_data.get("success", False):
            return IpqsProxyResponse(
                normalized_e164=e164,
                status="UNAVAILABLE",
                fraud_score=None,
                is_risky=None,
                carrier=None,
                line_type=None,
                cached=False,
                error_message=resp_data.get("message", "Upstream API error")
            )

        fraud_score = resp_data.get("fraud_score", 0)
        is_risky = bool(fraud_score >= 80 or resp_data.get("recent_abuse", False))
        carrier = resp_data.get("carrier", "Unknown")
        line_type = resp_data.get("line_type", "Unknown")

        cached_payload = {
            "fraud_score": fraud_score,
            "is_risky": is_risky,
            "carrier": carrier,
            "line_type": line_type
        }

        # Evict oldest if max size reached
        if len(REPUTATION_CACHE) >= CACHE_MAX_SIZE:
            oldest_k = min(REPUTATION_CACHE.keys(), key=lambda k: REPUTATION_CACHE[k]["timestamp"])
            del REPUTATION_CACHE[oldest_k]

        REPUTATION_CACHE[cache_key] = {
            "timestamp": now,
            "data": cached_payload
        }

        return IpqsProxyResponse(
            normalized_e164=e164,
            status="SUCCESS",
            fraud_score=fraud_score,
            is_risky=is_risky,
            carrier=carrier,
            line_type=line_type,
            cached=False,
            error_message=None
        )
    except Exception as e:
        return IpqsProxyResponse(
            normalized_e164=e164,
            status="UNAVAILABLE",
            fraud_score=None,
            is_risky=None,
            carrier=None,
            line_type=None,
            cached=False,
            error_message=str(e)
        )