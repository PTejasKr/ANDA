# Release v1.0.0: ANDA Dual-Plane OS Agent

**Release Version:** `v1.0.0`  
**Status:** Production Ready  
**Date:** October 11, 2026  
**Repository:** [https://github.com/PTejasKr/ANDA.git](https://github.com/PTejasKr/ANDA.git)  
**Cloud Deployment:** [https://anda-omni-operator.fly.dev](https://anda-omni-operator.fly.dev)  

---

## Executive Summary

ANDA (Adaptive Networked Desktop Agent) is an autonomous, dual-plane operating system agent engineered to bridge high-speed multimodal data synthesis with elevated hardware administration. 

This production release establishes cryptographic isolation between unprivileged cloud data workers and administrative host daemons, backed by a 5-gate machine learning verification pipeline and deterministic routing.

---

## Release Highlights

### 1. Dual-Plane Security Architecture
* **Unprivileged Cloud Plane (Fly.io):**
  * High-concurrency Go Orchestrator (`:8080`) routing tasks between worker planes and local proxies.
  * Python Data Worker (`:50051`) with 64-dimensional chunked vector memory and multimodal ingestion.
  * Token-bucket sliding-window rate limiters (20–120 req/min) and 15MB request payload constraints.
  * Pre-execution security heuristics blocking prompt injection and elevation bypasses (`403 Forbidden`).
* **Elevated Administrative Host Plane (Local Windows Daemon):**
  * Native Windows named pipe (`\\.\pipe\omni_daemon_ipc`).
  * Strict capability token verification; rejects unstructured payloads or raw shell execution.
  * Mandatory 60-second Human-In-The-Loop (HITL) physical button confirmation gate for destructive hardware operations (USB flashing, drive formatting, kernel quarantine).

### 2. Five-Gate Machine Learning Verification Pipeline
* **Gate 1 (Supervised Golden Dataset):** Evaluates 500+ static test cases (250 multimodal extractions + 250 capability token generations) requiring `>= 95%` extraction accuracy and `>= 98%` IPC accuracy.
* **Gate 2 (Strict RAG Grounding):** Cross-references extracted financial and tabular entities against retrieved vector memory chunks in `/app/storage/memory_store` to eliminate hallucinations.
* **Gate 3 (Constrained IPC Decoding):** Grammar-constrained JSON decoding rejecting extraneous keys and unauthorized system commands.
* **Gate 4 (Visual-Semantic Consistency):** Coordinate variance verification (`std_dev >= 8.0`) on UI crops to prevent click failures on whitespace.
* **Gate 5 (Token Confidence Thresholding):** Log-probability tracking enforcing autonomous halting and human escalation whenever average confidence drops below `0.90`.

### 3. Glassmorphism HUD Desktop Experience
* Floating, transparent desktop overlay triggered via native Windows hotkey `[Ctrl + Windows Key]`.
* Animated Whisper Orb with visual state feedback (`idle`, `listening`, `processing`, `executing`, `awaiting_auth`).
* Comprehensive Fallback Loops for handling ambiguity, runaway loops, execution timeouts, and hard elevation boundaries.

### 4. Zero Key Leakage & Environment Hygiene
* Strict `.gitignore` enforcement for `.env`, credentials, tokens, and build artifacts.
* Clean template provided in `.env.example`.
* Decoupled cloud build infrastructure via remote Depot builders on Fly.io.

---

## Test Verification

| Test Suite | Tests Run | Pass Rate | Execution Time |
| :--- | :--- | :--- | :--- |
| **Python Worker & Security Suite** | 30 | **100% (30/30)** | 32.19s |
| **Go Orchestrator & Daemon Suite** | 9 | **100% (9/9)** | 1.92s |
| **Windows Hotkey & Asset Suite** | 14 | **100% (14/14)** | 0.85s |

---

## Verification Endpoints

* **System Status:** `GET https://anda-omni-operator.fly.dev/api/system/status`
* **Brain Provider Status:** `GET https://anda-omni-operator.fly.dev/api/brain/status`
* **File System Ingest List:** `GET https://anda-omni-operator.fly.dev/api/fs/list?folder=ingest`
