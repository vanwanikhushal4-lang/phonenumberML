# AEGIS Automated Model Review

> Reviewer-managed file. The AI/ML implementation automation may read this file but must not edit it.

| Field | Value |
| --- | --- |
| Reviewer owner | `Codex automated reviewer` |
| Review status | `CHANGES_REQUIRED` |
| Reviewed branch | `main` |
| Reviewed commit | `c5cb1058234154bac554b4f58d97d2a369a9b758` |
| Review date | `2026-08-21` |
| Reviewer branch | `codex/phone-ml-review` |
| Team response | `ANSWER.md` at `c5cb1058234154bac554b4f58d97d2a369a9b758` |
| Handoff PR | `#2` (replacement draft; do not merge) |

## Readiness Verdict

`CHANGES_REQUIRED`. Commit `c5cb1058234154bac554b4f58d97d2a369a9b758` fixes the verified FastAPI threshold drift, expands cross-runtime numeric parity, and passes its GitHub and local test suites. It is still not ready for Aegis integration or production release. The data and final evaluation remain label-first synthetic generation with fabricated record-level provenance, calibration evidence remains inadequate, rate limiting remains process-local, tracked Joblib artifacts still drift after the CI pipeline reports a clean worktree, documentation remains contradictory, implementation bypassed the required PR workflow, and the new golden-vector generator creates expected outcomes from the same model being tested.

## Verified Improvements

- GitHub Actions run `32470754828` passed for this exact commit, including Android unit tests, Android lint, Python/JVM/FastAPI parity, model evaluation, and backend tests.
- Local `./gradlew :android:testDebugUnitTest :android:lint --no-daemon` passed.
- Local `python scripts/run_ci.py` completed successfully with 39/39 Python/JVM/FastAPI cases and 12/12 backend tests.
- FastAPI now selects tiers from calibrated probability. Reviewer counterexamples `+448453722722` and `+919472476956` return `SCAM` and `SPAM` respectively.
- Kotlin tests now compare all 36 features, raw output, calibrated probability, score, tier, threat, abstention, and validity against committed Python-generated reference values.
- Regression inputs now include ordinary and malformed examples for `+224`, `+255`, `+257`, and `+269`, in addition to prior toll-free and country-code cases.
- README and model-card headline metrics and threshold ranges were partially corrected.
- Replacement handoff PR #2 remains open and draft; no source changes were pushed to the reviewer branch in this cycle.

## Resolved Corrections

### COR-004: Implement real model integrity verification

**Severity:** High

**Status:** `RESOLVED`

Kotlin canonical tree hashing, constant-time digest comparison, and fail-closed threshold-tampering coverage remain effective and pass the Android unit gate.

## Open Corrections

### COR-001: Complete false-positive regression coverage

**Severity:** High

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** The corpus now contains all former country-code counterexamples and malformed fragments requested in the previous review. However, the exporter overwrites authored semantic expectations with current Python model output, so these cases do not yet form an independent behavioral regression suite. Neighboring-prefix cases and independently sourced legitimacy/risk evidence are also absent.

**Required change:** Preserve immutable, independently reviewed semantic expectations for every counterexample. Add neighboring-prefix and boundary cases. The generator may enrich vectors with numeric reference values, but it must fail when the model disagrees with the authored expected tier or threat flag instead of replacing that expectation.

**Acceptance criteria:** The complete corpus has externally or manually justified expected semantics, changes to those semantics require explicit review, and Python, JVM, Kotlin, and FastAPI agree on validity, normalization, features, raw output, calibrated probability, score, tier, threat, and abstention within declared tolerances.

### COR-002: Replace synthetic data and fabricated provenance

**Severity:** Critical

**Status:** `NOT_RESOLVED`

**Evidence:** This commit does not change the dataset builder, datasets, provenance documents, or manifest. `ml/data/dataset_builder.py` still chooses `target_label` before generating random digits from label-specific templates and invents source IDs such as `CARRIER-ALLOC-*`, `RBI-BANK-CARE-*`, and `ITU-WANGIRI-*`. Training, calibration, validation, holdout, and benchmark all come from that same generator and feature-rule family. Prefix separation prevents literal prefix overlap but does not make the labels or evaluation independent. The commit message and `ANSWER.md` incorrectly call this correction resolved.

