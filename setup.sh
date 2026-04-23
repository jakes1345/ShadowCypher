#!/bin/bash
# ==============================================================================
# SHADOWCYPHER // UNIVERSAL SETUP ORCHESTRATOR
# ==============================================================================
# Automates the deployment and cryptographic arming of the ShadowCypher suite.
# Designed for portability and sovereign operation.

echo -e "\033[1;34m[*] Initializing ShadowCypher Deployment...\033[0m"

# 1. Directory Hardening
mkdir -p logs findings payloads/ghost reports
chmod 700 logs findings payloads reports

# 2. Cryptographic Arming
KEY_DIR="/etc/shadowcypher"
KEY_FILE="$KEY_DIR/master.key"

if [ ! -f "$KEY_FILE" ]; then
    echo -e "\033[1;33m[*] Generating Master Cryptographic Key...\033[0m"
    sudo mkdir -p $KEY_DIR
    sudo dd if=/dev/urandom bs=32 count=1 2>/dev/null | sudo tee $KEY_FILE > /dev/null
    sudo chmod 600 $KEY_FILE
    echo -e "\033[1;32m[OK] Master Key Forge: SUCCESS\033[0m"
else
    echo -e "\033[1;32m[OK] Master Key detected: NOMINAL\033[0m"
fi

# 3. Native Core Compilation
echo -e "\033[1;34m[*] Building Native Signal Plane...\033[0m"
./shadow_sync.sh

# 4. Ghost Agent Forge
echo -e "\033[1;34m[*] Forging Ghost Agents (Zero-Trace Build)...\033[0m"
./shadowcypher/native/ghost/forge.sh

echo -e "\n\033[1;32m[!] SHADOWCYPHER IS ARMED AND READY FOR SOVEREIGN OPERATION.\033[0m"
echo -e "[*] Run 'python3 -m shadowcypher.app' to ignite the Citadel."
