"""
Worker API Service (Subsystem A, C, D)
Exposes unprivileged worker capabilities via REST API for Go Orchestrator and Frontend.
Includes sliding-window rate limiters, payload size constraints, and performance boundaries.
"""

from __future__ import annotations
import os
import sys
import time
from collections import defaultdict
from functools import wraps
from flask import Flask, request, jsonify

# Add worker directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_extractor import DataExtractor
from file_stager import FileStager
from vector_memory import VectorMemory
from security_scanner import SecurityScanner
from llm_brain import LLMBrain
from stt_service import STTService
from ml_validator import (
    GoldenDatasetVerifier,
    RAGGroundingValidator,
    ConstrainedIPCDecoder,
    VisualSemanticConsistencyVerifier,
    TokenConfidenceThreshold,
    ConstrainedDecodingError,
)

app = Flask(__name__)
# Performance constraint: Max 15MB total request payload
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

class WorkerRateLimiter:
    """Sliding-window rate limiter per client IP."""
    def __init__(self, limit_per_minute: int = 60):
        self.limit = limit_per_minute
        self.window = 60.0
        self.requests = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        timestamps = self.requests[client_ip]
        self.requests[client_ip] = [t for t in timestamps if now - t < self.window]
        if len(self.requests[client_ip]) >= self.limit:
            return False
        self.requests[client_ip].append(now)
        return True

heavy_limiter = WorkerRateLimiter(limit_per_minute=30)
general_limiter = WorkerRateLimiter(limit_per_minute=120)

def get_client_ip() -> str:
    if request.headers.get("X-Forwarded-For"):
        return request.headers["X-Forwarded-For"].split(",")[0].strip()
    if request.headers.get("X-Real-IP"):
        return request.headers["X-Real-IP"].strip()
    return request.remote_addr or "127.0.0.1"

def rate_limit(limiter: WorkerRateLimiter):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if app.config.get("TESTING"):
                return f(*args, **kwargs)
            ip = get_client_ip()
            if not limiter.is_allowed(ip):
                return jsonify({
                    "error": "Rate limit exceeded. Bounded compute threshold reached.",
                    "status": 429,
                    "retry_after_seconds": 30,
                }), 429, {"Retry-After": "30"}
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "error": "Payload exceeds maximum allowable size (15MB)",
        "status": 413,
    }), 413

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    return response

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return app.response_class(status=200)

extractor = DataExtractor()
stager = FileStager()
memory = VectorMemory()
scanner = SecurityScanner()
golden_verifier = GoldenDatasetVerifier()
rag_validator = RAGGroundingValidator()
ipc_decoder = ConstrainedIPCDecoder()
visual_verifier = VisualSemanticConsistencyVerifier()
confidence_evaluator = TokenConfidenceThreshold()
brain = LLMBrain()
stt = STTService()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "plane": "unprivileged_worker",
        "documents_in_memory": len(memory.documents),
        "brain": brain.get_brain_status()["active_provider"],
    })


