#!/usr/bin/env bash
# ==============================================================================
# SHADOWCYPHER // ENTERPRISE BUILD SYSTEM
# ==============================================================================
# Hardened Debian Packaging Script.
# Features: Secret stripping, crypto generation, and isolated venv handling.

set -euo pipefail

# --- Typography & Colors ---
BOLD='\033[1m'
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
log_succ()  { echo -e "${GREEN}[OK]${NC}   $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()   { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# --- Banner ---
cat << "EOF"
    __  ___     __         ______ __        _     
   /  |/  /___ / /_  ____ / ____// /_  ____(_)___ 
  / /|_/ // _ \/ __/ / __ `/ /    / __ \/ __ `/ / __ \
 / /  / //  __/ /_  / /_/ / /___ / / / / /_/ / / /_/ /
/_/  /_/ \___/\__/  \__,_/\____//_/ /_/\__,_/_/ .___/ 
      SOVEREIGN TACTICAL SUITE // BUILD SYSTEM /_/      
EOF
echo -e "${BOLD}==============================================================================${NC}\n"

# --- Prerequisites Check ---
log_info "Verifying build environment dependencies..."
for cmd in dpkg-deb rsync python3 openssl; do
    if ! command -v "$cmd" &> /dev/null; then
        log_err "Missing required build tool: $cmd"
    fi
done
log_succ "Build environment validated."

# --- Version Extraction ---
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [ ! -f "shadowcypher/__init__.py" ]; then
    log_err "Could not locate shadowcypher/__init__.py for version extraction."
fi

VERSION="$(python3 -c "import re,sys; m=re.search(r'__version__\s*=\s*[\"\']([^\"\']+)', open('shadowcypher/__init__.py').read()); print(m.group(1) if m else sys.exit('cannot read __version__'))")"
ARCH="amd64"
PACKAGE_NAME="shadowcypher"
BUILD_DIR="build/${PACKAGE_NAME}_${VERSION}_${ARCH}"

log_info "Target Version: ${BOLD}v${VERSION}${NC}"
log_info "Target Architecture: ${BOLD}${ARCH}${NC}"

# --- Cleanup & Scaffold ---
log_info "Scaffolding build directories..."
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/DEBIAN" \
         "${BUILD_DIR}/opt/${PACKAGE_NAME}" \
         "${BUILD_DIR}/usr/bin" \
         "${BUILD_DIR}/usr/share/applications" \
         "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps" \
         "${BUILD_DIR}/etc/shadowcypher"

# --- Control File ---
log_info "Generating Debian control file..."
cat <<EOF > "${BUILD_DIR}/DEBIAN/control"
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.10), python3-venv, python3-pip, bash, python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, libcairo2-dev, libgirepository1.0-dev, pkg-config, python3-dev, gcc, rsync, openssl
Maintainer: Sovereign Operator <admin@shadowcypher.local>
Description: ShadowCypher Tactical Security Suite
 Enterprise-grade offensive security platform with autonomous AI orchestration.
 Engineered for absolute digital sovereignty and zero-trace operations.
EOF

cat <<EOF > "${BUILD_DIR}/DEBIAN/conffiles"
/etc/shadowcypher/config.json
EOF

# --- Post-Install Script ---
log_info "Injecting hardened post-install cryptography generation..."
cat <<'POSTINST_EOF' > "${BUILD_DIR}/DEBIAN/postinst"
#!/usr/bin/env bash
set -e

INSTALL_DIR="/opt/shadowcypher"
ETC_DIR="/etc/shadowcypher"
KEY_FILE="${ETC_DIR}/master.key"
ADMIN_KEY="${ETC_DIR}/admin_private.pem"
ADMIN_PUB="${ETC_DIR}/admin_public.pem"
SESSION_SECRET="${ETC_DIR}/session.secret"

echo "[SHADOWCYPHER] Initializing secure environment..."

mkdir -p "${ETC_DIR}"
chmod 0750 "${ETC_DIR}"

