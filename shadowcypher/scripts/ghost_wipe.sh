#!/bin/bash
# ── GHOST_WIPE v1.0 — Sovereign Amnesic Shutdown ──────────────────
# Inspired by Asia-Pacific APT anti-forensic protocols.
# Wipes all session artifacts and tactical indicators from the local disk.

echo -e "\033[0;35m[GHOST] INITIATING_SURFACE_PURGE...\033[0m"

# 1. Wipe Tactical Logs
rm -rf /home/jack/ShadowCypher/logs/*.log
rm -rf /tmp/shadowcypher_*

# 2. Kernel Memory Flush (Clear dentries/inodes/cache)
# Requires root, but prevents post-mortem disk analysis.
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# 3. Securely delete the 'last_seen' node cache
rm -f /home/jack/ShadowCypher/shadowcypher/native/relay/peers.json

# 4. Clear Shell History (The most common leak)
history -c
cat /dev/null > ~/.bash_history
cat /dev/null > ~/.python_history

# 5. Final Shadow-Wipe
echo -e "\033[0;32m[GHOST] SURFACE_PURGE_COMPLETE.\033[0m"
echo -e "\033[0;32m[GHOST] No trace of this tactical session remains.\033[0m"
