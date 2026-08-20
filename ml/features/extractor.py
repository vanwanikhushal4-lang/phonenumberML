"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2)
Deterministic Privacy-Preserving Feature Extractor (36 Features)
Direct Integration with Google libphonenumber & Per-Instance Explainability
"""

import os
import sys
import json
import math
import re
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

import phonenumbers
from phonenumbers import PhoneNumberType, PhoneNumberFormat

SPEC_PATH = os.path.join(os.path.dirname(__file__), "feature_spec.json")
with open(SPEC_PATH, "r", encoding="utf-8-sig") as f:
    FEATURE_SPEC = json.load(f)

# High-Risk Wangiri & Revenue Sharing International Country / Area Codes
WANGIRI_PREFIXES = {
    "881", "882", "883", "247", "232", "252", "224", "255", "257", "269", "239", "245", "674", "688", "870", "871", "872", "873"
}

# Registered Commercial Telemarketing Series (e.g. India TRAI 140, UK 0843, US 844/855/866 marketing, France 089)
TELEMARKETING_PREFIXES = [
    r"^\+?91140\d{7}$",
    r"^\+?4484[345]\d{7}$",
    r"^\+?1(844|855|866)\d{7}$",
    r"^\+?3389\d{7}$",
]

# Legitimate Bank / Financial Institutions Customer Care Patterns (Hard Negatives)
LEGITIMATE_BANK_PATTERNS = [
    r"^\+?911800\d{4,8}$",
    r"^\+?1800\d{7}$",
    r"^\+?44800\d{6,8}$",
    r"^\+?611800\d{6,8}$",
    r"^\+?49800\d{6,8}$",
    r"^\+?33800\d{6,8}$",
]

# Emergency & Public Service Shortcodes
EMERGENCY_SHORTCODES = {"112", "911", "999", "100", "101", "102", "108", "1091", "1930", "000", "110", "119", "17", "18"}

def compute_shannon_entropy(digits: str) -> float:
    if not digits: return 0.0
    length = len(digits)
    freq = {}
    for ch in digits:
        freq[ch] = freq.get(ch, 0) + 1
    entropy = 0.0
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy

def compute_max_repeat_run(digits: str) -> int:
    if not digits: return 0
    max_run = 1
    curr_run = 1
    for i in range(1, len(digits)):
        if digits[i] == digits[i-1]:
            curr_run += 1
            if curr_run > max_run: max_run = curr_run
        else:
            curr_run = 1
    return max_run

def compute_sequential_runs(digits: str) -> Tuple[int, int]:
    if not digits or len(digits) < 2: return 0, 0
    max_asc = 1
    curr_asc = 1
    max_desc = 1
    curr_desc = 1

    for i in range(1, len(digits)):
        diff = int(digits[i]) - int(digits[i-1])
        if diff == 1:
            curr_asc += 1
            if curr_asc > max_asc: max_asc = curr_asc
        else:
            curr_asc = 1

        if diff == -1:
            curr_desc += 1
            if curr_desc > max_desc: max_desc = curr_desc
        else:
            curr_desc = 1

    return max_asc, max_desc

def compute_alternating_density(digits: str) -> float:
    if not digits or len(digits) < 4: return 0.0
    count = 0
    for i in range(len(digits) - 2):
        if digits[i] == digits[i+2] and digits[i] != digits[i+1]: count += 1
    return min(count / float(len(digits) - 2), 1.0)

def compute_repeated_block_density(digits: str) -> float:
    if not digits or len(digits) < 4: return 0.0
    for i in range(len(digits) - 3):
        if digits[i:i+2] == digits[i+2:i+4]: return 1.0
    for i in range(len(digits) - 5):
        if digits[i:i+3] == digits[i+3:i+6]: return 1.0
    return 0.0

def compute_palindrome_symmetry(digits: str) -> float:
    if not digits or len(digits) < 2: return 0.0
    rev = digits[::-1]
    matches = sum(1 for a, b in zip(digits, rev) if a == b)
    return matches / float(len(digits))

def normalize_and_parse(raw_number: str, default_country: str = "IN") -> Tuple[str, str, str, int, bool]:
    if not raw_number or not str(raw_number).strip():
        return "", "", "", 10, False

    raw_clean = str(raw_number).strip()
    only_digits = re.sub(r"[^\d]", "", raw_clean)
    cleaned = re.sub(r"[^\d+]", "", raw_clean)

    if only_digits in EMERGENCY_SHORTCODES:
        return only_digits, default_country, only_digits, len(only_digits), True

    all_zeros = (len(set(only_digits)) == 1 and only_digits[0] == "0") if only_digits else True
    if all_zeros or len(only_digits) < 3 or len(only_digits) > 15:
        cc = "91" if default_country == "IN" else ("1" if default_country == "US" else "44")
        return raw_clean, cc, only_digits, 10, False

    for wp in WANGIRI_PREFIXES:
        if cleaned.startswith(f"+{wp}") or only_digits.startswith(wp):
            nat = only_digits[len(wp):] if len(only_digits) > len(wp) else only_digits
            return f"+{wp}{nat}", wp, nat, 10, True

    try:
        parsed = phonenumbers.parse(raw_clean, default_country)
        is_v = phonenumbers.is_valid_number(parsed)
        e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        cc = str(parsed.country_code)
        nat = str(parsed.national_number)
        std_len = 10
        if cc in ("33", "61"): std_len = 9
        elif cc in ("55",): std_len = 11
        return e164, cc, nat, std_len, is_v
    except Exception:
        # Fallback deterministic parser
        if cleaned.startswith("+91") or (default_country == "IN" and len(only_digits) >= 10):
            cc = "91"
            nat = only_digits[2:] if cleaned.startswith("+91") or (only_digits.startswith("91") and len(only_digits) >= 12) else (only_digits[-10:] if len(only_digits) >= 10 else only_digits)
            is_v = (10 <= len(nat) <= 11)
            return f"+91{nat}", cc, nat, 10, is_v
        elif cleaned.startswith("+1") or (default_country == "US" and len(only_digits) == 10):
            cc = "1"
            nat = only_digits[1:] if cleaned.startswith("+1") or (only_digits.startswith("1") and len(only_digits) == 11) else (only_digits[-10:] if len(only_digits) >= 10 else only_digits)
            return f"+1{nat}", cc, nat, 10, (len(nat) == 10)
        else:
            cc = only_digits[:3] if len(only_digits) >= 3 else only_digits
            nat = only_digits[3:] if len(only_digits) > 3 else only_digits
            return f"+{cc}{nat}", cc, nat, 10, (7 <= len(only_digits) <= 15)

def extract_features_from_number(raw_number: str, default_country: str = "IN") -> np.ndarray:
    vec = np.zeros(FEATURE_SPEC["num_features"], dtype=np.float32)
    e164, country_code_str, nat_num_str, std_length, is_valid = normalize_and_parse(raw_number, default_country)
    
    if not nat_num_str:
        return vec

    only_digits = re.sub(r"[^\d]", "", str(raw_number).strip())
    nat_len = len(nat_num_str)
    full_e164 = e164 if e164 else f"+{country_code_str}{nat_num_str}"

    # 0. Validity
    vec[0] = 1.0 if is_valid else 0.0

    # 1. National length normalized
    vec[1] = min(nat_len / 15.0, 1.0)

    # 2. Length discrepancy
    vec[2] = min(abs(nat_len - std_length) / 15.0, 1.0)

    # 3. Shannon Entropy
    entropy = compute_shannon_entropy(nat_num_str)
    vec[3] = min(entropy / 3.321928, 1.0)

    # 4. Unique ratio
    vec[4] = (len(set(nat_num_str)) / float(nat_len)) if nat_len > 0 else 0.0

    # 5. Max repeat run
    max_run = compute_max_repeat_run(nat_num_str)
    vec[5] = min(max_run / 10.0, 1.0)

    # 6 & 7. Sequential runs (asc / desc)
    max_asc, max_desc = compute_sequential_runs(nat_num_str)
    vec[6] = min(max_asc / 10.0, 1.0)
    vec[7] = min(max_desc / 10.0, 1.0)

    # 8. Alternating density
    vec[8] = compute_alternating_density(nat_num_str)

    # 9. Repeated block density
    vec[9] = compute_repeated_block_density(nat_num_str)

    # 10. Palindrome symmetry
    vec[10] = compute_palindrome_symmetry(nat_num_str)

    # 11. Trailing zeros
    trailing_zeros = len(nat_num_str) - len(nat_num_str.rstrip("0"))
    vec[11] = min(trailing_zeros / 8.0, 1.0)

    # 12. Leading digit distribution anomaly
    if nat_len > 0 and nat_num_str[0] in ("0", "1") and country_code_str in ("1", "91") and only_digits not in EMERGENCY_SHORTCODES and not nat_num_str.startswith("1800") and not nat_num_str.startswith("1900") and not nat_num_str.startswith("140"):
        vec[12] = 1.0
    else:
        vec[12] = 0.0

    # 13 - 19. Number Type Metadata via libphonenumber
    ntype = PhoneNumberType.UNKNOWN
    try:
        parsed = phonenumbers.parse(raw_number, default_country)
        ntype = phonenumbers.number_type(parsed)
    except Exception:
        pass

    is_tollfree = (ntype == PhoneNumberType.TOLL_FREE) or nat_num_str.startswith("1800") or nat_num_str.startswith("800") or nat_num_str.startswith("888") or nat_num_str.startswith("877") or nat_num_str.startswith("866") or nat_num_str.startswith("855") or nat_num_str.startswith("844")
    is_premium = (ntype == PhoneNumberType.PREMIUM_RATE) or (nat_num_str.startswith("1900") or (country_code_str == "1" and nat_num_str.startswith("900")) or (country_code_str == "44" and nat_num_str.startswith("900")) or (country_code_str == "33" and nat_num_str.startswith("89")))
    is_voip = (ntype == PhoneNumberType.VOIP) or nat_num_str.startswith("140") or nat_num_str.startswith("843")
    is_mobile = (ntype == PhoneNumberType.MOBILE) or ((nat_len == 10 and nat_num_str[0] in ("6", "7", "8", "9") and country_code_str == "91") or (nat_len == 10 and country_code_str == "1" and not is_tollfree and not is_premium) or (country_code_str == "44" and nat_num_str.startswith("7")) or (country_code_str == "81" and nat_num_str.startswith(("90", "80", "70"))))
    is_fixed = (ntype == PhoneNumberType.FIXED_LINE) or (not is_mobile and not is_tollfree and not is_premium)
    is_uan = (ntype == PhoneNumberType.UAN) or nat_num_str.startswith("140") or only_digits in EMERGENCY_SHORTCODES

    vec[13] = 1.0 if is_tollfree else 0.0
    vec[14] = 1.0 if is_premium else 0.0
    vec[15] = 1.0 if (ntype == PhoneNumberType.SHARED_COST) else 0.0
    vec[16] = 1.0 if is_voip else 0.0
    vec[17] = 1.0 if is_mobile else 0.0
    vec[18] = 1.0 if is_fixed else 0.0
    vec[19] = 1.0 if is_uan else 0.0

    # 20. Wangiri High Cost Prefix
    is_wangiri = (country_code_str in WANGIRI_PREFIXES) or any(only_digits.startswith(wp) for wp in WANGIRI_PREFIXES)
    vec[20] = 1.0 if is_wangiri else 0.0

    # 21. Telemarketing series
    is_telemarketing = any(re.search(pat, full_e164) or re.search(pat, str(raw_number)) for pat in TELEMARKETING_PREFIXES)
    vec[21] = 1.0 if is_telemarketing else 0.0

    # 22. Unallocated exchange code
    is_unallocated = False
    if country_code_str == "1" and nat_len == 10:
        nxx = nat_num_str[3:6]
        if nxx.endswith("11") or nxx == "555": is_unallocated = True
    vec[22] = 1.0 if is_unallocated else 0.0

    # 23. Shortcode formatted as E.164
    vec[23] = 1.0 if (nat_len <= 6 and str(raw_number).strip().startswith("+")) else 0.0

    # 24. Hard Negative: Legitimate bank support pattern
    is_bank = is_tollfree or any(re.search(bp, full_e164) or re.search(bp, str(raw_number)) for bp in LEGITIMATE_BANK_PATTERNS)
    vec[24] = 1.0 if is_bank else 0.0

    # 25. Hard Negative: Emergency service
    vec[25] = 1.0 if (only_digits in EMERGENCY_SHORTCODES or nat_num_str in EMERGENCY_SHORTCODES) else 0.0

    # 26. Same country
    same_country = (default_country == "IN" and country_code_str == "91") or \
                   (default_country == "US" and country_code_str == "1") or \
                   (default_country == "GB" and country_code_str == "44") or \
                   (default_country == "FR" and country_code_str == "33") or \
                   (default_country == "DE" and country_code_str == "49") or \
                   (default_country == "AU" and country_code_str == "61") or \
                   (default_country == "JP" and country_code_str == "81") or \
                   (default_country == "BR" and country_code_str == "55") or \
                   (default_country == "ID" and country_code_str == "62") or \
                   (default_country == "NG" and country_code_str == "234")
    vec[26] = 1.0 if same_country else 0.0

    # 27. Country risk tier
    if is_wangiri: vec[27] = 1.0
    elif country_code_str in ("91", "1", "44", "61", "49", "33", "81", "55", "62", "234"): vec[27] = 0.10
    else: vec[27] = 0.40

    # 28. Joint: Wangiri Callback Trap
    vec[28] = 1.0 if (is_wangiri and (vec[3] < 0.70 or vec[2] > 0.0)) else 0.0

    # 29. Joint: Low-Entropy Robocall Pattern
    vec[29] = 1.0 if ((vec[5] >= 0.50 or vec[6] >= 0.60 or vec[7] >= 0.60 or vec[8] >= 0.50) and vec[24] == 0.0 and vec[25] == 0.0) else 0.0

    # 30. Joint: Spoofed Short Dialer
    vec[30] = 1.0 if (vec[2] >= 0.20 and (is_premium or is_unallocated)) else 0.0

    # 31. Joint: Telemarketer Block
    vec[31] = 1.0 if (is_telemarketing and vec[4] <= 0.70) else 0.0

    # 32. Digit variance density
    if nat_len > 0:
        counts = [nat_num_str.count(str(d)) for d in range(10)]
        var = float(np.var(counts))
        vec[32] = min(var / 5.0, 1.0)

    # 33. Consecutive diff sum
    if nat_len > 1:
        diff_sum = sum(abs(int(nat_num_str[i]) - int(nat_num_str[i-1])) for i in range(1, nat_len))
        vec[33] = min(diff_sum / (9.0 * (nat_len - 1)), 1.0)

    # 34 & 35
    vec[34] = 1.0 if (ntype == PhoneNumberType.PERSONAL_NUMBER) else 0.0
    vec[35] = 1.0 if (ntype == PhoneNumberType.PAGER) else 0.0

    return vec

def explain_instance(features: np.ndarray, top_k: int = 3) -> List[Tuple[str, str, float]]:
    reasons = []
    if features[20] > 0.5 or features[28] > 0.5:
        reasons.append(("risk_wangiri_high_cost_prefix", "High-risk international revenue-sharing callback trap (Wangiri scam)", 0.95))
    if features[21] > 0.5 or features[31] > 0.5:
        reasons.append(("risk_telemarketing_series", "Matches registered commercial telemarketing / automated dialer series", 0.90))
    if features[14] > 0.5:
        reasons.append(("plan_is_premium_rate", "High-charge premium rate number service", 0.85))
    if features[29] > 0.5 or features[5] >= 0.5 or features[6] >= 0.6 or features[7] >= 0.6:
        reasons.append(("digit_max_repeat_run", "Unnatural low-entropy repetitive or sequential digit pattern typical of automated robocallers", 0.80))
    if features[24] > 0.5:
        reasons.append(("hard_neg_legitimate_bank_support", "Verified legitimate customer care / banking institution toll-free line", 0.99))
    if features[25] > 0.5:
        reasons.append(("hard_neg_emergency_service", "Recognized national emergency or public service line", 0.99))
    if features[0] == 0.0:
        reasons.append(("num_is_valid_e164", "Invalid number syntax violating standard numbering plan", 0.95))

    if not reasons:
        reasons.append(("standard_entropy_structure", "Standard number structure. Digits alone provide insufficient evidence.", 0.10))

    reasons.sort(key=lambda x: x[2], reverse=True)
    return reasons[:top_k]