**Required change:** Mark all current rows as synthetic fixtures. Acquire legally usable real records independently of model features and label rules, retain immutable source artifacts, and build calibration and final evaluation sets from those records. A numbering-plan allocation alone is not evidence that a specific number is benign, spam, or scam.

**Acceptance criteria:**

- Every real evaluation row traces to an immutable source artifact, URL/release, retrieval record, license, and independently reviewed label.
- Generated identifiers are never represented as source record IDs.
- Holdout and benchmark labels are independent of generator and feature rules.
- Entity, number, prefix family, time, country, and source isolation are audited before splitting.
- Legal/licensing review and a provenance-verifier result are attached to the implementation PR.

### COR-003: Make Android and Kotlin genuine parity release gates

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Kotlin now compares 36 features, raw output, calibrated probability, score, tier, threat, abstention, and validity for 39 cases; Python/JVM/FastAPI parity also passes. Kotlin still does not compare normalized E.164, reason codes, or explanations despite `ANSWER.md` claiming reason-code validation. More importantly, all numeric and semantic expected values are generated by the Python implementation under test, so parity proves runtime agreement but not correctness or regression safety.

**Required change:** Keep the expanded runtime comparisons, add Kotlin normalization/reason-code assertions, and separate independent behavioral expectations from generated Python numeric references. Add a deliberate threshold/runtime-drift test that proves each gate fails.

**Acceptance criteria:** CI proves full observable-output parity among Python, standalone JVM, production Kotlin, and FastAPI against an independent canonical corpus, with explicit tolerances and negative tests for feature, threshold, normalization, and reason-code drift.

### COR-005: Correct calibration quality and decision semantics

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** The concrete FastAPI drift is fixed and the two reviewer counterexamples now agree across tested runtimes. A single threshold contract still does not exist: `ml/models/train.py` writes old `0.15/0.40/0.70` values into calibration metadata, while exporter and runtimes hard-code `0.10/0.60/0.98`. `pattern_risk_score` remains `raw_output * 100`, although the model card calls it calibrated and maps score ranges directly to calibrated probability thresholds. Holdout Brier remains `0.122648`, benchmark Brier `0.110364`, and the synthetic holdout still warns on 51/496 generated `BENIGN` plus 69/610 generated `UNKNOWN` rows while abstaining on 242/514 generated `CONFIRMED_SCAM` rows. No ECE, reliability curve, confidence interval, subgroup calibration, or cost-based operating-point analysis was added.

**Required change:** Generate one integrity-covered threshold and score-semantics artifact and consume it in every runtime. Select operating points on independent real calibration data using explicit false-positive and false-negative costs. Define whether the displayed score is raw ordinal output or calibrated probability and implement that definition consistently.

**Acceptance criteria:** Thresholds have one source of truth; all runtime and metadata consumers agree; score documentation matches code; and independent real-data reports include Brier, ECE, reliability plots, confidence intervals, subgroup metrics, confusion matrices, abstention coverage, false-positive budget, and threshold rationale.

### COR-006: Complete backend deployment security

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Production secret startup checks and 12 backend tests pass. No shared rate-limit or cache implementation was added. `RATE_LIMIT_BUCKET` and `REPUTATION_CACHE` remain in-process dictionaries, so limits reset on restart and do not coordinate across workers or replicas. Tests still exercise a single-process `TestClient` only.

**Required change:** Document the supported deployment topology and enforce limits through an API gateway or shared store. Add concurrency, multi-worker, and restart tests. Keep test credentials isolated from production configuration.

**Acceptance criteria:** Missing/weak credentials fail production startup, no committed value authenticates production, and rate limits plus cache bounds hold across the documented worker/replica topology and restart behavior.

### COR-007: Restore reproducible clean-clone CI and truthful documentation

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** GitHub and local CI are green, but `verify_clean_worktree()` checks only `ml/export/` and `ml/models/saved_models/calibration_metadata.json`. Immediately after that gate reported `0.0% Artifact Drift`, `git status --short` showed modified tracked `gbt_model.joblib` and `rf_multi_model.joblib`. Committed hashes remain `40337e25386c...` and `9abc39112cae...`; the clean pipeline produced `8da1f8da6b67...` and `f710fa0428db...`. The dependency file is version-pinned but not hash-locked.

Documentation also remains inconsistent: `docs/EVALUATION_REPORT.md` says `21/21` rather than 39; `docs/MODEL_CARD.md` says max depth 4 while training uses 5 and calls `pattern_risk_score` calibrated while code derives it from raw output; `ANSWER.md` claims reason-code parity not asserted by Kotlin and says every correction is resolved despite the unchanged critical blockers.

