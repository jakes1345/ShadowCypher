# ShadowOS Audit Logging

## Audit System

ShadowOS logs system activities via auditd for compliance and investigation.

## Enabled Auditing

- All system calls (execve, etc)
- Authentication and authorization
- Network configuration changes
- File integrity monitoring
- Administrative actions (sudo)
- Audit system changes

## Viewing Audit Logs

```bash
# View recent entries
sudo ausearch -k exec

# View authentication attempts
sudo ausearch -k auth

# Real-time monitoring
sudo tail -f /var/log/audit/audit.log
```

## Log Rotation

Logs are rotated when they exceed 30MB, with 5 rotations kept.

Located at: `/var/log/audit/audit.log*`

## Audit Rule Categories

### System Configuration Monitoring
- `/etc/audit/` - Audit framework configuration
- `/etc/libaudit.conf` - libaudit configuration
- `/etc/audisp/` - Audit dispatcher configuration

### Binary Integrity
- `/bin/` - Essential binaries
- `/sbin/` - System binaries
- `/usr/bin/` - User binaries
- `/usr/sbin/` - User system binaries

### System Call Monitoring
- **Process execution** - All execve system calls tracked
- **Time changes** - adjtimex, settimeofday
- **Network modifications** - sethostname, setdomainname, setsockopt
- **File deletion** - unlink, unlinkat, rename, renameat

### Privilege Monitoring
- `/etc/sudoers` - Sudo configuration
- `/etc/sudoers.d/` - Sudo configuration directory

## Audit Log Format

Logs are stored in RAW format at `/var/log/audit/audit.log`.

Each entry contains:
- timestamp
- system call type
- process ID
- user ID
- command/path
- result (success/failure)

## Searching Logs

Filter by key:
```bash
# View all execution audit events
sudo ausearch -k exec

# View all configuration changes
sudo ausearch -k audit-config

# View all binary modifications
sudo ausearch -k binaries

# View all privilege scope changes
sudo ausearch -k scope
```

Filter by date/time:
```bash
# View events from last 10 minutes
sudo ausearch --start recent

# View events from specific date
sudo ausearch --start today
```

## Audit Daemon Configuration

The auditd.conf file controls:
- **Log file location** - /var/log/audit/audit.log
- **Log rotation** - 5 rotations, 30MB each
- **Buffer size** - 8192 events
- **Flush mode** - INCREMENTAL (low latency)
- **Dispatcher** - /sbin/audispd for plugin support

### Failure Handling
- **space_left** - 75MB triggers syslog warning
- **admin_space_left** - 50MB triggers audit suspension
- **disk_full_action** - SUSPEND on disk full

## Compliance

ShadowOS audit rules implement CIS Arch Linux Benchmark requirements for:
- System monitoring and logging
- File integrity verification
- Access control auditing
- Configuration change tracking

## Disabling/Modifying Rules

To temporarily disable auditing:
```bash
sudo systemctl stop auditd
```

To modify rules, edit `/etc/audit/rules.d/shadowos.rules`:
```bash
sudo nano /etc/audit/rules.d/shadowos.rules
sudo systemctl restart auditd
```

Note: The last rule (`-e 2`) makes the configuration immutable until reboot.

## Troubleshooting

Check auditd status:
```bash
sudo systemctl status auditd
```

View recent audit daemon messages:
```bash
sudo journalctl -u auditd -n 20
```

Verify rules are loaded:
```bash
sudo auditctl -l
```
