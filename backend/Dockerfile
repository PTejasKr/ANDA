# Multi-Stage Dockerfile: Omni-Operator Orchestrator & Python Data Worker
# Stage 1: Build Static Linux Go Orchestrator
FROM golang:1.24-alpine AS go-builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY backend/orchestrator ./backend/orchestrator
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/orchestrator ./backend/orchestrator

# Stage 2: Production Runtime with Python Data Worker
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend/worker /app/backend/worker
COPY frontend /app/frontend
COPY directives /app/directives
COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

# Copy static orchestrator binary from builder
COPY --from=go-builder /out/orchestrator /app/orchestrator
RUN chmod +x /app/orchestrator

VOLUME ["/app/storage"]

EXPOSE 8080 50051

ENTRYPOINT ["/bin/sh", "/app/start.sh"]
