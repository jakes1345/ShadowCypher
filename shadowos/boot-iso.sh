#!/usr/bin/env bash
# Boot ShadowOS ISO in QEMU.
#
#   ./boot-iso.sh --gui              # visible GTK window (recommended)
#   ./boot-iso.sh --headless         # VNC :5901 + auto screenshots
#   ./boot-iso.sh --gui out/foo.iso  # explicit ISO path
#
set -uo pipefail

MODE=gui
ISO=""
for arg in "$@"; do
    case "$arg" in
        --gui|--headless|--smoke) MODE="${arg#--}" ;;
        -*) echo "Unknown flag: $arg" >&2; exit 1 ;;
        *) ISO="$arg" ;;
    esac
done

ISO="${ISO:-$(ls -t /home/jack/ShadowCypher/shadowos/out/shadowos-*.iso 2>/dev/null | head -1)}"
[[ -f "$ISO" ]] || { echo "No ISO found. Pass path or build first." >&2; exit 1; }

pkill -f 'qemu-system-x86_64.*shadowos-' 2>/dev/null || true
sleep 1

QMP=/tmp/qemu-shadowos-qmp.sock
LOG=/tmp/shadowos-qemu-gui.log
rm -f "$QMP"

echo "══════════════════════════════════════════════════════════"
echo "  ShadowOS QEMU boot"
echo "  ISO:  $ISO"
echo "  Mode: $MODE"
echo "  Log:  $LOG"
echo "══════════════════════════════════════════════════════════"

COMMON=(
    qemu-system-x86_64
    -enable-kvm -cpu host -smp 4 -m 4G
    -drive "file=$ISO,media=cdrom"
    -boot d
    -vga virtio
    -qmp "unix:$QMP,server=on,wait=off"
    -netdev "user,id=net0,hostfwd=tcp::2222-:22"
    -device virtio-net-pci,netdev=net0
    -name "shadowos-$MODE"
)

case "$MODE" in
    gui)
        SHOTS=/tmp/shadowos-gui-capture
        mkdir -p "$SHOTS"
        echo ">> Opening GTK window on ${DISPLAY:-:0}"
        echo ">> Live login: shadow / shadow  (password field only — username is pre-filled)"
        echo ">> If login fails on May 29 ISO: Ctrl+Alt+F2 → shadow/shadow → set new password to shadow"
        echo ">> Or boot May 26 ISO, or rebuild after login-fix profile update"
        echo ">> SSH (after boot, key auth): ssh -p 2222 shadow@127.0.0.1"
        echo ">> Boot screenshots → $SHOTS/"
        nohup "${COMMON[@]}" -display gtk >"$LOG" 2>&1 &
        ;;
    headless|smoke)
        SHOTS=/tmp/shadowos-shots
        rm -rf "$SHOTS"
        mkdir -p "$SHOTS"
        echo ">> Headless — VNC 127.0.0.1:5901  screenshots → $SHOTS"
        nohup "${COMMON[@]}" -display none -vnc 127.0.0.1:1 >"$LOG" 2>&1 &
        ;;
    *)
        echo "Unknown mode: $MODE" >&2
        exit 1
        ;;
esac

QPID=$!
echo ">> QEMU pid: $QPID"
disown

for i in $(seq 1 40); do
    [[ -S "$QMP" ]] && break
    sleep 0.25
done

if [[ "$MODE" == headless || "$MODE" == smoke ]]; then
    SHOTS=/tmp/shadowos-shots
    rm -rf "$SHOTS"
    mkdir -p "$SHOTS"
elif [[ "$MODE" == gui ]]; then
    SHOTS=/tmp/shadowos-gui-capture
    rm -f "$SHOTS"/*.png "$SHOTS"/*.ppm 2>/dev/null || true
    mkdir -p "$SHOTS"
fi

if [[ -n "${SHOTS:-}" ]]; then
    qmp_shot() {
        local n="$1" label="$2"
        local out="$SHOTS/$(printf '%03d' "$n")-${label}.ppm"
        { echo '{"execute":"qmp_capabilities"}'
          echo "{\"execute\":\"screendump\",\"arguments\":{\"filename\":\"$out\"}}"
        } | timeout 3 socat - UNIX-CONNECT:"$QMP" 2>/dev/null >/dev/null || true
        if [[ -f "$out" ]] && command -v convert >/dev/null; then
            convert "$out" "${out%.ppm}.png" 2>/dev/null && rm -f "$out"
            echo "  shot $n → ${label}.png"
        fi
    }
    echo ">> Capturing boot timeline..."
    sleep 5;  qmp_shot 1 grub
    sleep 7;  qmp_shot 2 plymouth
    sleep 8;  qmp_shot 3 plymouth-mid
    sleep 15; qmp_shot 4 sddm
    sleep 25; qmp_shot 5 desktop-wait
    sleep 30; qmp_shot 6 desktop
    echo ">> Screenshots in $SHOTS/"
fi

echo
echo ">> QEMU running. Kill: pkill -f 'qemu-system-x86_64.*shadowos-$MODE'"
echo ">> Tail log: tail -f $LOG"
