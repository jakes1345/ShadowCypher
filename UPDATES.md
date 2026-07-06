# ShadowCypher Update System

The ShadowCypher update system provides automatic and manual security updates for ShadowOS and related components. This document describes how to check for, install, and manage updates.

## Quick Start

### Check for Updates
```bash
shadowos-update check
```

### Install Available Updates
```bash
shadowos-update install
```

### View Current System Version
```bash
shadowos-update info
```

## Update Channels

ShadowCypher supports three update channels:

### 1. **Stable** (Default)
- **Release cycle**: Monthly security updates + critical patches
- **Target audience**: Production systems, users prioritizing stability
- **Testing**: Fully tested releases
- **Command**: `shadowos-update check --channel stable`
- **Automatic**: Enabled by default with 7-day delay

### 2. **Beta**
- **Release cycle**: Bi-weekly updates with new features + security patches
- **Target audience**: Advanced users, security professionals
- **Testing**: Tested but may contain edge cases
- **Command**: `shadowos-update check --channel beta`
- **Automatic**: Disabled by default, opt-in only

### 3. **Nightly**
- **Release cycle**: Daily development builds
- **Target audience**: Contributors, early adopters
- **Testing**: Minimal testing, cutting-edge features
- **Command**: `shadowos-update check --channel nightly`
- **Automatic**: Disabled by default, opt-in only
- **Warning**: May be unstable

## Checking for Updates

### Manual Check
```bash
shadowos-update check
```

Output:
```
ShadowCypher Update Check
═══════════════════════════════════════════════════════════════
Channel: stable
Current version: 2.4.1
Latest version: 2.5.0
Status: Update available
Size: 148 MB
Released: 2026-07-03
Security patches: 3
New features: 8

Update now? [y/N]:
```

### Check Specific Channel
```bash
shadowos-update check --channel beta
shadowos-update check --channel nightly
```

### Check Without Prompt
```bash
shadowos-update check --no-prompt
```

### Verbose Output
```bash
shadowos-update check --verbose
```

## Installing Updates

### Automatic Installation
Updates can be scheduled to install automatically:

```bash
shadowos-update schedule --when daily --time 02:00
```

Valid time values: `--when [daily|weekly|monthly]`

Systemd timer configuration:
```bash
systemctl enable shadowos-autoupdate.timer
systemctl start shadowos-autoupdate.timer
```

### Manual Installation

**Interactive mode:**
```bash
shadowos-update install
```

**Non-interactive mode:**
```bash
shadowos-update install --auto
```

**Installation process:**
1. Download update package from update server
2. Verify cryptographic signature (SHA-256 + ECDSA)
3. Backup current system state
4. Extract and apply updates
5. Run post-update integrity checks
6. Restart affected services

### Installation with Progress
```bash
$ shadowos-update install --verbose
Downloading update (2.5.0)... [=========>          ] 67%
Verifying signature... OK
Creating backup... OK
Applying updates... [====================] 100%
Running integrity checks... OK
Services restarted: shadow-guardian (2.1s), shadow-agent (1.3s)

Update completed successfully. System is now version 2.5.0.
```

### Installation Options

| Option | Description | Default |
|--------|-------------|---------|
| `--auto` | Non-interactive, auto-confirm | false |
| `--verbose` | Show detailed progress | false |
| `--dry-run` | Test without applying changes | false |
| `--backup` | Create system backup before update | true |
| `--restart-services` | Restart affected services after update | true |
| `--no-verify` | Skip signature verification (NOT recommended) | false |

## Update Server Integration

The update system connects to the ShadowCypher update server to:

- Check available updates for current version/platform
- Download update packages
- Verify package authenticity via ECDSA signatures
- Report update statistics (anonymized)

### Server Endpoints

**Check for updates:**
```
GET /api/updates/check?version=2.4.1&platform=linux&arch=x86_64&channel=stable
```

Response:
```json
{
  "available": true,
  "current_version": "2.4.1",
  "latest_version": "2.5.0",
  "released": "2026-07-03",
  "size_mb": 148,
  "changelog": "Security patches (3), New features (8)",
  "download_url": "https://updates.shadowcypher.site/packages/shadowcypher-2.5.0-x86_64.tar.gz",
  "signature_url": "https://updates.shadowcypher.site/packages/shadowcypher-2.5.0-x86_64.tar.gz.sig",
  "signature_algorithm": "sha256+ecdsa"
}
```

**Download package:**
```
GET /api/updates/download/{version}/{filename}
```

## Rollback Procedures

### View Rollback Options
```bash
shadowos-update rollback --list
```

Output:
```
Available rollback points:
1. Version 2.4.1 (Current previous version) - 2026-06-28
2. Version 2.4.0 - 2026-06-15
3. Version 2.3.5 - 2026-05-20
```

### Rollback to Previous Version
```bash
shadowos-update rollback
```

### Rollback to Specific Version
```bash
shadowos-update rollback --version 2.4.1
```

### Rollback Process
1. Verify backup integrity
2. Stop affected services
3. Restore system files from backup
4. Verify system integrity
5. Restart services
6. Perform validation tests

