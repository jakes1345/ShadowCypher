#!/usr/bin/env bash
# flash-usb.sh — safe writer for the ShadowOS ISO to a USB stick.
# Lists removable devices, asks for confirmation, then dd's.
set -euo pipefail

ISO="${1:-}"

if [[ -z "$ISO" ]]; then
    ISO=$(ls -t out/shadowos-*.iso 2>/dev/null | head -1 || true)
fi

[[ -f "$ISO" ]] || { echo "ISO not found. Usage: $0 <path/to/iso>"; exit 1; }

echo "ISO: $ISO ($(du -h "$ISO" | cut -f1))"
echo
echo "Removable block devices:"
lsblk -d -o NAME,SIZE,MODEL,TRAN,RM | awk 'NR==1 || $5==1'
echo

read -rp "Target device (e.g. sdb — NOT a partition like sdb1): " TARGET
TARGET_PATH="/dev/$TARGET"

[[ -b "$TARGET_PATH" ]] || { echo "Not a block device: $TARGET_PATH"; exit 1; }

# Refuse to flash to internal disks (rm=0)
RM=$(cat "/sys/block/$TARGET/removable" 2>/dev/null || echo 0)
if [[ "$RM" != "1" ]]; then
    echo "Refusing to flash to non-removable disk $TARGET_PATH. Use a USB stick."
    exit 1
fi

echo
echo "About to OVERWRITE $TARGET_PATH with $ISO"
echo "Everything currently on $TARGET_PATH will be ERASED."
read -rp 'Type "yes" to continue: ' CONFIRM
[[ "$CONFIRM" == "yes" ]] || { echo "aborted"; exit 1; }

echo
echo "Flashing..."
sudo dd if="$ISO" of="$TARGET_PATH" bs=4M status=progress oflag=sync
sync
echo
echo "Done. Eject and boot from $TARGET_PATH on your target machine."
