# AEGIS-PNP2: Dataset Provenance, Regulatory Ingestion & Labeling Policy

> **Current Project Status:**
> **Experimental Synthetic Phone-Pattern Baseline - Not Integrated.**
>
> *Disclaimer: Phone digits alone cannot identify a caller, confirm fraud, or determine caller identity. AEGIS-PNP2 is an experimental structural pattern anomaly risk model operating strictly in Advisory Mode.*

---

## 1. Authoritative Regulatory & Public Registry Sources

AEGIS-PNP2 sources its structural pattern datasets and baseline registries from published telecom numbering plans, consumer complaint databases, and official regulatory registries:

| Data Source | Governing Body / Jurisdiction | Ingestion Scope & Description | License / Legal Status |
| :--- | :--- | :--- | :--- |
| **TRAI TCCCPR 2018** | Telecom Regulatory Authority of India (India) | Commercial Communications Customer Preference Regulations: Mandatory **140-series** (`+91-140-xxxxxxx`) promotional telemarketing registry and **160-series** transactional service allocations. | Open Government Data (OGD) / Public Regulatory Registry |
| **TRAI National Numbering Plan (NNP)** | Department of Telecommunications (DoT, India) | 10-digit mobile series allocation matrices across 22 Licensed Service Areas (LSAs) for licensed Telecom Service Providers (Reliance Jio, Bharti Airtel, Vodafone Idea, BSNL/MTNL). | Public Telecom Allocation Matrix |
| **FCC Consumer Complaints Database** | Federal Communications Commission (USA) | Unsolicited robocall and telemarketing complaint records and NANPA prefix allocations (Catalog: `data.fcc.gov`). | US Public Domain / Freedom of Information Act |
| **NANPA North American Numbering Plan** | North American Numbering Plan Administrator (USA/Canada) | Toll-Free allocations (`800/888/877/866/855/844/833`), unassigned `555-01xx` blocks, and `900` premium rate allocations. | Public Telecom Allocation Standard |
| **OFCOM National Numbering Scheme** | Office of Communications (United Kingdom) | UK non-geographic bulk dialers (`0843/0844/0845/0870`), geographic PSTN (`01/02`), mobile (`07xxx`), and premium rate (`090/091/098`). | UK Open Government Licence (OGL) v3.0 |
| **ITU-T Recommendation E.164 / E.212** | International Telecommunication Union (Global) | Global satellite service codes (Inmarsat `+870`, Globalstar `+881`, Thuraya `+882`) and international high-cost termination destinations. | ITU Public International Standard |
| **RBI Certified Banking Customer Care Directory** | Reserve Bank of India / Scheduled Commercial Banks | Publicly published official toll-free customer support lines (SBI, HDFC, ICICI, Axis, PNB, BoB, Canara, Union, Kotak, Chase, Barclays, HSBC). | Public Directory / Consumer Service Allowlists |
| **National Public Emergency Registry** | Ministry of Home Affairs / Telecom Providers | Certified public emergency and cybercrime helplines (`112`, `100`, `101`, `102`, `108`, `1091`, `1930`, `911`, `999`). | Public Emergency Allowlists |

---

## 2. Ingestion Pipeline & Labeling Criteria

The ingestion pipeline ([`ml/data/ingest_real_data.py`](file:///C:/Users/user/Documents/phonenumberML/ml/data/ingest_real_data.py)) parses and standardizes records with row-level provenance:

* **Target Variable:** Continuous `PATTERN_RISK` $[0.0 - 1.0]$ (scaled to $0 - 100$).
* **Binary Threat Objective:**
  * `0`: Safe / Unknown (Legitimate bank care, emergency shortcodes, geographic landlines, standard cellular mobile subscribers).
  * `1`: High Pattern Risk (Registered TRAI 140 commercial dialers, OFCOM bulk dialers, ITU-T high-cost satellite traps, premium-rate redirection lines, low-entropy automated dialers).

---

## 3. Strict Prefix-Cluster Partitioning Policy (0 Shared Clusters)

To prevent any data leakage, data is partitioned by **6-Digit / 7-Digit Prefix Clusters (`CC + Area/Operator Prefix`)**:
* Every unique prefix cluster exists **exclusively** in Train, exclusively in Validation, or exclusively in Holdout Test.
* Verified: **Zero shared prefix clusters** between Train and Test splits.