@app.route("/api/extract", methods=["POST"])
@rate_limit(heavy_limiter)
def extract_excel():
    data = request.get_json(force=True)
    records = data.get("records", [])
    filename = data.get("filename", "extracted_report.xlsx")
    report_title = data.get("report_title", "Multimodal Synthesis Report")

    if not records:
        return jsonify({"error": "No records provided"}), 400

    if len(records) > 1000:
        return jsonify({
            "error": "Batch size exceeds maximum allowable limit of 1000 records",
            "status": 400,
        }), 400

    try:
        path = extractor.extract_to_excel(records, filename, report_title=report_title)
        # Also index synthesized records into vector memory
        memory.index_spreadsheet_rows(doc_id=filename, rows=records, metadata={"source_file": filename})
        return jsonify({
            "status": "success",
            "file_path": path,
            "filename": os.path.basename(path),
            "rows_extracted": len(records),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stage", methods=["POST"])
@rate_limit(heavy_limiter)
def stage_files():
    try:
        results = stager.process_ingest_directory()
        return jsonify({"status": "success", "staged_count": len(results), "files": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stage_file", methods=["POST"])
@rate_limit(heavy_limiter)
def stage_single_file():
    data = request.get_json(force=True)
    src_path = data.get("file_path")
    if not src_path or not os.path.exists(src_path):
        return jsonify({"error": f"File {src_path} not found"}), 400
    try:
        res = stager.stage_file(src_path)
        return jsonify({"status": "success", "file": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/memory/index", methods=["POST"])
@rate_limit(general_limiter)
def memory_index():
    data = request.get_json(force=True)
    doc_id = data.get("doc_id", "doc_generic")
    content = data.get("content", "")
    metadata = data.get("metadata", {})

    if not content:
        return jsonify({"error": "No content provided"}), 400

    if len(content) > 500_000:
        return jsonify({
            "error": "Document length exceeds maximum allowable limit of 500KB",
            "status": 400,
        }), 400

    count = memory.add_document(doc_id, content, metadata=metadata)
    return jsonify({"status": "success", "doc_id": doc_id, "chunks_indexed": count})


@app.route("/api/memory/query", methods=["POST"])
@rate_limit(heavy_limiter)
def memory_query():
    data = request.get_json(force=True)
    query_text = data.get("query", "")
    # Bound top_k between 1 and 20 to constrain compute and prevent memory bloat
    raw_k = int(data.get("top_k", 5))
    top_k = max(1, min(raw_k, 20))

    if not query_text:
        return jsonify({"error": "Query cannot be empty"}), 400

    results = memory.query(query_text, top_k=top_k)
    return jsonify({"status": "success", "query": query_text, "results": results})


@app.route("/api/security/scan_prompt", methods=["POST"])
@rate_limit(general_limiter)
def scan_prompt():
    data = request.get_json(force=True)
    text = data.get("text", "")
    if len(text) > 20_000:
        return jsonify({"error": "Text exceeds maximum 20000 characters limit"}), 400
    res = scanner.scan_prompt(text)
    return jsonify(res)


@app.route("/api/security/scan_file", methods=["POST"])
@rate_limit(general_limiter)
def scan_file():
    data = request.get_json(force=True)
    file_path = data.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Valid file_path is required"}), 400
    try:
        res = scanner.scan_file_for_malware(file_path)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ml/verify_golden", methods=["POST"])
@rate_limit(general_limiter)
def verify_golden():
    data = request.get_json(force=True) if request.data else {}
    predictions = data.get("predictions", [])
    threshold_ext = float(data.get("threshold_extraction", 0.95))
    threshold_ipc = float(data.get("threshold_ipc", 0.98))
    report = golden_verifier.verify_pipeline(
        predictions=predictions,
        threshold_extraction=threshold_ext,
        threshold_ipc=threshold_ipc,
    )
    status_code = 200 if report["passed"] else 422
    return jsonify(report), status_code


@app.route("/api/ml/validate_rag", methods=["POST"])
@rate_limit(general_limiter)
def validate_rag():
    data = request.get_json(force=True)
    records = data.get("records", [])
    chunks = data.get("chunks", [])
    report = rag_validator.validate_and_filter(records, chunks)
    return jsonify(report)


@app.route("/api/ml/validate_ipc", methods=["POST"])
@rate_limit(general_limiter)
def validate_ipc():
    data = request.get_json(force=True)
    payload = data.get("payload", {})
    try:
        result = ipc_decoder.validate_ipc_payload(payload)
        return jsonify(result), 200
    except ConstrainedDecodingError as e:
        return jsonify({"valid": False, "error": str(e)}), 400


@app.route("/api/ml/verify_visual_intent", methods=["POST"])
@rate_limit(general_limiter)
def verify_visual_intent():
    data = request.get_json(force=True)
    image_path = data.get("image_path")
    coords = (int(data.get("x", 0)), int(data.get("y", 0)))
    expected_intent = data.get("expected_intent", "button")
    try:
        res = visual_verifier.verify_click_target(image_path, coords, expected_intent)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/ml/check_confidence", methods=["POST"])
@rate_limit(general_limiter)
def check_confidence():
    data = request.get_json(force=True)
    confidences = data.get("confidences", [])
    threshold = float(data.get("threshold", 0.90))
    is_log_prob = bool(data.get("is_log_prob", False))
    res = confidence_evaluator.evaluate_confidence(confidences, threshold, is_log_prob)
    return jsonify(res)


@app.route("/api/brain/status", methods=["GET"])
def brain_status():
    return jsonify(brain.get_brain_status())


@app.route("/api/brain/parse", methods=["POST"])
@rate_limit(heavy_limiter)
def brain_parse():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    rag_context = data.get("rag_context", "")
    if len(prompt) > 10_000:
        return jsonify({"error": "Prompt exceeds maximum 10000 characters limit"}), 400
    res = brain.parse_intent_and_execute(prompt, rag_context=rag_context)
    return jsonify(res)


@app.route("/api/stt/transcribe", methods=["POST"])
@rate_limit(heavy_limiter)
def stt_transcribe():
    data = request.get_json(force=True)
    audio_b64 = data.get("audio_b64", "")
    format_hint = data.get("format", "wav")
    if not audio_b64:
        return jsonify({"error": "No audio_b64 payload received", "success": False}), 400
    if len(audio_b64) > 15 * 1024 * 1024:
        return jsonify({"error": "Audio payload exceeds maximum allowable 15MB limit", "success": False}), 400
    res = stt.transcribe_base64(audio_b64, format_hint=format_hint)
    return jsonify(res)


if __name__ == "__main__":
    port = int(os.environ.get("WORKER_PORT", 50051))
    print(f"[*] Starting Python Worker Plane on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
