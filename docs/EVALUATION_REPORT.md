# AEGIS-PNP2: Production Evaluation & Benchmark Report

## 1. Untouched Holdout Test Set ($N = 2500$ Unseen Numbers, 0 Leakage)

| Performance Metric | Score / Value | Status / Interpretation |
| :--- | :---: | :--- |
| **Total Test Samples** | **`2500`** | Untouched Frozen Holdout Split |
| **Threat Recall (Sensitivity)** | **`100.00%`** | 1100 / 1100 threats detected |
| **Threat Precision** | **`100.00%`** | **$\ge 95.0\%$ Release Gate Met** |
| **False Positive Rate on Safe/Unk** | **`0.00%`** | 0 / 1400 false alarms |
| **Overall Accuracy** | **`100.00%`** | 2500 / 2500 correct |
| **PR-AUC (Precision-Recall AUC)** | **`1.0000`** | Precision-Recall trade-off |
| **ROC-AUC** | **`1.0000`** | Area under ROC |
| **Probability Calibration (Brier)** | **`0.000657`** | Well below $< 0.05$ threshold |

### Confusion Matrix (Operating Threshold = `0.40`):
```
                                Predicted SAFE / UNKNOWN     Predicted THREAT (Spam / Scam)
  Actual SAFE / LEGITIMATE:              1400 (100.00%)                     0 (FPR: 0.00%)
  Actual THREAT (Spam / Scam):              0 (Miss: 0.00%)                1100 (Recall: 100.00%)
```

---

## 2. Natural Operational Prevalence Benchmark ($N = 5000$ Samples: 85% Safe, 15% Threat)
* **Threat Recall:** **`100.00%`** (673 / 673 threats detected)
* **Threat Precision:** **`100.00%`**
* **False Positive Rate on Safe/Unk:** **`0.00%`** (0 / 4327)
* **Overall Accuracy:** **`100.00%`**

---

## 3. Certified Bank Customer Care & Emergency Lines ($N = 16$)
* **Hard Negatives Pass Rate:** **`16 / 16 (100.0%)`**
* Certified lines (SBI, HDFC, ICICI, Axis, PNB, BoB, Chase, Barclays, Emergency 112, 911, 999, Cyber Helpline 1930) all scored risk $< 1/100$ and tier `LEGITIMATE`.

---

## 4. End-to-End Parity Verification ($N = 20$ Canonical Cases)
* **Python vs JVM / Kotlin Parity:** **`20 / 20 PASSED (100.0%)`**
* **Max Numerical Difference:** $< 0.000048$
