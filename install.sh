#!/bin/bash
# 💠 SHADOWCYPHER: INDUSTRIAL INSTALLATION ENGINE (V19)
# MISSION: RESIDENT_TASK_FORCE_DEPLOYMENT (EXTERNAL_BYPASS)

echo "[SHADOW] INITIATING_TACTICAL_DEPLOYMENT_V19..."
APP_DIR=$(pwd)
ICON_PATH="$APP_DIR/assets/icon.png"
DESKTOP_FILE="$HOME/.local/share/applications/shadowcypher.desktop"

# 1. Dependency Pulse (Handling Externally Managed Environments)
echo "[SHADOW] PULSING_INDUSTRIAL_REQUIREMENTS..."
# We try venv first, but if system is strict, we allow --break-system-packages
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt

# 2. Advanced Security Tools Installation
echo "[SHADOW] INSTALLING_ADVANCED_ARSENAL (Nuclei, Ffuf, Responder, Sliver)..."
sudo apt-get install -y ffuf wget unzip curl git 2>/dev/null
if [ ! -d "/opt/Responder" ]; then
    sudo git clone https://github.com/SpiderLabs/Responder.git /opt/Responder
fi
if ! command -v nuclei &> /dev/null; then
    wget -q https://github.com/projectdiscovery/nuclei/releases/download/v3.2.0/nuclei_3.2.0_linux_amd64.zip
    sudo unzip nuclei_3.2.0_linux_amd64.zip -d /usr/local/bin/
    rm nuclei_3.2.0_linux_amd64.zip
fi
if ! command -v sliver-server &> /dev/null; then
    wget -q https://github.com/BishopFox/sliver/releases/download/v1.5.42/sliver-server_linux -O sliver-server
    sudo mv sliver-server /usr/local/bin/sliver-server
    sudo chmod +x /usr/local/bin/sliver-server
fi

# 3. Universal Launcher Shell
echo "[SHADOW] ENGINEERING_LAUNCHER_SHELL..."
cat <<EOF > "$APP_DIR/run.sh"
#!/bin/bash
cd "$APP_DIR"
DISPLAY=:0 python3 -m shadowcypher.app
EOF
chmod +x "$APP_DIR/run.sh"

# 3. Desktop Identity Protocol
echo "[SHADOW] REGISTERING_DESKTOP_SIGIL..."
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=ShadowCypher
Comment=Professional Obsidian Stealth Security Suite
Exec=$APP_DIR/run.sh
Icon=security-high
Categories=Development;Security;System;
Terminal=false
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"

echo "[SUCCESS] MISSION_ACCOMPLISHED: SHADOWCYPHER_IS_NOW_A_REAL_NATIVE_ASSET."
echo "[VITAL] YOU_CAN_NOW_LAUNCH_SHADOWCYPHER_FROM_YOUR_APPLICATIONS_MENU."
