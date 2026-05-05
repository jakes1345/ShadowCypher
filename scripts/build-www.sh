#!/usr/bin/env bash
# Copies static web assets into www/ for Capacitor packaging.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WWW="$ROOT/www"

mkdir -p "$WWW/r"

for f in index.html styles.css manifest.json sw.js \
          icon-192.png icon-512.png apple-touch-icon.png \
          docs.html device.html privacy.html terms.html \
          status.html roadmap.html integrity.json; do
  [ -f "$ROOT/$f" ] && cp "$ROOT/$f" "$WWW/$f"
done

# r/ referral redirect
[ -f "$ROOT/r/index.html" ] && cp "$ROOT/r/index.html" "$WWW/r/index.html"

echo "[+] www/ synced"
