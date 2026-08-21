# AEGIS Automated Model Review

> Reviewer-managed file. The AI/ML implementation automation may read this file but must not edit it.

| Field | Value |
| --- | --- |
| Reviewer owner | `Codex automated reviewer` |
| Review status | `CHANGES_REQUIRED` |
| Reviewed branch | `main` |
| Reviewed commit | `489275005c9a113008b0b3ec88b54779e697afc7` |
| Reviewed range | `725db5d8b36ac47ce59083e4dfb75483e57c7fbd..489275005c9a113008b0b3ec88b54779e697afc7` |
| Review date | `2026-08-21` |
| Reviewer branch | `codex/phone-ml-review` |
| Team response | `ANSWER.md` at `489275005c9a113008b0b3ec88b54779e697afc7` |
| Handoff PR | `#2` (replacement draft; do not merge) |

## Readiness Verdict

`CHANGES_REQUIRED`. Exact-commit GitHub Actions and the local clean pipeline are now green. The update fixes the immediate repository-cleanliness failures, expands parity to normalized E.164, separates semantic expectations from generated numeric references, and corrects several documentation claims. It also creates a release-critical backend regression: a fresh checkout cannot import or start the FastAPI service because `gbt_model.joblib` was removed while the server still loads it at module import. The new semantic provenance and negative-control claims are not independently verifiable, and the synthetic-data, calibration, distributed-backend, and branch-governance blockers remain. Do not integrate this model into Aegis.

## Verified Improvements

- GitHub Actions run `32472864728` is green for exact commit `489275005c9a113008b0b3ec88b54779e697afc7`, including Android unit tests/lint and the master pipeline.
- A clean local `python scripts/run_ci.py` completed successfully with 39/39 Python/JVM/FastAPI parity cases, 12/12 backend tests, 4/4 newly added semantic-control tests, Brier scores `0.122648` on holdout and `0.110364` on benchmark, and an empty final worktree.
- `.gitignore` now excludes disposable Gradle output and generated Joblib/NumPy intermediates. The two unstable tracked Joblib files were removed, so the clean-worktree gate now passes.
- `ml/evaluation/fixtures/canonical_semantic_expectations.json` separates authored semantic expectations from generated numeric references.
- The exporter asserts tier, threat, validity, abstention, invalid state, and normalized E.164 against the semantic fixture.
- Kotlin parity now includes normalized E.164 in addition to features, raw output, probability, score, tier, and flags.
- `docs/EVALUATION_REPORT.md` now reports 39/39 parity and includes FastAPI; model depth and score-semantics documentation were corrected.
- Reviewer handoff PR #2 remains open and draft.

## Resolved Corrections

### COR-004: Implement real model integrity verification

**Severity:** High

**Status:** `RESOLVED`

Kotlin canonical tree hashing, constant-time digest comparison, and fail-closed threshold-tampering coverage remain effective.

## Open Corrections

### COR-001: Complete false-positive regression coverage

**Severity:** High

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** The 39-case corpus covers the requested toll-free and former blanket-country-code examples, semantic expectations now live outside exporter code, and normalization is asserted. The fixture's provenance fields are descriptive strings rather than verifiable evidence: cases provide no immutable source URL/release, source artifact hash, record identifier, retrieval record, license, or independent approval record. Neighboring-prefix coverage remains thin, and Kotlin does not assert expected reason codes or explanations.

**Required change:** Attach verifiable source/rationale evidence to every semantic case, add neighboring-prefix and decision-boundary examples, and assert every user-visible semantic output in every production runtime.

**Acceptance criteria:** Fixture changes require an identifiable independent approval; every case links to an immutable source artifact and rationale; and Python, JVM, Kotlin, and FastAPI agree on independently expected normalization, validity, features, score, probability, tier, threat, abstention, reason codes, and explanations.

### COR-002: Replace synthetic data and fabricated provenance

**Severity:** Critical

**Status:** `NOT_RESOLVED`

**Evidence:** This range changes no training/evaluation dataset or real-data provenance artifact. `dataset_builder.py` still selects labels first, generates digits using label-specific rules, and creates source-like identifiers. Training, calibration, validation, holdout, and benchmark sets still come from the same synthetic generator and labeling logic. Prefix-separated splits do not make labels or evaluation independent.

