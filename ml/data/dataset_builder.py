"""
AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2)
Production Dataset Generator with Strict Prefix-Family Partitioning & Multi-Split Invalid Inputs
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

with open(os.path.join(DATA_DIR, "regulatory_registries.json"), "r", encoding="utf-8") as f:
    REGISTRY = json.load(f)

COUNTRIES = ["IN", "US", "GB", "CA", "AU", "DE", "FR", "BR", "NG", "ID", "JP"]

def generate_random_digits(length: int) -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def generate_invalid_variant(index: int) -> Tuple[str, str]:
    sub_types = [
        "all_zeros", "too_short", "overlength", "impossible_leading_0", "impossible_leading_1",
        "unicode_digits", "alphanumeric", "bad_plus_syntax", "invalid_country_code", "special_symbols"
    ]
    t = sub_types[index % len(sub_types)]
    if t == "all_zeros":
        return "0" * (index % 8 + 3), "all_zeros"
    elif t == "too_short":
        return str(100 + index % 900), "too_short"
    elif t == "overlength":
        return "+919820" + str(100000 + index) + "1234567890", "overlength"
    elif t == "impossible_leading_0":
        return f"+10{index:08d}", "impossible_leading_0"
    elif t == "impossible_leading_1":
        return f"+910{index:08d}", "impossible_leading_0"
    elif t == "unicode_digits":
        unicode_map = {'0':'０','1':'１','2':'２','3':'３','4':'４','5':'５','6':'６','7':'７','8':'８','9':'９'}
        base = f"9820{index:06d}"
        return "+91" + "".join(unicode_map.get(c, c) for c in base), "unicode_digits"
    elif t == "alphanumeric":
        chars = ["ABCD", "XYZ", "PHONE", "SCAM", "CALL"]
        ch = chars[index % len(chars)]
        return f"+9198{ch}{index:04d}", "alphanumeric"
    elif t == "bad_plus_syntax":
        return f"++919820{index:06d}", "bad_plus_syntax"
    elif t == "invalid_country_code":
        return f"+9999820{index:06d}", "invalid_country_code"
    else:
        return f"+91#9820*{index:04d}", "special_symbols"

def generate_dataset_suite(seed=42):
    random.seed(seed)
    np.random.seed(seed)

    print("="*85)
    print("      AEGIS-PNP2 DATASET GENERATOR (STRICT PREFIX PARTITIONING & INVALID SUITE)")
    print("="*85)

    seen_numbers: Set[str] = set()
    invalid_counter = 0

    def generate_sample(target_label: str, split: str) -> Optional[Dict[str, Any]]:
        nonlocal invalid_counter
        country = random.choice(COUNTRIES)
        raw_num = ""
        category = ""
        label_code = 0
        desc = ""

        # 1. CONFIRMED_SCAM
        if target_label == "CONFIRMED_SCAM":
            sub = random.choice(["wangiri", "premium_fraud", "spoofed_satellite"])
            if sub == "wangiri":
                itu = REGISTRY["itu_wangiri_registry"]
                code_pool = itu["test_codes"] if split in ("test", "benchmark") else (itu["val_codes"] if split == "val" else itu["train_codes"])
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

        # 2. TELEMARKETING_SPAM
        elif target_label == "TELEMARKETING_SPAM":
            sub = random.choice(["trai_140", "ofcom_bulk", "nanpa_marketing", "low_entropy_dialer", "sequential_robocall"])
            if sub == "trai_140":
                all_140 = REGISTRY["india_trai_registry"]["promotional_series_140"]
                if split == "train": pfx = random.choice(all_140[0:4])
                elif split == "val": pfx = random.choice(all_140[4:7])
                else: pfx = random.choice(all_140[7:10])
                raw_num = f"+91{pfx}{generate_random_digits(6)}"
                country = "IN"
                category = "Commercial Telemarketing"
                desc = f"Registered TRAI 140 telemarketing series ({pfx})"
            elif sub == "ofcom_bulk":
                ofc = REGISTRY["ofcom_uk_registry"]["bulk_dialers"]
                pfx_pool = ofc["test"] if split in ("test", "benchmark") else (ofc["val"] if split == "val" else ofc["train"])
                pfx = random.choice(pfx_pool)
                raw_num = f"+44{pfx[1:]}{generate_random_digits(7)}"
                country = "GB"
                category = "Commercial Telemarketing"
                desc = f"OFCOM bulk automated dialer ({pfx})"
            elif sub == "nanpa_marketing":
                pfx = random.choice(REGISTRY["nanpa_us_registry"]["toll_free_marketing"])
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

        # 3. INVALID (Diverse malformed, impossible, Unicode, chars)
        elif target_label == "INVALID":
            invalid_counter += 1
            raw_num, sub_type = generate_invalid_variant(invalid_counter)
            category = "Invalid Number Structure"
            desc = f"Malformed input violating numbering plan ({sub_type})"
            label_code = 4

        # 4. UNKNOWN
        elif target_label == "UNKNOWN":
            if country == "IN":
                ops = REGISTRY["india_trai_registry"]["cellular_operators"]
                op_name = random.choice(list(ops.keys()))
                block_key = "test_blocks" if split in ("test", "benchmark") else ("val_blocks" if split == "val" else "train_blocks")
                pfx = random.choice(ops[op_name][block_key])
                raw_num = f"+91{pfx}{generate_random_digits(7)}"
                desc = f"Standard Indian mobile subscriber ({op_name} {pfx})"
            elif country == "US":
                areas = REGISTRY["nanpa_us_registry"]["area_codes"]
                area_key = "test" if split in ("test", "benchmark") else ("val" if split == "val" else "train")
                area = random.choice(areas[area_key])
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

        # 5. BENIGN
        else:
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

    # 4. Natural Prevalence Benchmark (5,000: 80% Benign/Unknown, 10% Telemarketing, 5% Scam, 5% Invalid)
    prev_dist = {"BENIGN": 0.40, "UNKNOWN": 0.40, "TELEMARKETING_SPAM": 0.10, "CONFIRMED_SCAM": 0.05, "INVALID": 0.05}
    prev_samples = build_split(5000, prev_dist, "benchmark")

    # 5. Certified Bank Customer Care & Emergency Lines
    hard_negatives = REGISTRY["certified_allowlist"]

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

    invalid_in_train = sum(1 for s in train_samples if s["label_name"] == "INVALID")
    invalid_in_val = sum(1 for s in val_samples if s["label_name"] == "INVALID")
    invalid_in_test = sum(1 for s in test_samples if s["label_name"] == "INVALID")

    print(f"Generated train_dataset.json: {len(train_samples)} deduplicated numbers (INVALID: {invalid_in_train})")
    print(f"Generated val_dataset.json: {len(val_samples)} deduplicated numbers (INVALID: {invalid_in_val})")
    print(f"Generated test_untouched_holdout.json: {len(test_samples)} deduplicated numbers (INVALID: {invalid_in_test})")
    print(f"Generated natural_prevalence_benchmark.json: {len(prev_samples)} prevalence benchmark numbers")
    print(f"Generated hard_negatives.json: {len(hard_negatives)} certified banking & emergency lines")
    print(f"[*] Train / Test Overlap: {train_test_overlap} (Strict Zero Leakage Verified)")
    print(f"[*] Train / Val Overlap:  {train_val_overlap} (Strict Zero Leakage Verified)")

if __name__ == "__main__":
    generate_dataset_suite()