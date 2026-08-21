"""
AEGIS-PNP2 Continuous Integration & Release Gate Verification Runner
Asserts every single release gate from a clean clone:
1. Dataset Generation & 6-Way Group Prefix Isolation Audit (ASSERT: 0 Shared 7-Digit Prefixes)
2. Model Training & Continuous Platt Calibration (ASSERT: Brier Loss < 0.05)
3. Model Export & Checksum Generation (ASSERT: 150 Trees + Full IEEE-754 Precision)
4. Complete End-to-End Prediction Parity Suite (ASSERT: 20 / 20 Cases, 0 Drift)
5. Untouched Holdout Test Set Production Evaluation (ASSERT: Brier Loss < 0.05, ROC-AUC > 0.90)
6. Backend API Security, Authentication & Rate Limiting Tests (ASSERT: 7 / 7 PASSED)
"""

import os
import sys
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

def main():
    print("="*90)
    print("      AEGIS-PNP2 CONTINUOUS INTEGRATION & RELEASE GATE SUITE")
    print("="*90)

    # 1. Dataset Generation & Prefix-Group Isolation Audit
    run_step("1/6 Dataset Generation & 6-Way Group Prefix Isolation Audit", [PYTHON, "ml/data/dataset_builder.py"])

    # 2. Model Training & Platt Calibration
    run_step("2/6 Model Training & Continuous Platt Calibration", [PYTHON, "ml/models/train.py"])

    # 3. Model Export & Checksum Generation
    run_step("3/6 Model Export & Checksum Generation", [PYTHON, "ml/export/exporter.py"])

    # 4. End-to-End Train/Serve Parity Suite (Python Scikit-Learn vs Pure JVM vs Golden Vectors)
    run_step("4/6 End-to-End Prediction Parity (Python vs JVM vs Golden)", [PYTHON, "ml/evaluation/test_end_to_end_parity.py"])

    # 5. Production Holdout Evaluation & Benchmark Report
    run_step("5/6 Production Holdout Evaluation & Benchmark Report", [PYTHON, "ml/evaluation/evaluate_production.py"])

    # 6. Backend API Security, Authentication & Rate Limiting Tests
    run_step("6/6 Backend API Security, Authentication & Rate Limiting Tests", [PYTHON, "-m", "unittest", "ml/api/test_server.py"])

    print("\n" + "="*90)
    print("      ALL AEGIS-PNP2 CI RELEASE GATES PASSED (100.0% SUCCESS)")
    print("="*90)

if __name__ == "__main__":
    main()