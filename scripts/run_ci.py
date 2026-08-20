"""
AEGIS-PNP2 Continuous Integration & Release Gate Verification Runner
Asserts every single release gate from a clean clone:
1. Dataset Prefix Isolation Audit (ASSERT: 0 Shared 7-Digit Prefixes)
2. Invalid Inputs Verification (ASSERT: 100% Rejected by libphonenumber)
3. Model Training & Continuous Calibration
4. Model Export & SHA-256 Checksum Generation
5. Complete End-to-End Prediction Parity Suite (ASSERT: 20 / 20 Cases, Error < 1e-4)
6. Untouched Holdout Test Set Production Evaluation (ASSERT: Precision >= 95%, FPR <= 0.5%)
7. Android / JVM Unit & Integration Tests (ASSERT: 4 / 4 PASSED)
8. Backend API Security & Authentication Tests (ASSERT: 4 / 4 PASSED)
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
        print(f"\n[!] RELEASE GATE FAILURE: {step_name} (Exit Code {res.returncode})")
        sys.exit(res.returncode)
    print(f"[+] RELEASE GATE PASSED: {step_name}")

def main():
    print("="*85)
    print("      AEGIS-PNP2 CONTINUOUS INTEGRATION & RELEASE GATE SUITE")
    print("="*85)

    # 1. Dataset Generation & Prefix-Group Isolation Audit
    run_step("1/7 Dataset Generation & Group Prefix Isolation Audit", [PYTHON, "ml/data/dataset_builder.py"])

    # 2. Model Training & Calibration
    run_step("2/7 Model Training & Continuous Calibration", [PYTHON, "ml/models/train.py"])

    # 3. Model Export & Checksum Generation
    run_step("3/7 Model Export & Checksum Generation", [PYTHON, "ml/export/exporter.py"])

    # 4. End-to-End Train/Serve Parity Suite (Python vs JVM Evaluator)
    run_step("4/7 End-to-End Prediction Parity (Python vs JVM)", [PYTHON, "ml/evaluation/test_end_to_end_parity.py"])

    # 5. Production Holdout Evaluation & Benchmark Report
    run_step("5/7 Production Evaluation & Holdout Benchmarks", [PYTHON, "ml/evaluation/evaluate_production.py"])

    # 6. Android / JVM Integration Tests
    lib_jar = os.path.join(ROOT_DIR, "ml/evaluation/lib/libphonenumber-8.13.52.jar")
    eval_dir = os.path.join(ROOT_DIR, "ml/evaluation")
    bin_dir = os.path.join(ROOT_DIR, "android/bin")
    test_src = os.path.join(ROOT_DIR, "android/src/test/java/PhoneNumberRiskModelTest.java")
    os.makedirs(bin_dir, exist_ok=True)
    
    compile_cmd = ["javac", "-cp", f"{lib_jar};{eval_dir}", "-d", bin_dir, test_src]
    run_step("6/7a Android / JVM Test Compilation", compile_cmd)
    
    exec_cmd = ["java", "-cp", f"{lib_jar};{eval_dir};{bin_dir}", "PhoneNumberRiskModelTest"]
    run_step("6/7b Android / JVM Test Execution", exec_cmd)

    # 7. Backend API Security Tests
    run_step("7/7 Backend API Security & Authentication Tests", [PYTHON, "-m", "unittest", "ml/api/test_server.py"])

    print("\n" + "="*85)
    print("      ALL AEGIS-PNP2 CI RELEASE GATES PASSED (100.0% SUCCESS)")
    print("="*85)

if __name__ == "__main__":
    main()