**Note:** Rollbacks maintain data integrity. User data is never affected.

### Automatic Rollback
If post-update validation fails, automatic rollback triggers:

```bash
shadowos-update install --auto-rollback-on-failure
```

## System Information

### View Current Versions
```bash
shadowos-update info
```

Output:
```
ShadowCypher System Information
═══════════════════════════════════════════════════════════════
Core Version:         2.4.1
Guardian Module:      3.2.1
Agent Version:        1.8.5
Shadow Backend:       Build 2643

Update Channel:       stable
Last Update Check:    2026-07-04 14:32:15 UTC
Last Update:          2026-06-28 02:15:00 UTC
Next Auto-Update:     2026-07-05 02:00:00 UTC

Platform:             linux
Architecture:         x86_64
Kernel:               6.17.0-35-generic
```

### View Update History
```bash
shadowos-update info --history
```

### Check Available Backups
```bash
shadowos-update info --backups
```

## Release Notes Format

Update packages include release notes in the following format:

```
# ShadowCypher 2.5.0 Release Notes
Released: July 3, 2026

## Security Patches (3)
- CVE-2026-xxxx: SQL injection in audit module (Critical)
- CVE-2026-xxxx: Path traversal in file scanner (High)
- CVE-2026-xxxx: XSS in web interface (Medium)

## New Features (8)
- Real-time threat detection improvements
- Enhanced Guardian module orchestration
- Expanded OS compatibility (Ubuntu 24.04, Fedora 40)
- Improved error reporting and diagnostics

## Improvements
- 15% faster module initialization
- Better memory management for long-running agents
- Improved logging and debugging capabilities

## Known Issues
- Audio capture requires elevated permissions on Ubuntu 24.04
- Some network features disabled on Wayland (temporary)

## Upgrade Path
- Automatic migration of Guardian vaults
- No user action required for settings migration
- Backward compatible with 2.3.x

## Contributors
- Security researchers: 12
- Community testers: 45
```

## Troubleshooting

### Update Fails to Download
```bash
shadowos-update check --verbose
# Check network connectivity
ping updates.shadowcypher.site
# Check system logs
journalctl -u shadowos-update -n 50
```

### Signature Verification Fails
```bash
# Re-download update
shadowos-update install --force-download

# Verify update server certificate
curl -v https://updates.shadowcypher.site/health
```

### Service Restart Issues
```bash
# Manual service restart
sudo systemctl restart shadow-guardian
sudo systemctl restart shadow-agent

# View service status
sudo systemctl status shadow-guardian
```

### Rollback Failed
```bash
# Check available backups
shadowos-update info --backups

# Manual restore from backup
tar -xzf /var/backups/shadowcypher-2.4.1.backup.tar.gz -C /

# Verify system integrity
shadowos-update verify --integrity-check
```

### Update Stuck
```bash
# Check update process
ps aux | grep shadowos-update

# View update logs
tail -f /var/log/shadowcypher-update.log

# Cancel update (if safe)
pkill -f shadowos-update
```

## Security Considerations

### Signature Verification
All update packages are signed with ECDSA (256-bit). Never install updates with `--no-verify`.

### Automatic Updates
The system can be configured for automatic installation with appropriate safeguards:
- Network outage detection (no forced restart)
- System load monitoring (delay installation if load > 4.0)
- Low battery detection (mobile systems)
- Active terminal session detection (won't restart while in use)

### Backup Strategy
- Automatic backup before every update (configurable)
- Incremental backups for efficient storage
- Encrypted backup storage
- Automatic cleanup of backups older than 30 days
- Manual backup retention possible

## Advanced Configuration

Update behavior can be customized in `/etc/shadowcypher/update-config.json`:

```json
{
  "channel": "stable",
  "auto_update": {
    "enabled": true,
    "schedule": "daily",
    "time": "02:00",
    "require_battery": false,
    "max_system_load": 4.0,
    "avoid_active_session": true
  },
  "backup": {
    "enabled": true,
    "compression": "gzip",
    "retention_days": 30,
    "encrypt": true
  },
  "server": {
    "url": "https://updates.shadowcypher.site",
    "timeout": 30,
    "retry_count": 3,
    "retry_delay": 300
  },
  "notifications": {
    "update_available": true,
    "update_installing": true,
    "update_complete": true,
    "update_failed": true
  }
}
```

## Command Reference

```
shadowos-update - ShadowCypher Update Manager

Usage: shadowos-update <command> [options]

Commands:
  check              Check for available updates
  install            Install available updates
  rollback           Rollback to previous version
  schedule           Schedule automatic updates
  info               Display system information
  verify             Verify system integrity
  help               Show this help message

Global Options:
  --channel {stable|beta|nightly}  Update channel
  --verbose                        Verbose output
  --help                          Show help

Use 'shadowos-update <command> --help' for command-specific help.
```

## Support and Reporting Issues

- **Bug reports**: Report update issues at https://github.com/jakes1345/ShadowCypher/issues
- **Security issues**: Contact security@shadowcypher.site with GPG key from https://shadowcypher.site/pgp
- **Update server status**: https://status.shadowcypher.site
