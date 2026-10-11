"""
Test Case 4: Malware Quarantine Mock Tests
Action: Worker downloads the standard EICAR anti-virus test file.
Expected Result: File is locked in the quarantine directory.
System Daemon identifies the signature, blocks execution, and alerts the Orchestrator.
"""

import json
import os
import pytest
from backend.worker.security_scanner import SecurityScanner


def test_eicar_quarantine_isolation(tmp_path):
    storage_base = tmp_path / "quarantine_test"
    scanner = SecurityScanner(base_storage_dir=str(storage_base))

    # Standard EICAR string
    eicar_content = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

    # Step 1: Simulate Worker downloading EICAR file into the untrusted sandbox
    download_path = os.path.join(scanner.sandbox_dir, "downloaded_sample_payload.bin")
    with open(download_path, "wb") as f:
        f.write(eicar_content)

    assert os.path.exists(download_path)

    # Step 2: Security scanner evaluates the downloaded file
    scan_result = scanner.scan_file_for_malware(download_path)

    # Step 3: Assert execution is blocked and signature identified
    assert scan_result["is_malicious"] is True
    assert "EICAR" in scan_result["signature"]
    assert scan_result["action_taken"] == "ISOLATED_AND_LOCKED"

    # Step 4: Verify original file was removed from sandbox and safely locked
    assert not os.path.exists(download_path)
    locked_path = scan_result["locked_path"]
    assert os.path.exists(locked_path)
    assert os.path.dirname(locked_path) == str(scanner.locked_dir)

    # Step 5: Verify forensic quarantine metadata was generated for Orchestrator alert
    meta_path = locked_path + ".meta.json"
    assert os.path.exists(meta_path)
    with open(meta_path, "r", encoding="utf-8") as mf:
        meta = json.load(mf)
    assert meta["status"] == "QUARANTINED_LOCKED"
    assert meta["original_filename"] == "downloaded_sample_payload.bin"
    assert meta["sha256"] == scan_result["sha256"]


def test_clean_file_sandbox_permissions(tmp_path):
    storage_base = tmp_path / "quarantine_test"
    scanner = SecurityScanner(base_storage_dir=str(storage_base))

    clean_content = b"Report data: all metrics operational"
    clean_path = os.path.join(scanner.sandbox_dir, "clean_document.txt")
    with open(clean_path, "wb") as f:
        f.write(clean_content)

    scan_result = scanner.scan_file_for_malware(clean_path)
    assert scan_result["is_malicious"] is False
    assert scan_result["action_taken"] == "PERMITTED_IN_SANDBOX"
    assert os.path.exists(clean_path)
