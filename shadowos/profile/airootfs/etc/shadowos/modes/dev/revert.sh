#!/usr/bin/env bash
# dev revert — restore balanced CPU, close dev ports
set -e

# CPU governor → balanced/schedutil
if command -v cpupower >/dev/null 2>&1; then
    cpupower frequency-set -g schedutil 2>/dev/null \
        || cpupower frequency-set -g powersave 2>/dev/null \
        || true
fi

# Remove dev firewall table
nft delete table inet shadowos_dev 2>/dev/null || true

echo "  ✓ Dev mode reverted"