**Required change:** Mark generated datasets as synthetic fixtures. Acquire legally usable real records with labels produced independently of model features and generator rules, preserve immutable source artifacts, and construct calibration/final evaluation sets from those records.

**Acceptance criteria:**

- Every real evaluation row traces to an immutable source artifact, source URL/release, retrieval record, license, and independently reviewed label.
- Generated IDs are never represented as source record IDs.
- Holdout and benchmark labels are independent of generator and feature rules.
- Entity, number, prefix family, time, country, and source isolation are audited before splitting.
- Legal/licensing review and a passing provenance-verifier result are attached to the implementation PR.

### COR-003: Make Android and Kotlin genuine parity release gates

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Exact-commit Android unit/lint and 39/39 Python/JVM/FastAPI parity pass. Kotlin now compares normalized E.164, but it still does not consume or assert the fixture's `expected_reason_codes` or `expected_explanations`. The independently authored fixture also lacks verifiable provenance, so the suite proves more runtime agreement than domain correctness.

**Required change:** Assert reason codes and explanations in production Kotlin, provide independently reviewed semantic evidence, and add mutation/fault-injection tests that exercise the actual export and runtime gates.

**Acceptance criteria:** CI proves full observable-output parity across Python, standalone JVM, production Kotlin, and FastAPI against an independently evidenced canonical corpus, with explicit numeric tolerances and demonstrated failing mutations for features, thresholds, normalization, reason codes, and explanations.

### COR-005: Correct calibration quality and decision semantics

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Documentation now correctly describes `pattern_risk_score` as raw regression output scaled to 100, and threshold metadata exists. The `0.10/0.60/0.98` cutoffs remain duplicated across training, export, Python/JVM/Kotlin, and FastAPI instead of being consumed from one integrity-covered contract. Holdout Brier remains `0.122648`, benchmark Brier `0.110364`, and no ECE, reliability curve, confidence interval, subgroup calibration, false-positive budget, or cost-based threshold analysis was added. All reported metrics are synthetic.

**Required change:** Export and consume one integrity-covered threshold/score contract everywhere. Select operating points on independent real calibration data using explicit user-harm costs.

**Acceptance criteria:** One verified artifact controls all runtime thresholds and score semantics; independent real-data reports include Brier, ECE, reliability plots, confidence intervals, subgroup metrics, confusion matrices, abstention coverage, false-positive budget, and threshold rationale.

### COR-006: Complete backend deployment security

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Production-secret validation and 12 backend tests pass after model training. Rate limiting and reputation caching remain process-local dictionaries, so behavior resets or diverges across workers, replicas, and restarts. No multi-worker, concurrent, or restart evidence was added.

**Required change:** Document the supported topology and use an API gateway or shared store for limits/cache wherever multi-worker or multi-replica deployment is supported. Add concurrency, restart, and multi-worker tests.

**Acceptance criteria:** Missing/weak credentials fail startup, no committed credential authenticates production, and rate/cache bounds hold across the documented worker/replica topology and restart behavior.

### COR-007: Restore reproducible clean-clone CI and truthful documentation

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Exact-commit run `32472864728` is green, a local clean pipeline leaves the worktree empty, unstable Joblib intermediates are no longer tracked, and the previously stale evaluation count/model-depth/score documentation is corrected. Dependency hashes and a locked build image are still absent. More importantly, removing the tracked serving model made a fresh checkout unable to start the backend; that release-path regression is tracked separately as COR-010.

**Required change:** Lock dependencies and the build image, publish reproducibility manifests for actual release artifacts, and test the clean deployment/startup path before any training step can create missing files.

**Acceptance criteria:**

- GitHub Actions is green for the exact reviewed implementation commit.
- Two clean builds on the declared runner produce byte-identical published artifacts and leave `git status --porcelain` empty.
- Dependencies and the build image are locked and integrity checked.
- CI exercises the same artifact acquisition/build and startup path used in deployment.
- README, model card, evaluation report, and team response match exact code, metrics, test counts, score semantics, and readiness.

### COR-008: Restore branch ownership and review workflow

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Feature branch `feature/pnp2-corrections` exists and reviewer handoff PR #2 remains separate and draft. There is still no implementation PR, and all three commits in this reviewed range were pushed directly to `main`. Reviewer-only history/files introduced when PR #1 was merged remain in production history.

