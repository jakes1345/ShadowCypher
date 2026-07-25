#!/bin/bash
# ShadowCypher Guardian Agent — venv install (PEP 668 safe)
set -euo pipefail

cd "$(dirname "$0")"
VENV=".venv"

if [ ! -d "$VENV" ]; then
  echo "[*] creating venv at $VENV"
  python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet requests
echo "[+] dependencies installed"

cat > shadow-agent <<'EOF'
#!/bin/bash
# Convenience wrapper — runs the agent with the venv Python
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/shadowcypher_agent.py" "$@"
EOF
chmod +x shadow-agent

echo
echo "Done. Run with:"
echo "  ./shadow-agent init               # paste API key"
echo "  ./shadow-agent install-service    # install as persistent daemon (systemd)"
echo "  ./shadow-agent run                # foreground daemon mode"
echo "  ./shadow-agent once               # single scan"
echo "  ./shadow-agent status             # daemon status + logs"
echo "  ./shadow-agent uninstall-service  # remove daemon"
