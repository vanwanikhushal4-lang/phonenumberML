# AEGIS-PNP2: Phone Number Pattern Risk Model & Call Guard Screening Engine

> **Current Repository Status**: **`Experimental Synthetic Phone-Pattern Baseline - Not Integrated.`**
> **Model Scope & Objective**: Phone-Pattern Structural Risk Scoring (0–100 Ordinal Pattern-Risk Score & Platt-Calibrated Binary Threat Probability).
> **Advisory Notice**: An incoming phone number's digits alone cannot prove caller identity or confirm fraud. This model strictly operates in local advisory screening mode.

---

## 1. Release Gate Verification Summary

All release gates are strictly enforced as non-zero exit code assertions in CI:

| Gate Metric | Enforced CI Release Gate | Untouched Holdout (N=2,500) | Natural Prevalence Benchmark (N=5,000) | Gate Status |
| :--- | :--- | :--- | :--- | :--- |
| **Brier Score Loss** | `< 0.0500` | **`0.000705`** | **`0.000839`** | **PASSED** |
| **ROC-AUC** | `> 0.9000` | **`1.0000`** | **`1.0000`** | **PASSED** |
| **PR-AUC** | `> 0.9000` | **`1.0000`** | **`1.0000`** | **PASSED** |
| **6-Way 7-Digit Prefix Overlap** | `== 0` | **`0`** | **`0`** | **PASSED** |
| **Train/Serve Parity (Py vs JVM vs Golden)** | `20 / 20 (100%)` | **`20 / 20`** | **`20 / 20`** | **PASSED** |
| **Backend API Security & Rate Limiting** | `7 / 7 (100%)` | **`7 / 7`** | **`7 / 7`** | **PASSED** |

---

## 2. Key Architecture & Features
* **Strict 6-Way Group Prefix Isolation:** All datasets are generated from disjoint prefix family `group_id` clusters. Nonzero overlap between any pair of Train, Validation, Test, and Benchmark splits fails CI.
* **True Platt Sigmoid Calibration:** Sigmoid parameters ($A = 25.4639, B = -10.8808$) fitted on validation splits to produce mathematically sound threat probabilities (Brier score $< 0.001$).
* **Google `libphonenumber` Validation:** Strict E.164 normalization, national length checking, and carrier metadata in both Python and Android Kotlin.
* **Pure Kotlin On-Device Runtime:** Evaluates 150 calibrated decision trees on-device with SHA-256 integrity verification, schema validation, and AST node validation.
* **Advisory Mode Call Guard:** Android `CallScreeningService` responding in $< 50\text{ ms}$ (safe fallback before 5s deadline) to warn users without auto-dropping calls from digits alone.
* **Secured Backend Proxy API:** Authenticated FastAPI proxy with strict token authentication (`X-AEGIS-API-KEY`), token bucket rate limiting (120 req/min), and zero PII logging.

---

## 3. Directory Layout
```
phonenumberML/
├── .github/workflows/         # GitHub Actions CI Workflow
├── android/                   # Pure Kotlin On-Device Runtime Engine
│   ├── build.gradle.kts       # Android Library Gradle configuration
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
│   ├── models/                # Training Pipeline & Platt Sigmoid Calibration
│   │   └── train.py
│   ├── export/                # Exported Models & Golden Test Vectors
│   │   ├── exporter.py
│   │   ├── phonenumber_risk_model.json
│   │   ├── scaler.json
│   │   └── golden_test_vectors.json
│   ├── evaluation/            # End-to-End Parity & Production Benchmarks
│   │   ├── JvmPhoneNumberEvaluator.java
│   │   ├── test_end_to_end_parity.py
│   │   └── evaluate_production.py
│   └── api/                   # FastAPI Server & Security Test Suite
│       ├── server.py
│       └── test_server.py
├── scripts/
│   └── run_ci.py              # Master CI Release Gate Verification Runner
├── docs/                      # Comprehensive Documentation & Model Card
│   ├── MODEL_CARD.md
│   └── EVALUATION_REPORT.md
└── requirements.txt           # Pinned Dependencies
```

---

## 4. Running CI & Tests Locally

To verify all release gates locally:
```bash
python scripts/run_ci.py
```