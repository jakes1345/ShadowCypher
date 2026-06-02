#!/usr/bin/env bash
# Build ShadowCypher .deb package
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG_DIR="$ROOT/packaging/debian/shadowcypher"
OUT_DIR="$ROOT/releases"
VERSION=$(cat "$ROOT/VERSION" 2>/dev/null || echo "3.0.0")

echo "Building ShadowCypher v$VERSION .deb..."

# Sync source into package
rsync -a --delete \
  --exclude='*.pyc' --exclude='__pycache__' \
  --exclude='.git' --exclude='packaging' \
  --exclude='releases' --exclude='store_assets' \
  --exclude='*.aab' --exclude='*.apk' \
  "$ROOT/shadowcypher/" "$PKG_DIR/usr/share/shadowcypher/shadowcypher/"

rsync -a "$ROOT/native/" "$PKG_DIR/usr/share/shadowcypher/native/"

# Copy icon
if [[ -f "$ROOT/native/icons/shadowcypher-256.png" ]]; then
  cp "$ROOT/native/icons/shadowcypher-256.png" "$PKG_DIR/usr/share/pixmaps/shadowcypher.png"
fi

# Update version in control
sed -i "s/^Version:.*/Version: $VERSION/" "$PKG_DIR/DEBIAN/control"

# Build
mkdir -p "$OUT_DIR"
dpkg-deb --build --root-owner-group "$PKG_DIR" "$OUT_DIR/shadowcypher-${VERSION}-amd64.deb"

echo "Built: $OUT_DIR/shadowcypher-${VERSION}-amd64.deb"
echo "Install: sudo dpkg -i $OUT_DIR/shadowcypher-${VERSION}-amd64.deb"
