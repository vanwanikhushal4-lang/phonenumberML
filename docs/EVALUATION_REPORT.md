# AEGIS-PNP2 Evaluation & Production Verification Report

> **Current Repository Status**: **`Experimental Synthetic Phone-Pattern Baseline - Not Integrated.`**
> **Model Objective**: Phone-Pattern Structural Risk Scoring (0–100 Ordinal Score & Platt-Calibrated Threat Probability).
> **Evaluation Date**: 2026-08-21 | **Architecture**: 150-Tree Gradient Boosted Decision Tree + Platt Sigmoid Calibrator.

---

## 1. Zero-Overlap 6-Way Group Partitioning Audit

All numbers are partitioned by immutable prefix family `group_id` before sample generation. The table below proves **strict zero 7-digit prefix overlap** across all split pairs:

| Split Pair | Shared 7-Digit Prefixes | Isolation Status |
| :--- | :--- | :--- |
| **Train vs. Validation** | `0` | **PASSED (Strict Zero Overlap)** |
| **Train vs. Untouched Holdout Test** | `0` | **PASSED (Strict Zero Overlap)** |
| **Train vs. Natural Prevalence Benchmark** | `0` | **PASSED (Strict Zero Overlap)** |
| **Validation vs. Untouched Holdout Test** | `0` | **PASSED (Strict Zero Overlap)** |
| **Validation vs. Natural Prevalence Benchmark** | `0` | **PASSED (Strict Zero Overlap)** |
| **Untouched Test vs. Natural Prevalence Benchmark** | `0` | **PASSED (Strict Zero Overlap)** |

---

## 2. Quantitative Release Gate Performance

| Gate Metric | Enforced Release Threshold | Untouched Holdout Test (N=2,500) | Natural Prevalence Benchmark (N=5,000) | Gate Status |
| :--- | :--- | :--- | :--- | :--- |
| **Brier Score Loss** | `< 0.0500` | **`0.000705`** | **`0.000839`** | **PASSED** |
| **ROC-AUC** | `> 0.9000` | **`1.0000`** | **`1.0000`** | **PASSED** |
| **PR-AUC** | `> 0.9000` | **`1.0000`** | **`1.0000`** | **PASSED** |
| **7-Digit Prefix Overlap** | `== 0` | **`0`** | **`0`** | **PASSED** |

---

## 3. Holdout Test Set Tier Breakdown (N=2,500)

| Sourced Ground-Truth Label | Total Samples | Evaluated `LEGITIMATE` | Evaluated `UNKNOWN` (Abstain) | Evaluated `SPAM` | Evaluated `SCAM` | Evaluated `INVALID` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BENIGN (Helpline/Bank)** | `436` | `436` | `0` | `0` | `0` | `0` |
| **UNKNOWN (Standard Mobile/Landline)** | `720` | `0` | `720` | `0` | `0` | `0` |
| **TELEMARKETING_SPAM** | `611` | `0` | `0` | `611` | `0` | `0` |
| **CONFIRMED_SCAM** | `699` | `0` | `0` | `0` | `699` | `0` |
| **INVALID (Syntax / Malformed)** | `34` | `0` | `0` | `0` | `0` | `34` |

---

## 4. End-to-End Golden Vector Parity Verification

The 20 independently authored golden test cases were evaluated across:
1. Python Scikit-Learn Pipeline (`extract_features_from_number` + `gbt.predict`)
2. Pure JVM Engine (`JvmPhoneNumberEvaluator.java`)
3. Android Kotlin Runtime (`PhoneNumberRiskModel.kt`)

**Result**: **20 / 20 Cases (100.0%) PASSED with 0.000000 semantic drift**.
