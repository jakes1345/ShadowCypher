#!/bin/bash
# ShadowCypher — Pull Gemma 4 and build the uncensored Heretic variant
set -e

echo "[*] Checking Ollama..."
if ! command -v ollama &>/dev/null; then
    echo "[!] Ollama not installed. Install: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

# Start Ollama if not running
if ! curl -s http://127.0.0.1:11434/api/tags &>/dev/null; then
    echo "[*] Starting Ollama service..."
    ollama serve &
    sleep 3
fi

echo "[*] Pulling base Gemma 4 model..."
ollama pull gemma4

echo "[*] Building gemma-4-heretic (uncensored security variant)..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ollama create gemma-4-heretic -f "$PROJECT_ROOT/Modelfile.gemma4-heretic"

echo "[+] Done. Available models:"
ollama list | grep -i gemma

echo ""
echo "[+] ShadowCypher is now configured to use gemma4 / gemma-4-heretic"
echo "[+] Run 'shadowcypher' to launch."