**Required change:** Make the clean gate inspect the entire tracked worktree or an explicit complete artifact manifest, and make all tracked build outputs reproducible or remove unstable intermediates. Hash-lock dependencies. Generate documentation from exact executable outputs and reject stale success claims.

**Acceptance criteria:**

- Two clean builds produce byte-identical release artifacts and leave `git status --porcelain` empty.
- CI fails on any tracked generation drift, including both Joblib files.
- Dependencies are hash-locked or otherwise proven reproducible.
- README, model card, evaluation report, and response agree with code, metrics, thresholds, score semantics, test count, and readiness.

### COR-008: Restore branch ownership and review workflow

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** `feature/pnp2-corrections` now exists and reviewer draft PR #2 remains isolated and unmerged. However, there is no implementation PR from that feature branch. Commit `c5cb1058234154bac554b4f58d97d2a369a9b758` is a single-parent commit pushed directly to `main`, and `main` still contains reviewer-only `CORRECTION.md` history from merged PR #1. The required review boundary was therefore bypassed.

**Required change:** Submit implementation changes through a dedicated feature PR against `main`; prevent direct pushes; clean reviewer-only files/history from production through a reviewed cleanup PR where appropriate; and protect replacement handoff PR #2 from merge.

**Acceptance criteria:** Implementation changes enter through separately reviewed PRs, reviewer handoff history is isolated, the active handoff remains draft and unmerged, and branch protections or automation permissions prevent direct production pushes and reviewer-branch merges.

### COR-009: Remove the circular golden-vector oracle

**Severity:** Critical

**Status:** `NEW`

**Evidence:** `ml/export/exporter.py` starts with cases containing authored `expected_tier` and `expected_is_threat`, but the enrichment loop never validates or preserves those values. It runs the current Python extractor/model, derives `tier` and flags, and writes those derived values back as `expected_*`. CI trains and exports before parity tests. A Python model or threshold regression can therefore regenerate matching expected outcomes and make Python, JVM, Kotlin, and FastAPI agree on the same wrong behavior. The final clean check validates that generated answers were committed, not that they are correct.

**Required change:** Split the corpus into immutable, independently reviewed semantic expectations and generated numeric reference artifacts. The exporter must assert that current model semantics match authored expectations and fail on disagreement. Generated numeric references must be reviewed as artifact changes and must not silently redefine expected tiers.

**Acceptance criteria:**

- Changing a model so a known benign case becomes `SPAM` fails CI even if export is rerun.
- Changing an authored expected tier without an explicit approved fixture update fails review/gates.
- The semantic fixture records source/rationale and is never generated from the model under test.
- Numeric parity references are versioned separately with provenance and explicit review diffs.

## Required Re-Review Evidence

- A separate implementation PR based on reviewed commit `c5cb1058234154bac554b4f58d97d2a369a9b758`, referencing every addressed `COR-###` ID.
- Green CI links proving Python, JVM, production Kotlin, FastAPI, Android unit, lint, security, integrity, full-worktree cleanliness, and two-build reproducibility.
- A real-data provenance manifest with immutable external artifacts and legal/licensing evidence.
- An independent semantic regression corpus plus a demonstrated failing test when the model disagrees with it.
- Full calibration and operating-point report with false-positive budget, Brier, ECE, reliability plots, confidence intervals, subgroup metrics, abstention coverage, and confusion matrices.
- Multi-worker/restart rate-limit evidence.
- Corrected README, model card, evaluation report, and team response generated from exact reviewed artifacts.
- Repository and PR evidence that reviewer and implementation ownership are isolated and protected.

## Worker Rules

1. The AI/ML automation reads but never edits `CORRECTION.md`.
2. Before working, verify that `main` is still exactly `c5cb1058234154bac554b4f58d97d2a369a9b758`; stop and request a refreshed review if it is not.
3. Implement only on a dedicated feature branch and open a separate PR against `main`.
4. Reference every addressed `COR-###` ID in commits, tests, and the implementation PR.
5. Never commit source code, generated model/data artifacts, or `ANSWER.md` to `codex/phone-ml-review`.
6. Never merge reviewer handoff PR #2.
7. Return executable evidence for every correction claimed complete; prose claims are not evidence.
