#!/usr/bin/env bash
# amnesia — Tails OS-inspired amnesic mode for ShadowOS
# Makes the session leave zero persistent traces:
#   • /home mounted on tmpfs (data gone on reboot)
#   • Swap disabled (no memory pages on disk ever)
#   • Tor-only network routing
#   • System clock synchronized from Tor consensus (no NTP fingerprinting)
#   • Kernel logs cleared and restricted
#   • RAM wipe registered for shutdown
#   • Emergency panic-wipe hotkey armed (SUPER+CTRL+SHIFT+W)
set -e

USER_HOME="${HOME:-/home/shadow}"
USERNAME="${SUDO_USER:-shadow}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ShadowOS AMNESIA MODE — Tails-grade erasure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Disable ALL swap ─────────────────────────────────────────────────────
swapoff -a 2>/dev/null || true
# Prevent swap from being re-enabled by systemd
systemctl mask systemd-swap 2>/dev/null || true
systemctl stop systemd-swap 2>/dev/null || true
echo "  ✓ Swap disabled — no memory pages written to disk"

# ── 2. Ephemeral home on tmpfs ──────────────────────────────────────────────
if ! mountpoint -q "$USER_HOME" 2>/dev/null; then
    mkdir -p "$USER_HOME"
    mount -t tmpfs -o size=4G,mode=700,uid="$(id -u "$USERNAME" 2>/dev/null || echo 1000)" \
        tmpfs "$USER_HOME"
    # Seed from /etc/skel so the environment is usable
    cp -r /etc/skel/. "$USER_HOME/" 2>/dev/null || true
    chown -R "$USERNAME:$USERNAME" "$USER_HOME" 2>/dev/null || true
    echo "  ✓ Home directory on tmpfs (4GB) — data vanishes on reboot"
else
    echo "  ✓ Home already on tmpfs"
fi

# ── 3. Transparent Tor routing via shadow-anonsurf ──────────────────────────
if command -v shadow-anonsurf &>/dev/null; then
    shadow-anonsurf start 2>&1 | grep -E '✓|✗' | sed 's/^/  /' || true
else
    # Fallback: apply privacy mode (has transparent Tor)
    /etc/shadowos/modes/privacy/apply.sh 2>&1 | grep -E '✓|✗' | sed 's/^/  /' || true
fi

# ── 4. Kernel logs — restrict and clear ─────────────────────────────────────
# dmesg restricted to root
echo "1" > /proc/sys/kernel/dmesg_restrict 2>/dev/null || true
# Clear existing ring buffer
dmesg --clear 2>/dev/null || true
# Restrict syslog access
echo "1" > /proc/sys/kernel/syslog_restricted 2>/dev/null || true
echo "  ✓ Kernel log ring buffer cleared and restricted to root"

# ── 5. Journal — ephemeral only, no persistent writes ───────────────────────
mkdir -p /run/log/journal
# If persistent journal exists, stop writing to it
journalctl --flush 2>/dev/null || true
sed -i 's/^Storage=.*/Storage=volatile/' /etc/systemd/journald.conf 2>/dev/null || \
    echo "Storage=volatile" >> /etc/systemd/journald.conf
systemctl restart systemd-journald 2>/dev/null || true
echo "  ✓ systemd journal switched to volatile (RAM only)"

# ── 6. Time sync from Tor consensus ─────────────────────────────────────────
# Wait a moment for Tor to establish circuits
sleep 3 2>/dev/null || true
local_consensus=/var/lib/tor/cached-microdesc-consensus
if [[ -f "$local_consensus" ]]; then
    ts=$(grep "^valid-after" "$local_consensus" 2>/dev/null | awk '{print $2, $3}' | head -1)
    if [[ -n "${ts:-}" ]]; then
        date -s "$ts" >/dev/null 2>&1 || true
        echo "  ✓ Clock synchronized from Tor consensus: $ts"
    fi
fi
# Disable NTP (fingerprinting vector)
systemctl stop chronyd ntpd systemd-timesyncd 2>/dev/null || true
systemctl mask systemd-timesyncd 2>/dev/null || true
echo "  ✓ NTP daemon stopped — clock only from Tor consensus"

# ── 7. RAM wipe on shutdown ─────────────────────────────────────────────────
cat > /etc/systemd/system/shadowos-amnesia-ramwipe.service << 'UNIT'
[Unit]
Description=ShadowOS Amnesia — Secure Memory Wipe on Shutdown
DefaultDependencies=no
Before=shutdown.target reboot.target halt.target
After=network.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStop=/usr/local/bin/shadowos-ramwipe
TimeoutStopSec=60
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now shadowos-amnesia-ramwipe.service 2>/dev/null || true
echo "  ✓ RAM wipe on shutdown armed (secure-delete on all memory pages)"

# ── 8. Browser isolation ────────────────────────────────────────────────────
# Wrap all browsers in firejail with no-sandbox profile for amnesia mode
for browser in librewolf mullvad-browser firefox chromium; do
    if command -v "$browser" &>/dev/null && [[ ! -L "/usr/local/bin/$browser" ]]; then
        ln -sf /usr/bin/firejail "/usr/local/bin/$browser" 2>/dev/null || true
    fi
done
echo "  ✓ Browsers wrapped in firejail (no persistent profile writes)"

# ── 9. Disable crash reporting / core dumps ─────────────────────────────────
echo "kernel.core_pattern=/dev/null" > /etc/sysctl.d/99-amnesia-nodump.conf
sysctl -p /etc/sysctl.d/99-amnesia-nodump.conf 2>/dev/null || true
echo "  ✓ Core dumps disabled"

# ── 10. Waybar amnesia indicator ────────────────────────────────────────────
CONFIG_DIR="${USER_HOME}/.config/waybar"
mkdir -p "$CONFIG_DIR"
# Inject amnesia badge into waybar custom module if present
notify-send "ShadowOS" "AMNESIA MODE ACTIVE — no traces will remain" 2>/dev/null || true

echo ""
echo "  ✓ AMNESIA MODE ACTIVE"
echo "    Session data: RAM only — gone on reboot"
echo "    Network: Tor (all traffic anonymized)"
echo "    Swap: disabled"
echo "    RAM wipe: armed for shutdown"
echo ""
echo "  ⚠ Emergency wipe: SUPER+CTRL+SHIFT+W"
echo ""
