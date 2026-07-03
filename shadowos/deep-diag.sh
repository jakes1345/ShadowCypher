#!/usr/bin/env bash
# ShadowOS deep diagnostic — boots the ISO once, dumps the full runtime error
# picture over SSH so we can fix real problems instead of guessing.
# Usage: ./deep-diag.sh [path/to/iso]
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ISO="${1:-$(ls -t "$HERE/out/"*.iso 2>/dev/null | head -1)}"
SERIAL_LOG="/tmp/shadowos-diag-serial.log"
TIMEOUT=200
SSH_PORT=2224
VNC_DISPLAY=98
QEMU_PID=""

cleanup() { [[ -n "$QEMU_PID" ]] && kill "$QEMU_PID" 2>/dev/null && wait "$QEMU_PID" 2>/dev/null || true; }
trap cleanup EXIT

[[ -f "$ISO" ]] || { echo "No ISO found."; exit 1; }
echo "ISO: $ISO"

UEFI_ARGS=()
for f in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/ovmf/OVMF.fd; do
    [[ -f "$f" ]] && { UEFI_ARGS=(-drive "if=pflash,format=raw,readonly=on,file=$f"); break; }
done

rm -f "$SERIAL_LOG"
qemu-system-x86_64 -enable-kvm -machine type=q35,accel=kvm -cpu host -smp 4 -m 4G \
    "${UEFI_ARGS[@]}" \
    -drive "file=$ISO,format=raw,if=virtio,readonly=on" -boot order=c \
    -device virtio-vga -display "vnc=127.0.0.1:${VNC_DISPLAY}" \
    -device virtio-net-pci,netdev=net0 \
    -netdev "user,id=net0,hostfwd=tcp::${SSH_PORT}-:22" \
    -device virtio-rng-pci -serial "file:${SERIAL_LOG}" -name "ShadowOS Diag" &
QEMU_PID=$!

echo "==> Waiting for SSH (up to ${TIMEOUT}s)..."
READY=0
for ((i=0; i<TIMEOUT; i+=3)); do
    if sshpass -p shadow ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 \
           -p "$SSH_PORT" shadow@localhost true 2>/dev/null; then READY=1; break; fi
    kill -0 "$QEMU_PID" 2>/dev/null || { echo "QEMU exited early."; break; }
    printf "."; sleep 3
done
echo ""
[[ "$READY" -eq 0 ]] && { echo "SSH never came up."; tail -40 "$SERIAL_LOG"; exit 1; }

sleep 10  # let desktop + autostarts settle

R() { sshpass -p shadow ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p "$SSH_PORT" shadow@localhost "$@" 2>/dev/null; }

sec() { echo ""; echo "════════════════════ $1 ════════════════════"; }

sec "FAILED SYSTEMD UNITS (system)"
R "systemctl --failed --no-pager --plain --no-legend"
sec "FAILED SYSTEMD UNITS (user)"
R "systemctl --user --failed --no-pager --plain --no-legend"
sec "JOURNAL ERRORS (priority<=err, this boot)"
R "sudo journalctl -p err -b --no-pager --no-hostname 2>/dev/null | tail -60"
sec "HYPRLAND LOG errors/warnings"
R "grep -iE 'err|warn|critical|fail' ~/.local/share/hyprland/hyprland.log 2>/dev/null | tail -30"
sec "WAYBAR stderr (from journal)"
R "journalctl --user --no-pager 2>/dev/null | grep -i waybar | tail -20"
sec "SHADOWCYPHER app import check"
R "cd /opt/shadowcypher && PYTHONPATH=/opt/shadowcypher python3 -c 'import shadowcypher.app; print(\"import OK\")' 2>&1 | tail -20"
sec "SHADOWCYPHER python deps"
R "for m in gi psutil aiohttp pydantic_settings websockets cryptography; do python3 -c \"import \$m\" 2>/dev/null && echo \"  ok \$m\" || echo \"  MISSING \$m\"; done"
sec "SHADOWCYPHER autostart log"
R "cat ~/.local/state/shadowcypher/autostart.log 2>/dev/null | tail -20"
sec "OLLAMA service"
R "systemctl is-enabled ollama 2>/dev/null; systemctl is-active ollama 2>/dev/null"
sec "MODE scripts present + executable"
R "ls -la /etc/shadowos/modes/*/apply.sh 2>/dev/null"
sec "shadow-mode current + dry test"
R "cat /etc/shadowos/current-mode 2>/dev/null; echo '---'; shadow-mode 2>&1 | head -5"
sec "DISK / writable /opt check"
R "touch /opt/shadowcypher/.writetest 2>&1 && echo 'opt writable' && rm -f /opt/shadowcypher/.writetest || echo 'opt NOT writable (logger fallback needed)'"
sec "CPU/MEM at idle"
R "uptime; free -m | head -2"
sec "DONE"
echo "Serial log: $SERIAL_LOG"
