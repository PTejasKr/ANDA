"""
Deterministic Execution Script: Run All Dual-Plane Verification Tests
Executes Pytest suite and Go backend tests, asserting 100% pass rate.
"""

import subprocess
import sys
import time


def run_command(cmd, name):
    print(f"\n{'='*70}")
    print(f"[*] Running: {name}")
    print(f"[*] Command: {' '.join(cmd)}")
    print(f"{'='*70}")
    import os
    env = os.environ.copy()
    if sys.platform == "win32":
        os.makedirs("d:\\tmp", exist_ok=True)
        env["GOTMPDIR"] = "d:\\tmp"
        env["TEMP"] = "d:\\tmp"
        env["TMP"] = "d:\\tmp"
    start = time.perf_counter()
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    elapsed = time.perf_counter() - start

    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)

    if res.returncode != 0:
        print(f"[FAIL] {name} failed with exit code {res.returncode} ({elapsed:.2f}s)")
        return False, elapsed
    else:
        print(f"[PASS] {name} succeeded ({elapsed:.2f}s)")
        return True, elapsed


def main():
    print("\n" + "#"*70)
    print("# OMNI-OPERATOR OS AGENT: DUAL-PLANE AUTOMATED TEST SUITE")
    print("#"*70)

    results = []

    # 1. Python Pytest Suite
    ok, elapsed = run_command([sys.executable, "-m", "pytest", "-v", "tests/"], "Python Worker & Security Tests")
    results.append(("Python Worker & Security Test Suite", ok, elapsed))

    # 2. Go Backend Tests
    ok, elapsed = run_command(["go", "test", "-v", "./backend/..."], "Go Orchestrator & Daemon IPC Security Tests")
    results.append(("Go Orchestrator & Daemon IPC Suite", ok, elapsed))

    # Summary
    print("\n" + "="*70)
    print("FINAL TEST RUNNER SUMMARY")
    print("="*70)
    all_passed = True
    for suite, passed, sec in results:
        status = "PASSED" if passed else "FAILED"
        print(f" - {suite:<45}: [{status}] ({sec:.2f}s)")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n>>> ALL TEST BENCHES AND SECURITY REQUIREMENTS VERIFIED (100% PASS) <<<\n")
        return 0
    else:
        print("\n>>> SOME TEST SUITES FAILED <<<\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
