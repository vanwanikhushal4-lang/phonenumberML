"""
AEGIS-PNP2 Continuous Integration & Release Gate Verification Runner
Runs complete end-to-end audit and test pipeline:
1. Dataset Prefix Isolation Audit (0 Shared Prefix Clusters)
2. Invalid Inputs Verification (100% Rejected by libphonenumber)
3. Model Training & Platt Sigmoid Calibration
4. JSON Model Export with SHA-256 Checksum Verification
5. End-to-End Prediction Parity Suite (20 / 20 Cases, Error < 1e-4)
6. Untouched Holdout Test Set Production Evaluation
7. Backend Security & Authentication Tests (FastAPI / IPQS Proxy)
"""

import os
import sys
import subprocess

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYTHON = sys.executable

def run_step(step_name: str, cmd: list):
    print("\n" + "="*85)
    print(f"[*] RUNNING CI STEP: {step_name}")
    print("="*85)
    res = subprocess.run(cmd, cwd=ROOT_DIR)
    if res.returncode != 0:
        print(f"\n[!] CI STEP FAILED: {step_name} (Exit Code {res.returncode})")
        sys.exit(res.returncode)
    print(f"[+] CI STEP PASSED: {step_name}")

def main():
    print("="*85)
    print("      AEGIS-PNP2 CONTINUOUS INTEGRATION & RELEASE GATE SUITE")
    print("="*85)

    # 1. Dataset Generation & Prefix-Group Isolation Audit
    run_step("Dataset Generation & Prefix Isolation", [PYTHON, "ml/data/dataset_builder.py"])

    # 2. Model Training & Sigmoid Calibration
    run_step("Model Training & Sigmoid Calibration", [PYTHON, "ml/models/train.py"])

    # 3. Model Export & Golden Suite Generation
    run_step("Model Export & Checksum Generation", [PYTHON, "ml/export/exporter.py"])

    # 4. End-to-End Train/Serve Parity Suite
    run_step("End-to-End Prediction Parity (Python vs JVM)", [PYTHON, "ml/evaluation/test_end_to_end_parity.py"])

    # 5. Production Holdout Evaluation & Benchmark Report
    run_step("Production Evaluation & Dynamic Report", [PYTHON, "ml/evaluation/evaluate_production.py"])

    # 6. Backend API Security Tests
    run_step("Backend API Security & Authentication Tests", [PYTHON, "-m", "unittest", "ml/api/test_server.py"])

    print("\n" + "="*85)
    print("      ALL AEGIS-PNP2 CI RELEASE GATES PASSED (100.0% SUCCESS)")
    print("="*85)

if __name__ == "__main__":
    main()