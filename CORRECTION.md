# AEGIS Automated Model Review

> Reviewer-managed file. The AI/ML implementation automation may read this file but must not edit it.

| Field | Value |
| --- | --- |
| Review status | `CHANGES_REQUIRED` |
| Reviewed branch | `main` |
| Reviewed commit | `c2e106ffc3a68409a5783944c632a75648990de8` |
| Model | `AEGIS-PNP2` |
| Review date | `2026-08-21` |

## Verified Improvements

- Clean six-stage Python/JVM CI passes locally and in GitHub Actions.
- All six measured seven-digit prefix intersections are zero.
- Python/JVM parity passes all 20 golden vectors.
- Seven backend API tests pass.
- Android call screening remains advisory and does not automatically reject calls.

## Required Corrections

### COR-001: Remove blanket country and toll-free threat labels

**Severity:** Critical

**Evidence:** Test probes classified valid-looking US `844`, `855`, `866`, `877`, and `888` toll-free numbers as `SPAM` with probability `0.9579`. The malformed number `+2521` was accepted as valid and classified as `SCAM` with probability `1.0000`.

**Required change:** Do not infer spam or scam solely from a country code, satellite code, toll-free area code, or broad number range. Require `libphonenumber` validity before feature extraction. Remove the Wangiri-prefix validity bypass from Python, Java, and Kotlin.

**Acceptance criteria:**

- `+2521` returns `INVALID` in Python, JVM, Kotlin, and backend tests.
- Ordinary numbers from every listed high-risk country code can return `UNKNOWN` rather than forced `SCAM`.
- US `833/844/855/866/877/888` numbers are not threats without independent risk evidence.
- Add adversarial positive and negative regression vectors for every affected rule.

### COR-002: Replace circular synthetic evaluation

**Severity:** Critical

**Evidence:** `dataset_builder.py` generates training, validation, holdout, and the so-called natural-prevalence benchmark from the same label-conditioned templates. CI regenerates the supposedly frozen holdout before every evaluation. `ingest_real_data.py` contains a hand-authored registry dictionary and is not a real ingestion pipeline or part of CI.

**Required change:** Keep synthetic data only for parser, parity, and robustness tests. Build separately versioned calibration and holdout datasets from licensed, timestamped, row-provenanced real records. Do not regenerate the holdout during CI.

**Acceptance criteria:**

- Every non-synthetic row has source, source record identifier, retrieval date, license, labeling method, and immutable dataset hash.
- Entity, source, temporal, and prefix-family isolation are tested independently.
- CI verifies the frozen holdout checksum and never writes the holdout.
- Report precision, recall, FPR, FNR, PR-AUC, ROC-AUC, Brier score, and calibration error overall and by country/number type.

### COR-003: Make Android build and test the actual Kotlin runtime

**Severity:** Critical

**Evidence:** Gradle cannot resolve the Android plugin because `settings.gradle.kts` lacks required plugin repositories. Source contains duplicate `ThreatTier` declarations. `CallGuardEngine` reads `topExplanations` and `evaluationLatencyMs`, which are absent from `PhoneRiskAssessment`. Current parity CI compiles a separate Java evaluator and never compiles Kotlin.

**Required change:** Commit a Gradle wrapper and complete repository configuration, unify the verdict/domain types, fix the missing fields, and run the real Kotlin extractor/model in CI.

**Acceptance criteria:**

- A clean clone passes the Android/Kotlin build without external project files.
- GitHub Actions runs Kotlin unit tests and Android lint.
- Golden parity compares Python with the production Kotlin implementation, not a handwritten Java equivalent.
- Corrupt-model and uninitialized-model safe fallbacks are covered.

### COR-004: Implement real model integrity verification

**Severity:** High

**Evidence:** `PhoneNumberRiskModel.loadModelFromJsonString` only checks whether `sha256_checksum` has 64 characters. It never hashes the canonical tree payload or compares the digest.

**Required change:** Recreate the exporter's canonical tree serialization in Kotlin, compute SHA-256, and compare it with the exported digest using a constant-time comparison.

**Acceptance criteria:** A test changes one tree threshold while retaining the original checksum and confirms that model loading fails closed.

### COR-005: Correct calibration and threshold semantics

**Severity:** High

**Evidence:** The Platt model is fitted on predictions from the same training records used by the regressor. Runtime threat tiers use the raw ordinal regressor output while documentation describes probability thresholds. `MODEL_CARD.md` contains stale calibration parameters and an incorrect tree depth.

**Required change:** Fit calibration on a dedicated calibration split, select operating points from calibrated probability using documented costs, and use one exported threshold definition in Python, JVM, Kotlin, backend, and documentation.

**Acceptance criteria:**

- Calibration data is disjoint from model fitting and final holdout data.
- Reliability diagrams, ECE, Brier score, confidence intervals, and threshold-selection rationale are published.
- Every runtime produces the same probability, tier, and threat decision for shared vectors.

### COR-006: Remove insecure backend defaults

**Severity:** Critical

**Evidence:** The backend falls back to the public token `aegis-production-secret-token-key-2026`, and tests accept that fallback as valid authentication.

**Required change:** Fail startup when `AEGIS_SERVER_API_KEY` is absent or weak, compare credentials in constant time, validate and bound all request fields, sanitize upstream errors, and use a deployment-grade shared rate limiter or gateway policy.

**Acceptance criteria:** Tests cover missing/weak secrets, invalid input sizes and countries, provider timeouts without secret leakage, and rate limiting across configured deployment workers.

### COR-007: Make builds reproducible and documentation truthful

**Severity:** High

**Evidence:** Dependencies use open-ended `>=` constraints. A clean release run modified committed model binaries and calibration metadata. CI does not fail on generated-artifact drift. Documentation claims Kotlin parity, SHA verification, independent data, and production characteristics that are not currently demonstrated.

**Required change:** Pin exact dependency versions with hashes, define the supported Python/JDK/Android toolchain, assert a clean worktree after deterministic regeneration, and generate factual model documentation from verified artifacts.

**Acceptance criteria:** Two clean builds produce identical exported assets and checksums, CI fails on stale generated files, and all reported values match the committed model metadata.

## Evidence Required For Re-Review

- GitHub Actions link showing Python, JVM, Kotlin, Android, security, and reproducibility gates.
- Immutable real-data provenance manifest and dataset hashes.
- False-positive regression output for toll-free and country-code counterexamples.
- Calibration report and threshold rationale.
- Model checksum tampering test output.
- Exact clean-clone commands and their complete results.

## Worker Rules

1. Confirm that `main` still contains reviewed commit `c2e106ffc3a68409a5783944c632a75648990de8` before implementing. If it does not, stop because this review may be stale.
2. Implement corrections on a feature branch and open a pull request against `main`; never push fixes directly to `main`.
3. Do not edit `CORRECTION.md`.
4. Include correction IDs in commits and the pull-request description.
5. Return the required evidence for every correction claimed complete.
