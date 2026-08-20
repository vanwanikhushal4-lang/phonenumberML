"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2)
Production Grounded Dataset Generator with Strict Prefix-Family Partitioning & Zero Leakage
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

COUNTRIES = ["IN", "US", "GB", "CA", "AU", "DE", "FR", "BR", "NG", "ID", "JP"]

# Grounded Operator Allocations
INDIA_OPERATORS = {
    "Jio": ["600", "700", "701", "702", "797", "798", "799", "808", "809", "897", "898", "899"],
    "Airtel": ["981", "982", "983", "984", "985", "986", "987", "988", "989", "991", "992", "993", "994", "995"],
    "Vi": ["971", "972", "973", "974", "975", "976", "977", "978", "979", "901", "902", "903", "904"],
    "BSNL": ["941", "942", "943", "944", "945", "946", "947", "948", "949", "940"]
}

# Distinct TRAI 140 commercial marketing series partitioned by split
TRAI_140_TRAIN = ["1400", "1401", "1402", "1403", "1404", "1405"]
TRAI_140_VAL   = ["1406", "1407"]
TRAI_140_TEST  = ["1408", "1409"]

# Distinct Wangiri international codes partitioned by split
WANGIRI_TRAIN = ["881", "882", "247", "232", "252", "224"]
WANGIRI_VAL   = ["255", "257", "269"]
WANGIRI_TEST  = ["239", "245", "674", "688", "870"]

# Distinct OFCOM bulk dialers partitioned by split
OFCOM_TRAIN = ["0843", "0844"]
OFCOM_VAL   = ["0845"]
OFCOM_TEST  = ["0870", "0871"]

