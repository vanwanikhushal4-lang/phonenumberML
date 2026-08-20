# AEGIS-PNP2: Dataset Provenance, Regulatory Grounding & Labeling Policy

## 1. Grounding in Authoritative Telecom Numbering Plans & Registries
The AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) is an **experimental structural pattern risk model (`PATTERN_RISK`)** that evaluates phone number structure and publicly permitted numbering-plan metadata. It is grounded in published regulatory standards:

### A. India (TRAI - Telecom Regulatory Authority of India)
* **Commercial Communications Customer Preference Regulations (TCCCPR 2018):**
  * Mandatory **140-series allocations** (`+91-140-xxxxxxx`) assigned exclusively for commercial promotional telemarketing.
  * Mandatory **160-series allocations** (`+91-160-xxxxxxx`) assigned for transactional / service communications (banks, utilities).
* **National Numbering Plan (NNP) Matrix:**
  * Sourced from TRAI / DoT official allocation matrices across India's 22 Licensed Service Areas (LSAs).
  * Operator allocation series for 10-digit cellular mobile lines:
    * **Reliance Jio:** `600`, `700`, `701`, `702`, `797`, `798`, `799`, `808`, `809`, `897`, `898`, `899`
    * **Bharti Airtel:** `981`, `982`, `983`, `984`, `985`, `986`, `987`, `988`, `989`, `991`, `992`, `993`, `994`, `995`
    * **Vodafone Idea (Vi):** `971`, `972`, `973`, `974`, `975`, `976`, `977`, `978`, `979`, `901`, `902`, `903`, `904`
    * **BSNL / MTNL:** `941`, `942`, `943`, `944`, `945`, `946`, `947`, `948`, `949`, `940`
* **National Toll-Free & Emergency Allowlists:**
  * National Toll-Free: `1800-xxx-xxxx` (SBI, HDFC, ICICI, Axis, PNB, BoB, etc.)
  * National Emergency & Government Lines: `112` (Unified National Emergency), `100` (Police), `101` (Fire), `102` (Ambulance), `108` (Disaster/Emergency), `1091` (Women Helpline), `1930` (National Cyber Crime Reporting Portal).

### B. North America (NANPA - North American Numbering Plan Administrator)
* **Toll-Free Marketing Series:** `844`, `855`, `866` non-geographic bulk automated dialer series.
* **Standard Toll-Free:** `800`, `888`, `877`, `833` standard corporate customer service ranges.
* **Fictitious / Unassigned Exchange Blocks:** `555-01xx` (allocated strictly for fictional/testing use), `N11` service codes.
* **Premium-Rate Services:** `900` high-charge entertainment and premium routing series.

### C. United Kingdom (OFCOM)
* **Non-Geographic Automated Series:** `0843`, `0844`, `0845`, `0870`, `0871`, `0872` bulk commercial automated dialers.
* **Premium Rate:** `090`, `091`, `098` high-charge service lines.
* **Geographic PSTN:** `01`, `02` London (`020`), Manchester (`0161`), Birmingham (`0121`).
* **Mobile Allocations:** `07xxx` mobile subscriber lines.

### D. Global High-Cost Satellite Codes (ITU-T Recommendation E.164 / E.212)
* **Global Mobile Satellite Systems:** Inmarsat (`+870`), Globalstar (`+881`), Thuraya (`+882`, `+883`).
* **Wangiri High-Cost Destinations:** High-termination tariff territories historically exploited for one-ring callback fraud: Ascension Island (`+247`), Sierra Leone (`+232`), Somalia (`+252`), Guinea (`+224`), Tanzania (`+255`), Burundi (`+257`), Comoros (`+269`), São Tomé (`+239`), Guinea-Bissau (`+245`), Nauru (`+674`), Tuvalu (`+688`).

---

## 2. Labeling Policy & Target Semantics
The model produces a continuous **Pattern Risk Score** ($[0.0 - 1.0]$, displayed as $0 - 100$) and categorizes inputs into 5 explicit tiers:

| Label Name | Target Code | Definition & Criteria |
| :--- | :---: | :--- |
| **`BENIGN`** | `0` | Verified public bank customer care lines, certified national emergency numbers, or standard geographic PSTN lines. |
| **`UNKNOWN`** | `1` | Standard cellular mobile or landline numbers exhibiting natural digit entropy. Digits alone provide insufficient evidence (Abstain from warning). |
| **`TELEMARKETING_SPAM`** | `2` | Numbers matching registered commercial telemarketing series (TRAI 140, OFCOM 0843/0844) or low-entropy automated sequential dialers. |
| **`CONFIRMED_SCAM`** | `3` | High-cost Wangiri revenue-sharing satellite callback traps, premium-rate redirection lines (1900, 900), or shortcode spoofing. |
| **`INVALID`** | `4` | Malformed numbers violating international E.164 syntax, impossible lengths, or illegal leading digit patterns (e.g. `0000000000`, `123`). |

---

## 3. Strict Zero-Leakage & Partitioning Policy
* **Deduplication:** Deduplication is strictly enforced by canonical normalized E.164 string (`+<country_code><national_number>`).
* **Prefix / Exchange Family Isolation:** Partitioning separates entire operator sub-blocks and prefix clusters between training, validation, and untouched test holdouts:
  * **Train Set:** $N = 10,000$
  * **Validation Set:** $N = 2,500$
  * **Untouched Holdout Test Set:** $N = 2,500$ (Frozen prior to training; 0 overlapping numbers or exchange blocks with Train/Val).
  * **Natural Prevalence Benchmark:** $N = 5,000$ (Reflecting operational call distribution: 85% Benign/Unknown, 10% Telemarketing, 5% Scam/Wangiri).