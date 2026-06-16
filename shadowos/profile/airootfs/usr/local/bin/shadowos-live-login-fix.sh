#!/usr/bin/env bash
# Live ISO only: SDDM cannot handle "password expired — change now".
# Reset demo credentials before the greeter starts.
set -euo pipefail

[[ -f /etc/shadowos/live-iso ]] || exit 0

if ! id shadow &>/dev/null; then
    exit 0
fi

echo "shadow:shadow" | chpasswd
chage -M 99999 -E -1 -I -1 shadow 2>/dev/null || true
chage -d "$(date +%F)" shadow 2>/dev/null || true
faillock --user shadow --reset 2>/dev/null || true
