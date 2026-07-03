#!/usr/bin/env bash
# ShadowOS smoke test — boots the ISO headlessly, verifies desktop comes up.
# Usage: ./smoke-test.sh [path/to/iso]
# Exit:  0 = all checks pass, N = number of failed checks
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ISO="${1:-$(ls -t "$HERE/out/"*.iso 2>/dev/null | head -1)}"
SERIAL_LOG="/tmp/shadowos-smoke-serial.log"
TIMEOUT=180   # seconds to wait for SSH
SSH_PORT=2223 # avoid collision with qemu-debug.sh (2222)
VNC_DISPLAY=99 # VNC port 5999 — well out of range of anything real

RED='\033[1;31m'; GREEN='\033[1;32m'; CYAN='\033[1;36m'; NC='\033[0m'
fails=0; passes=0
QEMU_PID=""

pass() { echo -e "  ${GREEN}✓${NC} $1"; ((passes++)); }
fail() { echo -e "  ${RED}✗${NC} $1"; ((fails++)); }

cleanup() {
    [[ -n "$QEMU_PID" ]] && kill "$QEMU_PID" 2>/dev/null && wait "$QEMU_PID" 2>/dev/null || true
}
trap cleanup EXIT

# ── Preflight ──────────────────────────────────────────────────────────────
[[ -f "$ISO" ]] || { echo "No ISO found — build first or pass path as argument."; exit 1; }
for dep in qemu-system-x86_64 sshpass; do
    command -v "$dep" >/dev/null 2>&1 || { echo "Missing dependency: $dep"; exit 1; }
done

echo -e "${CYAN}ShadowOS Smoke Test${NC}"
echo "ISO:     $ISO"
echo "Timeout: ${TIMEOUT}s"
echo ""

# UEFI firmware (optional — falls back to BIOS if not found)
UEFI_ARGS=()
for f in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/ovmf/OVMF.fd /usr/share/qemu/OVMF.fd; do
    if [[ -f "$f" ]]; then UEFI_ARGS=(-drive "if=pflash,format=raw,readonly=on,file=$f"); break; fi
done

# ── Boot ───────────────────────────────────────────────────────────────────
echo "==> Booting ISO in QEMU (headless VNC :${VNC_DISPLAY})..."
rm -f "$SERIAL_LOG"

qemu-system-x86_64 \
    -enable-kvm \
    -machine type=q35,accel=kvm \
    -cpu host,+topoext \
    -smp 4 \
    -m 4G \
    "${UEFI_ARGS[@]}" \
    -drive "file=$ISO,format=raw,if=virtio,readonly=on" \
    -boot order=c \
    -device virtio-vga \
    -display "vnc=127.0.0.1:${VNC_DISPLAY}" \
    -device virtio-net-pci,netdev=net0 \
    -netdev "user,id=net0,hostfwd=tcp::${SSH_PORT}-:22" \
    -device virtio-rng-pci \
    -serial "file:${SERIAL_LOG}" \
    -name "ShadowOS Smoke Test" &
QEMU_PID=$!
echo "==> QEMU PID: $QEMU_PID"

# ── Wait for SSH ───────────────────────────────────────────────────────────
echo "==> Waiting for SSH on port ${SSH_PORT} (up to ${TIMEOUT}s)..."
READY=0
for ((i=0; i<TIMEOUT; i+=3)); do
    if sshpass -p shadow ssh \
           -o StrictHostKeyChecking=no \
           -o ConnectTimeout=2 \
           -o BatchMode=no \
           -p "$SSH_PORT" shadow@localhost true 2>/dev/null; then
        READY=1; break
    fi
    # Bail early if QEMU died
    kill -0 "$QEMU_PID" 2>/dev/null || { echo "QEMU exited early."; break; }
    printf "."
    sleep 3
done
echo ""

if [[ "$READY" -eq 0 ]]; then
    echo -e "${RED}FAIL: SSH never came up after ${TIMEOUT}s${NC}"
    echo ""
    echo "=== SERIAL LOG (last 50 lines) ==="
    tail -50 "$SERIAL_LOG" 2>/dev/null || echo "(empty)"
    exit 1
fi

ssh_run() {
    sshpass -p shadow ssh \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=5 \
        -p "$SSH_PORT" shadow@localhost \
        "$@" 2>/dev/null
}

