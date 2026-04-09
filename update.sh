#!/bin/bash
# ShadowCypher Master Update Protocol — Absolute Integrity V4

echo "-------------------------------------------------------"
echo "🌌 SHADOWCYPHER_TOTAL_REJUVENATION_PROTOCOL"
echo "-------------------------------------------------------"

# 1. Repository Sync
echo "[*] SYNCHRONIZING_CORE_LOGIC..."
git pull origin master || git pull origin main

# 2. Toolbelt Refresh
echo "[*] REFRESHING_OFFENSIVE_TEMPLATES..."

# Update Nuclei
if command -v nuclei &> /dev/null; then
    nuclei -ut
else
    # Check local install if not in path
    if [ -f "/usr/local/bin/nuclei" ]; then /usr/local/bin/nuclei -ut; fi
fi

# Update ExploitDB
if [ -d "tools/exploitdb" ]; then
    echo "[+] Updating Local ExploitDB..."
    cd tools/exploitdb && git pull && cd ../..
fi

# Update Responder
if [ -d "tools/Responder" ]; then
    echo "[+] Updating Local Responder..."
    cd tools/Responder && git pull && cd ../..
fi

# Update Phishing Assets
if [ -d "shadowcypher/modules/phish_data" ]; then
    echo "[+] Refreshing Phishing Templates..."
    cd shadowcypher/modules/phish_data && git pull && cd ../../../
fi

# 3. Dependency Audit
echo "[*] AUDITING_PYTHON_DEPENDENCIES..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install --upgrade -r requirements.txt
elif [ -d "ai_engine/meta-venv" ]; then
    source ai_engine/meta-venv/bin/activate
    pip install --upgrade -r requirements.txt
fi

echo "-------------------------------------------------------"
echo "[+] SYSTEM_TOTAL_UPDATE_COMPLETE. MISSION_READY."
echo "-------------------------------------------------------"
