#!/usr/bin/env bash
# Boot the ShadowOS ISO in QEMU headless and capture screenshots at intervals
# via QMP screendump. Useful for visual smoke-testing without a desktop.
#
# Usage: ./boot-iso.sh out/shadowos-*.iso
set -uo pipefail

ISO="${1:-$(ls -t out/shadowos-*.iso 2>/dev/null | head -1)}"
if [[ ! -f "$ISO" ]]; then
    echo "No ISO found. Run build-docker.sh first." >&2
    exit 1
fi

SHOTS=/tmp/shadowos-shots
rm -rf "$SHOTS"
mkdir -p "$SHOTS"

QMP=/tmp/qemu-qmp.sock
rm -f "$QMP"

echo ">> Booting $ISO"
echo ">> Screenshots will land in $SHOTS"
echo ">> QMP socket: $QMP"

# Boot QEMU headless with QMP socket for screendump and VNC for live view if wanted
qemu-system-x86_64 \
    -enable-kvm -cpu host -smp 4 -m 4G \
    -drive file="$ISO",media=cdrom \
    -boot d \
    -vga virtio \
    -display none \
    -vnc 127.0.0.1:1 \
    -qmp "unix:$QMP,server=on,wait=off" \
    -netdev user,id=net0 -device virtio-net-pci,netdev=net0 \
    -name shadowos-test \
    > /tmp/qemu.log 2>&1 &

QPID=$!
echo ">> QEMU pid: $QPID"

# Wait for QMP to come up
for i in $(seq 1 30); do
    [[ -S "$QMP" ]] && break
    sleep 0.5
done
if [[ ! -S "$QMP" ]]; then
    echo "QMP socket never appeared. Check /tmp/qemu.log" >&2
    kill $QPID 2>/dev/null
    exit 1
fi

# Send QMP capabilities handshake
qmp() {
    local cmd="$1"
    {
        echo '{"execute":"qmp_capabilities"}'
        echo "$cmd"
    } | timeout 3 socat - UNIX-CONNECT:"$QMP" 2>/dev/null | tail -5
}

shot() {
    local n="$1"
    local out="$SHOTS/$(printf '%03d' "$n")-${2:-frame}.ppm"
    qmp "{\"execute\":\"screendump\",\"arguments\":{\"filename\":\"$out\"}}" > /dev/null
    if [[ -f "$out" ]]; then
        # Convert PPM → PNG for viewability
        if command -v convert >/dev/null; then
            convert "$out" "${out%.ppm}.png"
            rm "$out"
            echo "  shot $n → ${out%.ppm}.png"
        else
            echo "  shot $n → $out"
        fi
    fi
}

# Capture timeline:
#   t=5s    GRUB menu (default 5s timeout)
#   t=12s   GRUB → kernel + Plymouth handoff
#   t=20s   Plymouth animation
#   t=35s   SDDM login
#   t=60s   First-boot service / desktop wait
#   t=90s   Desktop (post-login if autologin)
echo ">> Capturing screenshots..."
sleep 5;  shot 1 grub
sleep 7;  shot 2 plymouth-early
sleep 8;  shot 3 plymouth-mid
sleep 15; shot 4 sddm
sleep 25; shot 5 desktop-wait
sleep 30; shot 6 desktop-final

echo
echo ">> Done. PNG screenshots in $SHOTS/"
echo ">> VNC view: vncviewer 127.0.0.1:1 (while QEMU runs)"
echo ">> Kill QEMU: kill $QPID"
ls -la "$SHOTS/"
