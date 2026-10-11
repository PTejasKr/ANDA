# Deployment & Cloud Integration SOP

## 1. Purpose
Define operational standards for deploying Project ANDA locally on Windows, connecting local inference engines (LM Studio / Docker Ollama Gemma), and scaling unprivileged components to Fly.io and Cloudflare Workers AI edge.

## 2. Local Dual-Plane Deployment
- **Local Stack Runner**: `execution/deploy_local.py`
  - Spawns Elevated Go Daemon on `\\.\pipe\omni_daemon_ipc` and HTTP admin `:8081`.
  - Spawns Python Worker Plane on `:50051`.
  - Spawns Go Orchestrator and File Manager on `:8080`.
  - Optional flag `--with-hotkey`: Spawns Win32 global hotkey listener for `Ctrl + Win + Space`.
  - Verification mode `--verify-only`: Executes health probes against all endpoints and exits cleanly.

## 3. Local Gemma Brain Routing
1. **LM Studio**:
   - Host: `http://localhost:1234/v1`
   - Zero-configuration auto-discovery via `/v1/models`.
   - Used for primary offline intent parsing and token generation.
2. **Docker Compose**:
   - Spawns `anda-gemma-brain` (Ollama running `gemma2:2b` on `:11434`) and `anda-qdrant-memory` (Qdrant on `:6333`).
   - Run: `docker compose up -d`
3. **Deterministic Fallback**:
   - Automatically activates if no local LLM daemon is listening, maintaining 100% test bench reliability.

## 4. Edge & Cloud Stack (Free Tier)
1. **Cloudflare Workers AI**:
   - Location: `cloudflare/`
   - AI Binding: `AI` -> `@cf/google/gemma-7b-it` (text) and `@cf/openai/whisper` (audio).
   - Generous free quota: 100,000 requests/day, 10,000 AI neurons/day.
   - Command: `cd cloudflare && npx wrangler deploy`
2. **Fly.io Worker & Orchestrator**:
   - Configuration: `fly.toml` & `Dockerfile`
   - Mounts persistent volume `omni_vector_data` to `/app/storage`.
   - Command: `fly deploy`

## 5. Security Invariant
- The Elevated Daemon (`daemon.exe`) **NEVER runs in the cloud**. It runs exclusively on the local Windows host, bound to local IPC (`\\.\pipe\omni_daemon_ipc`), guarding physical hardware and system state with mandatory Human-in-the-Loop approval.
