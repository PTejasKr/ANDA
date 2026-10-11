"""
Unit & Integration Tests: Machine Learning Validation & Hallucination Mitigation
Verifies all 5 checks specified in machine_learning_validation_checks.md:
1. Supervised 'Golden Dataset' Verification (500+ test cases, threshold rejection)
2. Strict RAG Grounding & Citation Validation (anti-hallucination cross-referencing)
3. Constrained Decoding for IPC Actions (grammar-constrained JSON schema validation)
4. Visual-Semantic Consistency Loop (target crop contrast check & ambiguity fallback)
5. Token Confidence Thresholding (log-probability evaluation & automatic HITL escalation)
"""

import math
import os
import pytest
from PIL import Image, ImageDraw

from backend.worker.ml_validator import (
    GoldenDatasetVerifier,
    RAGGroundingValidator,
    ConstrainedIPCDecoder,
    VisualSemanticConsistencyVerifier,
    TokenConfidenceThreshold,
    ConstrainedDecodingError,
    BuildRejectedError,
)


# =========================================================================
# Check 1: Supervised "Golden Dataset" Verification
# =========================================================================

def test_golden_dataset_creation_and_count(tmp_path):
    dataset_file = str(tmp_path / "golden_500.json")
    verifier = GoldenDatasetVerifier(dataset_path=dataset_file)

    assert os.path.exists(dataset_file)
    assert len(verifier.cases) >= 500

    # Ensure distribution of test cases
    extract_cases = [c for c in verifier.cases if c["type"] == "data_extraction"]
    ipc_cases = [c for c in verifier.cases if c["type"] == "ipc_token"]

    assert len(extract_cases) >= 250
    assert len(ipc_cases) >= 250


def test_golden_dataset_verification_passed(tmp_path):
    dataset_file = str(tmp_path / "golden_test_pass.json")
    verifier = GoldenDatasetVerifier(dataset_path=dataset_file)

    # Simulate model predictions with 99% accuracy
    predictions = []
    for idx, case in enumerate(verifier.cases):
        pred_output = dict(case["expected_output"])
        # Inject deliberate tiny error into 2 cases out of 500 (99.6% accuracy)
        if idx == 10:
            pred_output["vendor"] = "Wrong Vendor"
        predictions.append({
            "case_id": case["case_id"],
            "output": pred_output,
        })

    report = verifier.verify_pipeline(
        predictions=predictions,
        threshold_extraction=0.95,
        threshold_ipc=0.98,
    )

    assert report["passed"] is True
    assert report["data_extraction"]["accuracy"] >= 0.95
    assert report["ipc_token"]["accuracy"] >= 0.98
    assert len(report["rejection_reasons"]) == 0


def test_golden_dataset_verification_threshold_rejection(tmp_path):
    dataset_file = str(tmp_path / "golden_test_fail.json")
    verifier = GoldenDatasetVerifier(dataset_path=dataset_file)

    # Degraded model with 85% accuracy (below 95% threshold)
    predictions = []
    for idx, case in enumerate(verifier.cases):
        pred_output = dict(case["expected_output"])
        if idx % 5 == 0:  # Corrupt 20% of cases
            if case["type"] == "data_extraction":
                pred_output["total_cost"] = -999.0
            else:
                pred_output["action"] = "unauthorized_action"
        predictions.append({
            "case_id": case["case_id"],
            "output": pred_output,
        })

    report = verifier.verify_pipeline(
        predictions=predictions,
        threshold_extraction=0.95,
        threshold_ipc=0.98,
    )

    assert report["passed"] is False
    assert report["data_extraction"]["met"] is False
    assert len(report["rejection_reasons"]) > 0


# =========================================================================
# Check 2: Strict RAG Grounding & Citation
# =========================================================================

def test_rag_grounding_valid_and_hallucination_detection():
    validator = RAGGroundingValidator()

    retrieved_chunks = [
        {
            "chunk_id": "chunk_invoice_01",
            "text": "Invoice #4092 from Acme Logistics Corp. Line item: Enterprise Server Rack. Qty: 3. Price: $1499.50. Total: $4498.50. Paid via ACH.",
        },
        {
            "chunk_id": "chunk_memo_02",
            "text": "Internal memo: Office supplies ordered from Staples Inc for $120.00.",
        },
    ]

    # Candidate extracted records from LLM:
    # 1. Grounded record
    # 2. Hallucinated record with fabricated vendor and price
    records = [
        {
            "citation_chunk_id": "chunk_invoice_01",
            "vendor": "Acme Logistics Corp",
            "item": "Enterprise Server Rack",
            "quantity": 3,
            "unit_price": 1499.50,
            "total": 4498.50,
        },
        {
            "citation_chunk_id": "chunk_invoice_01",
            "vendor": "Fabricated Ghost Vendor LLC",
            "item": "Quantum Quantum Processor",
            "quantity": 99,
            "unit_price": 8888.88,
        },
    ]

    result = validator.validate_and_filter(records, retrieved_chunks)

    assert result["total_records"] == 2
    assert result["retained_count"] == 1
    assert result["discarded_count"] == 1
    assert result["is_valid"] is False

    # Check that grounded record was kept
    clean = result["clean_records"][0]
    assert clean["vendor"] == "Acme Logistics Corp"
    assert clean["grounded"] is True

    # Check that hallucinated record was identified and discarded
    hallucination = result["hallucinations"][0]
    assert hallucination["action"] == "DISCARDED_AS_HALLUCINATION"
    flagged_fields = [f["field"] for f in hallucination["flagged_fields"]]
    assert "vendor" in flagged_fields
    assert "unit_price" in flagged_fields


