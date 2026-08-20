"""
AEGIS Phone Number Pattern Risk Model — Multi-Country Dataset Generator
"""

import os
import sys
import json
import random
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, FEATURE_SPEC

DATA_DIR = os.path.dirname(__file__)
COUNTRIES = ["IN", "US", "GB", "CA", "AU", "DE", "FR", "BR", "NG", "ID", "JP"]

def generate_random_digits(length: int) -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def generate_pattern_digits(pattern_type: str, length: int) -> str:
    if pattern_type == "repeated":
        d = str(random.randint(0, 9))
        return d * length
    elif pattern_type == "sequential_asc":
        return "0123456789"[:length]
    elif pattern_type == "sequential_desc":
        return "9876543210"[:length]
    elif pattern_type == "alternating":
        a, b = str(random.randint(0, 9)), str(random.randint(0, 9))
        return "".join([a if i % 2 == 0 else b for i in range(length)])
    elif pattern_type == "block_repeat":
        block = str(random.randint(10, 99))
        return (block * (length // 2 + 1))[:length]
    elif pattern_type == "trailing_zeros":
        base = generate_random_digits(length - 4)
        return base + "0000"
    return generate_random_digits(length)

def build_datasets(n_train=12000, n_test=3000, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    train_telemarketer_prefixes_in = ["1401", "1402", "1403", "1404", "1405", "1406"]
    test_telemarketer_prefixes_in  = ["1407", "1408", "1409"]
    train_wangiri_codes = ["881", "882", "247", "232", "252", "224"]
    test_wangiri_codes  = ["255", "257", "269", "239", "245", "674", "688"]

    def create_sample(class_label: str, is_test: bool = False):
        country = random.choice(COUNTRIES)
        
        # 1. SCAM (Wangiri, Premium fraud, Spoofed satellite)
        if class_label == "SCAM":
            sub = random.choice(["wangiri", "premium_fraud", "spoofed_satellite"])
            if sub == "wangiri":
                code = random.choice(test_wangiri_codes if is_test else train_wangiri_codes)
                digits = generate_pattern_digits(random.choice(["alternating", "repeated", "random"]), 7)
                num = f"+{code}{digits}"
            elif sub == "premium_fraud":
                if country == "IN": num = f"+911900{generate_pattern_digits('random', 6)}"
                elif country == "US": num = f"+1900{generate_pattern_digits('random', 7)}"
                else: num = f"+44900{generate_pattern_digits('random', 6)}"
            else:
                num = f"+881{generate_pattern_digits('sequential_asc', 8)}"
            return {"raw_number": num, "country": country, "label_name": "SCAM", "label": 3, "risk_prob": random.uniform(0.75, 0.99)}

        # 2. SPAM (Telemarketing, Low-entropy robocallers)
        elif class_label == "SPAM":
            sub = random.choice(["telemarketer_in", "voip_dialer", "low_entropy_dialer", "sequential_desc"])
            if sub == "telemarketer_in":
                pfx = random.choice(test_telemarketer_prefixes_in if is_test else train_telemarketer_prefixes_in)
                num = f"+91{pfx}{generate_pattern_digits('random', 6)}"
                country = "IN"
            elif sub == "voip_dialer":
                num = f"+44843{generate_pattern_digits('random', 7)}"
                country = "GB"
            elif sub == "low_entropy_dialer":
                d = str(random.randint(0, 9))
                if country == "IN": num = f"+91{d * 10}"
                elif country == "US": num = f"+1{d * 10}"
                else: num = f"+44{d * 10}"
            else:
                if country == "IN": num = f"+91{generate_pattern_digits('sequential_desc', 10)}"
                elif country == "US": num = f"+1{generate_pattern_digits('sequential_desc', 10)}"
                else: num = f"+44{generate_pattern_digits('alternating', 10)}"
            return {"raw_number": num, "country": country, "label_name": "SPAM", "label": 2, "risk_prob": random.uniform(0.55, 0.70)}

        # 3. UNKNOWN / ABSTAIN (Standard numbers with normal entropy)
        elif class_label == "UNKNOWN":
            if country == "IN":
                pfx = random.choice(["98", "99", "97", "96", "95", "94", "88", "87", "86", "70", "72", "73"])
                num = f"+91{pfx}{generate_random_digits(8)}"
            elif country == "US":
                area = random.choice(["212", "415", "650", "312", "713", "305", "206", "617", "404", "512"])
                num = f"+1{area}{generate_random_digits(7)}"
            elif country == "GB":
                num = f"+447{generate_random_digits(9)}"
            elif country == "JP":
                num = f"+8190{generate_random_digits(8)}"
            else:
                num = f"+4915{generate_random_digits(8)}"
            return {"raw_number": num, "country": country, "label_name": "UNKNOWN", "label": 1, "risk_prob": random.uniform(0.18, 0.35)}

        # 4. LEGITIMATE (Verified Customer Care, Banks, Emergency, Normal PSTN, Family)
        else:
            sub = random.choice(["bank_care", "emergency", "standard_landline", "standard_mobile"])
            if sub == "bank_care":
                pfx = random.choice(["+911800", "+1800", "+44800", "+611800"])
                digits = generate_random_digits(7 if pfx.startswith("+1") or pfx.startswith("+91") else 6)
                num = f"{pfx}{digits}"
                country = "IN" if pfx.startswith("+91") else ("US" if pfx.startswith("+1") else "GB")
            elif sub == "emergency":
                num = random.choice(["112", "911", "999", "100", "108", "000", "110", "119", "17", "18"])
                country = "IN"
            elif sub == "standard_landline":
                if country == "IN": num = f"+9122{generate_random_digits(8)}"
                elif country == "US": num = f"+1212{generate_random_digits(7)}"
                elif country == "FR": num = f"+331{generate_random_digits(8)}"
                elif country == "DE": num = f"+4930{generate_random_digits(8)}"
                else: num = f"+4420{generate_random_digits(8)}"
            else:
                if country == "IN": num = f"+91{random.choice(['9820', '9819', '9821', '9845'])}{generate_random_digits(6)}"
                elif country == "US": num = f"+1{random.choice(['650', '415', '408'])}{generate_random_digits(7)}"
                elif country == "FR": num = f"+336{generate_random_digits(8)}"
                elif country == "DE": num = f"+49151{generate_random_digits(7)}"
                elif country == "JP": num = f"+8190{generate_random_digits(8)}"
                else: num = f"+447{random.choice(['700', '800', '900'])}{generate_random_digits(6)}"
            return {"raw_number": num, "country": country, "label_name": "LEGITIMATE", "label": 0, "risk_prob": random.uniform(0.01, 0.12)}

    classes = ["LEGITIMATE", "UNKNOWN", "SPAM", "SCAM"]
    train_samples = [create_sample(classes[i % len(classes)], is_test=False) for i in range(n_train)]
    test_samples = [create_sample(classes[i % len(classes)], is_test=True) for i in range(n_test)]
    random.shuffle(train_samples)
    random.shuffle(test_samples)

    with open(os.path.join(DATA_DIR, "train_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(train_samples, f, indent=2)
    with open(os.path.join(DATA_DIR, "test_prefix_holdout.json"), "w", encoding="utf-8") as f:
        json.dump(test_samples, f, indent=2)

    print(f"Generated train_dataset.json: {len(train_samples)} phone numbers")
    print(f"Generated test_prefix_holdout.json: {len(test_samples)} phone numbers")

if __name__ == "__main__":
    build_datasets()