#!/usr/bin/env bash
# End-to-end verify: boot ISO headless (SSH:2222), confirm the app CRASHED before,
# push the repo fix via sync-to-live, then confirm the app imports cleanly.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ISO="${1:-$(ls -t "$HERE/out/"*.iso 2>/dev/null | head -1)}"
SERIAL_LOG="/tmp/shadowos-verify-serial.log"
SSH_PORT=2222
VNC_DISPLAY=97
TIMEOUT=200
QEMU_PID=""
cleanup(){ [[ -n "$QEMU_PID" ]] && kill "$QEMU_PID" 2>/dev/null && wait "$QEMU_PID" 2>/dev/null || true; }
trap cleanup EXIT
[[ -f "$ISO" ]] || { echo "No ISO."; exit 1; }
echo "ISO: $ISO"
UEFI_ARGS=(); for f in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/ovmf/OVMF.fd; do [[ -f "$f" ]] && { UEFI_ARGS=(-drive "if=pflash,format=raw,readonly=on,file=$f"); break; }; done
rm -f "$SERIAL_LOG"
qemu-system-x86_64 -enable-kvm -machine type=q35,accel=kvm -cpu host -smp 4 -m 4G \
  "${UEFI_ARGS[@]}" -drive "file=$ISO,format=raw,if=virtio,readonly=on" -boot order=c \
  -device virtio-vga -display "vnc=127.0.0.1:${VNC_DISPLAY}" \
  -device virtio-net-pci,netdev=net0 -netdev "user,id=net0,hostfwd=tcp::${SSH_PORT}-:22" \
  -device virtio-rng-pci -serial "file:${SERIAL_LOG}" -name "ShadowOS Verify" &
QEMU_PID=$!
echo "==> waiting for SSH:${SSH_PORT}..."
READY=0
for ((i=0;i<TIMEOUT;i+=3)); do
  sshpass -p shadow ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=2 -p "$SSH_PORT" shadow@127.0.0.1 true 2>/dev/null && { READY=1; break; }
  kill -0 "$QEMU_PID" 2>/dev/null || { echo "QEMU died"; break; }
  printf .; sleep 3
done
echo ""
[[ "$READY" -eq 1 ]] || { echo "SSH never came up"; tail -30 "$SERIAL_LOG"; exit 1; }
R(){ sshpass -p shadow ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -p "$SSH_PORT" shadow@127.0.0.1 "$@" 2>/dev/null; }
sleep 6
echo "════ BEFORE fix: app import on the baked ISO ════"
R "cd /opt/shadowcypher && PYTHONPATH=/opt/shadowcypher python3 -c 'import shadowcypher.app; print(\"IMPORT OK\")' 2>&1 | tail -4"
echo ""
echo "════ pushing repo fix via sync-to-live.sh ════"
SHADOWOS_SSH_PORT=$SSH_PORT bash "$HERE/sync-to-live.sh" shadow@127.0.0.1 2>&1 | tail -8
echo ""
echo "════ INSPECT: is the NEW logger.py deployed to /opt? ════"
R "grep -c '_resolve_writable_log_dir' /opt/shadowcypher/shadowcypher/core/logger.py 2>&1"
R "ls -la /opt/shadowcypher | head -3; echo '--- logs dir ---'; ls -lad /opt/shadowcypher/logs 2>&1; id"
echo ""
echo "════ AFTER fix: app import (as shadow) ════"
R "cd /opt/shadowcypher && PYTHONPATH=/opt/shadowcypher python3 -c 'import shadowcypher.app; print(\"IMPORT OK\")' 2>&1 | tail -4"
echo ""
echo "════ AFTER fix: writable paths + persistence (as shadow) ════"
R "PYTHONPATH=/opt/shadowcypher python3 -c 'from shadowcypher.core.logger import logger; from shadowcypher.core.config import config; from shadowcypher.core.knowledge_graph import KnowledgeGraph; g=KnowledgeGraph(); print(\"log_dir :\", logger.log_dir); print(\"cfg     :\", config.writable_config_path()); print(\"kg_db   :\", g._db_path)' 2>&1 | grep -E 'log_dir|cfg|kg_db|Error'"
R "PYTHONPATH=/opt/shadowcypher python3 -c 'from shadowcypher.core.config import config; import json,os; config.set(\"identity\",\"handle\",\"persist_ok\"); p=config.writable_config_path(); print(\"persisted:\", json.load(open(p))[\"identity\"][\"handle\"] if os.path.exists(p) else \"NOT WRITTEN\")' 2>&1 | grep -E 'persisted|Error'"
echo "DONE"
