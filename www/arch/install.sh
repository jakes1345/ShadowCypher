#!/usr/bin/env bash
# ShadowOS — add the [shadowos] pacman repo to an existing Arch install.
#
# Usage:   curl -fsSL https://shadowcypher.site/arch/install.sh | sudo bash
# Or:      curl -fsSL https://shadowcypher.site/arch/install.sh | sudo bash -s -- --meta
#          (the --meta flag also installs shadowos-meta after configuring the repo)

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This installer needs root. Re-run with sudo." >&2
    exit 1
fi

REPO_URL="https://shadowcypher.site/arch"
KEY_FINGERPRINT="3ACC49288AC4F3BCBE1CDE98D9F1D18F1313F083"
KEY_URL="${REPO_URL}/shadowos.gpg"

CYAN='\033[1;36m'; GREEN='\033[1;32m'; RED='\033[1;31m'; NC='\033[0m'
ok()  { echo -e "${GREEN}[+]${NC} $1"; }
log() { echo -e "${CYAN}[*]${NC} $1"; }
err() { echo -e "${RED}[-]${NC} $1" >&2; exit 1; }

command -v pacman >/dev/null || err "This script only works on Arch Linux."
command -v curl   >/dev/null || pacman -S --noconfirm --needed curl

# 1. Import the signing key
log "Fetching ShadowOS signing key…"
TMPKEY=$(mktemp)
curl -fsSL "$KEY_URL" -o "$TMPKEY" || err "Could not fetch $KEY_URL"
pacman-key --add "$TMPKEY" >/dev/null
pacman-key --lsign-key "$KEY_FINGERPRINT" >/dev/null
rm -f "$TMPKEY"
ok "Key imported and locally signed: $KEY_FINGERPRINT"

# 2. Drop the mirrorlist
log "Writing /etc/pacman.d/shadowos-mirrorlist…"
cat > /etc/pacman.d/shadowos-mirrorlist <<EOF
# ShadowOS official mirror
Server = ${REPO_URL}/\$repo/\$arch
EOF
ok "Mirrorlist written"

# 3. Add the [shadowos] section to pacman.conf if not already present
if ! grep -q '^\[shadowos\]' /etc/pacman.conf; then
    log "Adding [shadowos] to /etc/pacman.conf…"
    cat >> /etc/pacman.conf <<'EOF'

[shadowos]
SigLevel = Required DatabaseOptional
Include = /etc/pacman.d/shadowos-mirrorlist
EOF
    ok "Repository entry added"
else
    log "[shadowos] entry already present, skipping"
fi

# 4. Sync the new repo
log "Syncing package database…"
pacman -Sy >/dev/null
ok "Repo is live. Browse: pacman -Sl shadowos"

# 5. Optional: install meta-package
if [[ "${1:-}" == "--meta" ]]; then
    log "Installing shadowos-meta (full ShadowOS experience)…"
    pacman -S --noconfirm shadowos-meta
    ok "ShadowOS installed. Reboot for Plymouth + SDDM + GRUB themes."
else
    cat <<EOF

${GREEN}[✓]${NC} ShadowOS repo configured.

Next steps:
  ${CYAN}sudo pacman -S shadowos-meta${NC}         install the full ShadowOS experience
  ${CYAN}sudo pacman -S shadowcypher${NC}          install just the security app
  ${CYAN}pacman -Sl shadowos${NC}                  browse available packages

EOF
fi
