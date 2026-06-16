#!/usr/bin/env bash
# Recover May 29+ live ISO when demo password was forced to expire (SDDM + SSH break).
set -euo pipefail

PORT="${SHADOWOS_SSH_PORT:-2222}"
HOST="${1:-127.0.0.1}"
TEMP_PASS="${SHADOWOS_TEMP_PASS:-ShadowOS1!}"
DEMO_PASS="${SHADOWOS_SSH_PASS:-shadow}"

echo ">> Waiting for SSH on port $PORT..."
for i in $(seq 1 90); do
    timeout 2 bash -c "</dev/tcp/$HOST/$PORT" 2>/dev/null && break
    sleep 2
done

if ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -p "$PORT" "shadow@$HOST" 'echo ok' 2>/dev/null; then
    echo ">> SSH shell works — resetting demo password to $DEMO_PASS/$DEMO_PASS"
    sshpass -p "$TEMP_PASS" ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -p "$PORT" "shadow@$HOST" \
        "echo '$TEMP_PASS' | sudo -S bash -c 'echo shadow:shadow | chpasswd; chage -M 99999 -E -1 -I -1 shadow; chage -d \$(date +%F) shadow; faillock --user shadow --reset 2>/dev/null || true'" 2>/dev/null || \
    sshpass -p "$DEMO_PASS" ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -p "$PORT" "shadow@$HOST" \
        "echo '$DEMO_PASS' | sudo -S /usr/local/bin/shadowos-live-login-fix.sh" 2>/dev/null || true
    echo ">> Done — SDDM login: shadow / shadow"
    exit 0
fi

if ! command -v expect >/dev/null; then
    echo "Install expect: sudo apt install expect" >&2
    exit 1
fi

echo ">> Expired password — step 1: set temporary password via SSH TTY..."
expect <<EOF
set timeout 120
spawn ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p $PORT shadow@$HOST
expect {
    -re "Current password:" { send "$DEMO_PASS\r"; exp_continue }
    -re "New password:" { send "$TEMP_PASS\r"; exp_continue }
    -re "Retype" { send "$TEMP_PASS\r"; exp_continue }
    "password updated successfully" { exit 0 }
    "password unchanged" { exit 1 }
    eof { exit 0 }
    timeout { exit 1 }
}
EOF

echo ">> Step 2: restore demo password shadow/shadow..."
sshpass -p "$TEMP_PASS" ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -p "$PORT" "shadow@$HOST" \
    "echo '$TEMP_PASS' | sudo -S bash -c 'echo shadow:shadow | chpasswd; chage -M 99999 -E -1 -I -1 shadow; chage -d \$(date +%F) shadow; faillock --user shadow --reset 2>/dev/null || true; echo FIX_OK'"

echo ">> Done — SDDM login: shadow / shadow"
