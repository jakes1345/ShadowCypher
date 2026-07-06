#!/bin/bash
set -e

echo "🔧 ShadowOS Firmware Manager"
echo "============================"
echo ""

case "${1:-check}" in
    check)
        echo "Checking available firmware updates..."
        fwupdmgr refresh
        fwupdmgr get-updates
        ;;
    install)
        echo "Installing firmware updates..."
        fwupdmgr refresh
        fwupdmgr update --allow-older
        ;;
    list)
        echo "Installed firmware:"
        fwupdmgr get-devices
        ;;
    history)
        echo "Firmware update history:"
        fwupdmgr get-history
        ;;
    *)
        echo "Usage: $0 {check|install|list|history}"
        exit 1
        ;;
esac

echo ""
echo "✓ Firmware management complete"
