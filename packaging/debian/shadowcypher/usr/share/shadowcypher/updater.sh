#!/usr/bin/env bash
# shadowcypher --update
# Downloads and installs the latest .deb from releases.shadowcypher.site
set -euo pipefail

RELEASES="https://releases.shadowcypher.site"
CURRENT_VERSION="$(dpkg-query -W -f='${Version}' shadowcypher 2>/dev/null || echo '0.0.0')"
ARCH="$(dpkg --print-architecture 2>/dev/null || uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')"

echo "ShadowCypher updater"
echo "  installed: ${CURRENT_VERSION}  arch: ${ARCH}"

# Fetch manifest
MANIFEST="$(curl -fsSL --max-time 10 "${RELEASES}/manifest.json" 2>/dev/null || true)"
if [[ -z "$MANIFEST" ]]; then
    echo "ERROR: could not reach releases server" >&2
    exit 1
fi

LATEST="$(echo "$MANIFEST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version',''))" 2>/dev/null || true)"
if [[ -z "$LATEST" ]]; then
    echo "ERROR: could not parse manifest" >&2
    exit 1
fi

echo "  latest:    ${LATEST}"

# Compare using dpkg's version ordering
if dpkg --compare-versions "$CURRENT_VERSION" ge "$LATEST" 2>/dev/null; then
    echo "Already up to date."
    exit 0
fi

echo "Updating ${CURRENT_VERSION} → ${LATEST}..."

DEB_NAME="shadowcypher_${LATEST}_${ARCH}.deb"
DEB_URL="${RELEASES}/latest/${DEB_NAME}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Downloading ${DEB_NAME}..."
if ! curl -fL --progress-bar --max-time 300 -o "${TMP}/${DEB_NAME}" "$DEB_URL"; then
    echo "ERROR: download failed — ${DEB_URL}" >&2
    exit 1
fi

echo "Installing..."
if [[ "$EUID" -ne 0 ]]; then
    sudo dpkg -i "${TMP}/${DEB_NAME}"
    sudo apt-get install -f -y 2>/dev/null || true
else
    dpkg -i "${TMP}/${DEB_NAME}"
    apt-get install -f -y 2>/dev/null || true
fi

echo "ShadowCypher updated to ${LATEST}."
