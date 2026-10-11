#!/bin/sh
set -e

echo "[*] Initializing Omni-Operator Cloud Container..."

# Ensure storage hierarchy is present
mkdir -p /app/storage/ingest \
         /app/storage/staging/receipts \
         /app/storage/staging/financial_reports \
         /app/storage/staging/spreadsheets \
         /app/storage/staging/general \
         /app/storage/quarantine/sandbox \
         /app/storage/quarantine/locked \
         /app/storage/memory_store \
         /app/storage/dataset

export WORKER_PORT=${WORKER_PORT:-50051}
export ORCHESTRATOR_PORT=${PORT:-8080}
export WORKER_HOST=${WORKER_HOST:-"http://127.0.0.1:50051"}
export STORAGE_ROOT=${STORAGE_ROOT:-"/app/storage"}

echo "[*] Launching Python Data Worker Plane on port ${WORKER_PORT}..."
python3 /app/backend/worker/worker_api.py &
WORKER_PID=$!

echo "[*] Python Worker started (PID: ${WORKER_PID})"

# Give worker process a moment to initialize
sleep 1

echo "[*] Launching Go Orchestrator on port ${ORCHESTRATOR_PORT}..."
exec /app/orchestrator
