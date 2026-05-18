#!/usr/bin/env bash
# Launch ShadowCypher dashboard on Hyprland workspace 1.
# Falls back to a foot welcome banner if the app isn't yet installed.
set -e

APP_DIR="/opt/shadowcypher"

# Resolve the actual app.py — repo layout puts it under shadowcypher/ subdir
for candidate in "$APP_DIR/app.py" "$APP_DIR/shadowcypher/app.py"; do
    if [[ -f "$candidate" ]]; then
        cd "$(dirname "$candidate")"
        exec python3 app.py "$@"
    fi
done

# Fallback: open a foot terminal with the ShadowOS welcome banner
exec foot --title "ShadowCypher (not yet installed)" -e bash -c '
fastfetch --config /etc/fastfetch/shadowos.jsonc 2>/dev/null || fastfetch
echo
echo "ShadowCypher app is not yet installed."
echo "Drop your shadowcypher/ directory into /opt/shadowcypher/ and re-login."
echo
exec zsh
'
