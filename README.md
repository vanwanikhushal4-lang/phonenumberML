# AEGIS-PNP2: Phone Number Pattern Risk Model & Call Guard Screening Engine

> **Current Repository Status**: **`Experimental Synthetic Phone-Pattern Baseline - Not Integrated.`**  
> **Model Scope & Objective**: Phone-Pattern Structural Risk Scoring (0–100 Pattern-Risk Score & Platt-Calibrated Binary Threat Probability).  
> **Advisory Notice**: An incoming phone number's digits alone cannot prove caller identity or confirm fraud. This model strictly operates in local advisory screening mode.

---

## 1. Release Gate Verification Summary

All release gates are strictly enforced as non-zero exit code assertions in CI:

| Gate Metric | Enforced CI Release Gate | Untouched Holdout (N=2,500) | Natural Prevalence Benchmark (N=5,000) | Gate Status |
| :--- | :--- | :--- | :--- | :--- |
| **Brier Score Loss** | `< 0.2000` | **`0.122648`** | **`0.110364`** | **PASSED** |
| **ROC-AUC** | `> 0.8500` | **`0.9075`** | **`0.9279`** | **PASSED** |
| **PR-AUC** | `> 0.8000` | **`0.9199`** | **`0.8524`** | **PASSED** |
| **10-Way 7-Digit Prefix Overlap** | `== 0` | **`0`** | **`0`** | **PASSED** |
| **4-Way Train/Serve Parity (Py / JVM / Kotlin / API)** | `39 / 39 (100%)` | **`39 / 39`** | **`39 / 39`** | **PASSED** |
| **Backend API Security, Auth & Rate Limiting** | `12 / 12 (100%)` | **`12 / 12`** | **`12 / 12`** | **PASSED** |

---

## 2. Key Architecture & Features
* **Strict 10-Way Group Prefix Isolation:** All datasets are generated from disjoint prefix family `group_id` clusters. Nonzero overlap between any pair of Train, Calibration, Validation, Test, and Benchmark splits fails CI.
* **True Platt Sigmoid Calibration:** Sigmoid parameters ($A = 12.0786, B = -4.1048$) fitted on dedicated disjoint calibration split (`calib_dataset.json`) to produce mathematically calibrated threat probabilities.
* **Unified Probability Operating Thresholds:** Every runtime (Python, JVM, Kotlin, FastAPI) consumes identical calibrated probability cutoffs:
  - `LEGITIMATE`: $P < 0.10$
  - `UNKNOWN`: $0.10 \le P < 0.60$ (Safe ring, abstain)
  - `SPAM`: $0.60 \le P < 0.98$ (Advisory warning)
  - `SCAM`: $P \ge 0.98$ (High-risk advisory warning)
  - `INVALID`: Malformed number syntax
* **Google `libphonenumber` Validation:** Strict E.164 normalization, national length checking, and carrier metadata in Python, JVM, and Android Kotlin without heuristic validity bypasses.
* **Pure Kotlin On-Device Runtime:** Evaluates 150 calibrated decision trees on-device with SHA-256 integrity verification, schema validation, and AST node validation.
* **Advisory Mode Call Guard:** Android `CallScreeningService` responding in $< 50\text{ ms}$ (safe fallback before 5s deadline) to warn users without auto-dropping calls from digits alone.
* **Secured Backend Proxy API:** Authenticated FastAPI proxy with strict token authentication (`X-AEGIS-API-KEY`), token bucket rate limiting (120 req/min), and fail-closed startup validation.

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
│   │   ├── evaluate_production.py
│   │   ├── test_end_to_end_parity.py
│   │   ├── JvmPhoneNumberEvaluator.java
│   │   └── JvmPhoneNumberExtractor.java
│   └── api/                   # Hardened Backend Proxy API
│       ├── server.py
│       └── test_server.py
├── docs/                      # Model Cards & Verification Reports
│   ├── MODEL_CARD.md
│   ├── DATASET_PROVENANCE.md
│   └── EVALUATION_REPORT.md
├── scripts/                   # Continuous Integration Runner
│   └── run_ci.py
└── requirements.txt           # Pinned Dependencies
```

---

## 4. Running Verification Locally

```bash
# Run Master CI Release Gate Suite
python scripts/run_ci.py

# Run Android Kotlin Unit Tests & Lint
./gradlew :android:testDebugUnitTest :android:lint --no-daemon
```