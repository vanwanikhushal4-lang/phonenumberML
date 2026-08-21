"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2)
Strict Group-Based Prefix Partitioning & Dedicated Benchmark Partition
Guarantees Exactly 0 Shared 7-Digit Prefixes Across All 6 Split Pairs:
(Train, Val), (Train, Test), (Train, Bench), (Val, Test), (Val, Bench), (Test, Bench)
"""

import os
import sys
import json
import random
import re
from typing import Dict, Any, List, Optional, Tuple, Set
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import normalize_and_parse

DATA_DIR = os.path.dirname(__file__)

PREFIX_CLUSTERS = {
    "train": {
        "india_trai_140": {"group_id": "GRP_TRAI_140_TR", "prefixes": ["1400", "1401"]},
        "india_jio": {"group_id": "GRP_IN_JIO_TR", "prefixes": ["600", "601"]},
        "india_airtel": {"group_id": "GRP_IN_AIRTEL_TR", "prefixes": ["981", "982"]},
        "india_vi": {"group_id": "GRP_IN_VI_TR", "prefixes": ["971", "972"]},
        "india_bsnl": {"group_id": "GRP_IN_BSNL_TR", "prefixes": ["941", "942"]},
        "india_pstn": {"group_id": "GRP_IN_PSTN_TR", "prefixes": ["22"]},
        "india_bank": {"group_id": "GRP_IN_BANK_TR", "prefixes": ["180011", "180012"]},
        "us_area": {"group_id": "GRP_US_AREA_TR", "prefixes": ["212", "415"]},
        "us_marketing": {"group_id": "GRP_US_MKTG_TR", "prefixes": ["844"]},
        "ofcom_bulk": {"group_id": "GRP_UK_BULK_TR", "prefixes": ["0843"]},
        "ofcom_mobile": {"group_id": "GRP_UK_MOB_TR", "prefixes": ["07911"]},
        "wangiri_codes": {"group_id": "GRP_WANGIRI_TR", "prefixes": ["8811", "247"]}
    },
    "val": {
        "india_trai_140": {"group_id": "GRP_TRAI_140_VAL", "prefixes": ["1402", "1403"]},
        "india_jio": {"group_id": "GRP_IN_JIO_VAL", "prefixes": ["700", "701"]},
        "india_airtel": {"group_id": "GRP_IN_AIRTEL_VAL", "prefixes": ["983", "984"]},
        "india_vi": {"group_id": "GRP_IN_VI_VAL", "prefixes": ["973", "974"]},
        "india_bsnl": {"group_id": "GRP_IN_BSNL_VAL", "prefixes": ["943", "944"]},
        "india_pstn": {"group_id": "GRP_IN_PSTN_VAL", "prefixes": ["33"]},
        "india_bank": {"group_id": "GRP_IN_BANK_VAL", "prefixes": ["180020", "180021"]},
        "us_area": {"group_id": "GRP_US_AREA_VAL", "prefixes": ["312", "713"]},
        "us_marketing": {"group_id": "GRP_US_MKTG_VAL", "prefixes": ["855"]},
        "ofcom_bulk": {"group_id": "GRP_UK_BULK_VAL", "prefixes": ["0844"]},
        "ofcom_mobile": {"group_id": "GRP_UK_MOB_VAL", "prefixes": ["07912"]},
        "wangiri_codes": {"group_id": "GRP_WANGIRI_VAL", "prefixes": ["8821", "232"]}
    },
    "test": {
        "india_trai_140": {"group_id": "GRP_TRAI_140_TE", "prefixes": ["1404", "1405"]},
        "india_jio": {"group_id": "GRP_IN_JIO_TE", "prefixes": ["702", "703"]},
        "india_airtel": {"group_id": "GRP_IN_AIRTEL_TE", "prefixes": ["985", "986"]},
        "india_vi": {"group_id": "GRP_IN_VI_TE", "prefixes": ["975", "976"]},
        "india_bsnl": {"group_id": "GRP_IN_BSNL_TE", "prefixes": ["945", "946"]},
        "india_pstn": {"group_id": "GRP_IN_PSTN_TE", "prefixes": ["44"]},
        "india_bank": {"group_id": "GRP_IN_BANK_TE", "prefixes": ["180030", "180031"]},
        "us_area": {"group_id": "GRP_US_AREA_TE", "prefixes": ["650", "305"]},
        "us_marketing": {"group_id": "GRP_US_MKTG_TE", "prefixes": ["866"]},
        "ofcom_bulk": {"group_id": "GRP_UK_BULK_TE", "prefixes": ["0845"]},
        "ofcom_mobile": {"group_id": "GRP_UK_MOB_TE", "prefixes": ["07913"]},
        "wangiri_codes": {"group_id": "GRP_WANGIRI_TE", "prefixes": ["252", "224"]}
    },
    "benchmark": {
        "india_trai_140": {"group_id": "GRP_TRAI_140_BM", "prefixes": ["1406", "1407"]},
        "india_jio": {"group_id": "GRP_IN_JIO_BM", "prefixes": ["808", "809"]},
        "india_airtel": {"group_id": "GRP_IN_AIRTEL_BM", "prefixes": ["987", "988"]},
        "india_vi": {"group_id": "GRP_IN_VI_BM", "prefixes": ["977", "978"]},
        "india_bsnl": {"group_id": "GRP_IN_BSNL_BM", "prefixes": ["947", "948"]},
        "india_pstn": {"group_id": "GRP_IN_PSTN_BM", "prefixes": ["11"]},
        "india_bank": {"group_id": "GRP_IN_BANK_BM", "prefixes": ["180040", "180041"]},
        "us_area": {"group_id": "GRP_US_AREA_BM", "prefixes": ["206", "617"]},
        "us_marketing": {"group_id": "GRP_US_MKTG_BM", "prefixes": ["877"]},
        "ofcom_bulk": {"group_id": "GRP_UK_BULK_BM", "prefixes": ["0870"]},
        "ofcom_mobile": {"group_id": "GRP_UK_MOB_BM", "prefixes": ["07914"]},
        "wangiri_codes": {"group_id": "GRP_WANGIRI_BM", "prefixes": ["255", "257"]}
    }
}

def generate_random_digits(length: int) -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def generate_strictly_invalid_number(index: int, split_name: str) -> Tuple[str, str]:
    sub_types = [
        "all_zeros", "too_short", "overlength", "impossible_leading_zero",
        "letters_inside", "impossible_country_code", "special_symbols"
    ]
    t = sub_types[index % len(sub_types)]
    tag = "1" if split_name == "train" else ("4" if split_name == "val" else ("7" if split_name == "test" else "9"))
    
    if t == "all_zeros":
        return "00000" if split_name == "train" else ("0000" if split_name == "val" else ("000" if split_name == "test" else "00")), "All zeros invalid sequence"
    elif t == "too_short":
        base = 10 if split_name == "train" else (40 if split_name == "val" else (70 if split_name == "test" else 90))
        return str(base + (index % 10)), "Length below international minimum"
    elif t == "overlength":
        return f"+99{tag}0{index:04d}123456789012345", "Length exceeds E.164 15-digit maximum"
    elif t == "impossible_leading_zero":
        return f"+99{tag}00{index:07d}", "Impossible leading 00 in subscriber number"
    elif t == "letters_inside":
        chars = ["ABCD", "XYZ", "SCAM", "CALL", "TEST"]
        ch = chars[index % len(chars)]
        return f"+99{tag}88{ch}{index:03d}", "Alphabetic characters in dial string"
    elif t == "impossible_country_code":
        return f"+99{tag}{index:07d}", "Unassigned ITU-T country dial code +99x"
    else:
        return f"+99{tag}##{index:05d}**", "Non-dialable special symbols"

def build_dataset_suite(seed=42):
    random.seed(seed)
    np.random.seed(seed)

    print("="*85)
    print("      AEGIS-PNP2 DATASET GENERATOR (6-WAY STRICT GROUP-BASED PREFIX ISOLATION)")
    print("="*85)

    seen_numbers: Set[str] = set()
    invalid_counter = 0

    def generate_sample(target_label: str, split_name: str) -> Optional[Dict[str, Any]]:
        nonlocal invalid_counter
        clusters = PREFIX_CLUSTERS[split_name]
        country = "IN"
        raw_num = ""
        category = ""
        label_code = 0
        desc = ""
        chosen_group_id = ""

        # 1. CONFIRMED_SCAM
        if target_label == "CONFIRMED_SCAM":
            sub = random.choice(["wangiri", "premium_fraud", "spoofed_satellite"])
            if sub == "wangiri":
                grp = clusters["wangiri_codes"]
                chosen_group_id = grp["group_id"]
                code = random.choice(grp["prefixes"])
                raw_num = f"+{code}{generate_random_digits(7)}"
                category = "Wangiri High-Cost Trap"
                desc = f"Wangiri toll fraud destination (+{code})"
            elif sub == "premium_fraud":
                pfx = "19002" if split_name == "train" else ("19003" if split_name == "val" else ("19004" if split_name == "test" else "19005"))
                chosen_group_id = f"GRP_US_PREMIUM_{split_name.upper()}"
                raw_num = f"+1900{pfx[4:]}{generate_random_digits(6)}"
                country = "US"
                category = "Premium Rate Fraud"
                desc = "High-charge premium rate service line"
            else:
                tag = "1" if split_name == "train" else ("4" if split_name == "val" else ("7" if split_name == "test" else "9"))
                chosen_group_id = f"GRP_SATELLITE_{split_name.upper()}"
                raw_num = f"+881{tag}{generate_random_digits(7)}"
                category = "Wangiri High-Cost Trap"
                desc = f"Satellite callback trap (+881{tag})"
            label_code = 3

        # 2. TELEMARKETING_SPAM
        elif target_label == "TELEMARKETING_SPAM":
            sub = random.choice(["trai_140", "ofcom_bulk", "nanpa_marketing", "low_entropy_dialer"])
            if sub == "trai_140":
                grp = clusters["india_trai_140"]
                chosen_group_id = grp["group_id"]
                pfx = random.choice(grp["prefixes"])
                raw_num = f"+91{pfx}{generate_random_digits(6)}"
                country = "IN"
                category = "Commercial Telemarketing"
                desc = f"Registered TRAI 140 telemarketing series ({pfx})"
            elif sub == "ofcom_bulk":
                grp = clusters["ofcom_bulk"]
                chosen_group_id = grp["group_id"]
                pfx = random.choice(grp["prefixes"])
                raw_num = f"+44{pfx[1:]}{generate_random_digits(7)}"
                country = "GB"
                category = "Commercial Telemarketing"
                desc = f"OFCOM bulk automated dialer ({pfx})"
            elif sub == "nanpa_marketing":
                grp = clusters["us_marketing"]
                chosen_group_id = grp["group_id"]
                pfx = random.choice(grp["prefixes"])
                raw_num = f"+1{pfx}{generate_random_digits(7)}"
                country = "US"
                category = "Commercial Telemarketing"
                desc = f"NANPA bulk marketing dialer (+1-{pfx})"
            else:
                grp = clusters["india_jio"]
                chosen_group_id = f"{grp['group_id']}_ROBOCALL"
                d = str(random.randint(0, 9))
                pfx = random.choice(grp["prefixes"])
                raw_num = f"+91{pfx}{d * 7}"
                country = "IN"
                category = "Low-Entropy Automated Robocall"
                desc = f"Automated dialer repeated pattern ({pfx}-{d*7})"
            label_code = 2

        # 3. INVALID
        elif target_label == "INVALID":
            invalid_counter += 1
            chosen_group_id = f"GRP_INVALID_{split_name.upper()}"
            raw_num, desc = generate_strictly_invalid_number(invalid_counter, split_name)
            country = "IN"
            category = "Invalid Number Structure"
            label_code = 4

        # 4. UNKNOWN
        elif target_label == "UNKNOWN":
            sub_c = random.choice(["IN", "US", "GB"])
            if sub_c == "IN":
                op = random.choice(["india_jio", "india_airtel", "india_vi", "india_bsnl"])
                grp = clusters[op]
                chosen_group_id = grp["group_id"]
                pfx = random.choice(grp["prefixes"])
                raw_num = f"+91{pfx}{generate_random_digits(7)}"
                country = "IN"
                desc = f"Standard Indian cellular subscriber ({pfx})"
            elif sub_c == "US":
                grp = clusters["us_area"]
                chosen_group_id = grp["group_id"]
                area = random.choice(grp["prefixes"])
                raw_num = f"+1{area}{generate_random_digits(7)}"
                country = "US"
                desc = f"Standard US subscriber (Area {area})"
            else:
                grp = clusters["ofcom_mobile"]
                chosen_group_id = grp["group_id"]
                pfx = random.choice(grp["prefixes"])
                raw_num = f"+44{pfx[1:]}{generate_random_digits(6)}"
                country = "GB"
                desc = "Standard UK mobile subscriber"
            category = "Standard Mobile Line"
            label_code = 1

        # 5. BENIGN
        else:
            sub = random.choice(["bank_care", "emergency", "pstn_landline"])
            if sub == "bank_care":
                grp = clusters["india_bank"]
                chosen_group_id = grp["group_id"]
                pfx = random.choice(grp["prefixes"])
                country = "IN"
                raw_num = f"+91{pfx}{generate_random_digits(5)}"
                category = "Bank Toll-Free Care"
                desc = f"Verified corporate customer service line (+91-{pfx})"
            elif sub == "emergency":
                chosen_group_id = f"GRP_EMERGENCY_{split_name.upper()}"
                if split_name == "train": raw_num = "112"
                elif split_name == "val": raw_num = "911"
                elif split_name == "test": raw_num = "1930"
                else: raw_num = "999"
                country = "IN" if raw_num in ("112", "1930") else ("GB" if raw_num == "999" else "US")
                category = "Emergency & Public Service"
                desc = "Recognized national emergency helpline"
            else:
                grp = clusters["india_pstn"]
                chosen_group_id = grp["group_id"]
                pfx = random.choice(grp["prefixes"])
                raw_num = f"+91{pfx}{generate_random_digits(8)}"
                country = "IN"
                category = "PSTN Geographic Landline"
                desc = f"Standard PSTN landline (+91-{pfx})"
            label_code = 0

        e164, cc, nat, std_l, is_v = normalize_and_parse(raw_num, country)
        norm_key = e164 if e164 else raw_num

        # Generator Validation Assertion Check:
        # Non-INVALID samples MUST be valid according to libphonenumber
        if target_label != "INVALID" and not is_v:
            return None
        # INVALID samples MUST NOT be valid
        if target_label == "INVALID" and is_v:
            return None

        if norm_key in seen_numbers:
            return None

        seen_numbers.add(norm_key)

        return {
            "raw_number": raw_num,
            "normalized_e164": norm_key,
            "country": country,
            "group_id": chosen_group_id,
            "split": split_name,
            "category": category,
            "label_name": target_label,
            "label": label_code,
            "is_threat": 1 if target_label in ("TELEMARKETING_SPAM", "CONFIRMED_SCAM") else 0,
            "is_invalid": 1 if target_label == "INVALID" else 0,
            "desc": desc
        }

    def build_split(n_samples: int, target_distribution: Dict[str, float], split_name: str) -> List[Dict[str, Any]]:
        samples = []
        labels = list(target_distribution.keys())
        weights = list(target_distribution.values())

        attempts = 0
        while len(samples) < n_samples and attempts < n_samples * 50:
            attempts += 1
            chosen_label = random.choices(labels, weights=weights, k=1)[0]
            s = generate_sample(chosen_label, split_name)
            if s is not None:
                samples.append(s)

        random.shuffle(samples)
        return samples

    # 1. Train (10,000)
    train_dist = {"BENIGN": 0.25, "UNKNOWN": 0.25, "TELEMARKETING_SPAM": 0.25, "CONFIRMED_SCAM": 0.20, "INVALID": 0.05}
    train_samples = build_split(10000, train_dist, "train")

    # 2. Validation (2,500)
    val_dist = {"BENIGN": 0.25, "UNKNOWN": 0.25, "TELEMARKETING_SPAM": 0.25, "CONFIRMED_SCAM": 0.20, "INVALID": 0.05}
    val_samples = build_split(2500, val_dist, "val")

    # 3. Untouched Frozen Holdout Test Set (2,500)
    test_dist = {"BENIGN": 0.25, "UNKNOWN": 0.25, "TELEMARKETING_SPAM": 0.25, "CONFIRMED_SCAM": 0.20, "INVALID": 0.05}
    test_samples = build_split(2500, test_dist, "test")

    # 4. Natural Prevalence Benchmark (5,000)
    prev_dist = {"BENIGN": 0.40, "UNKNOWN": 0.40, "TELEMARKETING_SPAM": 0.10, "CONFIRMED_SCAM": 0.05, "INVALID": 0.05}
    prev_samples = build_split(5000, prev_dist, "benchmark")

    # Audit & 6-Way Assertions
    def get_7digit_prefixes(samples):
        pfxs = set()
        for s in samples:
            digits = re.sub(r"[^\d]", "", s["raw_number"])
            if len(digits) >= 7:
                pfxs.add(digits[:7])
        return pfxs

    train_pfxs = get_7digit_prefixes(train_samples)
    val_pfxs = get_7digit_prefixes(val_samples)
    test_pfxs = get_7digit_prefixes(test_samples)
    bench_pfxs = get_7digit_prefixes(prev_samples)

    tr_val_overlap = len(train_pfxs.intersection(val_pfxs))
    tr_te_overlap = len(train_pfxs.intersection(test_pfxs))
    tr_bm_overlap = len(train_pfxs.intersection(bench_pfxs))
    val_te_overlap = len(val_pfxs.intersection(test_pfxs))
    val_bm_overlap = len(val_pfxs.intersection(bench_pfxs))
    te_bm_overlap = len(test_pfxs.intersection(bench_pfxs))

    invalid_test = [s for s in test_samples if s["label_name"] == "INVALID"]
    invalid_accepted = sum(1 for s in invalid_test if normalize_and_parse(s["raw_number"], s["country"])[4] is True)

    print(f"[*] 7-Digit Overlap Audit:")
    print(f"    - Train vs Val:       {tr_val_overlap} (STRICT ZERO)")
    print(f"    - Train vs Test:      {tr_te_overlap} (STRICT ZERO)")
    print(f"    - Train vs Benchmark: {tr_bm_overlap} (STRICT ZERO)")
    print(f"    - Val vs Test:        {val_te_overlap} (STRICT ZERO)")
    print(f"    - Val vs Benchmark:   {val_bm_overlap} (STRICT ZERO)")
    print(f"    - Test vs Benchmark:  {te_bm_overlap} (STRICT ZERO)")

    assert tr_val_overlap == 0, f"FATAL: Train vs Val overlap is {tr_val_overlap}!"
    assert tr_te_overlap == 0, f"FATAL: Train vs Test overlap is {tr_te_overlap}!"
    assert tr_bm_overlap == 0, f"FATAL: Train vs Benchmark overlap is {tr_bm_overlap}!"
    assert val_te_overlap == 0, f"FATAL: Val vs Test overlap is {val_te_overlap}!"
    assert val_bm_overlap == 0, f"FATAL: Val vs Benchmark overlap is {val_bm_overlap}!"
    assert te_bm_overlap == 0, f"FATAL: Test vs Benchmark overlap is {te_bm_overlap}!"
    assert invalid_accepted == 0, f"FATAL: {invalid_accepted} invalid test samples accepted as valid!"

    with open(os.path.join(DATA_DIR, "train_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(train_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "val_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(val_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "test_untouched_holdout.json"), "w", encoding="utf-8") as f:
        json.dump(test_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "natural_prevalence_benchmark.json"), "w", encoding="utf-8") as f:
        json.dump(prev_samples, f, indent=2)

    print(f"Generated train_dataset.json: {len(train_samples)} rows")
    print(f"Generated val_dataset.json: {len(val_samples)} rows")
    print(f"Generated test_untouched_holdout.json: {len(test_samples)} rows")
    print(f"Generated natural_prevalence_benchmark.json: {len(prev_samples)} rows")
    print(f"[*] Test Set Invalid Samples: {len(invalid_test)} (Accepted as valid: {invalid_accepted} / {len(invalid_test)})")
    print("[+] All 6-way dataset audit assertions PASSED.")

if __name__ == "__main__":
    build_dataset_suite()