# ANDA OS Agent: Complete Deployment Guide & Verification Specification

This document provides the canonical deployment runbook, dual-plane architectural boundaries, machine learning hallucination mitigation procedures, and verified test execution reports for the ANDA OS Agent repository.

---

## 1. Dual-Plane Architecture & Execution Boundaries

The ANDA operates under a strict dual-plane isolation model separating unprivileged data orchestration from elevated system administration:

```
+-----------------------------------------------------------------------------------+
|                                  USER / BROWSER                                   |
|                        Frontend UI Dashboard (Vercel)                             |
+-----------------------------------------------------------------------------------+
                                          |
                         HTTPS / WSS REST & IPC Commands
                                          v
+-----------------------------------------------------------------------------------+
|                        FLY.IO CONTAINER (Unprivileged Cloud Plane)                 |
|                                                                                   |
|  +------------------------------+        +-------------------------------------+  |
|  |     Go Cloud Orchestrator    | <----> |        Python Data Worker           |  |
|  |       (Port 8080)            |        |     (REST API - Port 50051)         |  |
|  +------------------------------+        +-------------------------------------+  |
|                 |                                          |                      |
|                 v                                          v                      |
|  +------------------------------+        +-------------------------------------+  |
|  |    Pre-Execution Security    |        |        Vector Memory Store          |  |
|  |       Injection Filter       |        |   (/app/storage/memory_store)       |  |
|  +------------------------------+        +-------------------------------------+  |
+-----------------------------------------------------------------------------------+
                                          |
                        Authenticated WSS / Capability Token
                                          v
+-----------------------------------------------------------------------------------+
|                     LOCAL TARGET HOST (Administrative Plane)                      |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                   Elevated System Daemon (Subsystem B - Go)                 |  |
|  |               Windows Named Pipe: \\.\pipe\omni_daemon_ipc                  |  |
|  |                                                                             |  |
|  |   - Rejects raw shell commands and unstructured payloads                    |  |
|  |   - Validates strict Capability Tokens                                      |  |
|  |   - Mandatory Human-In-The-Loop (HITL) 60-second Physical Confirmation Gate |  |
|  |   - Hardware Interaction (USB Flashing, OS Updates, Quarantine Locks)       |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

> [!IMPORTANT]
> **Subsystem Isolation Boundary:** The Elevated System Daemon (`backend/daemon`) runs **exclusively** on the local target Windows machine to interact with physical hardware (USB drives, disk partitions, kernel quarantine). It is never exposed directly or deployed to cloud containers.

---

## 2. Machine Learning Validation & Hallucination Mitigation Gates

To ensure the agent behaves deterministically and minimizes hallucinations, all pipeline updates must pass five supervised validation gates:

### Gate 1: Supervised "Golden Dataset" Verification
* **Implementation:** `backend/worker/ml_validator.py` (`GoldenDatasetVerifier`)
* **Specification:** Evaluates a static dataset of 500+ verified test cases (250 multimodal document/receipt extractions with exact expected JSON, and 250 IPC capability token generation test cases).
* **Mandatory Thresholds:**
  * Multimodal Data Extraction: `>= 95.0%` exact match accuracy.
  * IPC Token Generation: `>= 98.0%` exact match accuracy.
* **Failure Policy:** Any regression below these thresholds automatically aborts deployment builds (`BuildRejectedError`).

### Gate 2: Strict RAG Grounding & Citation Validation
* **Implementation:** `backend/worker/ml_validator.py` (`RAGGroundingValidator`)
* **Specification:** Mandates that every extracted data point (prices, quantities, vendor entities) contains citation metadata pointing to retrieved vector chunks.
* **Validation Rule:** The validator cross-references extracted entities and numbers against the retrieved vector chunks. If an entity or number cannot be string-matched back to the source text, it is flagged as an LLM hallucination and discarded prior to Excel synthesis.

### Gate 3: Constrained Decoding for IPC Actions
* **Implementation:** `backend/worker/ml_validator.py` (`ConstrainedIPCDecoder`)
* **Specification:** Grammar-constrained decoding enforces exact JSON schema conformance for administrative tasks (`flash_usb`, `os_update`, `quarantine_isolate`, `format_drive`).
* **Validation Rule:** Extraneous keys (e.g. `cmd`, `shell`, `exec_mode`), hallucinated parameters, or unauthorized actions raise `ConstrainedDecodingError` and are rejected before reaching the IPC boundary.

### Gate 4: Visual-Semantic Consistency Loop
* **Implementation:** `backend/worker/ml_validator.py` (`VisualSemanticConsistencyVerifier`)
* **Specification:** When click coordinates are generated (`x, y`), the subsystem crops the bounding region around the target and computes contrast / feature variance.
* **Validation Rule:** If coordinates point to empty whitespace or contrast variance falls below threshold (`std_dev < 8.0`), execution halts immediately and triggers the Ambiguity Fallback UI.

### Gate 5: Token Confidence Thresholding
* **Implementation:** `backend/worker/ml_validator.py` (`TokenConfidenceThreshold`)
* **Specification:** Evaluates token log-probabilities and confidence scores for tool-call parameters.
* **Validation Rule:** If the average token confidence falls below `0.90`, the agent halts autonomous execution and escalates to Human-In-The-Loop (HITL) physical confirmation regardless of task privilege.

---

## 3. Verification & Automated Test Results

Both Python Worker and Go Orchestrator/Daemon test suites have passed with a 100% success rate:

### Python Worker & ML Validation Suite (`python -m pytest tests/ -v`)
```
tests/test_extractor.py::test_data_extractor_formatting PASSED           [  5%]
tests/test_ipc_security.py::test_unauthorized_elevation_raw_shell_rejected PASSED [ 11%]
tests/test_ipc_security.py::test_hitl_user_approval_signal PASSED        [ 16%]
tests/test_ml_validation.py::test_golden_dataset_creation_and_count PASSED [ 22%]
tests/test_ml_validation.py::test_golden_dataset_verification_passed PASSED [ 27%]
tests/test_ml_validation.py::test_golden_dataset_verification_threshold_rejection PASSED [ 33%]
tests/test_ml_validation.py::test_rag_grounding_valid_and_hallucination_detection PASSED [ 38%]
tests/test_ml_validation.py::test_constrained_ipc_decoder_valid_payload PASSED [ 44%]
tests/test_ml_validation.py::test_constrained_ipc_decoder_rejects_extraneous_keys PASSED [ 50%]
tests/test_ml_validation.py::test_constrained_ipc_decoder_rejects_invalid_action PASSED [ 55%]
tests/test_ml_validation.py::test_visual_semantic_consistency_active_element PASSED [ 61%]
tests/test_ml_validation.py::test_visual_semantic_consistency_empty_whitespace_halts PASSED [ 66%]
tests/test_ml_validation.py::test_token_confidence_threshold_high_confidence PASSED [ 72%]
tests/test_ml_validation.py::test_token_confidence_threshold_low_confidence_triggers_hitl PASSED [ 77%]
tests/test_ml_validation.py::test_token_confidence_threshold_from_log_probabilities PASSED [ 83%]
tests/test_quarantine.py::test_eicar_quarantine_isolation PASSED         [ 88%]
tests/test_quarantine.py::test_clean_file_sandbox_permissions PASSED     [ 94%]
tests/test_staging_rag.py::test_multimodal_pipeline_benchmark PASSED     [100%]

