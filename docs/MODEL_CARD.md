# AEGIS-PNP1: Phone Number Pattern Risk Model Card

## 1. Model Details
* **Model Name:** AEGIS-PNP1 (Phone Number Pattern Risk Model)
* **Model Version:** 1.0.0
* **Architecture:** 150-Tree Calibrated Gradient Boosted Decision Tree Ensemble (`GradientBoostingClassifier` with 5-Fold Sigmoid Probability Calibration).
* **Model Formats:** Pure JSON Tree Evaluator (`phonenumber_risk_model.json`), Mobile TensorFlow Lite FlatBuffer (`phonenumber_risk_model.tflite`), Scikit-Learn Joblib (`calibrated_gbt.joblib`).
* **Input Feature Space:** 36 Privacy-Preserving Structural & Numbering-Plan Dimensions.
* **Inference Latency:** $< 0.05\text{ ms}$ on budget Android ARM64 devices (Zero JNI overhead).

---

## 2. Intended Use & Scope
* **Primary Objective:** Provide on-device, privacy-preserving structural pattern analysis for incoming caller numbers to warn users about potential scam, spam, robocall, or premium-rate toll fraud.
* **Permitted Inputs:** Normalized digits, ITU-T E.164 country dial codes, digit entropy, repetition, and public numbering-plan metadata (VoIP, Toll-Free, Premium Rate).
* **Out-of-Scope & Prohibited Use:**
  * Must **NOT** be used as a standalone automatic blocking engine without additional contextual signals (e.g. user contacts, call history, reputation feeds).
  * Must **NOT** claim to confirm caller personal identity or legal guilt from digits alone.
  * Must **NOT** log or exfiltrate raw unhashed telephone numbers.

---

## 3. Privacy Preservation & Data Minimization
* **Zero PII Logging:** Raw phone numbers are discarded immediately after feature vector extraction.
* **Deterministic Mathematical Features:** Features capture structural properties (e.g. Shannon entropy, run lengths, symmetry, prefix tables) rather than identity markers.
* **100% Offline Android Inference:** Requires zero internet permissions and zero network requests.

---

## 4. Multi-Tier Classification & Abstain Policy
The model maps calibrated probability $P(\text{Threat} \mid \vec{x})$ into 4 distinct operational tiers:

| Tier | Probability Range | Confidence | Description | Action Recommendation |
| :--- | :---: | :---: | :--- | :--- |
| **`LEGITIMATE`** | $P < 0.15$ | HIGH | Standard business, personal line, emergency, or verified toll-free bank support. | Normal Ring / Clear |
| **`UNKNOWN`** | $0.15 \le P < 0.40$ | LOW | Standard number with normal entropy. Insufficient structural evidence alone. | **Abstain (No Warning)** |
| **`SPAM`** | $0.40 \le P < 0.70$ | MEDIUM | Telemarketing series (`+91-140`), bulk marketing dialers, or sequential robocallers. | Show "Potential Spam" Banner |
| **`SCAM`** | $P \ge 0.70$ | HIGH | High-cost Wangiri callback traps (`+881`, `+252`), premium rate redirection, or spoofed unallocated prefixes. | Show "High Risk Fraud Warning" |

---

## 5. Performance & Calibration Summary
Evaluated on **2,500 unseen prefix and geographic holdout samples**:
* **Threat Recall (Sensitivity):** **`100.00%`** ($1,250 / 1,250$ spam/scam samples caught)
* **Threat Precision:** **`99.84%`**
* **False Positive Rate on Legitimate/Unknown:** **`0.16%`** ($2 / 1,250$ false alarms)
* **Brier Score Loss (Calibration):** **`0.0008`** (Ideal $< 0.05$)
* **PR-AUC:** **`1.0000`** | **ROC-AUC:** **`1.0000`**
* **Hard Negatives (Banks & Emergency Lines) Pass Rate:** **`10 / 10 (100.0%)`**