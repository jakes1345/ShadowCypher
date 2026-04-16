#!/bin/bash
# --- SHADOWCYPHER SYSTEM-WIDE MASTER-GO UPGRADE ---
# Upgrading and Installing Go v1.26.2 (Latest Stable) throughout the entire PC.

echo "🚀 Initiating Full System Master-Go Upgrade Sequence..."

VERSION="1.26.2"
FILE="go${VERSION}.linux-amd64.tar.gz"
URL="https://go.dev/dl/${FILE}"
TARGET_PATH="/usr/local/go"

# 1. Purge Legacy Distribution Trace (Requires Sudo Approval)
echo "[*] Purging legacy distribution Go packages..."
sudo apt-get remove golang-go -y 2>/dev/null

# 2. Extract Latest Stable tarball to System-Wide path
echo "[*] Downloading and deploying Master-Go v${VERSION} to ${TARGET_PATH}..."
rm -rf /tmp/${FILE}
curl -L $URL -o /tmp/${FILE}
sudo rm -rf ${TARGET_PATH}
sudo tar -C /usr/local -xzf /tmp/${FILE}

# 3. Universal Environment Orchestration
echo "[*] Orchestrating system-wide environment variables..."

# Update individual user profile
if ! grep -q "${TARGET_PATH}/bin" ~/.bashrc; then
    echo "export PATH=${TARGET_PATH}/bin:\$PATH" >> ~/.bashrc
fi

# 4. Verification Check
echo "[*] Final Verification Sequence..."
${TARGET_PATH}/bin/go version

echo "✅ Master-Go v${VERSION} has been deployed system-wide."
rm -rf /tmp/${FILE}