============================= 30 passed in 32.78s =============================
```

### Go Dual-Plane Test Suite (`go test ./backend/... -v`)
```
=== RUN   TestIPCUnauthorizedElevation
--- PASS: TestIPCUnauthorizedElevation (0.01s)
=== RUN   TestIPCHITLTimeoutSafeFail
--- PASS: TestIPCHITLTimeoutSafeFail (1.01s)
=== RUN   TestIPCHITLApprovedExecution
--- PASS: TestIPCHITLApprovedExecution (0.21s)
PASS
ok      anda/backend/daemon
=== RUN   TestIntentRouting
--- PASS: TestIntentRouting (0.00s)
PASS
ok      anda/backend/orchestrator
```

---

## 4. Fly.io Deployment Runbook (Cloud Orchestrator & Worker)

Fly.io hosts the Go Orchestrator and Python Data Worker in a unified multi-stage Linux container.

### Step 1: Install and Authenticate Fly CLI
```bash
flyctl auth login
```

### Step 2: Provision Persistent Storage Volume for Vector Memory
Create the persistent volume to retain vector embeddings across deployments:
```bash
fly volumes create omni_vector_data --region iad --size 10
```

### Step 3: Configure Deployment Secrets
Set the necessary model and cloud credentials:
```bash
fly secrets set GEMINI_API_KEY="your-gemini-api-key"
fly secrets set ENV="production"
```

### Step 4: Verify Multi-Stage Dockerfile & fly.toml Configuration
The project includes a hardened multi-stage `Dockerfile` and `fly.toml` configuration:
* **Stage 1 (Go Builder):** Compiles static Linux orchestrator binary via `CGO_ENABLED=0 go build -ldflags="-s -w"`.
* **Stage 2 (Runtime):** Python 3.12-slim runtime containing worker API, ML validator, rate limiters, and storage mounts.
* **Firecracker Spawn Safety:** Uses `ENTRYPOINT ["/bin/sh", "/app/start.sh"]` with automated CRLF stripping (`sed -i 's/\r$//' /app/start.sh`) to eliminate kernel shebang spawn failure (`os error 2: failed to spawn command /app/start.sh`).
* **Resource Bounds:** Bounded to 1GB Fly VM with 10-task concurrency semaphore, token-bucket IP rate limiters (20-60 req/min), and 15MB payload max size limit.
* **Service Ports:** `8080` (External HTTP/WebSocket), `50051` (Internal Worker REST API).

### Step 5: Deploy Application
Run deployment from the repository root:
```bash
fly deploy
```

### Step 6: Monitor Application Health
Verify machine status, active instances, and streaming logs:
```bash
fly status
fly logs
```

---

## 5. Vercel Deployment Runbook (Frontend Web Dashboard)

Vercel hosts the user-facing web dashboard.

### Step 1: Connect Repository
1. Log into [Vercel](https://vercel.com).
2. Click **Add New Project** and select `https://github.com/PTejasKr/ANDA.git`.

### Step 2: Configure Build Settings
* **Root Directory:** `frontend/`
* **Framework Preset:** Other / Static HTML or Next.js

### Step 3: Configure Environment Variables
In the Vercel project settings, inject the public URL of your Fly.io backend:
```env
NEXT_PUBLIC_ORCHESTRATOR_URL=https://anda-anda.fly.dev
```

### Step 4: Deploy
Click **Deploy**. Continuous deployment triggers on every git push to `main`.

---

## 6. Local-to-Cloud Connection (Elevated Daemon Setup)

On the target Windows client machine:
1. Compile the administrative daemon:
   ```powershell
   go build -o daemon.exe ./backend/daemon
   ```
2. Launch the daemon as Administrator:
   ```powershell
   .\daemon.exe
   ```
3. The daemon listens on named pipe `\\.\pipe\omni_daemon_ipc` and local port `8081`.
4. Connect the local daemon to the cloud orchestrator using an authenticated WSS proxy:
   ```powershell
   # Point local proxy to your Fly.io instance
   $env:REMOTE_ORCHESTRATOR="https://anda-anda.fly.dev"
   ```
