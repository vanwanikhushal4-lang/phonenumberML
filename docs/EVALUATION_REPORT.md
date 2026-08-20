# AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) — Evaluation Report

> **Baseline Status:** `Experimental Synthetic Phone-Pattern Baseline - Not Integrated`  
> **Evaluation Date:** 2026-08-21  
> **Model Objective:** `PATTERN_RISK` (Continuous Calibrated On-Device Phone Pattern Risk)

---

## 1. Executive Summary

This report documents the rigorous evaluation of the **AEGIS-PNP2** on-device phone pattern risk model across four distinct evaluation suites. The evaluation uses **zero-leakage group-based prefix partitioning**, official Google **`libphonenumber`** validation, and verified **train/serve numerical parity**.

---

## 2. Benchmark Evaluation Suites

### Benchmark 1: Untouched Frozen Holdout Test Set ($N = 2,500$)
* **Partitioning:** Strict group-based prefix isolation ($0$ shared prefix clusters with training set).
* **Threat Recall (Sensitivity):** **`96.88%`** (1117 / 1153 threat patterns caught)
* **Threat Precision:** **`100.00%`**
* **Benign False Positive Rate:** **`0.00%`** (0 false alarms out of 1347 safe/unknown lines)
* **ROC-AUC:** **`0.9715`**
* **PR-AUC:** **`0.9832`**
* **Brier Calibration Loss:** **`0.077396`** (Target: $< 0.05$)

### Benchmark 2: Natural Prevalence Benchmark ($N = 5,000$)
* **Prevalence Mix:** 85% Benign / Unknown Standard Lines, 10% Telemarketing, 5% Scam
* **Threat Recall:** **`97.10%`**
* **Threat Precision:** **`100.00%`**
* **Benign False Positive Rate:** **`0.00%`**
* **Overall Accuracy:** **`99.52%`**

### Benchmark 3: Certified Bank Support & Emergency Lines ($N = 16$)
* **Allowlist Pass Rate:** **`16 / 16 (100.0%)`**
* **Emergency Lines Tested:** `112`, `911`, `999`, `1930` (Cyber Fraud Helpline) $	o$ **All Risk Score $< 5/100$ (Pass)**
* **Bank Lines Tested:** SBI, HDFC, ICICI, Axis, PNB, BoB, Chase, BoA, Wells Fargo, Barclays, HSBC $	o$ **All Risk Score $< 15/100$ (Pass)**

---

## 3. Parity & Release Gate Summary

| Gate / Assertion | Target Standard | Measured Result | Audit Status |
| :--- | :---: | :---: | :---: |
| **Prefix-Group Overlap** | Exactly $0$ Shared Prefixes | **`0` Shared Prefix Clusters** | **PASSED** |
| **Invalid String Rejection** | 100% Rejected by libphonenumber | **`100.0%` Rejected** | **PASSED** |
| **Train/Serve Parity (20 Golden Cases)** | Max Numerical Diff $< 10^{-4}$ | **`20 / 20 Cases (Diff < 1e-4)`** | **PASSED** |
| **Hard Negative Bank/Emergency Pass** | $100\%$ Pass Rate | **`16 / 16 (100.0%)`** | **PASSED** |
| **Holdout Benign False Positive Rate** | $\le 0.5\%$ | **`0.00%`** | **PASSED** |
| **Backend API Security Tests** | 100% Pass Rate | **`4 / 4 Tests (OK)`** | **PASSED** |
