# AEGIS Phone Number Pattern Risk Model (AEGIS-PNP1)

A privacy-preserving, on-device Machine Learning engine that analyzes telephone number structures and numbering-plan metadata to detect **scam, spam, automated robocalls, and Wangiri toll fraud**.

---

## Key Capabilities
* **Privacy-Preserving:** Operates solely on digit entropy, repetition run lengths, sequential runs, symmetry, and public ITU-T numbering-plan metadata without storing or processing PII.
* **4-Class Decision Engine:** Outputs calibrated risk probabilities `[0.0 - 1.0]` across `LEGITIMATE`, `UNKNOWN (Abstain)`, `SPAM`, and `SCAM`.
* **Hard-Negative Protection:** Curated rules and training representations ensure bank customer support lines (`1800-11-2211`, `1-800-935-9935`) and emergency numbers (`112`, `911`) never trigger false alarms.
* **Sub-Millisecond On-Device Inference:** Pure-Kotlin 150-tree decision evaluator ($< 0.05\text{ ms}$ latency, zero JNI) and mobile TFLite FlatBuffer binary.
* **100% Train/Serve Parity:** Validated against Python and Java JVM parity harnesses ($< 5 \times 10^{-5}$ max numerical diff).

---

## Project Structure
```
phonenumberML/
├── docs/
│   ├── MODEL_CARD.md              # Ethics, limitations, privacy, and bias analysis
│   ├── FEATURE_SPECIFICATION.md   # Mathematical definition of all 36 features
│   └── EVALUATION_REPORT.md       # Prefix holdout benchmarks and country slices
├── ml/
│   ├── data/
│   │   ├── dataset_builder.py     # Zero-leakage multi-country dataset generator
│   │   ├── train_dataset.json     # 10,000 balanced multi-country phone numbers
│   │   ├── test_prefix_holdout.json # 2,500 unseen prefix & country holdouts
│   │   └── hard_negatives.json    # Curated bank & emergency lines
│   ├── features/
│   │   ├── extractor.py           # Deterministic 36-feature extractor
│   │   └── feature_spec.json      # Versioned schema specification
│   ├── models/
│   │   ├── train.py               # GBT & RF training pipeline
│   │   └── saved_models/          # Serialized model binaries
│   ├── export/
│   │   ├── exporter.py            # JSON tree and TFLite FlatBuffer exporter
│   │   ├── scaler.json            # Deterministic normalization divisors
│   │   ├── golden_test_vectors.json # 15 verified golden test vectors
│   │   └── phonenumber_risk_model.tflite # Mobile TFLite model
│   ├── evaluation/
│   │   ├── evaluate.py            # Comprehensive evaluation suite
│   │   ├── test_golden_vectors.py # 15/15 golden vector regression test
│   │   ├── test_parity_jvm.py     # Python vs JVM parity test
│   │   └── JvmPhoneNumberExtractor.java # Compiled JVM extractor
│   └── api/
│       └── server.py              # FastAPI REST server
└── android/
    └── src/main/java/com/aegis/guard/phonenumber/
        ├── PhoneNumberRiskModel.kt        # Pure Kotlin 150-tree decision evaluator
        ├── PhoneNumberFeatureExtractor.kt # Pure Kotlin 36-feature extractor
        ├── PhoneNumberVerdict.kt          # Threat tiers & confidence models
        └── ReasonCodes.kt                 # Explainability constants
```

---

## Quickstart

### 1. Run Evaluation Benchmarks
```bash
python ml/evaluation/evaluate.py
python ml/evaluation/test_golden_vectors.py
python ml/evaluation/test_parity_jvm.py
```

### 2. Launch FastAPI REST Server
```bash
uvicorn ml.api.server:app --host 127.0.0.1 --port 8001
```

### 3. Android Kotlin Integration Example
```kotlin
val riskModel = PhoneNumberRiskModel()
val modelJson = context.assets.open("phonenumber_risk_model.json").bufferedReader().use { it.readText() }
riskModel.loadModelFromJsonString(modelJson)

val verdict = riskModel.assessNumber("+911409988776", defaultCountry = "IN")
println("Threat Tier: ${verdict.tier}") // SPAM / SCAM
println("Risk Score: ${verdict.riskScore}/100")
println("Reasons: ${verdict.topExplanations}")
```