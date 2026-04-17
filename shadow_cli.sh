#!/bin/bash
# ShadowCLI Launcher — High-Velocity Tactical Bridge
# Phase Sigma: Autonomous Unification

# Resolve script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PYTHON_BIN="$DIR/venv/bin/python3"

if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

# Ensure tactical environment is present
export PYTHONPATH="$DIR:$PYTHONPATH"

# Check for Ollama
if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
    echo -e "\033[31m[!] NEURAL_OFFLINE: Ollama is not running. Mission signal lost.\033[0m"
    exit 1
fi

# Engagement
$PYTHON_BIN "$DIR/shadow_cli.py" "$@"
