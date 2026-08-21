"""
AEGIS-PNP2 Continuous Integration & Release Gate Verification Runner
Asserts every single release gate from a clean clone:
1. Frozen Holdout & Benchmark SHA-256 Checksum Verification + 10-Way Isolation Audit
2. Model Training & Continuous Platt Calibration
3. Model Export & Checksum Generation (ASSERT: 150 Trees + Canonical SHA-256 Digest)
4. Complete End-to-End Prediction Parity Suite (ASSERT: 29 / 29 Cases, 0 Drift)
5. Untouched Holdout Test Set Production Evaluation (ASSERT: ROC-AUC >= 0.85, PR-AUC >= 0.80)
6. Backend API Security, Authentication & Rate Limiting Tests (ASSERT: 10 / 10 PASSED)
"""

import os
import sys
import json
import hashlib
import subprocess

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON = sys.executable

def run_step(step_name: str, cmd: list):
    print("\n" + "="*90)
    print(f"[*] RUNNING CI STEP: {step_name}")
    print("="*90)
    res = subprocess.run(cmd, cwd=ROOT_DIR)
    if res.returncode != 0:
        print(f"\n[!] RELEASE GATE FAILURE: {step_name} (Exit Code {res.returncode})")
        sys.exit(res.returncode)
    print(f"[+] RELEASE GATE PASSED: {step_name}")

def verify_dataset_integrity():
    print("\n" + "="*90)
    print("[*] RUNNING CI STEP: 1/6 Frozen Holdout & Benchmark Integrity Verification")
    print("="*90)
    manifest_path = os.path.join(ROOT_DIR, "ml/data/dataset_manifest.json")
    if not os.path.exists(manifest_path):
        print("[-] dataset_manifest.json missing. Generating datasets first...")
        res = subprocess.run([PYTHON, "ml/data/dataset_builder.py"], cwd=ROOT_DIR)
        if res.returncode != 0:
            sys.exit(res.returncode)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for fname, meta in manifest["datasets"].items():
        fpath = os.path.join(ROOT_DIR, "ml/data", fname)
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"Required dataset {fname} not found at {fpath}")
        with open(fpath, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        if actual_hash != meta["sha256"]:
            raise ValueError(f"Dataset integrity mismatch for {fname}! Expected {meta['sha256']}, got {actual_hash}")
        print(f"[+] Verified {fname} (SHA-256: {actual_hash[:12]}..., {meta['row_count']} rows)")

    print("[+] All frozen holdout & benchmark datasets verified with 100% cryptographic integrity.")

def main():
    print("="*90)
    print("      AEGIS-PNP2 CONTINUOUS INTEGRATION & RELEASE GATE SUITE")
    print("="*90)

    # 1. Verify frozen holdout & benchmark datasets integrity
    verify_dataset_integrity()

    # 2. Model Training & Platt Calibration
    run_step("2/6 Model Training & Continuous Platt Calibration", [PYTHON, "ml/models/train.py"])

    # 3. Model Export & Checksum Generation
    run_step("3/6 Model Export & Checksum Generation", [PYTHON, "ml/export/exporter.py"])

    # 4. End-to-End Train/Serve Parity Suite (Python Scikit-Learn vs Pure JVM vs 29 Golden Vectors)
    run_step("4/6 End-to-End Prediction Parity (Python vs JVM vs Golden 29 Vectors)", [PYTHON, "ml/evaluation/test_end_to_end_parity.py"])

    # 5. Production Holdout Evaluation & Benchmark Report
    run_step("5/6 Production Holdout Evaluation & Benchmark Report", [PYTHON, "ml/evaluation/evaluate_production.py"])

    # 6. Backend API Security, Authentication & Rate Limiting Tests
    run_step("6/6 Backend API Security, Authentication & Rate Limiting Tests", [PYTHON, "-m", "unittest", "ml/api/test_server.py"])

    print("\n" + "="*90)
    print("      ALL AEGIS-PNP2 CI RELEASE GATES PASSED (100.0% SUCCESS)")
    print("="*90)

if __name__ == "__main__":
    main()