if [ ! -f "${KEY_FILE}" ]; then
    echo " -> Generating per-install master key..."
    head -c 32 /dev/urandom > "${KEY_FILE}"
    chmod 0600 "${KEY_FILE}"
fi

if [ ! -f "${ADMIN_KEY}" ]; then
    echo " -> Generating RSA-4096 Sovereign keypair..."
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out "${ADMIN_KEY}" 2>/dev/null
    openssl rsa -pubout -in "${ADMIN_KEY}" -out "${ADMIN_PUB}" 2>/dev/null
    chmod 0600 "${ADMIN_KEY}"
    chmod 0644 "${ADMIN_PUB}"
fi

if [ ! -f "${SESSION_SECRET}" ]; then
    head -c 32 /dev/urandom | base64 | tr -d '\n=' | tr '/+' '_-' > "${SESSION_SECRET}"
    chmod 0600 "${SESSION_SECRET}"
fi

if [ ! -f "${ETC_DIR}/config.json" ] && [ -f "${INSTALL_DIR}/config.example.json" ]; then
    cp "${INSTALL_DIR}/config.example.json" "${ETC_DIR}/config.json"
    chmod 0640 "${ETC_DIR}/config.json"
fi

echo " -> Establishing Python virtual environment..."
cd "${INSTALL_DIR}"
python3 -m venv --system-site-packages venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip --quiet || true

if [ -f "requirements.txt" ]; then
    echo " -> Installing dependencies (timeout 120s to prevent apt hang)..."
    timeout 120s pip install -r requirements.txt --quiet || echo "[!] Warning: Dependency installation timed out or failed. You may need to run 'pip install -r requirements.txt' manually in /opt/shadowcypher/venv."
fi

[ -f "${INSTALL_DIR}/run.sh" ] && chmod +x "${INSTALL_DIR}/run.sh"
chmod +x /usr/bin/shadowcypher

echo ""
echo "========================================================"
echo " SHADOWCYPHER v__VERSION__ DEPLOYMENT COMPLETE"
echo "========================================================"
echo " Launch using command: shadowcypher"
exit 0
POSTINST_EOF

sed -i "s/__VERSION__/${VERSION}/g" "${BUILD_DIR}/DEBIAN/postinst"
chmod 0755 "${BUILD_DIR}/DEBIAN/postinst"

# --- Uninstall Scripts ---
cat <<'PRERM_EOF' > "${BUILD_DIR}/DEBIAN/prerm"
#!/usr/bin/env bash
set -e
pkill -f "shadowcypher.app" 2>/dev/null || true
exit 0
PRERM_EOF
chmod 0755 "${BUILD_DIR}/DEBIAN/prerm"

cat <<'POSTRM_EOF' > "${BUILD_DIR}/DEBIAN/postrm"
#!/usr/bin/env bash
set -e
case "$1" in
    purge)
        rm -rf /opt/shadowcypher/venv
        rm -rf /etc/shadowcypher
        ;;
esac
exit 0
POSTRM_EOF
chmod 0755 "${BUILD_DIR}/DEBIAN/postrm"

# --- Staging & Security Excludes ---
log_info "Staging application files with strict security excludes..."
rsync -a \
    --exclude='.git' --exclude='.github' --exclude='.gitignore' \
    --exclude='.claude' --exclude='.sisyphus' --exclude='.vscode' \
    --exclude='.ruff_cache' --exclude='.cursor' \
    --exclude='venv' --exclude='test_venv' --exclude='ai_engine/meta-venv' \
    --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='build' --exclude='*.deb' \
    --exclude='bin/go/**' --exclude='distill/checkpoints/**' \
    --exclude='logs/**' --exclude='*.log' \
    --exclude='findings' --exclude='loot' --exclude='reports' \
    --exclude='sessions' --exclude='tickets' --exclude='scratch' \
    --exclude='shadow_test' --exclude='dashboard*.png' \
    --exclude='*.gguf' --exclude='models' --exclude='wordlists' \
    --exclude='*.pem' --exclude='!shadowcypher/core/admin_public.pem' \
    --exclude='*.key' --exclude='.session-secret' --exclude='session.secret' \
    --exclude='.env*' --exclude='admin_private*' --exclude='auth.json' \
    --exclude='credentials' --exclude='extracted_creds.txt' \
    --exclude='config.json' --exclude='config/local_config.py' \
    --exclude='*.db' --exclude='*.sqlite' \
    ./ "${BUILD_DIR}/opt/${PACKAGE_NAME}/"

