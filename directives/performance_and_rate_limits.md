# Performance Constraints & Rate Limiting Standard Operating Procedure (SOP)

## 1. Objective
Establish deterministic rate limits, resource bounds, and payload quotas across both the Go Orchestrator and Python Worker Plane to prevent resource exhaustion, memory leaks, and Denial-of-Service attacks in both local and Fly.io microVM environments (1 shared CPU, 1GB RAM).

---

## 2. Rate Limiting Matrix

### Tier 1: Go Orchestrator (Client Gateway)
Implemented via thread-safe Token Bucket (`backend/orchestrator/ratelimit.go`) keyed by client IP (respecting `X-Forwarded-For` and `X-Real-IP`).

| Route | Method | Rate Limit | Burst Capacity | Exceeded Response |
| :--- | :--- | :--- | :--- | :--- |
| `/api/orchestrator/command` | POST | 20 req/min | 5 | `429 Too Many Requests` (`Retry-After: 30`) |
| `/api/stt/transcribe` | POST | 20 req/min | 5 | `429 Too Many Requests` (`Retry-After: 30`) |
| `/api/orchestrator/benchmark` | POST | 20 req/min | 5 | `429 Too Many Requests` (`Retry-After: 30`) |
| `/api/fs/list` | GET | 60 req/min | 15 | `429 Too Many Requests` (`Retry-After: 30`) |
| `/api/fs/read` | GET | 60 req/min | 15 | `429 Too Many Requests` (`Retry-After: 30`) |
| `/api/orchestrator/hitl/*` | GET/POST | 60 req/min | 15 | `429 Too Many Requests` (`Retry-After: 30`) |
| `/api/brain/status` | GET | 60 req/min | 15 | `429 Too Many Requests` (`Retry-After: 30`) |
| `/api/system/status` | GET | **Unthrottled** | Unlimited | Never throttled (Fly.io health check uptime probes) |

### Tier 2: Python Worker Plane (Compute Engine)
Implemented via sliding-window tracker (`backend/worker/worker_api.py`) per client IP.

| Endpoint Category | Limit | Rationale |
| :--- | :--- | :--- |
| **Heavy Compute** (`/api/extract`, `/api/stage`, `/api/memory/query`, `/api/brain/parse`, `/api/stt/transcribe`) | 30 req/min | Prevents CPU saturation during vector similarity search and Excel serialization |
| **General Metadata** (`/api/memory/index`, `/api/security/*`, `/api/ml/*`) | 120 req/min | Fast synchronous operations with minimal CPU footprint |
| **Automated Testing** (`TESTING=True`) | Exempt | Unconstrained execution during automated pytest and verify test runs |

---

## 3. Payload & Performance Constraints

### 3.1 Request Payload Limits
1. **Orchestrator JSON APIs**: Enforced via `http.MaxBytesReader` at **5 MB** (`5 * 1024 * 1024` bytes).
2. **Audio Transcription API**: Enforced via `http.MaxBytesReader` and Flask `MAX_CONTENT_LENGTH` at **15 MB** (`15 * 1024 * 1024` bytes).
3. **HITL Decision Payloads**: Enforced at **1 MB** (`1 * 1024 * 1024` bytes).
4. **Rejection Response**: Returns `413 Request Entity Too Large`:
   ```json
   {
     "status": 413,
     "error": "Payload exceeds maximum allowable size (15MB)"
   }
   ```

### 3.2 Computational Boundaries
1. **RAG Vector Search (`/api/memory/query`)**:
   - `top_k` query parameter is strictly bounded: `1 <= top_k <= 20`.
   - Prevents memory spikes from vector matrix cosine similarity scans.
2. **Multimodal Excel Extraction (`/api/extract`)**:
   - Batch size capped at **1,000 records** per extraction request.
   - Payloads with > 1,000 records return `400 Bad Request`.
3. **Memory Document Ingestion (`/api/memory/index`)**:
   - Document string length capped at **500,000 characters** (approx. 500 KB text).
4. **Prompt Security Scanning (`/api/security/scan_prompt`)**:
   - Raw prompt length capped at **20,000 characters**.

### 3.3 Concurrency & Timeouts
1. **Concurrency Semaphore**:
   - Go Orchestrator limits concurrent command executions to **10 tasks** simultaneously.
   - Excess concurrent requests receive immediate `503 Service Unavailable`:
     ```json
     {
       "status": 503,
       "error": "Server execution capacity reached. Please retry in a few moments."
     }
     ```
2. **Context Deadlines**:
   - All inter-service worker requests utilize a strict **45-second deadline context** (`context.WithTimeout(ctx, 45*time.Second)`).
   - If downstream services do not respond within 45 seconds, the request is aborted and resources are reclaimed.
3. **HTTP Server Timeouts**:
   - `ReadHeaderTimeout`: 10 seconds
   - `ReadTimeout`: 30 seconds
   - `WriteTimeout`: 60 seconds
   - `IdleTimeout`: 120 seconds
   - `MaxHeaderBytes`: 1 MB
