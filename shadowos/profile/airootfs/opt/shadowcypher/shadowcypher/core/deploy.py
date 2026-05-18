"""
ShadowCypher Sovereign Deployment — 24/7 Cloud Orchestration.
Generates artifacts for Fly.io and Google Cloud Run deployments.
"""

import os
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger

DOCKERFILE = """
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    git \
    libgtk-3-0 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sovereign Hub Ports: 8888 (WS), 6667 (IRC)
EXPOSE 8888 6667

CMD ["python", "-m", "shadowcypher.core.sovereign"]
"""

FLY_TOML = """
app = "shadow-hub-{id}"
primary_region = "bos"

[http_service]
  internal_port = 8888
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

[[services]]
  internal_port = 6667
  protocol = "tcp"
  [[services.ports]]
    port = 6667
"""

class CloudDeployer:
    @staticmethod
    def generate_deploy_artifacts():
        """Generates Dockerfile and Fly.io config for 24/7 availability."""
        root = config.project_root
        
        # 1. Dockerfile
        with open(os.path.join(root, "Dockerfile"), "w") as f:
            f.write(DOCKERFILE.strip())
            
        # 2. Fly.toml
        node_id = os.urandom(4).hex()
        with open(os.path.join(root, "fly.toml"), "w") as f:
            f.write(FLY_TOML.format(id=node_id).strip())
            
        # 3. requirements.txt (if missing)
        req_path = os.path.join(root, "requirements.txt")
        if not os.path.exists(req_path):
            with open(req_path, "w") as f:
                f.write("websockets\naiohttp\ncryptography\nnetifaces\n")

        logger.info("deploy", "ARTIFACTS_GENERATED: Dockerfile & fly.toml are ready for cloud ignition.")
        return True

deployer = CloudDeployer()
