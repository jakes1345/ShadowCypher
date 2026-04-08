#!/bin/bash
cd "$(dirname "$0")"
if [ -d "ai_engine/meta-venv" ] && [ -f "ai_engine/meta-venv/bin/activate" ]; then
    source ai_engine/meta-venv/bin/activate
elif [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi
DISPLAY="${DISPLAY:-:0}" python3 -m shadowcypher.app "$@"
