#!/bin/bash
# --- SHADOWCYPHER SOVEREIGN SETUP v3.0 ---
# Orchestrates the complete installation of the ShadowCypher tactical ecosystem.

set -e

PROJECT_ROOT="$(dirname "$(readlink -f "$0")")/.."
cd "$PROJECT_ROOT"

echo -e "\e[36m[SETUP] IGNITING_SOVEREIGN_INSTALLATION...\e[0m"

# 1. System Dependencies (Informational)
echo -e "\e[90m[INFO] Verifying system primitives (Go, Python, GTK)...\e[0m"
if ! command -v go &> /dev/null; then echo -e "\e[31m[ERROR] Go not found.\e[0m"; exit 1; fi
if ! command -v python3 &> /dev/null; then echo -e "\e[31m[ERROR] Python3 not found.\e[0m"; exit 1; fi

# 2. Virtual Environment
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "\e[36m[VENV] Creating sovereign environment...\e[0m"
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# 3. Python Dependencies
echo -e "\e[36m[DEPS] Synchronizing Python strike-set...\e[0m"
pip install --upgrade pip
pip install -r requirements.txt

# 4. Native Compilation (Go Relay & Arsenal)
echo -e "\e[36m[BUILD] Compiling native signal layer...\e[0m"
(cd shadowcypher/native/relay && go build -o shadow-relay relay.go)

echo -e "\e[36m[BUILD] Compiling arsenal primitives...\e[0m"
find shadowcypher/arsenal/primitives -name "main.go" | while read go_file; do
    target_dir=$(dirname "$go_file")
    bin_name="$(basename "$target_dir")"
    echo "  -> Building $bin_name"
    (cd "$target_dir" && go build -o "$bin_name" main.go)
done

# 5. Elite Tool Acquisition
echo -e "\e[36m[ELITE] Synchronizing God-Tier Arsenal...\e[0m"
mkdir -p tools/elite
cd tools/elite

# MHDDoS
if [ ! -d "MHDDoS" ]; then
    git clone https://github.com/MatrixTM/MHDDoS.git
    cd MHDDoS && pip install -r requirements.txt && cd ..
fi

# GHunt
if [ ! -d "GHunt" ]; then
    git clone https://github.com/mxrch/GHunt.git
    cd GHunt && pip install -r requirements.txt && cd ..
fi

# garak
if [ ! -d "garak" ]; then
    git clone https://github.com/leondz/garak.git
    cd garak && pip install -r requirements.txt && cd ..
fi

cd "$PROJECT_ROOT"

# 6. Asset Synchronization (Proxies)
if [ -f "tools/elite/MHDDoS/fetch_proxies.sh" ]; then
    bash tools/elite/MHDDoS/fetch_proxies.sh
fi

echo -e "\e[32m[SUCCESS] SHADOWCYPHER_SOVEREIGN_READY.\e[0m"
echo -e "Launch with: ./shadowcypher_launch"
