# AEGIS-PNP2: Phone Number Pattern Risk Model Card

## 1. Model Overview
* **Model Name:** AEGIS-PNP2 (Phone Number Pattern Risk Model v2.1)
* **Model Objective:** `PATTERN_RISK` — Continuous structural risk probability estimation ($P \in [0.0, 1.0]$, scaled to $0 - 100$).
* **Architecture:** 150-Tree Gradient Boosted Decision Tree Ensemble (`GradientBoostingRegressor`, max depth 5) with explicit Platt Sigmoid Scaling.
* **Intended Platform:** Android Native (`CallGuardEngine.kt`, pure Kotlin, zero JNI, latency $< 0.05\text{ ms}$) and Backend Proxy (`server.py`, FastAPI).
* **Release Status:** **Experimental Structural Pattern Risk Baseline (Advisory Mode)**.

---

## 2. Ethical Framing & Advisory Mode Mandate
> [!IMPORTANT]
> **Advisory Mode Only:** Phone digits alone cannot identify a caller or confirm fraud. Incoming calls with high pattern risk or Wangiri/telemarketing signatures trigger **Advisory Warnings** (e.g. *"⚠️ Suspicious phone-number pattern detected"*) and **must NOT auto-block or auto-drop calls** without explicit user blocklist rules or verified fresh server reputation.

---

## 3. Input & Output Specification
* **Inputs:**
  * Raw Phone Number (e.g. `"+911409988776"`, `"1800112211"`, `"0000000000"`)
  * Device Default Region / SIM Country (e.g. `"IN"`, `"US"`, `"GB"`)
* **Outputs:**
  * `normalized_e164`: Normalized E.164 string via `libphonenumber`.
  * `is_valid`: Boolean numbering-plan syntax validity.
  * `pattern_risk_score`: Structural risk integer from `0` to `100` scaled from raw regression output ($\lfloor \min(1.0, \max(0.0, r(x))) \cdot 100 \rceil$).
  * `calibrated_probability`: Calibrated probability $P(\text{Threat} \mid x) = \frac{1}{1 + e^{-(12.0786 \cdot r(x) - 4.1048)}} \in [0.0, 1.0]$.
  * `threat_tier`: Categorical classification (`LEGITIMATE`, `UNKNOWN` [Abstain], `SPAM`, `SCAM`, `INVALID`).
  * `confidence`: `LOW`, `MEDIUM`, or `HIGH`.
  * `top_reason_codes`: Active structural tell codes (e.g. `risk_telemarketing_series`, `risk_wangiri_high_cost_prefix`).
  * `top_explanations`: Human-readable explanation strings for user interface display.

---

## 4. Probability Calibration & Operating Thresholds
The model fits explicit Sigmoid Platt scaling parameters on a dedicated, disjoint calibration split:
\[
P(\text{Pattern Risk} \mid \text{logit}) = \frac{1}{1 + \exp(-(A \cdot \text{logit} + B))}
\]
* **Fitted Parameters:** $A = 12.0786, B = -4.1048$, fitted on `calib_dataset.json` (2,500 samples, disjoint from train/val/test/benchmark).
* **Evaluation Loss:** Holdout Brier Score = `0.122648`, Benchmark Brier Score = `0.110364`.

| Threat Tier | Calibrated Probability ($P$) | Risk Score | System Behavior |
| :--- | :---: | :---: | :--- |
| **`LEGITIMATE`** | $P < 0.10$ | $0 - 9$ | Verified Bank / Emergency / Toll-Free Customer Line |
| **`UNKNOWN`** | $0.10 \le P < 0.60$ | $10 - 59$ | Standard subscriber line (Abstain from warning) |
| **`SPAM`** | $0.60 \le P < 0.98$ | $60 - 97$ | Telemarketer / Automated Robocall Advisory Warning |
| **`SCAM`** | $P \ge 0.98$ | $98 - 100$ | Wangiri / Premium Fraud High-Risk Advisory Warning |
| **`INVALID`** | *Malformed* | $0$ | Number syntax violates international numbering plan |

---

## 5. Privacy & Data Handling Specification
1. **Local Model Execution:** Layers 1 and 2 execute 100% on-device inside Kotlin runtime. Raw phone numbers never leave the device for local inference.
2. **Backend Reputation Proxy:** When remote reputation lookup is triggered, the normalized E.164 number is transmitted securely over TLS to the self-hosted Aegis proxy. The proxy queries upstream reputation (IPQS) using server-side API keys (zero keys in the client APK).
3. **Telemetry & Logging:** Raw phone numbers and contact names are never logged. Telemetry and audit logs record only truncated SHA-256 hashes (`HMAC-SHA256(E.164)[:16]`).