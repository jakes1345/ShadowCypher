#!/bin/bash
# --- SHADOWCYPHER SOVEREIGN-GO IGNITION (Local Mode) ---
# High-perf, zero-sudo Go 1.26.2 deployment for Native Strike Core.

echo "🚀 Initiating Shadow-Go Autonomous Upgrade..."

VERSION="1.26.2"
FILE="go${VERSION}.linux-amd64.tar.gz"
URL="https://go.dev/dl/${FILE}"
GO_DIR="/home/jack/ShadowCypher/bin/go"

# 1. Download Core Tarball
echo "[*] Downloading ${FILE}..."
curl -L $URL -o /tmp/${FILE}

# 2. Local Deployment (No sudo required)
echo "[*] Provisioning local runtime in ${GO_DIR}..."
rm -rf ${GO_DIR}
mkdir -p /home/jack/ShadowCypher/bin
tar -C /home/jack/ShadowCypher/bin -xzf /tmp/${FILE}

# 3. Path Resilience
echo "[*] Reinforcing PATH environments..."
if ! grep -q "${GO_DIR}/bin" ~/.bashrc; then
    echo "export PATH=${GO_DIR}/bin:\$PATH" >> ~/.bashrc
    source ~/.bashrc
fi

# 4. Check results
echo "[*] Final Verification Sequence..."
${GO_DIR}/bin/go version

echo "✅ Go v${VERSION} has been deployed into the Sovereign binary path."
rm /tmp/${FILE}
