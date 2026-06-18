#!/usr/bin/env bash
# Debug boot of ShadowOS ISO — captures serial log, waits for SSH, pulls Hyprland + systemd errors.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ISO=$(ls -t "$HERE/out/"*.iso 2>/dev/null | head -1)
SERIAL_LOG="/tmp/shadowos-serial.log"
HYPR_LOG="/tmp/shadowos-hypr.log"

if [[ -z "$ISO" ]]; then
    echo "No ISO in $HERE/out/ — build first."
    exit 1
fi

echo "==> ISO: $ISO"
echo "==> Serial log: $SERIAL_LOG"
echo "==> SSH will be on localhost:2222 (user: shadow / pass: shadow)"
echo ""

DISK="$HERE/test-disk.qcow2"
[[ ! -f "$DISK" ]] && qemu-img create -f qcow2 "$DISK" 32G

OVMF=""
for f in /usr/share/OVMF/OVMF_CODE_4M.fd \
          /usr/share/ovmf/OVMF.fd \
          /usr/share/qemu/OVMF.fd; do
    [[ -f "$f" ]] && { OVMF="$f"; break; }
done
UEFI_ARGS=()
[[ -n "$OVMF" ]] && UEFI_ARGS=(-drive "if=pflash,format=raw,readonly=on,file=$OVMF")

# Launch QEMU with:
#   - Serial output to file (catches systemd + kernel + SDDM errors)
#   - Display kept open (so Hyprland actually tries to start)
#   - SSH forwarded on 2222 so we can pull logs
qemu-system-x86_64 \
    -enable-kvm \
    -machine type=q35,accel=kvm \
    -cpu host,+topoext \
    -smp 4,sockets=1,cores=4,threads=1 \
    -m 4G \
    "${UEFI_ARGS[@]}" \
    -drive "file=$DISK,format=qcow2,if=virtio,cache=writeback" \
    -cdrom "$ISO" \
    -boot order=d,menu=on \
    -device virtio-vga \
    -device virtio-net-pci,netdev=net0 \
    -netdev "user,id=net0,hostfwd=tcp::2222-:22" \
    -device virtio-balloon \
    -device virtio-rng-pci \
    -audiodev pa,id=audio0 -device intel-hda -device hda-duplex,audiodev=audio0 \
    -usb -device usb-tablet \
    -serial "file:$SERIAL_LOG" \
    -display gtk,show-cursor=on \
    -name "ShadowOS Debug" &

QEMU_PID=$!
echo "==> QEMU PID: $QEMU_PID"
echo "==> Waiting for system to boot (up to 120s)..."

# Poll SSH until it responds — means system is up enough to login
READY=0
for i in $(seq 1 60); do
    if ssh -o StrictHostKeyChecking=no \
           -o ConnectTimeout=2 \
           -o PasswordAuthentication=no \
           -o BatchMode=yes \
           -p 2222 shadow@localhost true 2>/dev/null; then
        READY=1
        break
    fi
    # Also accept password auth (live image uses password)
    if sshpass -p shadow ssh -o StrictHostKeyChecking=no \
           -o ConnectTimeout=2 \
           -p 2222 shadow@localhost true 2>/dev/null; then
        READY=1
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

if [[ "$READY" -eq 0 ]]; then
    echo "==> SSH not available after 120s — checking serial log for early failures..."
    echo ""
    echo "=== SERIAL LOG (last 80 lines) ==="
    tail -80 "$SERIAL_LOG" 2>/dev/null || echo "(serial log empty)"
    echo ""
    echo "==> QEMU still running (PID $QEMU_PID) — inspect the window manually."
    wait "$QEMU_PID"
    exit 1
fi

echo "==> SSH up — pulling logs from VM..."

# Grab systemd failures
echo ""
echo "=== SYSTEMD FAILED UNITS ==="
sshpass -p shadow ssh -o StrictHostKeyChecking=no -p 2222 shadow@localhost \
    "systemctl --failed --no-pager 2>/dev/null" 2>/dev/null || echo "(could not query systemd)"

# Grab Hyprland log
echo ""
echo "=== HYPRLAND LOG ==="
sshpass -p shadow ssh -o StrictHostKeyChecking=no -p 2222 shadow@localhost \
    "cat ~/.local/share/hyprland/hyprland.log 2>/dev/null || echo '(no hyprland log found)'" \
    2>/dev/null | tail -100

# Grab SDDM journal
echo ""
echo "=== SDDM JOURNAL ==="
sshpass -p shadow ssh -o StrictHostKeyChecking=no -p 2222 shadow@localhost \
    "sudo journalctl -u sddm --no-pager -n 50 2>/dev/null" 2>/dev/null || echo "(could not read sddm journal)"

# Grab full journal errors
echo ""
echo "=== SYSTEMD JOURNAL ERRORS ==="
sshpass -p shadow ssh -o StrictHostKeyChecking=no -p 2222 shadow@localhost \
    "sudo journalctl -p err --no-pager -n 80 2>/dev/null" 2>/dev/null || echo "(could not read journal)"

# Save Hyprland log locally
sshpass -p shadow ssh -o StrictHostKeyChecking=no -p 2222 shadow@localhost \
    "cat ~/.local/share/hyprland/hyprland.log 2>/dev/null" > "$HYPR_LOG" 2>/dev/null || true

echo ""
echo "==> Done. Full Hyprland log saved to: $HYPR_LOG"
echo "==> Serial log: $SERIAL_LOG"
echo "==> QEMU still running (PID $QEMU_PID) — close the window when done."
wait "$QEMU_PID"
