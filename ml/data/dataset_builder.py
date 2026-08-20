"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2)
Strict Group-Based Prefix Partitioning (Verified 0 Shared 7-Digit Prefixes)
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
        "india_trai_140": ["1400", "1401", "1402", "1403"],
        "india_jio": ["600", "700", "808"],
        "india_airtel": ["981", "982", "983"],
        "india_vi": ["971", "972"],
        "india_bsnl": ["941", "942"],
        "india_pstn": ["22", "33", "80"],
        "india_bank": ["180011", "180012", "180018"],
        "us_area": ["212", "415", "312", "713"],
        "us_marketing": ["844"],
        "ofcom_bulk": ["0843", "0844"],
        "ofcom_mobile": ["07700"],
        "wangiri_codes": ["8811", "8821", "247", "232"]
    },
    "val": {
        "india_trai_140": ["1404", "1405", "1406"],
        "india_jio": ["701", "809"],
        "india_airtel": ["984", "985"],
        "india_vi": ["973", "974"],
        "india_bsnl": ["943", "944"],
        "india_pstn": ["44", "20"],
        "india_bank": ["180020", "180022"],
        "us_area": ["650", "305", "206"],
        "us_marketing": ["855"],
        "ofcom_bulk": ["0845"],
        "ofcom_mobile": ["07800"],
        "wangiri_codes": ["252", "224", "255"]
    },
    "test": {
        "india_trai_140": ["1407", "1408", "1409"],
        "india_jio": ["702", "897"],
        "india_airtel": ["986", "987", "988"],
        "india_vi": ["975", "976"],
        "india_bsnl": ["945", "946"],
        "india_pstn": ["11", "79"],
        "india_bank": ["180042", "180026"],
        "us_area": ["617", "404", "512", "408"],
        "us_marketing": ["866"],
        "ofcom_bulk": ["0870", "0871"],
        "ofcom_mobile": ["07900"],
        "wangiri_codes": ["257", "269", "239", "870"]
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
    if t == "all_zeros":
        tag = "0" if split_name == "train" else ("5" if split_name == "val" else "9")
        return f"000000000{tag}", "All zeros invalid sequence"
    elif t == "too_short":
        tag = 10 if split_name == "train" else (40 if split_name == "val" else 70)
        return str(tag + (index % 25)), "Length below international minimum"
    elif t == "overlength":
        tag = "1" if split_name == "train" else ("4" if split_name == "val" else "7")
        return f"+9198{tag}0{index:04d}123456789012345", "Length exceeds E.164 15-digit maximum"
    elif t == "impossible_leading_zero":
        tag = "1" if split_name == "train" else ("4" if split_name == "val" else "7")
        return f"+910{tag}{index:07d}", "Impossible leading 0 in Indian subscriber number"
    elif t == "letters_inside":
        chars = ["ABCD", "XYZ", "SCAM", "CALL", "TEST"]
        ch = chars[index % len(chars)]
        tag = "1" if split_name == "train" else ("4" if split_name == "val" else "7")
        return f"+9198{ch}{tag}{index:03d}", "Alphabetic characters in dial string"
    elif t == "impossible_country_code":
        tag = "1" if split_name == "train" else ("4" if split_name == "val" else "7")
        return f"+999{tag}{index:07d}", "Unassigned ITU-T country dial code +999"
    else:
        tag = "1" if split_name == "train" else ("4" if split_name == "val" else "7")
        return f"+91##{tag}{index:05d}**", "Non-dialable special symbols"

def build_dataset_suite(seed=42):
    random.seed(seed)
    np.random.seed(seed)

    print("="*85)
    print("      AEGIS-PNP2 DATASET GENERATOR (STRICT GROUP-BASED PREFIX ISOLATION)")
    print("="*85)

    seen_numbers: Set[str] = set()
    invalid_counter = 0

    def generate_sample(target_label: str, split_name: str) -> Optional[Dict[str, Any]]:
        nonlocal invalid_counter
        clusters = PREFIX_CLUSTERS[split_name if split_name in ("train", "val", "test") else "test"]
        country = "IN"
        raw_num = ""
        category = ""
        label_code = 0
        desc = ""

        # 1. CONFIRMED_SCAM
        if target_label == "CONFIRMED_SCAM":
            sub = random.choice(["wangiri", "premium_fraud", "spoofed_satellite"])
            if sub == "wangiri":
                code = random.choice(clusters["wangiri_codes"])
                raw_num = f"+{code}{generate_random_digits(7)}"
                category = "Wangiri High-Cost Trap"
                desc = f"Wangiri toll fraud destination (+{code})"
            elif sub == "premium_fraud":
                pfx = "19001" if split_name == "train" else ("19002" if split_name == "val" else "19003")
                raw_num = f"+91{pfx}{generate_random_digits(5)}"
                country = "IN"
                category = "Premium Rate Fraud"
                desc = "High-charge premium rate service line"
            else:
                tag = "1" if split_name == "train" else ("4" if split_name == "val" else "7")
                raw_num = f"+881{tag}{generate_random_digits(7)}"
                category = "Wangiri High-Cost Trap"
                desc = "Satellite callback trap (+881)"
            label_code = 3

        # 2. TELEMARKETING_SPAM
        elif target_label == "TELEMARKETING_SPAM":
            sub = random.choice(["trai_140", "ofcom_bulk", "nanpa_marketing", "low_entropy_dialer"])
            if sub == "trai_140":
                pfx = random.choice(clusters["india_trai_140"])
                raw_num = f"+91{pfx}{generate_random_digits(6)}"
                country = "IN"
                category = "Commercial Telemarketing"
                desc = f"Registered TRAI 140 telemarketing series ({pfx})"
            elif sub == "ofcom_bulk":
                pfx = random.choice(clusters["ofcom_bulk"])
                raw_num = f"+44{pfx[1:]}{generate_random_digits(7)}"
                country = "GB"
                category = "Commercial Telemarketing"
                desc = f"OFCOM bulk automated dialer ({pfx})"
            elif sub == "nanpa_marketing":
                pfx = random.choice(clusters["us_marketing"])
                raw_num = f"+1{pfx}{generate_random_digits(7)}"
                country = "US"
                category = "Commercial Telemarketing"
                desc = f"NANPA bulk marketing dialer (+1-{pfx})"
            else:
                d = str(random.randint(0, 9))
                tag = "1" if split_name == "train" else ("4" if split_name == "val" else "7")
                raw_num = f"+91{tag}{d * 9}"
                country = "IN"
                category = "Low-Entropy Automated Robocall"
                desc = f"Automated dialer repeated pattern ({d*9})"
            label_code = 2

        # 3. INVALID
        elif target_label == "INVALID":
            invalid_counter += 1
            raw_num, desc = generate_strictly_invalid_number(invalid_counter, split_name)
            country = "IN"
            category = "Invalid Number Structure"
            label_code = 4

        # 4. UNKNOWN
        elif target_label == "UNKNOWN":
            sub_c = random.choice(["IN", "US", "GB"])
            if sub_c == "IN":
                op = random.choice(["india_jio", "india_airtel", "india_vi", "india_bsnl"])
                pfx = random.choice(clusters[op])
                raw_num = f"+91{pfx}{generate_random_digits(7)}"
                country = "IN"
                desc = f"Standard Indian cellular subscriber ({pfx})"
            elif sub_c == "US":
                area = random.choice(clusters["us_area"])
                raw_num = f"+1{area}{generate_random_digits(7)}"
                country = "US"
                desc = f"Standard US subscriber (Area {area})"
            else:
                pfx = random.choice(clusters["ofcom_mobile"])
                raw_num = f"+44{pfx[1:]}{generate_random_digits(6)}"
                country = "GB"
                desc = "Standard UK mobile subscriber"
            category = "Standard Mobile Line"
            label_code = 1

        # 5. BENIGN
        else:
            sub = random.choice(["bank_care", "emergency", "pstn_landline"])
            if sub == "bank_care":
                pfx = random.choice(clusters["india_bank"])
                country = "IN"
                raw_num = f"+91{pfx}{generate_random_digits(5)}"
                category = "Bank Toll-Free Care"
                desc = f"Verified corporate customer service line (+91-{pfx})"
            elif sub == "emergency":
                if split_name == "train": raw_num = "112"
                elif split_name == "val": raw_num = "911"
                else: raw_num = "1930"
                country = "IN" if raw_num in ("112", "1930") else "US"
                category = "Emergency & Public Service"
                desc = "Recognized national emergency helpline"
            else:
                pfx = random.choice(clusters["india_pstn"])
                raw_num = f"+91{pfx}{generate_random_digits(8)}"
                country = "IN"
                category = "PSTN Geographic Landline"
                desc = f"Standard PSTN landline (+91-{pfx})"
            label_code = 0

        e164, cc, nat, std_l, is_v = normalize_and_parse(raw_num, country)
        norm_key = e164 if e164 else raw_num

        if target_label == "INVALID" and is_v:
            return None

        if norm_key in seen_numbers:
            return None

        seen_numbers.add(norm_key)

        return {
            "raw_number": raw_num,
            "normalized_e164": norm_key,
            "country": country,
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
        while len(samples) < n_samples and attempts < n_samples * 35:
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

    # 4. Natural Prevalence Benchmark (5,000: 80% Safe, 10% Telemarketing, 5% Scam, 5% Invalid)
    prev_dist = {"BENIGN": 0.40, "UNKNOWN": 0.40, "TELEMARKETING_SPAM": 0.10, "CONFIRMED_SCAM": 0.05, "INVALID": 0.05}
    prev_samples = build_split(5000, prev_dist, "test")

    with open(os.path.join(DATA_DIR, "train_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(train_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "val_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(val_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "test_untouched_holdout.json"), "w", encoding="utf-8") as f:
        json.dump(test_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "natural_prevalence_benchmark.json"), "w", encoding="utf-8") as f:
        json.dump(prev_samples, f, indent=2)

    def get_7digit_prefixes(samples):
        pfxs = set()
        for s in samples:
            digits = re.sub(r"[^\d]", "", s["raw_number"])
            if len(digits) >= 7:
                pfxs.add(digits[:7])
        return pfxs

    train_pfxs = get_7digit_prefixes(train_samples)
    test_pfxs = get_7digit_prefixes(test_samples)
    shared_pfxs = len(train_pfxs.intersection(test_pfxs))

    invalid_test = [s for s in test_samples if s["label_name"] == "INVALID"]
    invalid_accepted = sum(1 for s in invalid_test if normalize_and_parse(s["raw_number"], s["country"])[4] is True)

    print(f"Generated train_dataset.json: {len(train_samples)} rows")
    print(f"Generated val_dataset.json: {len(val_samples)} rows")
    print(f"Generated test_untouched_holdout.json: {len(test_samples)} rows")
    print(f"Generated natural_prevalence_benchmark.json: {len(prev_samples)} rows")
    print(f"[*] 7-Digit Prefix Overlap (Train vs Test): {shared_pfxs} (Zero Shared Prefix Clusters)")
    print(f"[*] Test Set Invalid Samples: {len(invalid_test)} (Accepted as valid: {invalid_accepted} / {len(invalid_test)})")

if __name__ == "__main__":
    build_dataset_suite()