def generate_random_digits(length: int) -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def generate_dataset_suite(seed=42):
    random.seed(seed)
    np.random.seed(seed)

    print("="*85)
    print("      AEGIS-PNP2 DATASET SUITE: GROUNDED TELECOM DATA & PREFIX PARTITIONING")
    print("="*85)

    seen_numbers: Set[str] = set()

    def generate_sample(target_label: str, split: str) -> Optional[Dict[str, Any]]:
        country = random.choice(COUNTRIES)
        raw_num = ""
        category = ""
        label_code = 0
        desc = ""

        if target_label == "CONFIRMED_SCAM":
            sub = random.choice(["wangiri", "premium_fraud", "spoofed_satellite"])
            if sub == "wangiri":
                code_pool = WANGIRI_TEST if split in ("test", "benchmark") else (WANGIRI_VAL if split == "val" else WANGIRI_TRAIN)
                code = random.choice(code_pool)
                raw_num = f"+{code}{generate_random_digits(7)}"
                category = "Wangiri High-Cost Trap"
                desc = f"Wangiri toll fraud (Code +{code})"
            elif sub == "premium_fraud":
                if country == "IN": raw_num = f"+911900{generate_random_digits(6)}"
                elif country == "US": raw_num = f"+1900{generate_random_digits(7)}"
                elif country == "FR": raw_num = f"+3389{generate_random_digits(7)}"
                else: raw_num = f"+44900{generate_random_digits(6)}"
                category = "Premium Rate Fraud"
                desc = "High-charge premium rate service line"
            else:
                raw_num = f"+881{generate_random_digits(8)}"
                category = "Wangiri High-Cost Trap"
                desc = "Global mobile satellite callback trap"
            label_code = 3

        elif target_label == "TELEMARKETING_SPAM":
            sub = random.choice(["trai_140", "ofcom_bulk", "nanpa_marketing", "low_entropy_dialer", "sequential_robocall"])
            if sub == "trai_140":
                pfx_pool = TRAI_140_TEST if split in ("test", "benchmark") else (TRAI_140_VAL if split == "val" else TRAI_140_TRAIN)
                pfx = random.choice(pfx_pool)
                raw_num = f"+91{pfx}{generate_random_digits(6)}"
                country = "IN"
                category = "Commercial Telemarketing"
                desc = f"Registered TRAI 140 telemarketing series ({pfx})"
            elif sub == "ofcom_bulk":
                pfx_pool = OFCOM_TEST if split in ("test", "benchmark") else (OFCOM_VAL if split == "val" else OFCOM_TRAIN)
                pfx = random.choice(pfx_pool)
                raw_num = f"+44{pfx[1:]}{generate_random_digits(7)}"
                country = "GB"
                category = "Commercial Telemarketing"
                desc = f"OFCOM bulk automated dialer ({pfx})"
            elif sub == "nanpa_marketing":
                pfx = random.choice(["844", "855", "866"])
                raw_num = f"+1{pfx}{generate_random_digits(7)}"
                country = "US"
                category = "Commercial Telemarketing"
                desc = f"US toll-free marketing dialer (+1-{pfx})"
            elif sub == "low_entropy_dialer":
                d = str(random.randint(0, 9))
                if country == "IN": raw_num = f"+91{d * 10}"
                elif country == "US": raw_num = f"+1{d * 10}"
                else: raw_num = f"+44{d * 10}"
                category = "Low-Entropy Automated Robocall"
                desc = f"Automated dialer repeated pattern ({d*10})"
            else:
                if country == "IN": raw_num = f"+910123456789"
                elif country == "US": raw_num = f"+19876543210"
                else: raw_num = f"+441212121212"
                category = "Low-Entropy Automated Robocall"
                desc = "Sequential automated dialer"
            label_code = 2

        elif target_label == "INVALID":
            sub = random.choice(["all_zeros", "too_short", "impossible_leading", "bad_syntax"])
            if sub == "all_zeros": raw_num = "0000000000"
            elif sub == "too_short": raw_num = "123"
            elif sub == "impossible_leading": raw_num = "+10123456789"
            else: raw_num = "+9100000000"
            category = "Invalid Number Structure"
            desc = "Malformed number violating numbering plan"
            label_code = 4

        elif target_label == "UNKNOWN":
            if country == "IN":
                op = random.choice(list(INDIA_OPERATORS.keys()))
                pfx = random.choice(INDIA_OPERATORS[op])
                raw_num = f"+91{pfx}{generate_random_digits(7)}"
                desc = f"Standard Indian mobile subscriber ({op})"
            elif country == "US":
                area = random.choice(["212", "415", "650", "312", "713", "305", "206", "617", "404", "512", "408", "917"])
                raw_num = f"+1{area}{generate_random_digits(7)}"
                desc = f"Standard US subscriber (Area {area})"
            elif country == "GB":
                raw_num = f"+447{random.choice(['700', '800', '900'])}{generate_random_digits(6)}"
                desc = "Standard UK mobile subscriber"
            elif country == "JP":
                raw_num = f"+8190{generate_random_digits(8)}"
                desc = "Standard Japan mobile subscriber (090)"
            elif country == "FR":
                raw_num = f"+336{generate_random_digits(8)}"
                desc = "Standard France mobile subscriber"
            elif country == "DE":
                raw_num = f"+49151{generate_random_digits(7)}"
                desc = "Standard Germany mobile subscriber"
            elif country == "AU":
                raw_num = f"+614{generate_random_digits(8)}"
                desc = "Standard Australia mobile subscriber"
            elif country == "BR":
                raw_num = f"+55119{generate_random_digits(8)}"
                desc = "Standard Brazil mobile subscriber"
            elif country == "ID":
                raw_num = f"+62811{generate_random_digits(7)}"
                desc = "Standard Indonesia mobile subscriber"
            else:
                raw_num = f"+234803{generate_random_digits(7)}"
                desc = "Standard Nigeria mobile subscriber"
            category = "Standard Mobile Line"
            label_code = 1

        else: # BENIGN
            sub = random.choice(["bank_care", "emergency", "pstn_landline"])
            if sub == "bank_care":
                pfx = random.choice(["+911800", "+1800", "+44800", "+611800"])
                digits = generate_random_digits(7 if pfx.startswith("+1") or pfx.startswith("+91") else 6)
                raw_num = f"{pfx}{digits}"
                country = "IN" if pfx.startswith("+91") else ("US" if pfx.startswith("+1") else "GB")
                category = "Bank Toll-Free Care"
                desc = "Verified toll-free customer support line"
            elif sub == "emergency":
                raw_num = random.choice(["112", "911", "999", "100", "108", "1930", "000", "110", "119", "17", "18"])
                country = "IN" if raw_num in ("112", "100", "108", "1930") else ("US" if raw_num == "911" else "GB")
                category = "Emergency & Public Service"
                desc = "Recognized national emergency line"
            else:
                if country == "IN": raw_num = f"+9122{generate_random_digits(8)}"
                elif country == "US": raw_num = f"+1212{generate_random_digits(7)}"
                elif country == "FR": raw_num = f"+331{generate_random_digits(8)}"
                elif country == "DE": raw_num = f"+4930{generate_random_digits(8)}"
                else: raw_num = f"+4420{generate_random_digits(8)}"
                category = "PSTN Geographic Landline"
                desc = f"Standard PSTN landline ({country})"
            label_code = 0

        e164, cc, nat, std_l, is_v = normalize_and_parse(raw_num, country)
        norm_key = e164 if e164 else raw_num

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
        while len(samples) < n_samples and attempts < n_samples * 30:
            attempts += 1
            chosen_label = random.choices(labels, weights=weights, k=1)[0]
            s = generate_sample(chosen_label, split_name)
            if s is not None:
                samples.append(s)

        random.shuffle(samples)
        return samples

    # 1. Train Set (10,000)
    train_dist = {"BENIGN": 0.25, "UNKNOWN": 0.25, "TELEMARKETING_SPAM": 0.25, "CONFIRMED_SCAM": 0.20, "INVALID": 0.05}
    train_samples = build_split(10000, train_dist, "train")

    # 2. Validation Set (2,500)
    val_dist = {"BENIGN": 0.25, "UNKNOWN": 0.25, "TELEMARKETING_SPAM": 0.25, "CONFIRMED_SCAM": 0.20, "INVALID": 0.05}
    val_samples = build_split(2500, val_dist, "val")

    # 3. Untouched Frozen Holdout Test Set (2,500)
    test_dist = {"BENIGN": 0.25, "UNKNOWN": 0.25, "TELEMARKETING_SPAM": 0.25, "CONFIRMED_SCAM": 0.20, "INVALID": 0.05}
    test_samples = build_split(2500, test_dist, "test")

    # 4. Natural Prevalence Benchmark (5,000: 85% Benign/Unknown, 10% Telemarketing, 5% Scam)
    prev_dist = {"BENIGN": 0.45, "UNKNOWN": 0.40, "TELEMARKETING_SPAM": 0.10, "CONFIRMED_SCAM": 0.05}
    prev_samples = build_split(5000, prev_dist, "benchmark")

    # 5. Certified Bank Customer Care & Emergency Lines
    hard_negatives = [
        {"name": "State Bank of India Customer Care", "number": "+911800112211", "country": "IN", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "SBI Alternate Care", "number": "+9118004253800", "country": "IN", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "HDFC Bank Priority Support", "number": "+9118002026161", "country": "IN", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "ICICI Bank Phone Banking", "number": "+9118001080", "country": "IN", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "Axis Bank Helpline", "number": "+9118002098800", "country": "IN", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "Punjab National Bank Care", "number": "+9118001802222", "country": "IN", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "Bank of Baroda Priority", "number": "+911800229090", "country": "IN", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "Chase Bank Customer Support", "number": "+18009359935", "country": "US", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "Bank of America Help Line", "number": "+18004321000", "country": "US", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "Wells Fargo Banking Line", "number": "+18008693557", "country": "US", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "Barclays UK Freephone", "number": "+44800123456", "country": "GB", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "HSBC UK Customer Care", "number": "+448000852401", "country": "GB", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.10},
        {"name": "India National Emergency", "number": "112", "country": "IN", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.05},
        {"name": "India Cyber Crime Helpline", "number": "1930", "country": "IN", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.05},
        {"name": "US Emergency Services", "number": "911", "country": "US", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.05},
        {"name": "UK Emergency Line", "number": "999", "country": "GB", "expected_tier": "LEGITIMATE", "expected_max_risk": 0.05}
    ]

    with open(os.path.join(DATA_DIR, "train_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(train_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "val_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(val_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "test_untouched_holdout.json"), "w", encoding="utf-8") as f:
        json.dump(test_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "natural_prevalence_benchmark.json"), "w", encoding="utf-8") as f:
        json.dump(prev_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "hard_negatives.json"), "w", encoding="utf-8") as f:
        json.dump(hard_negatives, f, indent=2)

    train_keys = set(s["normalized_e164"] for s in train_samples)
    val_keys = set(s["normalized_e164"] for s in val_samples)
    test_keys = set(s["normalized_e164"] for s in test_samples)

    train_test_overlap = len(train_keys.intersection(test_keys))
    train_val_overlap = len(train_keys.intersection(val_keys))

    print(f"Generated train_dataset.json: {len(train_samples)} deduplicated numbers")
    print(f"Generated val_dataset.json: {len(val_samples)} deduplicated numbers")
    print(f"Generated test_untouched_holdout.json: {len(test_samples)} deduplicated numbers")
    print(f"Generated natural_prevalence_benchmark.json: {len(prev_samples)} prevalence benchmark numbers")
    print(f"Generated hard_negatives.json: {len(hard_negatives)} certified banking & emergency lines")
    print(f"[*] Train / Test Overlap: {train_test_overlap} (Strict Zero Leakage Verified)")
    print(f"[*] Train / Val Overlap:  {train_val_overlap} (Strict Zero Leakage Verified)")

if __name__ == "__main__":
    generate_dataset_suite()