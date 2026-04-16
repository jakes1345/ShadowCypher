#!/bin/bash
# --- SHADOWCYPHER GHOST FORGE ---
# Cross-compiling the Shadow-Ghost Agent for all major offensive targets.

echo "🔥 Igniting the Ghost Forge (Target: v1.0)..."

AGENT_DIR="/home/jack/ShadowCypher/shadowcypher/native/ghost"
OUTPUT_DIR="/home/jack/ShadowCypher/payloads/ghost"
mkdir -p $OUTPUT_DIR

# Using Sovereign-Go Runtime
export PATH="/home/jack/ShadowCypher/bin/go/bin:$PATH"

echo "[*] Forging [Linux_x64]..."
GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o $OUTPUT_DIR/ghost_linux_x64 $AGENT_DIR/agent.go

echo "[*] Forging [Windows_x64]..."
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o $OUTPUT_DIR/ghost_win_x64.exe $AGENT_DIR/agent.go

echo "[*] Forging [macOS_x64]..."
GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w" -o $OUTPUT_DIR/ghost_mac_x64 $AGENT_DIR/agent.go

echo "✅ Ghost Agents are armed and available in ${OUTPUT_DIR}"
ls -lh $OUTPUT_DIR