echo ""
echo "==> SSH up — waiting 8s for desktop to settle..."
sleep 8

# ── Checks ─────────────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}[SYSTEMD]${NC}"
failed_units=$(ssh_run "systemctl list-units --state=failed --no-pager --plain --no-legend 2>/dev/null | wc -l")
failed_units=${failed_units//[^0-9]/}
[[ -z "$failed_units" ]] && failed_units=0
if [[ "${failed_units:-0}" -eq 0 ]]; then
    pass "no failed systemd units"
else
    fail "$failed_units failed systemd unit(s)"
    ssh_run "systemctl --failed --no-pager 2>/dev/null" | sed 's/^/      /' || true
fi

echo ""
echo -e "${CYAN}[DISPLAY MANAGER]${NC}"
sddm_state=$(ssh_run "systemctl is-active sddm 2>/dev/null" || echo "unknown")
if [[ "$sddm_state" == "active" || "$sddm_state" == "activating" ]]; then
    pass "sddm: $sddm_state"
else
    # Auto-login hands off quickly; SDDM may deactivate after session start
    if ssh_run "sudo journalctl -u sddm --no-pager -n 20 2>/dev/null" | grep -qi "started session\|autologin\|session opened"; then
        pass "sddm: auto-login session started (sddm is $sddm_state — expected)"
    else
        fail "sddm: $sddm_state — auto-login may not have fired"
        ssh_run "sudo journalctl -u sddm --no-pager -n 20 2>/dev/null" | sed 's/^/      /' || true
    fi
fi

echo ""
echo -e "${CYAN}[COMPOSITOR]${NC}"
hypr_pid=$(ssh_run "pgrep -u shadow -x Hyprland 2>/dev/null | head -1" || true)
if [[ -n "$hypr_pid" ]]; then
    pass "Hyprland running (pid $hypr_pid)"
else
    fail "Hyprland not running"
    echo "      --- Hyprland log (last 30 lines) ---"
    ssh_run "cat ~/.local/share/hyprland/hyprland.log 2>/dev/null | tail -30" | sed 's/^/      /' || true
fi

echo ""
echo -e "${CYAN}[CONFIG ERRORS]${NC}"
hypr_errs=$(ssh_run "grep -cE 'Config error|parse error|CRITICAL' ~/.local/share/hyprland/hyprland.log 2>/dev/null" || echo "0")
if [[ "${hypr_errs:-0}" -eq 0 ]]; then
    pass "no config/parse errors in Hyprland log"
else
    fail "$hypr_errs config/parse error(s) in Hyprland log"
    ssh_run "grep -E 'Config error|parse error|CRITICAL' ~/.local/share/hyprland/hyprland.log 2>/dev/null" | sed 's/^/      /' || true
fi

echo ""
echo -e "${CYAN}[PANEL]${NC}"
wb_pid=$(ssh_run "pgrep -u shadow -x waybar 2>/dev/null | head -1" || true)
if [[ -n "$wb_pid" ]]; then
    pass "waybar running (pid $wb_pid)"
else
    fail "waybar not running — panel crashed or failed to start"
    ssh_run "sudo journalctl --no-pager -n 30 2>/dev/null | grep -i waybar" | sed 's/^/      /' || true
fi

echo ""
echo -e "${CYAN}[WALLPAPER]${NC}"
wp_pid=$(ssh_run "pgrep -u shadow -x swaybg 2>/dev/null | head -1" || true)
if [[ -n "$wp_pid" ]]; then
    pass "swaybg running (pid $wp_pid)"
else
    fail "swaybg not running — wallpaper failed to load"
fi

echo ""
echo -e "${CYAN}[NETWORK]${NC}"
nm_state=$(ssh_run "systemctl is-active NetworkManager 2>/dev/null" || echo "unknown")
if [[ "$nm_state" == "active" ]]; then
    pass "NetworkManager: active"
else
    fail "NetworkManager: $nm_state"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo -e "  ${GREEN}PASS${NC}: $passes   ${RED}FAIL${NC}: $fails"
echo "═══════════════════════════════════════════════"
if [[ "$fails" -eq 0 ]]; then
    echo -e "${GREEN}SMOKE TEST PASSED${NC}"
else
    echo -e "${RED}SMOKE TEST FAILED${NC}"
    echo ""
    echo "Full serial log: $SERIAL_LOG"
fi
echo ""
exit "$fails"
