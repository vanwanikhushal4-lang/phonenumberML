# AEGIS-PNP2: Phone Number Pattern Risk Model & Call Guard Screening Engine

Production-grade, privacy-preserving on-device machine learning model and Android Call Guard screening engine for detecting structural phone scam, spam, automated robocall, and Wangiri patterns.

---

## Key Features
* **Google `libphonenumber` Validation:** Strict E.164 normalization, standard national length verification, and carrier metadata.
* **On-Device Local Risk Model (AEGIS-PNP2):** 150 calibrated decision trees evaluated in pure Kotlin ($< 0.05\text{ ms}$, zero JNI).
* **Exact Sigmoid Calibration:** Fit on dedicated validation splits to guarantee calibrated risk probabilities across Python, Java, and Android Kotlin.
* **Zero-Leakage Grounded Data:** Ingests official regulatory telecom allocations (India TRAI 140/160 series, US NANPA, UK OFCOM, ITU-T satellite Wangiri codes) with 0 normalized-number overlap between train, validation, and untouched test splits.
* **Advisory Mode Call Guard:** Android `CallScreeningService` responding in $< 50\text{ ms}$ (safe fallback before 5s deadline) to warn users without auto-dropping calls from digits alone.
* **Secure Backend Reputation Proxy:** Authenticated IPQS reputation adapter with LRU caching, SHA-256 hashed queries, and zero API keys in client APKs.

---

## Benchmark & Performance Highlights
* **Untouched Holdout ($N = 2,500$ unseen numbers):**
  * **Threat Recall:** `97.42%`
  * **Threat Precision:** `95.88%`
  * **PR-AUC:** `0.9975`
  * **ROC-AUC:** `0.9979`
  * **Brier Calibration Score:** `0.018361`
* **Hard Negatives (Banks & Emergency):** `16 / 16 (100.0% Pass)`
* **Train / Serve End-to-End Parity:** `20 / 20 (100.0% Pass, Max Diff < 0.000048)`

---

## Directory Layout
```
phonenumberML/
├── android/                   # Pure Kotlin On-Device Runtime Engine
│   └── src/main/java/com/aegis/guard/phonenumber/
│       ├── PhoneNumberFeatureExtractor.kt
│       ├── PhoneNumberRiskModel.kt
│       ├── PhoneNumberVerdict.kt
│       ├── ReasonCodes.kt
│       ├── CallGuardEngine.kt
│       └── AegisCallScreeningService.kt
├── ml/
│   ├── features/              # 36-Feature Extractor & Spec
│   │   ├── extractor.py
│   │   └── feature_spec.json
│   ├── data/                  # Grounded Telecom Datasets & Provenance
│   │   └── dataset_builder.py
│   ├── models/                # Training Pipeline & Sigmoid Calibration
│   │   └── train.py
│   ├── export/                # Exported Models & Golden Suite
│   │   ├── exporter.py
│   │   ├── phonenumber_risk_model.json
│   │   ├── scaler.json
│   │   └── golden_test_vectors.json
│   ├── evaluation/            # End-to-End Parity & Production Benchmarks
│   │   ├── JvmPhoneNumberEvaluator.java
│   │   ├── test_end_to_end_parity.py
│   │   └── evaluate_production.py
│   └── api/                   # FastAPI Server & IPQS Reputation Proxy
│       └── server.py
└── docs/                      # Comprehensive Documentation & Model Card
    ├── MODEL_CARD.md
    ├── DATASET_PROVENANCE.md
    ├── EVALUATION_REPORT.md
    └── CALL_SCREENING_INTEGRATION.md
```