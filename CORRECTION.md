# AEGIS Automated Model Review

> Reviewer-managed file. The AI/ML implementation automation may read this file but must not edit it.

| Field | Value |
| --- | --- |
| Reviewer owner | `Codex automated reviewer` |
| Review status | `CHANGES_REQUIRED` |
| Reviewed branch | `main` |
| Reviewed commit | `725db5d8b36ac47ce59083e4dfb75483e57c7fbd` |
| Reviewed range | `c5cb1058234154bac554b4f58d97d2a369a9b758..725db5d8b36ac47ce59083e4dfb75483e57c7fbd` |
| Review date | `2026-08-21` |
| Reviewer branch | `codex/phone-ml-review` |
| Team response | `ANSWER.md` at `725db5d8b36ac47ce59083e4dfb75483e57c7fbd` |
| Handoff PR | `#2` (replacement draft; do not merge) |

## Readiness Verdict

`CHANGES_REQUIRED`. The update makes two useful corrections: exporter output can no longer silently replace authored tier/threat expectations, and the clean-worktree gate now checks the full repository. That stronger gate correctly exposes that the release is not reproducible. Both GitHub runs for this update are red; the final run reports modified tracked Joblib files plus untracked Gradle build directories after all earlier gates pass. The synthetic-data, calibration-quality, process-local rate-limit, documentation, and implementation-PR blockers also remain. Do not integrate this model into Aegis.

## Verified Improvements

- `ml/export/exporter.py` now preserves authored `expected_tier` and `expected_is_threat` values and raises when current Python predictions disagree.
- Generated numeric values were renamed to `reference_*`, making their Python-derived status clearer.
- Kotlin tests consume the renamed numeric references and the Android unit/lint step passed on GitHub for the reviewed commit.
- Training metadata now records the same `0.10/0.60/0.98` cutoffs used by the current runtimes.
- Random-forest fitting is single-threaded and Joblib output is compressed. Repeated retraining in one local environment produced stable bytes.
- `verify_clean_worktree()` now checks `git status --porcelain` for the full repository instead of a narrow artifact subset.
- GitHub run `32471619706` passed training, export, 39/39 Python/JVM/FastAPI parity, evaluation, 12/12 backend tests, and Android unit/lint before correctly failing the cleanliness gate.
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

**Evidence:** The 39-case input corpus covers all previously requested toll-free and former blanket-country-code examples. Tier and threat expectations are now authored rather than overwritten. Those expectations still have no immutable external source or review rationale, neighboring-prefix coverage remains thin, and other semantics such as validity, abstention, normalization, reasons, and explanations are still generated from current code.

**Required change:** Move semantic fixtures to a separately reviewed file with source/rationale per case. Add neighboring-prefix and boundary cases. Preserve all expected observable semantics independently from generated runtime references.

**Acceptance criteria:** Fixture changes require explicit review; every case records its rationale/source; and Python, JVM, Kotlin, and FastAPI agree on independently expected normalization, validity, features, score, probability, tier, threat, abstention, and reason outputs.

### COR-002: Replace synthetic data and fabricated provenance

**Severity:** Critical

**Status:** `NOT_RESOLVED`

**Evidence:** The reviewed range changes no dataset, builder, provenance document, or data manifest. `dataset_builder.py` still chooses labels first, generates digits from label-specific rules, and invents record IDs. Training, calibration, validation, holdout, and benchmark remain products of the same synthetic generator. Prefix separation does not create independent labels or real-world evaluation.

**Required change:** Mark current datasets as synthetic fixtures. Acquire legally usable real records independently of model features and label rules, preserve immutable source artifacts, and construct calibration/final evaluation sets from those records.

**Acceptance criteria:**

- Every real evaluation row traces to an immutable source artifact, source URL/release, retrieval record, license, and independently reviewed label.
- Generated IDs are never presented as source record IDs.
- Holdout and benchmark labels are independent of generator and feature rules.
- Entity, number, prefix family, time, country, and source isolation are audited before splitting.
- Legal/licensing review and a provenance-verifier result are attached to the implementation PR.

### COR-003: Make Android and Kotlin genuine parity release gates

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Android tests and lint pass, Kotlin checks features/raw output/probability/score/tier/flags, and Python/JVM/FastAPI parity passes 39/39. Kotlin still does not compare normalized E.164, reason codes, or explanations. Numeric references, validity, abstention, and reasons are generated from Python, so the suite mainly proves runtime agreement rather than independent correctness.

**Required change:** Add Kotlin normalization and reason-output assertions, independently author all semantic expectations, and add negative tests proving the gate fails on feature, threshold, normalization, and explanation drift.

**Acceptance criteria:** CI proves full observable-output parity across Python, standalone JVM, production Kotlin, and FastAPI against an independent canonical corpus with explicit tolerances and deliberate failing controls.

### COR-005: Correct calibration quality and decision semantics

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Threshold metadata now matches the current hard-coded runtime values, and earlier FastAPI counterexamples remain fixed. Thresholds are still duplicated across training, exporter, Python evaluation, JVM, Kotlin, and FastAPI rather than consumed from one integrity-covered artifact. `pattern_risk_score` remains raw model output scaled to 100 while documentation calls it calibrated. Holdout Brier remains `0.122648`, benchmark Brier `0.110364`, and no ECE, reliability curve, confidence interval, subgroup calibration, false-positive budget, or cost-based operating analysis was added. All metrics are still synthetic.

**Required change:** Export one threshold/score contract and consume it everywhere. Define score semantics consistently. Select operating points on independent real calibration data using explicit user-harm costs.

