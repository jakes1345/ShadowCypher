#!/usr/bin/env bash
# ShadowCypher — macOS installer
set -e

echo "==> ShadowCypher macOS bootstrap"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew required. Install from https://brew.sh then re-run."
  exit 1
fi

echo "==> Installing GTK3 + PyGObject stack via brew"
brew install python@3.12 gtk+3 pygobject3 gobject-introspection pkg-config cairo py3cairo adwaita-icon-theme

echo "==> Installing Python requirements"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "==> Optional offensive tools (skip any you don't want)"
brew install nmap whois openssl curl || true

echo "==> First-run will prompt for your handle on launch."
echo "    Run: python3 -m shadowcypher.app"
