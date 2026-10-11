# Architecture Mapping: Omni-Operator Dual-Plane Subsystems

## 1. Subsystem Topology & Plane Isolation

Omni-Operator is split into two non-overlapping execution planes to prevent privilege escalation and ensure reliable autonomous desktop automation.

```
+-----------------------------------------------------------------------------------+
|                              UNPRIVILEGED CLOUD / HOST PLANE                      |
|                                                                                   |
|   +-----------------------+              +------------------------------------+   |
|   |   Whisper Flow UI     |  HTTP/JSON   |   Go Orchestrator (:8080)          |   |
|   |  Transparent Floating | <----------> |  - Reverse Proxy & Static UI Host  |   |
|   |  Popup & Status Orb   |              |  - Token Bucket IP Rate Limiter    |   |
|   +-----------------------+              |  - Concurrency Semaphore (N=10)    |   |
|                                          |  - Semantic Intent Router          |   |
|                                          |  - Indirect Injection Heuristic    |   |
|                                          +-----------------+------------------+   |
|                                                            |                      |
|                                                HTTP REST   | 45s Deadline Context |
|                                                :50051      v                      |
|                                          +------------------------------------+   |
|                                          |   Python Worker Plane (:50051)     |   |
|                                          |  - Sliding-Window Rate Limiter     |   |
|                                          |  - Data Extraction (Excel)         |   |
|                                          |  - File Stager & Sandboxing        |   |
|                                          |  - Vector Memory RAG (Top_K <= 20) |   |
|                                          |  - STT Voice Transcriber (<= 15MB) |   |
|                                          |  - LLM Brain Multi-Tier Fallback   |   |
|                                          +------------------------------------+   |
+-----------------------------------------------------------------------------------+
                                   ||  Elevated IPC (Only on Local Windows Host)
                                   ||  Strict JSON Capability Tokens
                                   \/
+-----------------------------------------------------------------------------------+
|                        PRIVILEGED ADMINISTRATIVE PLANE                            |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   |                     Elevated Daemon (daemon.exe)                          |   |
|   |  - Listens strictly on Named Pipe: \\.\pipe\omni_daemon_ipc               |   |
|   |  - Admin HTTP port: :8081 (Localhost only)                                |   |
|   |  - Mandatory Physical Human-In-The-Loop (HITL) Gate (60s Timeout)         |   |
|   |  - Dispatches destructive operations:                                     |   |
|   |      * flash_usb: Block device write with SHA256 integrity                |   |
|   |      * os_update: Controlled OS package update                            |   |
|   |      * quarantine_isolate: Cryptographic quarantine lock                  |   |
|   |  - NEVER runs in cloud / container environments                           |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Port & Interface Matrix

| Component | Port / Interface | Binding | Purpose | Authentication / Security |
| :--- | :--- | :--- | :--- | :--- |
| **Go Orchestrator** | `TCP 8080` (or `$PORT`) | `0.0.0.0` | Primary gateway, Web UI, API router | IP Rate Limiter (60/min global, 20/min command), Max 5MB/15MB body |
| **Python Worker** | `TCP 50051` | `127.0.0.1` (or `0.0.0.0` in Docker) | Compute, extraction, RAG, STT, LLM parsing | Internal worker plane, sliding-window rate limiter, max 15MB payload |
| **Elevated Daemon** | `TCP 8081` | `127.0.0.1` | Local admin status check | Localhost only, elevated process permissions |
| **Windows Named Pipe**| `\\.\pipe\omni_daemon_ipc` | Local Kernel | Inter-process capability token dispatch | Strict JSON schema, SHA256 prompt hash, physical HITL confirmation |
| **HotKey Daemon** | Win32 `RegisterHotKey` | Windows Shell | Global `Ctrl + Win` shortcut handler | Launches chromeless app mode via Edge/Chrome `--app` |

---

## 3. Four Fallback & Safety Loops

### Loop A: Ambiguity Clarification (< 0.70 Confidence)
- **Trigger**: When LLM Brain or Orchestrator semantic route confidence drops below `0.70`, or intent is underspecified.
- **Action**: UI enters `amber` state, displays disambiguation cards with selectable options.
- **Resolution**: User selects target intent or provides supplemental guidance; execution resumes deterministically.

### Loop B: Runaway Loop & Rate Limiter
- **Trigger**: Repeated agent iterations exceed 5 cycles without terminal state, or client fires > 20 command requests/min.
- **Action**: Orchestrator immediately returns `429 Too Many Requests` or aborts recursive cycles, rendering the Action Drawer warning.
- **Resolution**: Requires explicit manual user continuation.

### Loop C: 45-Second Execution Timeout
- **Trigger**: Any downstream compute step (RAG retrieval, Excel generation, STT transcription, or external API call) takes longer than 45 seconds.
- **Action**: Go `context.WithTimeout(ctx, 45*time.Second)` cancels the in-flight HTTP request.
- **Resolution**: UI returns safe error message: *"Task exceeded 45s execution limit. Partial state preserved."*

### Loop D: 60-Second HITL Elevation Gate
- **Trigger**: Destructive hardware or OS modification (`flash_usb`, `format_drive`, `os_update`).
- **Action**: Orchestrator issues capability token with `hitl_pending` status and triggers visual confirmation dialog.
- **Resolution**: Physical user button click approves dispatch over Named Pipe. If unconfirmed within 60 seconds, token auto-expires and request safely fails closed.

---

## 4. Storage Hierarchy Mapping

All transient and persisted files are organized into structured directories rooted at `/app/storage` (or `storage/` locally):

```
storage/
├── ingest/                    # Unprocessed user drops and raw files
├── staging/
│   ├── receipts/             # Categorized expense vouchers and receipts
│   ├── financial_reports/    # Quarterly summaries and audit logs
│   ├── spreadsheets/         # Extracted Excel workbooks (.xlsx)
│   └── general/              # Uncategorized staged documents
├── quarantine/
│   ├── sandbox/              # Quarantined suspicious payloads under inspection
│   └── locked/               # Cryptographically isolated malware artifacts
└── memory_store/             # Persisted vector embeddings and document chunks
```
