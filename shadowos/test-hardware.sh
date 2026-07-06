#!/bin/bash

echo "🖥️  ShadowOS Hardware Test"
echo "=========================="
echo ""

RESULTS="/tmp/shadowos-hw-test-$(date +%Y%m%d-%H%M%S).json"

{
    echo "{"
    echo "  \"device\": \"$(hostnamectl | grep 'Hardware Vendor' | awk -F': ' '{print $2}')\","
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"tests\": {"

    # Boot time test
    echo "    \"boot_time\": $(( $(date +%s) - $(stat -c %Y /proc/1) )),"

    # Disk detection
    echo "    \"disk_detected\": $(lsblk | wc -l),"

    # Memory detection
    echo "    \"memory_mb\": $(free -m | awk '/^Mem:/ {print $2}'),"

    # USB ports
    echo "    \"usb_ports\": $(lsusb | wc -l),"

    # Wireless detection
    echo "    \"wireless\": \"$(ip link | grep -i wl | wc -l > 0 && echo 'detected' || echo 'none')\","

    # GPU detection
    echo "    \"gpu\": \"$(lspci | grep -i display | wc -l > 0 && echo 'detected' || echo 'none')\""

    echo "  }"
    echo "}"
} | tee "$RESULTS"

echo ""
echo "Test results saved to: $RESULTS"
echo "Share results for certification:"
echo "  https://github.com/jakes1345/ShadowCypher/issues"