# =========================================================================
# Check 3: Constrained Decoding for IPC Actions
# =========================================================================

def test_constrained_ipc_decoder_valid_payload():
    decoder = ConstrainedIPCDecoder()

    valid_payload = {
        "action": "flash_usb",
        "drive": "E:",
        "hash": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        "token_id": "cap-valid-449",
        "params": {"source": "recovery_image.iso"},
    }

    result = decoder.validate_ipc_payload(valid_payload)
    assert result["valid"] is True
    assert result["action"] == "flash_usb"
    assert result["token_id"] == "cap-valid-449"


def test_constrained_ipc_decoder_rejects_extraneous_keys():
    decoder = ConstrainedIPCDecoder()

    # Adversarial injection attempting to slip raw shell commands
    poisoned_payload = {
        "action": "flash_usb",
        "token_id": "cap-evil-1",
        "drive": "E:",
        "shell_cmd": "rmdir /s /q C:\\",  # Extraneous key
        "exec_mode": "bypass",            # Extraneous key
    }

    with pytest.raises(ConstrainedDecodingError) as exc_info:
        decoder.validate_ipc_payload(poisoned_payload)

    assert "Extraneous or hallucinated keys detected" in str(exc_info.value)


def test_constrained_ipc_decoder_rejects_invalid_action():
    decoder = ConstrainedIPCDecoder()

    invalid_action = {
        "action": "drop_production_database",
        "token_id": "cap-bad-act",
    }

    with pytest.raises(ConstrainedDecodingError) as exc_info:
        decoder.validate_ipc_payload(invalid_action)

    assert "not in allowed capability grammar" in str(exc_info.value)


# =========================================================================
# Check 4: Visual-Semantic Consistency Loop
# =========================================================================

def test_visual_semantic_consistency_active_element(tmp_path):
    verifier = VisualSemanticConsistencyVerifier()

    # Create mock screenshot image with a button drawn at (400, 300)
    img_path = str(tmp_path / "mock_ui.png")
    img = Image.new("RGB", (800, 600), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    # Draw button with high contrast
    draw.rectangle([360, 280, 440, 320], fill=(14, 165, 233), outline=(2, 132, 199), width=2)
    draw.text((375, 292), "SUBMIT", fill=(255, 255, 255))
    img.save(img_path)

    # Click on the button
    result = verifier.verify_click_target(
        image_input=img_path,
        target_coords=(400, 300),
        expected_intent="submit_button",
    )

    assert result["is_consistent"] is True
    assert result["trigger_ambiguity_fallback"] is False


def test_visual_semantic_consistency_empty_whitespace_halts(tmp_path):
    verifier = VisualSemanticConsistencyVerifier()

    # Image with button elsewhere, but target coordinates point to blank white area
    img_path = str(tmp_path / "mock_ui_white.png")
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    img.save(img_path)

    # Click coordinate (100, 100) is pure blank whitespace
    result = verifier.verify_click_target(
        image_input=img_path,
        target_coords=(100, 100),
        expected_intent="submit_button",
    )

    # Must halt execution and trigger Ambiguity Fallback UI
    assert result["is_consistent"] is False
    assert result["trigger_ambiguity_fallback"] is True
    assert "whitespace" in result["reason"].lower()


# =========================================================================
# Check 5: Token Confidence Thresholding
# =========================================================================

def test_token_confidence_threshold_high_confidence():
    evaluator = TokenConfidenceThreshold()

    # Model tool-call parameters with high confidence (mean = 0.95)
    token_scores = [0.98, 0.96, 0.94, 0.92, 0.95]
    res = evaluator.evaluate_confidence(token_scores, safety_threshold=0.90)

    assert res["meets_safety_threshold"] is True
    assert res["trigger_hitl"] is False
    assert res["average_confidence"] == 0.95


def test_token_confidence_threshold_low_confidence_triggers_hitl():
    evaluator = TokenConfidenceThreshold()

    # Model parameters generated with lower confidence (mean = 0.81 < 0.90)
    token_scores = [0.85, 0.78, 0.82, 0.80, 0.80]
    res = evaluator.evaluate_confidence(token_scores, safety_threshold=0.90)

    # Must automatically trigger Human-In-The-Loop confirmation
    assert res["meets_safety_threshold"] is False
    assert res["trigger_hitl"] is True
    assert res["average_confidence"] < 0.90
    assert "Escalating to Human-In-The-Loop" in res["reason"]


def test_token_confidence_threshold_from_log_probabilities():
    evaluator = TokenConfidenceThreshold()

    # Log probabilities: exp(-0.02) ≈ 0.98, exp(-0.05) ≈ 0.95
    log_probs = [-0.02, -0.05, -0.03]
    res = evaluator.evaluate_confidence(log_probs, safety_threshold=0.90, is_log_prob=True)

    assert res["meets_safety_threshold"] is True
    assert res["trigger_hitl"] is False
    assert res["average_confidence"] > 0.90
