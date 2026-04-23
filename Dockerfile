# ==============================================================================
# SHADOWCYPHER // CLOUD CITADEL DOCKER ORCHESTRATION
# ==============================================================================
# Enterprise-grade containerization for 24/7 autonomous C2 and Tactical operations.

FROM python:3.11-slim

# 1. System Hardening & Dependencies
RUN apt-get update \u0026\u0026 apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    tor \
    openssl \
    ca-certificates \
    \u0026\u0026 rm -rf /var/lib/apt/lists/*

# 2. Workspace Setup
WORKDIR /opt/shadowcypher
COPY . .

# 3. Environment Sanitization
ENV SHADOW_PATH="/opt/shadowcypher"
ENV PYTHONPATH="${PYTHONPATH}:${SHADOW_PATH}"

# 4. Port Configuration (C2, Signal, UI Relay)
EXPOSE 44444 6667 9999

# 5. Bootstrap Sequence
RUN chmod +x setup.sh shadow_sync.sh shadowcypher/native/ghost/forge.sh
# Note: Master key should be mounted as a volume for persistence in production.

ENTRYPOINT ["/bin/bash", "-c", "service tor start \u0026\u0026 ./setup.sh \u0026\u0026 python3 -m shadowcypher.app --headless"]
