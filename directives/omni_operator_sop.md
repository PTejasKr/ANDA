# ANDA OS Agent - Standard Operating Procedure (SOP)

## 1. Objective
Establish dual-plane execution boundaries between unprivileged user-level data orchestration (research, file parsing, spreadsheet synthesis) and elevated administrative OS operations (USB flashing, system updates, quarantine isolation).

## 2. Architecture & Plane Isolation
- **Unprivileged Plane (Python Worker)**:
  - Operates inside restricted working directories (`storage/ingest/`, `storage/staging/`, `storage/quarantine/sandbox/`).
  - No access to raw system execution APIs.
  - Restricted from calling elevated system calls or spawning privileged processes.
  - Guarded by Sliding-Window Rate Limiters (`heavy`: 30 req/min, `general`: 120 req/min).
  - Enforces payload bounds: max 15MB request payload, max 1000 records batch extract, bounded RAG `1 <= top_k <= 20`.
- **Administrative Plane (Elevated Daemon - Go)**:
  - Listens strictly on Windows Named Pipe: `\\.\pipe\omni_daemon_ipc`.
  - Rejects all unstructured shell commands (e.g. `cmd.exe /c ...`).
  - Accepts ONLY validated Capability Tokens:
    ```json
    {
      "action": "flash_usb|quarantine_isolate|os_update",
      "drive": "E:",
      "hash": "<sha256>",
      "token_id": "<uuid>",
      "params": {}
    }
    ```
- **Go Orchestrator & Gateway**:
  - Token-Bucket IP Rate Limiter (60 req/min global, 20 req/min command).
  - Bounded concurrency semaphore (max 10 parallel heavy tasks).
  - Inter-service 45-second execution deadline context (`context.WithTimeout`).
- **Human-In-The-Loop (HITL) Gate**:
  - Every destructive or administrative action pauses execution.
  - Spawns a physical approval prompt (UI button click or explicit confirmation signal).
  - Timeout after 60 seconds fails safely by default.

## 3. Communication Protocol
1. User enters prompt in UI / File Manager.
2. Go Orchestrator checks prompt injection heuristics and rate limit allowances.
3. If intent is unprivileged (research/extract/stage), Orchestrator delegates to Python Worker within a 45s context deadline.
4. If intent is elevated (USB flash, system modification), Orchestrator drafts Capability Token and presents HITL challenge.
5. Upon human verification, token is dispatched over Named Pipe to Daemon for deterministic execution.

## 4. Associated Directives
- **Subsystem & Plane Mapping**: [directives/architecture_mapping.md](file:///d:/mlh/directives/architecture_mapping.md)
- **Performance & Rate Limiting SOP**: [directives/performance_and_rate_limits.md](file:///d:/mlh/directives/performance_and_rate_limits.md)
- **Deployment & Cloud SOP**: [directives/deployment_and_cloud.md](file:///d:/mlh/directives/deployment_and_cloud.md)
- **File Staging & RAG Memory SOP**: [directives/file_staging_rag.md](file:///d:/mlh/directives/file_staging_rag.md)
- **Quarantine Security SOP**: [directives/quarantine_security.md](file:///d:/mlh/directives/quarantine_security.md)
- **ML Validation & Golden Checks SOP**: [directives/ml_validation_checks.md](file:///d:/mlh/directives/ml_validation_checks.md)