if [ -f "shadowcypher/core/admin_public.pem" ]; then
    mkdir -p "${BUILD_DIR}/opt/${PACKAGE_NAME}/shadowcypher/core"
    cp "shadowcypher/core/admin_public.pem" "${BUILD_DIR}/opt/${PACKAGE_NAME}/shadowcypher/core/admin_public.pem"
fi

# --- Leak Audit ---
log_info "Auditing staged tree for cryptographic material leaks..."
LEAKED="$(find "${BUILD_DIR}/opt/${PACKAGE_NAME}" \
    \( -name '*.pem' -not -name 'admin_public.pem' \
       -o -name '*.key' \
       -o -name '.session-secret' \
       -o -name 'session.secret' \
       -o -name '.env' \
       -o -name 'admin_private*' \
       -o -name 'auth.json' \) 2>/dev/null | grep -v '/bin/go/' || true)"

if [ -n "${LEAKED}" ]; then
    log_err "FATAL SEC-AUDIT FAILURE. Secrets leaked into staging tree:\n${LEAKED}"
fi
log_succ "Zero-leak audit passed."

# --- Bin Wrapper & Desktop File ---
cat <<EOF > "${BUILD_DIR}/usr/bin/shadowcypher"
#!/usr/bin/env bash
cd /opt/${PACKAGE_NAME}
exec ./venv/bin/python3 -m shadowcypher.app "\$@"
EOF
chmod 0755 "${BUILD_DIR}/usr/bin/shadowcypher"

if [ -f "config.example.json" ]; then
    cp "config.example.json" "${BUILD_DIR}/opt/${PACKAGE_NAME}/config.example.json"
fi

cat <<EOF > "${BUILD_DIR}/usr/share/applications/shadowcypher.desktop"
[Desktop Entry]
Version=${VERSION}
Type=Application
Name=ShadowCypher
GenericName=Tactical Security Suite
Comment=Enterprise sovereign tactical infrastructure.
Exec=/usr/bin/shadowcypher
Path=/opt/${PACKAGE_NAME}
Icon=shadowcypher
Terminal=false
Categories=Network;Security;System;Monitor;
Keywords=pentest;security;ai;
StartupNotify=true
StartupWMClass=org.shadowcypher.ShadowCypher
EOF
chmod 0644 "${BUILD_DIR}/usr/share/applications/shadowcypher.desktop"

# Icons
[ -f "native/icon.svg" ] && cp "native/icon.svg" "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/shadowcypher.svg"
for size in 16 24 32 48 64 128 256; do
    if [ -f "native/icons/shadowcypher-${size}.png" ]; then
        mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/${size}x${size}/apps"
        cp "native/icons/shadowcypher-${size}.png" "${BUILD_DIR}/usr/share/icons/hicolor/${size}x${size}/apps/shadowcypher.png"
    fi
done

# --- Build Execution ---
log_info "Executing dpkg-deb compression..."
dpkg-deb --build "${BUILD_DIR}" > /dev/null

DEB_PATH="build/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
DEB_SIZE="$(du -h "${DEB_PATH}" | cut -f1)"
sha256sum "${DEB_PATH}" > "${DEB_PATH}.sha256"

echo -e "\n${GREEN}${BOLD}==============================================================================${NC}"
echo -e "${GREEN}[SUCCESS]${NC} Build finalized: ${BOLD}${DEB_PATH}${NC} (${DEB_SIZE})"
echo -e "${CYAN}SHA256:${NC}   $(cat "${DEB_PATH}.sha256")"
echo -e "${CYAN}INSTALL:${NC}  sudo apt install ./${DEB_PATH}"
echo -e "${GREEN}${BOLD}==============================================================================${NC}\n"
