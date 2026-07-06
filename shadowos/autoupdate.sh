#!/bin/bash

# ShadowOS Automatic Security Update Script

LOG_FILE="/var/log/shadowos-autoupdate.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting security update check..."

# Check for updates
if sudo pacman -Sy 2>/dev/null | grep -q "database is up to date"; then
    log "System is up to date"
    exit 0
fi

# Check if security-related packages have updates
SECURITY_PKGS="linux-hardened linux-headers glibc openssl shadow sudo"

for pkg in $SECURITY_PKGS; do
    if pacman -Q "$pkg" >/dev/null 2>&1; then
        UPDATE=$(pacman -Sp --print-format='%v' "$pkg" 2>/dev/null)
        CURRENT=$(pacman -Q --quiet "$pkg" 2>/dev/null)

        if [ "$UPDATE" != "$CURRENT" ]; then
            log "Security update available: $pkg ($CURRENT -> $UPDATE)"
            sudo pacman -S --noconfirm "$pkg" >> "$LOG_FILE" 2>&1
        fi
    fi
done

log "Security update check complete"
