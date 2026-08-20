# AEGIS-PNP2: Dataset Provenance & Labeling Policy

## 1. Grounding in Authoritative Telecom Numbering Plans
The AEGIS-PNP2 dataset is built upon published regulatory numbering plans and telecom allocations:
1. **India (TRAI - Telecom Regulatory Authority of India):**
   * *Commercial Telemarketing:* Mandatory 140-series allocations (`+91-140-xxxxxxx`).
   * *Transactional Series:* Mandatory 160-series allocations (`+91-160-xxxxxxx`).
   * *Cellular Mobile:* Real 10-digit mobile operator allocation blocks across Jio (`600`, `700`, `701`, `808`, `809`, etc.), Airtel (`981`, `982`, `983`, `984`, etc.), Vodafone Idea (`971`, `972`, `973`, `901`, etc.), and BSNL (`941`, `942`, `943`, etc.).
   * *Toll-Free:* Standard `1800` series allocated to financial and government institutions.
   * *National Shortcodes:* `112` (Emergency), `100` (Police), `108` (Ambulance), `1930` (National Cyber Crime Reporting Helpline).
2. **North America (NANPA - North American Numbering Plan Administrator):**
   * *Toll-Free Marketing:* `844`, `855`, `866` bulk dialer ranges.
   * *Standard Toll-Free:* `800`, `888`, `877`, `833`.
   * *Fictitious / Unassigned Blocks:* `555-01xx`, `N11` service codes.
   * *Premium Rate:* `900` high-charge service series.
3. **United Kingdom (OFCOM):**
   * *Non-Geographic Automated Series:* `0843`, `0844`, `0845`, `0870`, `0871`.
   * *Premium Rate:* `090` premium service series.
   * *Geographic PSTN:* `01`, `02` London and Manchester landline ranges.
4. **Global Wangiri High-Cost Satellite Codes (ITU-T E.164):**
   * Global Mobile Satellite Systems (`+881`, `+882`, `+883`, `+870`).
   * High-cost international termination destinations historically exploited for one-ring callback fraud (Ascension `+247`, Sierra Leone `+232`, Somalia `+252`, Guinea `+224`, Burundi `+257`, Comoros `+269`, etc.).

---

## 2. Zero-Leakage Deduplication Policy
* **Canonical Deduplication Key:** `Normalized E.164 String` (e.g. `+911409988776`).
* **Strict Set Isolation:** Every generated number is strictly checked against a global hash set before assignment.
* **Leakage Verification:**
  * Train Set ($N = 10,000$) $\cap$ Untouched Test Holdout ($N = 2,500$) $= \mathbf{0}$.
  * Train Set ($N = 10,000$) $\cap$ Validation Set ($N = 2,500$) $= \mathbf{0}$.