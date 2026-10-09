#!/usr/bin/env bash
# Revert qubes mode
set -e

echo "  Reverting qubes mode..."

# Stop all running shadow-qube VMs
if command -v virsh &>/dev/null && systemctl is-active --quiet libvirtd 2>/dev/null; then
    virsh list --name 2>/dev/null | grep -v '^$' | while read -r vm; do
        virsh shutdown "$vm" 2>/dev/null || true
    done
    echo "  ✓ VMs shut down"
fi

systemctl stop libvirtd 2>/dev/null || true
echo "  ✓ libvirtd stopped"
