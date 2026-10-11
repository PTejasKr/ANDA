#!/bin/sh
set -e

echo "[*] Starting Omni-Operator Cloud Container..."

mkdir -p /app/storage/ingest \
         /app/storage/staging/receipts \
         /app/storage/staging/financial_reports \
         /app/storage/staging/spreadsheets \
         /app/storage/staging/general \
         /app/storage/quarantine/sandbox \
         /app/storage/quarantine/locked \
         /app/storage/memory_store \
         /app/storage/dataset

export WORKER_PORT=50051
python3 /app/backend/worker/worker_api.py &
WORKER_PID=$!

echo "[*] Python Worker Plane active (PID: ${WORKER_PID}, Port: ${WORKER_PORT})"

export ORCHESTRATOR_PORT=${PORT:-8080}
export WORKER_HOST="http://127.0.0.1:50051"
export STORAGE_ROOT="/app/storage"

exec /app/orchestrator
