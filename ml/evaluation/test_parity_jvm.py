"""
AEGIS Train / Serve Parity Verification Suite
Executes the compiled JVM Java extractor on real phone numbers and diffs against Python extractor.
"""

import os
import sys
import json
import subprocess
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from ml.features.extractor import extract_features_from_number, FEATURE_SPEC

EVAL_DIR = os.path.dirname(__file__)

def compile_java():
    print("Compiling JvmPhoneNumberExtractor.java...")
    cmd = ["javac", "-d", EVAL_DIR, os.path.join(EVAL_DIR, "JvmPhoneNumberExtractor.java")]
    subprocess.run(cmd, check=True)
    print("Java compilation successful.")

def extract_via_jvm(raw_number: str, country: str) -> np.ndarray:
    cmd = ["java", "-cp", EVAL_DIR, "JvmPhoneNumberExtractor", raw_number, country]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = res.stdout.strip()
    raw_vec = json.loads(out)
    return np.array(raw_vec, dtype=np.float32)

def verify_parity():
    print("="*80)
    print("AEGIS TRAIN / SERVE PARITY VERIFICATION (Phone Number Pattern Model)")
    print("  [Python (Training Extractor)] vs [JVM (Java 17 / Kotlin-equivalent)]")
    print("="*80)

    compile_java()

    test_numbers = [
        ("+911800112211", "IN", "SBI Bank Customer Care (Hard Negative)"),
        ("+911409988776", "IN", "TRAI 140-series Telemarketing Dialer"),
        ("+881631555123", "IN", "Wangiri Satellite Callback Trap"),
        ("+18009359935",  "US", "Chase Bank Customer Support (Hard Negative)"),
        ("+919820481729", "IN", "Standard Indian Mobile Line"),
        ("112",           "IN", "Emergency Line 112"),
        ("+18445551212",  "US", "US Toll-free Marketing Dialer"),
        ("+25270112233",  "IN", "Wangiri High-Cost Africa Trap")
    ]

    total_checks = 0
    passed_checks = 0

    for num, country, label in test_numbers:
        v_py = extract_features_from_number(num, country)
        v_jvm = extract_via_jvm(num, country)

        diff = np.abs(v_py - v_jvm)
        max_diff = float(np.max(diff))
        is_parity = (max_diff < 1e-3)

        total_checks += 1
        if is_parity: passed_checks += 1

        status = "[PARITY OK]" if is_parity else f"[DIFF ERROR - Max Diff {max_diff:.5f}]"
        print(f"[{label}] {num:<16} | Max Diff: {max_diff:.6f} | {status}")

    print("-" * 80)
    print(f"Train / Serve Parity Result: {passed_checks} / {total_checks} PASSED ({passed_checks/total_checks*100:.1f}%)")
    return passed_checks == total_checks

if __name__ == "__main__":
    success = verify_parity()
    if not success: sys.exit(1)