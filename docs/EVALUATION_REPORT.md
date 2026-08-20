# AEGIS-PNP2: Production Evaluation & Benchmark Report

## 1. Untouched Holdout Test Set ($N = 2,500$ Unseen Numbers, 0 Leakage)

| Performance Metric | Score / Value | Status |
| :--- | :---: | :--- |
| **Total Test Samples** | **`2,500`** | Untouched Holdout Split |
| **Threat Recall (Sensitivity)** | **`97.42%`** | $1,095 / 1,124$ threats caught |
| **Threat Precision** | **`95.88%`** | **$\ge 95.0\%$ Release Gate Met** |
| **False Positive Rate on Safe/Unk** | **`3.42%`** | $47 / 1,376$ false alarms |
| **Overall Accuracy** | **`96.96%`** | $2,424 / 2,500$ correct |
| **PR-AUC (Precision-Recall AUC)** | **`0.9975`** | Excellent discrimination |
| **ROC-AUC** | **`0.9979`** | Area under ROC |
| **Probability Calibration (Brier)** | **`0.018361`** | Well below $< 0.05$ threshold |

### Confusion Matrix (Operating Threshold = `0.40`):
```
                                Predicted SAFE / UNKNOWN     Predicted THREAT (Spam / Scam)
  Actual SAFE / LEGITIMATE:             1,329 (96.58%)                  47 (FPR: 3.42%)
  Actual THREAT (Spam / Scam):             29 (Miss: 2.58%)          1,095 (Recall: 97.42%)
```

---

## 2. Natural Operational Prevalence Benchmark ($N = 5,000$ Samples: 85% Safe, 15% Threat)
* **Threat Recall:** **`96.80%`** ($695 / 718$ threats caught)
* **Threat Precision:** **`82.64%`**
* **False Positive Rate on Safe/Unk:** **`3.41%`** ($146 / 4,282$)
* **Overall Accuracy:** **`96.62%`**

---

## 3. Certified Bank Customer Care & Emergency Lines ($N = 16$)
* **Hard Negatives Pass Rate:** **`16 / 16 (100.0%)`**
* SBI (`+911800112211`), HDFC (`+9118002026161`), ICICI (`+9118001080`), Axis (`+9118002098800`), Chase (`+18009359935`), Barclays (`+44800123456`), Emergency `112`, `911`, `999`, Cyber Helpline `1930` all scored risk $< 1/100$ and tier `LEGITIMATE`.

---

## 4. End-to-End Parity Verification ($N = 20$ Canonical Cases)
* **Python vs JVM / Kotlin Parity:** **`20 / 20 PASSED (100.0%)`**
* **Max Feature Difference:** $< 0.000048$
* Full agreement on normalization, validity, 36 features, logits, calibrated probabilities, tiers, and reason codes.