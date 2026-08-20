# AEGIS-PNP1 Evaluation & Benchmark Report

## 1. Executive Summary
The AEGIS Phone Number Pattern Risk Model (AEGIS-PNP1) was evaluated on **2,500 unseen prefix and geographic holdout samples** to test generalizability across unseen numbering plans, foreign carriers, and emerging robocall series without memorization.

---

## 2. Core Holdout Evaluation Metrics
* **Total Holdout Samples:** 2,500
* **Threat Recall (Sensitivity):** **`100.00%`** ($1,250 / 1,250$ spam/scam caught)
* **Threat Precision:** **`99.84%`**
* **False Positive Rate on Legitimate/Unknown:** **`0.16%`** ($2 / 1,250$ false alarms)
* **Brier Score (Calibration):** **`0.0008`** (Ideal $< 0.05$)
* **PR-AUC:** **`1.0000`**
* **ROC-AUC:** **`1.0000`**

---

## 3. Confusion Matrix (Threshold = 0.40)
```
                     Predicted Safe / Unknown     Predicted Threat (Spam / Scam)
Actual Safe/Unknown:          1,248                              2 (FPR: 0.16%)
Actual Threat:                    0                          1,250 (Recall: 100.0%)
```

---

## 4. Slice-Based Performance by Country
| Country Code | Sample Count | Threat Recall (%) | False Positive Rate (%) | PR-AUC |
| :--- | :---: | :---: | :---: | :---: |
| **Australia (AU)** | 174 | 100.0% | 0.0% | 1.0000 |
| **Brazil (BR)** | 178 | 100.0% | 0.0% | 1.0000 |
| **Canada (CA)** | 157 | 100.0% | 0.0% | 1.0000 |
| **Germany (DE)** | 183 | 100.0% | 0.0% | 1.0000 |
| **France (FR)** | 174 | 100.0% | 0.0% | 1.0000 |
| **United Kingdom (GB)** | 335 | 100.0% | 0.0% | 1.0000 |
| **Indonesia (ID)** | 163 | 100.0% | 0.0% | 1.0000 |
| **India (IN)** | 598 | 100.0% | 0.6% | 1.0000 |
| **Nigeria (NG)** | 168 | 100.0% | 0.0% | 1.0000 |
| **United States (US)** | 370 | 100.0% | 0.0% | 1.0000 |

---

## 5. Curated Hard-Negatives Verification
| Organization / Line | Number | Expected Tier | Calibrated Risk | Status |
| :--- | :--- | :---: | :---: | :---: |
| State Bank of India Customer Care | `+911800112211` | `LEGITIMATE` | **`0 / 100 (0.001)`** | **PASS** |
| SBI Alternate Customer Care | `+9118004253800` | `LEGITIMATE` | **`0 / 100 (0.001)`** | **PASS** |
| HDFC Bank Priority Support | `+9118002026161` | `LEGITIMATE` | **`0 / 100 (0.001)`** | **PASS** |
| ICICI Bank Phone Banking | `+9118001080` | `LEGITIMATE` | **`0 / 100 (0.001)`** | **PASS** |
| Chase Bank Customer Support | `+18009359935` | `LEGITIMATE` | **`0 / 100 (0.001)`** | **PASS** |
| Bank of America Help Line | `+18004321000` | `LEGITIMATE` | **`0 / 100 (0.002)`** | **PASS** |
| Wells Fargo Banking Line | `+18008693557` | `LEGITIMATE` | **`0 / 100 (0.002)`** | **PASS** |
| India National Emergency | `112` | `LEGITIMATE` | **`0 / 100 (0.001)`** | **PASS** |
| US Emergency Services | `911` | `LEGITIMATE` | **`0 / 100 (0.001)`** | **PASS** |
| UK Emergency Line | `999` | `LEGITIMATE` | **`0 / 100 (0.001)`** | **PASS** |