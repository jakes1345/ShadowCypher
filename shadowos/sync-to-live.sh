#!/usr/bin/env bash
# Push profile + ShadowCypher fixes to a running ShadowOS VM/live session over SSH.
# No ISO rebuild.
#
#   ./sync-to-live.sh                    # QEMU default: shadow@127.0.0.1:2222
#   ./sync-to-live.sh user@192.168.1.50  # physical machine on LAN
#
# Prereqs: sshpass, rsync, VM booted with SSH (shadow/shadow)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
TARGET="${1:-shadow@127.0.0.1}"
PORT="${SHADOWOS_SSH_PORT:-2222}"
PASS="${SHADOWOS_SSH_PASS:-shadow}"

PATCH_ROOT="$REPO/shadowos/profile/airootfs"
APPLY="$HERE/shadowos-apply-fixes.sh"

[[ -d "$PATCH_ROOT" ]] || { echo "Missing $PATCH_ROOT"; exit 1; }
[[ -f "$APPLY" ]] || { echo "Missing $APPLY"; exit 1; }
command -v sshpass >/dev/null || { echo "Install: sudo apt install sshpass"; exit 1; }

SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10)
if [[ "$TARGET" == *@* ]]; then
    SSH_HOST="$TARGET"
else
    SSH_HOST="shadow@$TARGET"
fi

echo "═══════════════════════════════════════════════════════════"
echo "  ShadowOS live sync (no rebuild)"
echo "  Repo:   $REPO"
echo "  Target: $SSH_HOST port $PORT"
echo "═══════════════════════════════════════════════════════════"

echo ">> Waiting for SSH..."
for i in $(seq 1 60); do
    if timeout 2 bash -c "</dev/tcp/${SSH_HOST#*@}/${PORT}" 2>/dev/null; then
        break
    fi
    sleep 2
done

echo ">> Uploading patch payload..."
sshpass -p "$PASS" ssh "${SSH_OPTS[@]}" -p "$PORT" "$SSH_HOST" "echo '$PASS' | sudo -S rm -rf /tmp/shadowos-patch && mkdir -p /tmp/shadowos-patch"
sshpass -p "$PASS" rsync -az --delete \
    -e "ssh ${SSH_OPTS[*]} -p $PORT" \
    "$PATCH_ROOT/" "$SSH_HOST:/tmp/shadowos-patch/"
RSYNC_EX=(--exclude='meta-venv' --exclude='**/meta-venv/**' --exclude='.git' --exclude='__pycache__' --exclude='.venv' --exclude='venv')
sshpass -p "$PASS" ssh "${SSH_OPTS[@]}" -p "$PORT" "$SSH_HOST" 'mkdir -p /tmp/shadowos-sc-src'
for src in shadowcypher ai_engine shadowai shadow_skills shadowscript agent; do
    [[ -d "$REPO/$src" ]] || continue
    echo ">>   rsync $src"
    sshpass -p "$PASS" rsync -az "${RSYNC_EX[@]}" \
        -e "ssh ${SSH_OPTS[*]} -p $PORT" \
        "$REPO/$src/" "$SSH_HOST:/tmp/shadowos-sc-src/$src/"
done
[[ -d "$REPO/assets" ]] && \
    sshpass -p "$PASS" rsync -az \
        -e "ssh ${SSH_OPTS[*]} -p $PORT" \
        "$REPO/assets/" "$SSH_HOST:/tmp/shadowos-sc-src/assets/"
[[ -f "$REPO/config.example.json" ]] && \
    sshpass -p "$PASS" scp "${SSH_OPTS[@]}" -P "$PORT" "$REPO/config.example.json" "$SSH_HOST:/tmp/shadowos-sc-src/"
[[ -f "$APPLY" ]] && \
    sshpass -p "$PASS" scp "${SSH_OPTS[@]}" -P "$PORT" "$APPLY" "$SSH_HOST:/tmp/shadowos-apply-fixes.sh"

echo ">> Applying fixes on live system..."
sshpass -p "$PASS" ssh "${SSH_OPTS[@]}" -p "$PORT" "$SSH_HOST" \
    "echo '$PASS' | sudo -S SHADOWOS_PATCH_SRC=/tmp/shadowos-patch SHADOWOS_SC_SRC=/tmp/shadowos-sc-src SHADOWOS_REPO=/tmp/shadowos-sc-src bash /tmp/shadowos-apply-fixes.sh"

echo
echo ">> Done. In the VM: log out and log back in (shadow/shadow), or Super+S for ShadowCypher."
