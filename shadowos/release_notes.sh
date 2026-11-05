#!/usr/bin/env bash
# Print GitHub release notes for a ShadowOS VERSION. Used by
# .github/workflows/release-notes.yml. Optional second argument: highlights.
set -euo pipefail

version="${1:-Unreleased}"
highlights="${2:-Major release with significant improvements}"

cat <<NOTES
# ShadowOS ${version} Release Notes

**Release Date:** $(date +%Y-%m-%d)

## Highlights

${highlights}

## Installation

### From USB
\`\`\`bash
# Write ISO to USB device
sudo dd if=shadowos-${version}.iso of=/dev/sdX bs=4M status=progress
\`\`\`

### From Cloud
\`\`\`bash
# QEMU/KVM
qemu-system-x86_64 -cdrom shadowos-${version}.iso -m 4G -smp 4
\`\`\`

## What's New

### Security Enhancements
- Enhanced kernel hardening
- Improved access controls
- Security audit logging

### User Experience
- Updated desktop environment
- Improved installation wizard
- Better hardware detection

### Developer Experience
- Enhanced CLI tools
- Better documentation
- Improved debugging support

## Known Issues

- [GitHub Issues](https://github.com/jakes1345/ShadowCypher/issues)

## Upgrading

\`\`\`bash
sudo shadowos-update check
sudo shadowos-update install
\`\`\`

## Support

- [Documentation](https://shadowcypher.site/docs)
- [Community Forums](https://forums.shadowcypher.site)
- [Issue Tracker](https://github.com/jakes1345/ShadowCypher/issues)

## Contributors

Thank you to all contributors in this release.

---

[Full Changelog](CHANGELOG.md)
NOTES
