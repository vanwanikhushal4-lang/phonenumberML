"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP1) — REST API Server
Provides real-time, privacy-preserving risk assessment of phone number patterns.
"""

import os
import sys
import json
import numpy as np
import joblib
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, explain_prediction, FEATURE_SPEC

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/saved_models"))

app = FastAPI(
    title="AEGIS Phone Number Pattern Risk API",
    description="Privacy-Preserving Phone Number Structural Risk & Fraud Analysis Engine (AEGIS-PNP1)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

calibrated_gbt = None
feature_importances = None

@app.on_event("startup")
def load_models():
    global calibrated_gbt, feature_importances
    model_path = os.path.join(MODELS_DIR, "calibrated_gbt.joblib")
    if not os.path.exists(model_path):
        model_path = os.path.join(MODELS_DIR, "gbt_model.joblib")
    calibrated_gbt = joblib.load(model_path)
    
    imp_path = os.path.join(MODELS_DIR, "feature_importances.npy")
    if os.path.exists(imp_path):
        feature_importances = np.load(imp_path)
    else:
        feature_importances = np.ones(FEATURE_SPEC["num_features"], dtype=np.float32) / float(FEATURE_SPEC["num_features"])
    print(f"Loaded Phone Number Pattern Risk Model ({FEATURE_SPEC['num_features']} features).")

class NumberAssessRequest(BaseModel):
    raw_number: str = Field(..., example="+911409988776", description="Raw phone number string")
    default_country: str = Field("IN", example="IN", description="ISO 3166-1 alpha-2 default country code")

class VectorAssessRequest(BaseModel):
    vector_36: List[float] = Field(..., min_items=36, max_items=36, description="36-dimensional normalized feature vector")

class PhoneNumberVerdictResponse(BaseModel):
    raw_number: str
    country: str
    risk_score: int
    malware_probability: float
    threat_tier: str
    confidence: str
    is_threat: bool
    is_abstain: bool
    top_reasons: List[str]

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AEGIS Phone Number Pattern Risk API (AEGIS-PNP1)",
        "model_loaded": calibrated_gbt is not None,
        "features_count": FEATURE_SPEC["num_features"]
    }

@app.post("/assess/number", response_model=PhoneNumberVerdictResponse)
def assess_number(req: NumberAssessRequest):
    vec = extract_features_from_number(req.raw_number, req.default_country)
    p_cal = float(calibrated_gbt.predict_proba(vec.reshape(1, -1))[0, 1])
    score = int(round(p_cal * 100))

    tier = "LEGITIMATE" if p_cal < 0.15 else ("UNKNOWN" if p_cal < 0.40 else ("SPAM" if p_cal < 0.70 else "SCAM"))
    confidence = "HIGH" if (p_cal >= 0.75 or p_cal <= 0.10) else ("MEDIUM" if p_cal >= 0.40 else "LOW")
    reasons = [desc for _, desc, _ in explain_prediction(vec, feature_importances, top_k=3)]

    return PhoneNumberVerdictResponse(
        raw_number=req.raw_number,
        country=req.default_country,
        risk_score=score,
        malware_probability=round(p_cal, 4),
        threat_tier=tier,
        confidence=confidence,
        is_threat=(tier in ("SPAM", "SCAM")),
        is_abstain=(tier == "UNKNOWN"),
        top_reasons=reasons
    )

@app.post("/assess/vector", response_model=PhoneNumberVerdictResponse)
def assess_vector(req: VectorAssessRequest):
    vec = np.array(req.vector_36, dtype=np.float32)
    p_cal = float(calibrated_gbt.predict_proba(vec.reshape(1, -1))[0, 1])
    score = int(round(p_cal * 100))

    tier = "LEGITIMATE" if p_cal < 0.15 else ("UNKNOWN" if p_cal < 0.40 else ("SPAM" if p_cal < 0.70 else "SCAM"))
    confidence = "HIGH" if (p_cal >= 0.75 or p_cal <= 0.10) else ("MEDIUM" if p_cal >= 0.40 else "LOW")
    reasons = [desc for _, desc, _ in explain_prediction(vec, feature_importances, top_k=3)]

    return PhoneNumberVerdictResponse(
        raw_number="[CUSTOM_VECTOR]",
        country="GLOBAL",
        risk_score=score,
        malware_probability=round(p_cal, 4),
        threat_tier=tier,
        confidence=confidence,
        is_threat=(tier in ("SPAM", "SCAM")),
        is_abstain=(tier == "UNKNOWN"),
        top_reasons=reasons
    )