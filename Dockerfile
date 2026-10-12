# Production Dockerfile: ANDA Orchestrator & Python Data Worker
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

# Copy pre-compiled static Linux orchestrator binary
COPY orchestrator /app/orchestrator
RUN chmod +x /app/orchestrator

VOLUME ["/app/storage"]

EXPOSE 8080 50051

ENTRYPOINT ["/bin/sh", "/app/start.sh"]
