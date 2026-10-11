# Omni-Operator OS Agent - Standard Operating Procedure (SOP)

## 1. Objective
Establish dual-plane execution boundaries between unprivileged user-level data orchestration (research, file parsing, spreadsheet synthesis) and elevated administrative OS operations (USB flashing, system updates, quarantine isolation).

## 2. Architecture & Plane Isolation
- **Unprivileged Plane (Python Worker)**:
  - Operates inside restricted working directories (`storage/ingest/`, `storage/staging/`, `storage/quarantine/sandbox/`).
  - No access to raw system execution APIs.
  - Restricted from calling elevated system calls or spawning privileged processes.
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
- **Human-In-The-Loop (HITL) Gate**:
  - Every destructive or administrative action pauses execution.
  - Spawns a physical approval prompt (UI button click or explicit confirmation signal).
  - Timeout after 60 seconds fails safely by default.

## 3. Communication Protocol
1. User enters prompt in UI / File Manager.
2. Go Orchestrator checks prompt injection heuristics.
3. If intent is unprivileged (research/extract/stage), Orchestrator delegates to Python Worker.
4. If intent is elevated (USB flash, system modification), Orchestrator drafts Capability Token and presents HITL challenge.
5. Upon human verification, token is dispatched over Named Pipe to Daemon for deterministic execution.
