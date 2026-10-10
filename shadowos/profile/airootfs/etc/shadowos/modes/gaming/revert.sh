#!/usr/bin/env bash
# gaming revert — restore balanced CPU, stop gamemode
set -e

# CPU governor → balanced/schedutil
if command -v cpupower >/dev/null 2>&1; then
    cpupower frequency-set -g schedutil 2>/dev/null \
        || cpupower frequency-set -g powersave 2>/dev/null \
        || true
fi

# Stop gamemode service
systemctl stop gamemoded.service 2>/dev/null || true

echo "  ✓ Gaming mode reverted"
