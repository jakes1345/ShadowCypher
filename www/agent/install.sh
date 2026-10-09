#!/usr/bin/env bash
# ShadowCypher Guardian Agent Installer
# Usage: curl -sSL https://shadowcypher.site/agent/install.sh | bash
set -euo pipefail

CYAN='\033[38;2;0;224;164m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "\n${CYAN}${BOLD}ShadowCypher Guardian Agent${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"

OS="$(uname -s)"
ARCH="$(uname -m)"
BASE="https://shadowcypher.site/releases"
VERSION="$(curl -sSL https://api.shadowcypher.site/v1/agent/version | python3 -c 'import sys,json; print(json.load(sys.stdin).get("version","0.3.0"))' 2>/dev/null || echo '0.3.0')"

echo "  OS:       $OS"
echo "  Arch:     $ARCH"
echo "  Version:  $VERSION"
echo ""

# Detect package manager and install Python deps if needed
if command -v apt-get &>/dev/null; then
    echo "[*] Installing Python deps..."
    sudo apt-get install -y python3 python3-pip python3-requests 2>/dev/null || true
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm python python-requests 2>/dev/null || true
fi

# Install the agent
INSTALL_DIR="${SHADOWCYPHER_AGENT_DIR:-/opt/shadowcypher-agent}"
sudo mkdir -p "$INSTALL_DIR"

echo "[*] Downloading agent to $INSTALL_DIR..."
sudo curl -sSL "$BASE/guardian-agent-$VERSION-linux-$ARCH.tar.gz" \
    | sudo tar -xz -C "$INSTALL_DIR" 2>/dev/null || {
    # Fallback: install Python-based agent
    echo "[*] Binary not found — installing Python agent..."
    sudo curl -sSL "$BASE/guardian-agent.py" -o "$INSTALL_DIR/guardian-agent.py"
    sudo chmod +x "$INSTALL_DIR/guardian-agent.py"
}

# Install systemd service
if command -v systemctl &>/dev/null; then
    sudo tee /etc/systemd/system/shadowcypher-guardian.service >/dev/null <<SERVICE
[Unit]
Description=ShadowCypher Guardian Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/opt/shadowcypher-agent/guardian-agent
Restart=on-failure
RestartSec=30
Environment=SHADOWCYPHER_API_KEY=
EnvironmentFile=-/etc/shadowcypher/guardian.env

[Install]
WantedBy=multi-user.target
SERVICE
    sudo systemctl daemon-reload
    sudo systemctl enable --now shadowcypher-guardian 2>/dev/null || true
fi

echo ""
echo -e "${CYAN}${BOLD}✓ Guardian Agent installed${RESET}"
echo ""
echo "  Set your API key:"
echo "  sudo mkdir -p /etc/shadowcypher"
echo "  echo 'SHADOWCYPHER_API_KEY=sc_live_...' | sudo tee /etc/shadowcypher/guardian.env"
echo "  sudo systemctl restart shadowcypher-guardian"
echo ""
echo "  Get your API key at: https://shadowcypher.site/?nav=account"
echo ""
