#!/bin/bash
set -e

ISO_FILE="$1"

if [ -z "$ISO_FILE" ]; then
    echo "Usage: $0 <path-to-iso>"
    echo "Example: $0 shadowos-3.0.0.iso"
    exit 1
fi

if [ ! -f "$ISO_FILE" ]; then
    echo "Error: File not found: $ISO_FILE"
    exit 1
fi

echo "🔐 ShadowOS Download Verification"
echo "=================================="
echo ""

# Download checksums and signatures
BASEDIR=$(dirname "$ISO_FILE")
FILENAME=$(basename "$ISO_FILE")

echo "Downloading checksums and signatures..."
curl -fL "https://shadowcypher.site/downloads/SHA256SUMS" -o "$BASEDIR/SHA256SUMS"
curl -fL "https://shadowcypher.site/downloads/SHA256SUMS.sig" -o "$BASEDIR/SHA256SUMS.sig"

echo "Importing ShadowCypher release key..."
curl -fL "https://shadowcypher.site/shadowos_release.pub" | gpg --import --no-tty 2>/dev/null

echo ""
echo "Verifying GPG signature on checksums..."
if gpg --verify "$BASEDIR/SHA256SUMS.sig" "$BASEDIR/SHA256SUMS" 2>/dev/null; then
    echo "✓ GPG signature valid"
else
    echo "✗ GPG signature INVALID - download may be compromised"
    exit 1
fi

echo ""
echo "Verifying file integrity..."
cd "$BASEDIR"
if sha256sum -c SHA256SUMS --ignore-missing 2>/dev/null | grep "$FILENAME"; then
    echo "✓ SHA256 checksum valid"
else
    echo "✗ SHA256 checksum INVALID - file is corrupted"
    exit 1
fi

echo ""
echo "✓ Download verified successfully!"
echo "Safe to write to USB and boot"
