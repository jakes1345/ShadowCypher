#!/usr/bin/env bash
# shadowos-live-login-fix — ensure live session autologin is configured correctly
set -e

STAMP=/var/lib/shadowos/live-login-fix.stamp
[ -f "$STAMP" ] && exit 0

# Fix getty autologin for the live user
GETTY_DIR=/etc/systemd/system/getty@tty1.service.d
mkdir -p "$GETTY_DIR"
cat > "$GETTY_DIR/autologin.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o '-p -f -- \\u' --noclear --autologin shadowos %I $TERM
EOF

systemctl daemon-reload 2>/dev/null || true

mkdir -p /var/lib/shadowos
touch "$STAMP"
