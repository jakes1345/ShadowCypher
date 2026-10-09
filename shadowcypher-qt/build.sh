#!/usr/bin/env bash
# Build ShadowCypher Qt6 app
# Requirements: cmake, ninja, qt6-base-dev (Debian/Ubuntu) or qt6-qtbase-devel (Arch/Fedora)
set -e

BUILD_DIR="build"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

cmake .. \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/usr

ninja -j"$(nproc)"

echo ""
echo "Build complete: $BUILD_DIR/shadowcypher"
echo "Run: ./$BUILD_DIR/shadowcypher"
echo "Install (as root): sudo ninja -C $BUILD_DIR install"
