# AEGIS-PNP1 Feature Specification (36 Dimensions)

The model operates across 7 orthogonal structural sensor domains:

## 1. Syntax & Length Validity (0–2)
* **`[00] num_is_valid_e164`:** `1.0` if number strictly satisfies ITU-T E.164 length ($7 - 15$ digits) and country dial code.
* **`[01] num_national_length_normalized`:** Normalized national length $\text{len} / 15.0$.
* **`[02] num_length_discrepancy`:** Discrepancy from standard 10-digit national plan $|\text{len} - 10| / 15.0$.

## 2. Digit Entropy & Repetition (3–7)
* **`[03] digit_shannon_entropy`:** Normalized Shannon entropy $H / \log_2(10) \in [0.0, 1.0]$.
* **`[04] digit_unique_ratio`:** Unique digits divided by total length.
* **`[05] digit_max_repeat_run`:** Contiguous repeat run length $/ 10.0$ (e.g. `9999` $\to 0.40$).
* **`[06] digit_max_sequential_asc`:** Contiguous ascending run length $/ 10.0$ (e.g. `12345` $\to 0.50$).
* **`[07] digit_max_sequential_desc`:** Contiguous descending run length $/ 10.0$ (e.g. `54321` $\to 0.50$).

## 3. Pattern Symmetry & Vanity Formations (8–12)
* **`[08] digit_alternating_pattern_density`:** Alternating pair density (e.g. `121212`, `505050`).
* **`[09] digit_repeated_block_density`:** Repeated 2-digit or 3-digit block presence.
* **`[10] digit_palindrome_symmetry`:** Reversal character alignment score $[0.0, 1.0]$.
* **`[11] digit_trailing_zeros_count`:** Trailing zeros count $/ 8.0$ (e.g. `...0000`).
* **`[12] digit_leading_digit_distribution`:** Anomaly indicator for illegal leading 0/1 digits in standard mobile lines.

## 4. Numbering-Plan Classifications (13–19)
* **`[13] plan_is_tollfree`:** Toll-free prefix series (`1800`, `800`, `888`, `877`, `866`, `855`, `844`).
* **`[14] plan_is_premium_rate`:** High-charge premium-rate series (`1900`, `900`, `0900`).
* **`[15] plan_is_shared_cost`:** Shared cost designation.
* **`[16] plan_is_voip_virtual`:** Virtual cloud PBX / VoIP allocation.
* **`[17] plan_is_mobile`:** Standard cellular mobile allocation.
* **`[18] plan_is_fixed_line`:** Geographic PSTN landline allocation.
* **`[19] plan_is_uan_shortcode`:** Universal Access Number (UAN) or emergency shortcode.

## 5. High-Risk Prefix Indicators (20–23)
* **`[20] risk_wangiri_high_cost_prefix`:** International high-cost / satellite prefix (`+881`, `+882`, `+247`, `+232`, `+252`, etc.).
* **`[21] risk_telemarketing_series`:** Domestic registered bulk telemarketing series (`+91-140`, `+44-843`, etc.).
* **`[22] risk_unallocated_exchange_code`:** Unassigned / fictitious exchange code (NANP 555-01xx / N11).
* **`[23] risk_short_code_spoofing`:** Shortcode disguised as international E.164.

## 6. Hard-Negative Protective Indicators (24–27)
* **`[24] hard_neg_legitimate_bank_support`:** Verified bank customer support lines (e.g. SBI `1800 11 2211`, Chase `1-800-935-9935`).
* **`[25] hard_neg_emergency_service`:** Emergency service lines (`112`, `911`, `999`, `100`).
* **`[26] geo_is_same_country`:** Country code matches device local SIM country.
* **`[27] geo_country_risk_tier`:** Normalized international telecom fraud risk tier.

## 7. Joint Interaction Tells & Variance (28–35)
* **`[28] joint_wangiri_callback_trap`:** Foreign satellite code combined with low entropy.
* **`[29] joint_voip_robocall_pattern`:** VoIP range combined with repetitive/sequential patterns.
* **`[30] joint_spoofed_short_dialer`:** Length discrepancy combined with premium rate / unallocated codes.
* **`[31] joint_telemarketer_block`:** Telemarketing prefix combined with low unique digit ratio.
* **`[32] digit_variance_density`:** Normalized variance of digit frequency distribution.
* **`[33] digit_consecutive_diff_sum`:** Normalized sum of adjacent digit absolute differences.
* **`[34] plan_is_personal_number`:** Personal follow-me number.
* **`[35] plan_is_pager`:** Pager allocation.