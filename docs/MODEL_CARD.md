# AEGIS-PNP2: Phone Number Pattern Risk Model Card

## 1. Model Overview
* **Model Name:** AEGIS-PNP2 (Phone Number Pattern Risk Model v2.0)
* **Model Architecture:** 150-Tree Gradient Boosted Trees Ensemble (`GradientBoostingClassifier`, max depth 4) with explicit Sigmoid Platt probability calibration.
* **Release Status:** Production Rebuild (Advisory Mode).
* **Target Task:** On-Device Privacy-Preserving Structural Phone Number Risk Assessment.
* **Supported Platforms:** Android (Kotlin Engine, Zero JNI, Latency $< 0.05\text{ ms}$), Backend (FastAPI REST Server).

---

## 2. Intended Use & Advisory Mode Framing
* **Intended Purpose:** Provide on-device, pre-call structural risk estimation on incoming phone numbers to detect automated robocallers, commercial telemarketers (e.g. TRAI 140 series), high-cost Wangiri callback traps, and premium-rate fraud before the call is answered.
* **Advisory Mode Directive:** A phone number's digits alone cannot prove caller identity or confirm malicious intent. The model operates in **Advisory Mode** (displaying warning banners such as "*⚠️ High-Risk Scam Pattern Detected*" or "*⚡ Suspected Telemarketer*") and **does NOT auto-block or auto-drop calls** based solely on pattern scores without explicit user blocklist rules or verified fresh server reputation.
* **Out-of-Scope Uses:** Caller ID resolution, contact name lookup, direct call blocking without user consent.

---

## 3. Input & Output Specification
* **Inputs:**
  * Raw Phone Number (e.g. `"+911409988776"`, `"1800112211"`, `"0000000000"`)
  * Device Default Region / SIM Country (e.g. `"IN"`, `"US"`, `"GB"`)
* **Outputs:**
  * `normalized_e164`: Normalized E.164 string via `libphonenumber`.
  * `is_valid`: Boolean numbering-plan syntax validity.
  * `risk_score`: Calibrated risk integer from `0` to `100`.
  * `calibrated_probability`: Calibrated probability $P(\text{Threat} \mid x) \in [0.0, 1.0]$.
  * `threat_tier`: Categorical classification (`LEGITIMATE`, `UNKNOWN` [Abstain], `SPAM`, `SCAM`, `INVALID`).
  * `confidence`: `LOW`, `MEDIUM`, or `HIGH`.
  * `top_reason_codes`: Active structural tell codes (e.g. `risk_telemarketing_series`, `risk_wangiri_high_cost_prefix`).
  * `top_explanations`: Human-readable explanation strings for user interface display.

---

## 4. Probability Calibration & Operating Thresholds
The model fits explicit Sigmoid Platt scaling parameters on a dedicated validation set:
\[
P(\text{Threat} \mid \text{logit}) = \frac{1}{1 + \exp(A \cdot \text{logit} + B)}
\]
* Fitted Parameters: $A = -1.237963, B = -0.067662$.
* Brier Score Loss: `0.019581` (Well below ideal $< 0.05$ threshold).

| Threat Tier | Probability Range | Risk Score | System Behavior |
| :--- | :---: | :---: | :--- |
| **`LEGITIMATE`** | $P < 0.15$ | $0 - 14$ | Verified Bank / Emergency / Clean PSTN line |
| **`UNKNOWN`** | $0.15 \le P < 0.40$ | $15 - 39$ | Standard mobile/landline (Abstain from warning) |
| **`SPAM`** | $0.40 \le P < 0.70$ | $40 - 69$ | Telemarketer / Automated Robocall Advisory |
| **`SCAM`** | $P \ge 0.70$ | $70 - 100$ | Wangiri / Premium Fraud High-Risk Advisory |
| **`INVALID`** | *Malformed* | $0$ | Number syntax violates international numbering plan |

---

## 5. Privacy & Security Guarantees
1. **Zero PII Logging:** Raw phone numbers, contact names, and caller details are never written to disk, sent in telemetry, or stored in server logs.
2. **Offline Local Inference:** Layer 1 and Layer 2 execute 100% on-device without network connectivity.
3. **Secure Reputation Proxy:** External lookups (Layer 3) transmit only SHA-256 truncated hashes over TLS to a self-hosted proxy. No third-party provider API keys are embedded in client APKs.