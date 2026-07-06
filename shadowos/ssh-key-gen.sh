#!/bin/bash
set -e

KEYDIR="$HOME/.ssh"
KEYFILE="$KEYDIR/id_ed25519"

if [ -f "$KEYFILE" ]; then
    echo "SSH key already exists: $KEYFILE"
    exit 0
fi

mkdir -p "$KEYDIR"
chmod 700 "$KEYDIR"

echo "Generating ED25519 SSH key..."
ssh-keygen -t ed25519 -f "$KEYFILE" -N "" -C "$(hostname)-$(date +%Y%m%d)"

chmod 600 "$KEYFILE"
chmod 644 "$KEYFILE.pub"

echo "✓ SSH key generated:"
echo "  Private: $KEYFILE"
echo "  Public:  $KEYFILE.pub"
echo ""
echo "Add to remote server:"
echo "  ssh-copy-id -i $KEYFILE.pub user@remote"
