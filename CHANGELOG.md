# Changelog

All notable changes to the ANDA OS Agent codebase will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-11

### Added
- **Dual-Plane Architecture:** Strict separation between cloud data worker plane and local elevated host daemon.
- **5-Gate Machine Learning Verification Pipeline:**
  - Gate 1: Supervised 500+ Golden Dataset benchmark with threshold enforcement (`backend/worker/ml_validator.py`).
  - Gate 2: Strict RAG grounding and citation verification against vector memory.
  - Gate 3: Constrained decoding for IPC capability tokens.
  - Gate 4: Visual-semantic consistency loop with coordinate variance analysis.
  - Gate 5: Token confidence tracking with automatic human escalation below 0.90 threshold.
- **Glassmorphism HUD:** Minimal Whisper Flow frontend with Whisper Orb, Action Drawer, and all 4 spec fallback loops (A, B, C, D).
- **Windows System Daemon:** Win32 hotkey daemon listening for `[Ctrl + Windows Key]` with zero third-party dependencies.
- **Performance Guards:** Sliding-window token-bucket IP rate limiters and 15MB request payload bounding.
- **Cloud Infrastructure:** Multi-stage Fly.io deployment with persistent vector storage volume (`omni_vector_data`).

### Security
- Purged all hardcoded tokens and credentials from config files.
- Untracked `.env` from git and configured `.gitignore` with `.env.example` template.
- Implemented pre-execution prompt injection scanner blocking adversarial inputs with HTTP 403.
- Enforced mandatory 60-second physical button confirmation gate (HITL) for destructive hardware operations.

### Cleaned
- Removed all prototype and casual coding artifacts in favor of robust, production-ready implementations.
- Restored enterprise glassmorphism HUD design conforming to architectural specifications.
