#!/usr/bin/env bash
# Boot latest ShadowOS ISO in QEMU with KVM acceleration
# Simulates a real PC as closely as possible without dual-booting.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ISO=$(ls -t "$HERE/out/"*.iso 2>/dev/null | head -1)

if [[ -z "$ISO" ]]; then
    echo "No ISO found in $HERE/out/ — build first with: bash build-docker.sh"
    exit 1
fi

echo "Booting: $ISO"
echo "RAM: 4G | CPUs: 4 | KVM: yes | UEFI: yes"
echo "Controls: Ctrl+Alt+G = release mouse | Ctrl+Alt+F = fullscreen | Ctrl+Alt+Q = quit"
echo ""

# Create persistent disk image for install testing (8GB, only if not exists)
DISK="$HERE/test-disk.qcow2"
if [[ ! -f "$DISK" ]]; then
    qemu-img create -f qcow2 "$DISK" 32G
    echo "Created test disk: $DISK (32GB)"
fi

# OVMF UEFI firmware
OVMF=""
for f in /usr/share/OVMF/OVMF_CODE_4M.fd \
          /usr/share/ovmf/OVMF.fd \
          /usr/share/qemu/OVMF.fd; do
    [[ -f "$f" ]] && { OVMF="$f"; break; }
done

UEFI_ARGS=()
if [[ -n "$OVMF" ]]; then
    UEFI_ARGS=(-drive "if=pflash,format=raw,readonly=on,file=$OVMF")
    echo "UEFI: $OVMF"
else
    echo "UEFI: not found — booting BIOS (install ovmf for UEFI)"
fi

DISPLAY_ARGS=(-display gtk,show-cursor=on)
# Fallback to SDL if GTK not available
if ! qemu-system-x86_64 -display gtk -version >/dev/null 2>&1; then
    DISPLAY_ARGS=(-display sdl)
fi

exec qemu-system-x86_64 \
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
    -netdev user,id=net0,hostfwd=tcp::2222-:22 \
    -device virtio-balloon \
    -device virtio-rng-pci \
    -audiodev pa,id=audio0 \
    -device intel-hda \
    -device hda-duplex,audiodev=audio0 \
    -usb \
    -device usb-tablet \
    "${DISPLAY_ARGS[@]}" \
    -name "ShadowOS Test VM" \
    2>/dev/null
