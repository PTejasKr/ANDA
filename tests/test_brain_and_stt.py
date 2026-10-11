"""
Unit Tests for Brain Service & STT Engine
Verifies multi-tier LLM Brain fallback and free Google Speech / GBoard STT service.
"""

import base64
import json
import pytest
from backend.worker.llm_brain import LLMBrain
from backend.worker.stt_service import STTService
from backend.worker.worker_api import app


@pytest.fixture
def test_client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_brain_status_offline_defaults():
    brain = LLMBrain(lm_studio_url="http://127.0.0.1:9999/v1", docker_ollama_url="http://127.0.0.1:9998")
    status = brain.get_brain_status()
    assert "active_provider" in status
    assert status["active_provider"] == "deterministic_semantic_router"
    assert status["lm_studio"]["available"] is False
    assert status["docker_ollama"]["available"] is False
    assert status["cloudflare_workers_ai"]["free_tier"] is True


def test_brain_deterministic_intent_routing():
    brain = LLMBrain()

    # Flash USB
    res = brain.parse_intent_and_execute("Flash Ubuntu ISO to USB drive E:")
    assert res["action"] == "flash_usb"
    assert res["plane"] == "ELEVATED_DAEMON"
    assert res["is_elevated"] is True
    assert res["drive"] == "E:"

    # OS Update
    res = brain.parse_intent_and_execute("Update system packages and patch security kernel")
    assert res["action"] == "os_update"
    assert res["plane"] == "ELEVATED_DAEMON"
    assert res["is_elevated"] is True

    # Excel Extraction
    res = brain.parse_intent_and_execute("Extract multimodal data into an excel spreadsheet")
    assert res["action"] == "extract_excel"
    assert res["plane"] == "WORKER_PLANE"
    assert res["is_elevated"] is False

    # File Staging
    res = brain.parse_intent_and_execute("Stage and sort all incoming documents in the ingest folder")
    assert res["action"] == "stage_files"
    assert res["plane"] == "WORKER_PLANE"

    # Memory Query
    res = brain.parse_intent_and_execute("Recall our past quarterly performance from vector memory")
    assert res["action"] == "query_memory"
    assert res["plane"] == "SHARED_MEMORY"

    # Web Research
    res = brain.parse_intent_and_execute("Search the internet for current weather patterns in Seattle")
    assert res["action"] == "web_research"
    assert res["plane"] == "WORKER_PLANE"


def test_brain_mock_llm_json_parsing(monkeypatch):
    brain = LLMBrain()

    mock_llm_output = json.dumps({
        "action": "flash_usb",
        "plane": "ELEVATED_DAEMON",
        "drive": "F:",
        "rationale": "High-risk raw device block write requires elevation token and HITL"
    })

    # Mock _query_lm_studio to return valid JSON
    monkeypatch.setattr(brain, "_query_lm_studio", lambda p, s: mock_llm_output)

    res = brain.parse_intent_and_execute("Flash installer on drive F:")
    assert res["source"] == "lm_studio_gemma"
    assert res["action"] == "flash_usb"
    assert res["plane"] == "ELEVATED_DAEMON"
    assert res["drive"] == "F:"
    assert res["is_elevated"] is True


def test_stt_empty_and_invalid_payloads():
    stt = STTService()

    # Empty payload
    res = stt.transcribe_audio_bytes(b"")
    assert res["text"] == ""
    assert res["engine"] == "none"

    # Invalid base64
    res = stt.transcribe_base64("not-valid-base64-!!!")
    assert res["success"] is False
    assert "error" in res


def test_stt_transcribe_base64_fallback():
    stt = STTService()
    # Dummy PCM bytes
    dummy_audio = b"RIFF" + b"\x00" * 40
    dummy_b64 = base64.b64encode(dummy_audio).decode("utf-8")

    res = stt.transcribe_base64(dummy_b64)
    assert res["success"] is True
    assert len(res["text"]) > 0


def test_worker_api_brain_and_stt_endpoints(test_client):
    # Test Brain Status
    resp = test_client.get("/api/brain/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "active_provider" in data

    # Test Brain Parse
    resp = test_client.post("/api/brain/parse", json={"prompt": "Flash ISO to USB drive E:"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["action"] == "flash_usb"
    assert data["plane"] == "ELEVATED_DAEMON"

    # Test STT Transcribe with valid b64
    dummy_b64 = base64.b64encode(b"RIFF" + b"\x00" * 40).decode("utf-8")
    resp = test_client.post("/api/stt/transcribe", json={"audio_b64": dummy_b64})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True

    # Test STT Transcribe with missing b64
    resp = test_client.post("/api/stt/transcribe", json={})
    assert resp.status_code == 400
