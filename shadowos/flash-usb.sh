#!/usr/bin/env bash
# flash-usb.sh — safe writer for the ShadowOS ISO to a USB stick.
# - Lists removable devices only (refuses internal disks)
# - Verifies ISO SHA256 against companion .sha256 file if present
# - dd with progress, sync, then verifies first 1GB readback
# - Friendly colored output

set -euo pipefail

TEAL=$'\033[1;36m'; GREEN=$'\033[1;32m'; RED=$'\033[1;31m'
YELLOW=$'\033[1;33m'; BOLD=$'\033[1m'; NC=$'\033[0m'

cat <<EOF
${BOLD}${TEAL}╔═══════════════════════════════════════════╗
║       SHADOWOS  ·  USB  FLASH  TOOL       ║
╚═══════════════════════════════════════════╝${NC}

EOF

ISO="${1:-}"
if [[ -z "$ISO" ]]; then
    ISO=$(ls -t out/shadowos-*.iso 2>/dev/null | head -1 || true)
fi
[[ -f "$ISO" ]] || { echo "${RED}ISO not found.${NC} Usage: $0 <path/to/iso>"; exit 1; }

# Verify ISO integrity
if [[ -f "$ISO.sha256" ]]; then
    echo "${TEAL}[*]${NC} Verifying ISO SHA256 against companion file..."
    if (cd "$(dirname "$ISO")" && sha256sum -c "$(basename "$ISO").sha256" 2>&1 | head -1); then
        echo "    ${GREEN}OK${NC}"
    else
        echo "    ${RED}MISMATCH — refusing to flash a corrupted ISO${NC}"
        exit 1
    fi
fi
ISO_SIZE=$(du -h "$ISO" | cut -f1)
ISO_BYTES=$(stat -c%s "$ISO")

echo "${TEAL}[*]${NC} ISO: ${BOLD}$ISO${NC}  ($ISO_SIZE)"
echo
echo "${TEAL}[*]${NC} Removable block devices:"
lsblk -d -o NAME,SIZE,MODEL,TRAN,RM | awk 'NR==1 || $5==1' | sed 's/^/      /'
echo

read -rp "${BOLD}Target device${NC} (e.g. ${YELLOW}sdb${NC} — NOT a partition like sdb1): " TARGET
TARGET_PATH="/dev/$TARGET"
[[ -b "$TARGET_PATH" ]] || { echo "${RED}Not a block device: $TARGET_PATH${NC}"; exit 1; }

# Refuse to flash to internal disks (rm=0)
RM=$(cat "/sys/block/$TARGET/removable" 2>/dev/null || echo 0)
if [[ "$RM" != "1" ]]; then
    echo "${RED}Refusing to flash to non-removable disk $TARGET_PATH.${NC}"
    echo "   This safety check prevents you from accidentally wiping your system drive."
    echo "   If you really need to flash to this device, use dd manually."
    exit 1
fi

TARGET_SIZE_BYTES=$(blockdev --getsize64 "$TARGET_PATH" 2>/dev/null || echo 0)
TARGET_SIZE=$(lsblk -dno SIZE "$TARGET_PATH" | tr -d ' ')

if [[ "$TARGET_SIZE_BYTES" -lt "$ISO_BYTES" ]]; then
    echo "${RED}Device too small: $TARGET_SIZE < ISO size${NC}"
    exit 1
fi

echo
echo "${YELLOW}${BOLD}WARNING:${NC} About to OVERWRITE ${BOLD}$TARGET_PATH${NC} ($TARGET_SIZE) with"
echo "         ${BOLD}$ISO${NC}"
echo "         Everything currently on $TARGET_PATH will be ${RED}PERMANENTLY ERASED${NC}."
echo
read -rp "Type \"${BOLD}yes${NC}\" to continue: " CONFIRM
[[ "$CONFIRM" == "yes" ]] || { echo "aborted"; exit 1; }

# Unmount any mounted partitions on the target first
for part in $(lsblk -ln -o NAME "$TARGET_PATH" | tail -n +2); do
    sudo umount "/dev/$part" 2>/dev/null || true
done

echo
echo "${TEAL}[*]${NC} Flashing (this takes 5-15 minutes for a 10GB ISO)..."
sudo dd if="$ISO" of="$TARGET_PATH" bs=4M status=progress oflag=sync conv=fdatasync
sync
echo
echo "${TEAL}[*]${NC} Verifying first 1GB readback..."
EXPECTED=$(head -c 1G "$ISO" | sha256sum | awk '{print $1}')
ACTUAL=$(sudo head -c 1G "$TARGET_PATH" | sha256sum | awk '{print $1}')
if [[ "$EXPECTED" == "$ACTUAL" ]]; then
    echo "    ${GREEN}OK — first 1GB matches${NC}"
else
    echo "    ${RED}MISMATCH — flash may be corrupted, re-flash recommended${NC}"
    exit 1
fi

cat <<EOF

${GREEN}${BOLD}✓ Flash complete${NC}

${BOLD}Next steps:${NC}
  1. Eject the USB: ${TEAL}sudo eject $TARGET_PATH${NC}
  2. Boot your target machine from the USB (BIOS/UEFI boot menu, usually F12/F11/Esc)
  3. ShadowOS will auto-login as ${BOLD}shadow${NC} (live session)
  4. To install permanently: open the Activities launcher → "Install ShadowOS"

EOF