**Acceptance criteria:** One integrity-covered source controls all runtime thresholds and score semantics; independent real-data reports include Brier, ECE, reliability plots, confidence intervals, subgroup metrics, confusion matrices, abstention coverage, false-positive budget, and threshold rationale.

### COR-006: Complete backend deployment security

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Production secret validation and 12 backend tests still pass. No backend deployment change appears in this range. Rate limiting and reputation caching remain process-local dictionaries and reset or diverge across workers, replicas, and restarts.

**Required change:** Document the supported topology and use an API gateway or shared store for limits/cache where multi-worker deployment is supported. Add concurrency, restart, and multi-worker tests.

**Acceptance criteria:** Missing/weak credentials fail startup, no committed credential authenticates production, and limits/cache bounds hold across the documented worker/replica topology and restart behavior.

### COR-007: Restore reproducible clean-clone CI and truthful documentation

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** The broader gate is an improvement, but both exact-commit GitHub runs failed. Run `32471619706` reported:

- Modified `ml/models/saved_models/gbt_model.joblib`
- Modified `ml/models/saved_models/rf_multi_model.joblib`
- Untracked `.gradle/`, `android/build/`, and `build/`

The workflow creates the Gradle directories before running the master gate, while `.gitignore` does not exclude them. The tracked Joblib bytes also do not reproduce on the Python 3.11 GitHub runner. Locally, committed hashes `582c6cccf108...` and `0abc806cd6a3...` became `394c733044c8...` and `75f4dc3ff800...`; a second local retrain was byte-stable only within that environment. `ANSWER.md` nevertheless claims the entire worktree is clean. Dependency hashes/lock evidence remain absent, `docs/EVALUATION_REPORT.md` still says 21/21, and the model-card depth/score claims remain inconsistent with code.

**Required change:** Ignore only disposable Gradle outputs, then make tracked release artifacts reproducible on the declared build image or stop tracking unstable Joblib intermediates. Pin the build environment and dependency hashes. Generate documentation from exact gates and forbid success claims while CI is red.

**Acceptance criteria:**

- GitHub Actions is green for the exact reviewed implementation commit.
- Two clean builds on the declared runner produce byte-identical published artifacts and leave `git status --porcelain` empty.
- CI covers every tracked generated artifact and ignores only documented disposable build outputs.
- Dependencies and build image are locked.
- README, model card, evaluation report, and response match code, metrics, score semantics, test count, and readiness.

### COR-008: Restore branch ownership and review workflow

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Feature branch `feature/pnp2-corrections` and draft handoff PR #2 remain separate. There is still no implementation PR. Both new commits were pushed directly to `main`, and reviewer-only history/files from merged PR #1 remain in production history.

**Required change:** Put implementation changes in a dedicated PR against `main`, prevent direct pushes, clean reviewer-only production files through a reviewed cleanup PR where appropriate, and protect PR #2 from merge.

**Acceptance criteria:** Implementation enters through separately reviewed PRs, the reviewer handoff remains isolated/draft/unmerged, and branch protections or automation permissions prevent direct production pushes and reviewer-branch merges.

### COR-009: Remove the circular golden-vector oracle

**Severity:** Critical

**Status:** `PARTIALLY_RESOLVED`

**Evidence:** Export now fails when Python tier or threat output disagrees with authored values, which removes the original direct overwrite defect. The semantic fixture still lives as mutable constants inside the exporter, carries no source/rationale, and can be edited in the same implementation commit. Validity, abstention, invalid state, normalization, reason codes, and explanations are still computed by the implementation under test. No negative test demonstrates that a known semantic regression fails CI.

**Required change:** Store immutable semantic expectations separately from exporter code and generated numeric references. Add provenance/rationale and approval ownership. Assert every authored semantic field, and add deliberate failing tests.

**Acceptance criteria:**

- A known benign-to-SPAM model change fails CI even when export is rerun.
- Semantic fixture changes are isolated, attributed, and require explicit approval.
- All semantic expectations are independent of the model/parser under test.
- Numeric references are versioned separately with provenance and reviewable diffs.

## Required Re-Review Evidence

- A separate implementation PR based on reviewed commit `725db5d8b36ac47ce59083e4dfb75483e57c7fbd`, referencing every addressed `COR-###` ID.
- A green exact-commit GitHub Actions link and two-build reproducibility manifests.
- A real-data provenance manifest with immutable external artifacts and legal/licensing evidence.
- A separately owned semantic regression fixture plus demonstrated negative tests.
- Independent calibration report with false-positive budget, Brier, ECE, reliability plots, confidence intervals, subgroup metrics, abstention coverage, and confusion matrices.
- Multi-worker/restart rate-limit evidence.
- Corrected README, model card, evaluation report, and team response generated from exact reviewed artifacts.
- Branch-protection and PR evidence proving reviewer/implementation isolation.

## Worker Rules

1. The AI/ML automation reads but never edits `CORRECTION.md`.
2. Before working, verify that `main` is still exactly `725db5d8b36ac47ce59083e4dfb75483e57c7fbd`; stop and request a refreshed review if it is not.
3. Implement only on a dedicated feature branch and open a separate PR against `main`.
4. Reference every addressed `COR-###` ID in commits, tests, and the implementation PR.
5. Never commit source code, generated model/data artifacts, or `ANSWER.md` to `codex/phone-ml-review`.
6. Never merge reviewer handoff PR #2.
7. Return executable evidence for every correction claimed complete; prose claims are not evidence.
