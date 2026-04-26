#!/bin/bash
# ShadowCypher: Sovereign Node Setup (v1.0.0)
# This script hardens a fresh Linux box and installs the ShadowNode engine (Coolify).

set -e

echo "--------------------------------------------------"
echo "🛡️  SHADOWCYPHER: SOVEREIGN NODE INITIALIZATION"
echo "--------------------------------------------------"

# 1. System Hardening
echo "[*] Hardening system and installing dependencies..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose ufw curl git build-essential

# 2. Firewall Configuration
echo "[*] Configuring firewall (UFW)..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 3. Installing ShadowNode Engine (Coolify)
echo "[*] Installing Coolify (Self-Hosted Cloud Engine)..."
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash

# 4. Finalizing
IP_ADDR=$(hostname -I | awk '{print $1}')
echo ""
echo "--------------------------------------------------"
echo "✅ SHADOWNODE READY"
echo "--------------------------------------------------"
echo "ACCESS_URL: http://$IP_ADDR:3000"
echo "INSTRUCTIONS:"
echo "1. Visit the URL above to set up your admin account."
echo "2. Connect your GitHub Repo (jakes1345/ShadowCypher)."
echo "3. Deploy the index.html and styles.css as a Static Site."
echo "4. (Optional) Deploy a PostgreSQL database for local storage."
echo "--------------------------------------------------"
