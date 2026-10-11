# Omni-Operator OS Agent

> A multi-agent operating system assistant built with a **Dual-Plane Architecture** strictly separating unprivileged user-level data orchestration (multimodal ingestion, directory staging, Excel synthesis, chunked RAG vector memory) from elevated administrative OS operations (USB flashing, firmware upgrades, malware quarantine).

---

## 1. System Architecture

```
                          +------------------------------------------+
                          |   Operator UI / File Manager Dashboard   |
                          |      (Huemint Theme, Port 8080)          |
                          +--------------------+---------------------+
                                               |
                                     HTTP REST / Events
                                               v
+------------------------------------------------------------------------------------------+
|                                Go Orchestrator Plane                                     |
|  - Pre-Execution Security Filter (Prompt Injection Defense)                              |
|  - Intent Routing & RAG Context Assembly                                                 |
|  - File Manager Filesystem Provider (/api/fs/list, /api/fs/read)                         |
+-------------------+------------------------------------------+---------------------------+
                    |                                          |
        Unprivileged Worker API                                | Named Pipe IPC
        (REST HTTP / Port 50051)                               | (\\.\pipe\omni_daemon_ipc)
                    v                                          v
+---------------------------------------+  +-----------------------------------------------+
|     Unprivileged Worker Plane         |  |             Elevated Daemon Plane             |
|                                       |  |                                               |
| - Subsystem A: Data Extractor & Stager|  | - Subsystem B: Elevated OS Operations         |
|   (openpyxl, pandas, vision formats)  |  |   (flash_usb, os_update, quarantine_isolate)  |
| - Subsystem C: Local Vector Memory    |  | - Strict Capability Token Verification        |
|   (Chunked RAG, Cosine Indexing)      |  | - Human-in-the-Loop (HITL) Gate               |
| - Subsystem D: Non-Exec Sandbox       |  |   (Physical user confirmation button, 60s     |
|   (Heuristic scanner, EICAR detector) |  |    safe-fail timeout)                         |
+---------------------------------------+  +-----------------------------------------------+
```

---

## 2. Directory Structure

```
d:\mlh\
├── directives/                        # Layer 1: SOPs and operational directives
│   ├── omni_operator_sop.md
│   ├── file_staging_rag.md
│   └── quarantine_security.md
├── execution/                         # Layer 3: Deterministic scripts & runners
│   ├── deploy_local.py                # Local stack deployment & health orchestrator
│   ├── generate_mock_artifacts.py     # Generates receipts & audit reports
│   └── run_all_tests.py               # Complete dual-plane automated test runner
├── backend/                           # Backend Specialist Architecture
│   ├── daemon/                        # Subsystem B: Go Elevated Daemon
│   │   ├── main.go                    # Windows Named Pipe IPC listener & HITL gate
│   │   └── daemon_test.go             # IPC security tests
│   ├── orchestrator/                  # Subsystem A & Broker: Go Orchestrator
│   │   ├── main.go                    # REST & File Manager server
│   │   ├── router.go                  # Semantic router & prompt injection filter
│   │   ├── router_test.go             # Routing & security unit tests
│   │   └── client_ipc.go              # IPC Named Pipe client
│   └── worker/                        # Subsystems A, C, D: Python Worker Plane
│       ├── data_extractor.py          # Multimodal JSON -> styled .xlsx with openpyxl
│       ├── file_stager.py             # Semantic directory categorization
│       ├── vector_memory.py           # Local embedded Vector DB & chunked RAG
│       ├── security_scanner.py        # Malware isolation & prompt injection defense
│       └── worker_api.py              # Worker REST API (port 50051)
├── frontend/                          # Delivery & Frontend Engineering
│   ├── index.html                     # Dual-pane File Manager UI with HITL modal
│   ├── styles.css                     # Huemint-inspired design palette
│   └── app.js                         # File manager controller & live audit stream
├── storage/                           # Layered Filesystem
│   ├── ingest/                        # Incoming unclassified queue
│   ├── staging/                       # Categorized files (receipts, reports, sheets)
│   ├── quarantine/                    # Zero-trust sandbox and locked malware
│   └── memory_store/                  # Persistent vector index
├── tests/                             # Test Benches & Security Validation
│   ├── test_extractor.py              # Pytest for openpyxl formatting & formulas
│   ├── test_ipc_security.py           # Test Case 1 & 2 (Unauthorized IPC & HITL)
│   ├── test_staging_rag.py            # Test Case 3 (Multimodal RAG Benchmark < 5s)
│   └── test_quarantine.py             # Test Case 4 (EICAR malware quarantine & locking)
├── .env                               # Environment configurations
└── README.md
```

---

## 3. Test Bench & Security Verification

All four test cases defined in `test_bench_and_setup.md` are implemented and passing 100%:

| Test Suite | Test Case | Target | Result |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | Data Extraction & Formulas | `tests/test_extractor.py` | **PASSED** (0.61s) |
| **Unit Tests** | Go Intent Routing & Injection Filter | `backend/orchestrator/router_test.go` | **PASSED** (0.48s) |
| **IPC Security** | Test Case 1: Unauthorized Elevation | `tests/test_ipc_security.py` | **PASSED** (0.01s) |
| **IPC Security** | Test Case 2: HITL Confirmation & Timeout | `tests/test_ipc_security.py` | **PASSED** (1.72s) |
| **Staging & RAG**| Test Case 3: Multimodal Pipeline (< 5s SLA) | `tests/test_staging_rag.py` | **PASSED** (0.087s) |
| **Quarantine**   | Test Case 4: EICAR Signature Quarantine | `tests/test_quarantine.py` | **PASSED** (0.08s) |

Run the full automated verification test suite anytime:
```bash
python execution/run_all_tests.py
```

---

## 4. Local Deployment & Running

### Option A: Complete Automated Local Stack
Start the Elevated Daemon, Python Worker, and Go Orchestrator with one command:
```bash
python execution/deploy_local.py
```
Open **[http://localhost:8080/](http://localhost:8080/)** in your browser.

### Option B: Individual Service Launch
1. **Elevated Daemon**:
   ```bash
   ./daemon.exe
   ```
2. **Python Worker Plane**:
   ```bash
   python backend/worker/worker_api.py
   ```
3. **Go Orchestrator & File Manager**:
   ```bash
   ./orchestrator.exe
   ```

---

## 5. Security & Isolation Guarantees
1. **Dual-Plane Separation**: Worker plane runs completely unprivileged. No shell access is permitted across IPC.
2. **Strict IPC Capability Tokens**: The Elevated Daemon accepts ONLY structured JSON tokens with explicit action specifications (`flash_usb`, `os_update`, `quarantine_isolate`). Raw shell commands are rejected immediately with `UNAUTHORIZED_PAYLOAD`.
3. **Human-In-The-Loop (HITL) Gate**: Elevated tasks halt execution and require a physical button click. A 60-second countdown timeout automatically safe-fails if unconfirmed.
4. **Zero-Trust Sandbox**: Downloaded files are placed in `storage/quarantine/sandbox/` with execute permissions stripped.
5. **EICAR Malware Defense**: Known signatures and malicious executables are isolated and locked into `storage/quarantine/locked/` with forensic JSON manifests.
6. **Prompt Injection Defense**: Regex and heuristic pre-execution hooks detect system overrides (`[SYSTEM]`, `IGNORE PREVIOUS INSTRUCTIONS`) and dangerous execution syntax (`powershell -enc`, `format C:`, `rmdir /s /q`).
