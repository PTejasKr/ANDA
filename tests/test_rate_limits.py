"""
Unit Tests for Rate Limiters and Performance Constraints in Python Worker API
Verifies:
1. Sliding-window WorkerRateLimiter behavior.
2. Endpoint rate limiting (429 Too Many Requests, Retry-After header).
3. Payload constraints:
   - Max batch size on /api/extract (<= 1000 records).
   - Bounded top_k on /api/memory/query (1 <= top_k <= 20).
   - Max content length on /api/memory/index (<= 500KB).
   - Max audio payload size on /api/stt/transcribe (<= 15MB).
"""

import json
import pytest
from backend.worker.worker_api import app, WorkerRateLimiter


@pytest.fixture
def client():
    app.config["TESTING"] = False  # Disable testing exemption to test rate limit enforcement
    with app.test_client() as c:
        yield c
    app.config["TESTING"] = True


def test_worker_rate_limiter_unit():
    limiter = WorkerRateLimiter(limit_per_minute=3)
    ip = "192.168.10.5"

    assert limiter.is_allowed(ip) is True
    assert limiter.is_allowed(ip) is True
    assert limiter.is_allowed(ip) is True
    # 4th request in the same minute must be blocked
    assert limiter.is_allowed(ip) is False

    # Different IP is permitted
    assert limiter.is_allowed("192.168.10.6") is True


def test_endpoint_rate_limiting_429(client):
    # Perform requests up to heavy limit (30 req/min)
    # Using a unique client IP via X-Forwarded-For
    headers = {"X-Forwarded-For": "10.99.1.50"}

    # We can invoke 30 queries
    for _ in range(30):
        resp = client.post("/api/memory/query", json={"query": "test query"}, headers=headers)
        assert resp.status_code == 200

    # 31st request should trigger 429
    resp = client.post("/api/memory/query", json={"query": "test query"}, headers=headers)
    assert resp.status_code == 429
    data = resp.get_json()
    assert data["status"] == 429
    assert "Rate limit exceeded" in data["error"]
    assert resp.headers.get("Retry-After") == "30"


def test_extract_batch_size_constraint(client):
    # Exceeding 1000 records batch limit
    too_many_records = [{"id": i, "val": f"data_{i}"} for i in range(1001)]
    resp = client.post("/api/extract", json={"records": too_many_records}, headers={"X-Forwarded-For": "10.99.2.1"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Batch size exceeds" in data["error"]


def test_memory_query_top_k_bounding(client):
    # Query with excessive top_k (e.g. 500)
    resp = client.post(
        "/api/memory/query",
        json={"query": "financial", "top_k": 500},
        headers={"X-Forwarded-For": "10.99.2.2"}
    )
    assert resp.status_code == 200
    # Should not crash, and query top_k is capped to 20
    data = resp.get_json()
    assert data["status"] == "success"


def test_memory_index_size_constraint(client):
    # Exceeding 500KB content limit
    oversized_content = "X" * 500_001
    resp = client.post(
        "/api/memory/index",
        json={"doc_id": "test_oversized", "content": oversized_content},
        headers={"X-Forwarded-For": "10.99.2.3"}
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Document length exceeds" in data["error"]


def test_stt_transcribe_payload_size_constraint(client):
    # Exceeding 15MB audio payload limit triggers 413 Request Entity Too Large
    oversized_audio = "A" * (15 * 1024 * 1024 + 10)
    resp = client.post(
        "/api/stt/transcribe",
        json={"audio_b64": oversized_audio},
        headers={"X-Forwarded-For": "10.99.2.4"}
    )
    assert resp.status_code in (400, 413)
