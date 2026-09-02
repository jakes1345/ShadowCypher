#!/usr/bin/env bash
# qubes — Qubes OS-inspired compartmentalization mode for ShadowOS
# Enables VM isolation via libvirt/KVM and sets up trust-level networks.
set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ShadowOS QUBES MODE — VM Compartmentalization"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Start libvirt stack
if ! systemctl is-active --quiet libvirtd; then
    systemctl start libvirtd
    systemctl start virtlogd 2>/dev/null || true
    echo "  ✓ libvirtd started"
fi

# Enable KVM kernel modules
modprobe kvm 2>/dev/null || true
modprobe kvm_intel 2>/dev/null || true
modprobe kvm_amd 2>/dev/null || true
if [[ -e /dev/kvm ]]; then
    echo "  ✓ KVM hardware virtualization available"
else
    echo "  ⚠ KVM not available — VMs will run slowly (software emulation)"
fi

# Ensure default libvirt network is up
if virsh net-info default &>/dev/null; then
    virsh net-start default 2>/dev/null || true
    echo "  ✓ Default NAT network ready"
fi

# Create trust-level isolated networks
shadow-qube list 2>/dev/null || true

# Set user in libvirt group
if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG libvirt,kvm "$SUDO_USER" 2>/dev/null || true
    echo "  ✓ User '$SUDO_USER' added to libvirt and kvm groups"
fi

# Hyprland: source qube border rules if they exist
HYPR_QUBE_RULES="${HOME:-/root}/.config/hypr/qube-borders.conf"
if [[ ! -f "$HYPR_QUBE_RULES" ]]; then
    touch "$HYPR_QUBE_RULES"
fi

# Tell user if the source line needs adding to hyprland.conf
USER_HYPR="${HOME:-/root}/.config/hypr/hyprland.conf"
if ! grep -q "qube-borders.conf" "$USER_HYPR" 2>/dev/null; then
    echo "" >> "$USER_HYPR"
    echo "# Qubes-style trust-level window borders" >> "$USER_HYPR"
    echo "source = ~/.config/hypr/qube-borders.conf" >> "$USER_HYPR"
    hyprctl reload 2>/dev/null || true
    echo "  ✓ Hyprland trust-level border rules enabled"
fi

echo ""
echo "  ✓ QUBES MODE ACTIVE"
echo "    Use 'shadow-qube start <name>' to launch compartmentalized VMs"
echo ""
echo "  Quick start:"
echo "    shadow-qube disposable         # one-shot untrusted browsing"
echo "    shadow-qube new-vault secrets  # offline password vault"
echo "    shadow-qube start work TRUST=work"
echo ""