**Required change:** Submit implementation changes through a dedicated PR against `main`, prevent direct pushes, remove reviewer-only production files through a separately reviewed cleanup PR where appropriate, and keep PR #2 unmergeable by worker automation.

**Acceptance criteria:** Implementation enters through separately reviewed PRs, reviewer handoff remains isolated/draft/unmerged, and branch protection plus automation permissions prevent direct production pushes and reviewer-branch merges.

### COR-009: Remove the circular golden-vector oracle

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Semantic expectations now live in a separate JSON fixture and the exporter asserts several fields, which is a useful structural improvement. The fixture's provenance and approval are self-asserted strings, not independently verifiable records. Python negative tests manually assign known-wrong values or mutate an isolated feature array and then assert that the hand-written mismatch is detectable; they do not mutate and execute the production exporter/runtime gate. Kotlin tests use `assertNotEquals` against hard-coded bad values rather than fault-injecting the production evaluator. Reason codes and explanations are still not asserted in Kotlin.

**Required change:** Make semantic evidence immutable and independently approved, assert every authored field, and implement mutation tests that run the real export/parity/runtime paths with known defects.

**Acceptance criteria:**

- A known benign-to-SPAM production-model mutation fails the real CI gate even after export is rerun.
- Feature, threshold, normalization, reason-code, and explanation mutations fail the corresponding production paths.
- Semantic fixture changes are isolated, attributed, independently approved, and linked to immutable evidence.
- Numeric references remain versioned separately with provenance and reviewable diffs.

### COR-010: Ship a runnable, verified backend model artifact

**Severity:** Critical

**Status:** `NEW`

**Evidence:** The reviewed range removes `ml/models/saved_models/gbt_model.joblib`, but `ml/api/server.py` still loads that path during module import. In a fresh checkout, before training, `AEGIS_TEST_MODE=1 AEGIS_SERVER_API_KEY=<valid-test-secret> python -c 'import ml.api.server'` fails with `FileNotFoundError` for `ml/models/saved_models/gbt_model.joblib`. CI hides the defect because `scripts/run_ci.py` trains and recreates the ignored file before importing/testing FastAPI. The README documents the pipeline but no reproducible backend artifact build/acquisition and deployment contract.

**Required change:** Define one explicit serving-artifact contract: make FastAPI evaluate the tracked integrity-checked JSON model, package a reproducibly built model in the deployment image with a hash manifest, or acquire a versioned artifact with mandatory integrity verification. Add a fresh-checkout backend startup test that runs before training.

**Acceptance criteria:**

- The documented backend command imports and starts from a fresh release checkout or freshly built deployment image without relying on prior CI/training side effects.
- CI runs this startup test before any command can create the serving artifact.
- Artifact identity, model version, and integrity digest are tied to the release manifest and verified at startup.
- A missing or corrupt artifact fails startup with a clear actionable error rather than an unhandled file-loading traceback.

## Required Re-Review Evidence

- A separate implementation PR based on reviewed commit `489275005c9a113008b0b3ec88b54779e697afc7`, referencing every addressed `COR-###` ID.
- A green exact-commit GitHub Actions link plus two-build release-artifact reproducibility manifests from a locked environment.
- A fresh-checkout or fresh-image backend startup log produced before training, including artifact identity and integrity verification.
- A real-data provenance manifest with immutable external artifacts and legal/licensing evidence.
- Independently owned semantic fixtures with source evidence and production-path mutation-test logs.
- Independent calibration report with false-positive budget, Brier, ECE, reliability plots, confidence intervals, subgroup metrics, abstention coverage, and confusion matrices.
- Multi-worker/restart rate-limit and cache evidence.
- Branch-protection and implementation-PR evidence proving reviewer/worker isolation.

## Worker Rules

1. The AI/ML automation reads but never edits `CORRECTION.md`.
2. Before working, verify that `main` is still exactly `489275005c9a113008b0b3ec88b54779e697afc7`; stop and request a refreshed review if it is not.
3. Implement only on a dedicated feature branch and open a separate PR against `main`.
4. Reference every addressed `COR-###` ID in commits, tests, and the implementation PR.
5. Never commit source code, generated model/data artifacts, or `ANSWER.md` to `codex/phone-ml-review`.
6. Never merge reviewer handoff PR #2.
7. Return executable evidence for every correction claimed complete; prose claims are not evidence.
