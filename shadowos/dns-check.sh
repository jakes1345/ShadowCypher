#!/bin/bash

echo "🔒 ShadowOS DNS Security Check"
echo "==============================="
echo ""

# Check DNS resolver
echo "DNS Resolver:"
systemctl status systemd-resolved --no-pager | grep Active

echo ""
echo "DNSSEC Status:"
resolvectl status | grep DNSSEC

echo ""
echo "Current DNS Server:"
resolvectl query google.com | head -5

echo ""
echo "Testing DNSSEC validation:"
# Should be authenticated
dig google.com +dnssec

echo ""
echo "✓ DNS security check complete"
