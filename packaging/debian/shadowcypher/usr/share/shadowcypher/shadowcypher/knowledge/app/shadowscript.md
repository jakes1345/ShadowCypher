# ShadowScript Reference

## What is ShadowScript?

ShadowScript is ShadowCypher's mission language — commands you send from your phone to the Guardian agent running on your desktop. The agent executes them locally and returns the output.

ShadowScript is a security-focused command DSL (domain-specific language). It's not a full programming language — it maps to safe, predefined operations on the host.

## Mission Flow

```
Phone (Missions tab) → API → Queue → Guardian Agent (polling) → Execute → Report Result → Phone
```

Execution latency: typically 10–30 seconds (depends on mission_poll_interval).

## ShadowScript Syntax

### Basic Commands

```shadowscript
# Network information
net.status                    # Network interface summary
net.arp                       # ARP table (IP → MAC)
net.connections               # Active TCP/UDP connections
net.scan 192.168.1.0/24       # Quick ping sweep of subnet
net.dns <domain>              # DNS lookup
net.traceroute <host>         # Traceroute

# System information
sys.info                      # OS, CPU, RAM, uptime
sys.processes                 # Running process list
sys.users                     # Logged-in users
sys.ports                     # Listening ports + process names

# File operations (sandboxed to allowed paths)
file.list <path>              # Directory listing
file.read <path>              # Read file (text only, max 50KB)
file.hash <path>              # SHA256 hash of file
file.find <pattern> <path>    # Search for files

# Security operations
sec.scan <host>               # Run nmap quick scan
sec.cve <host>                # Check host's services against NVD
sec.log <lines>               # Recent auth/security log entries (default: 50)
sec.vuln                      # List local vulnerable packages

# Ghost mode
ghost.status                  # Check anonymity status
ghost.on                      # Enable ghost mode
ghost.off                     # Disable ghost mode
```

### Shell Passthrough (Operator Plan Only)

```shadowscript
shell: <command>              # Execute any shell command
```

Example:
```shadowscript
shell: netstat -antp | grep ESTABLISHED | head -20
```

Shell passthrough requires Operator plan and is logged with full audit trail.

## Sending Missions from Android

1. Open Guardian app → Missions tab
2. Tap the ▶ (play) button to open composer
3. Select target agent from dropdown
4. Add optional label (e.g., "Check active connections")
5. Enter ShadowScript in the code field
6. Tap "Submit Mission"
7. Pull to refresh or use Refresh button to see result

## Mission Statuses

| Status | Description |
|--------|-------------|
| pending | Queued; waiting for agent to poll |
| running | Agent picked up; executing |
| completed | Finished; result available |
| failed | Error during execution; error in result_output |
| timeout | Agent didn't poll within 5 minutes |

## Mission Results

Results are truncated to 400 characters in the mobile app card view.
Full results available via API: `GET /v1/missions/:id`

## ShadowScript Security Model

- Missions are authenticated: API key required
- All missions are logged with timestamp, agent, user
- Shell passthrough: operator plan gate + additional audit log
- Agent enforces allowlist: ShadowScript commands map to Python functions, not raw shell
- File read operations: sandboxed to ~/shadowcypher/ and /tmp unless shell: used
- No persistent state between missions: each runs in isolation

## Example Missions

### Quick Security Audit
```shadowscript
net.connections
sys.users
sec.log 100
```

### Network Sweep
```shadowscript
net.arp
net.scan 192.168.1.0/24
```

### Check Specific Host
```shadowscript
sec.scan 192.168.1.50
net.dns 192.168.1.50
```

### System Health Check
```shadowscript
sys.info
sys.processes
sys.ports
```

## Rate Limits

- Mission creation: 10 per minute per user
- Operator plan: unlimited shell passthrough
- Free plan: ShadowScript commands only (no shell:)
