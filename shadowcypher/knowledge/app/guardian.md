# ShadowCypher Guardian — Reference

## What is Guardian?

Guardian is ShadowCypher's network monitoring agent. It runs on your desktop/server and provides:
- Real-time LAN device discovery (ARP + mDNS + DHCP tracking)
- Network traffic anomaly detection
- CVE correlation against discovered services
- Incident creation and alerting
- ShadowScript mission execution from your phone

## Guardian Agent (Desktop)

### Installation
Download from shadowcypher.site → Guardian tab or GitHub Releases.
Supports: Linux, macOS, Windows

```bash
# Linux/macOS
curl -O https://releases.shadowcypher.site/guardian/latest/shadowcypher-guardian.tar.gz
tar xzf shadowcypher-guardian.tar.gz
./shadowcypher-guardian --api-key sc_live_YOUR_KEY_HERE
```

### Configuration
Config file: `~/.shadowcypher/guardian.toml`
```toml
api_key = "sc_live_..."
api_url = "https://api.shadowcypher.site"
scan_interval = 300        # seconds between passive scans
heartbeat_interval = 60    # seconds between heartbeats
interfaces = ["eth0"]      # or [] for auto-detect
ghost_mode = false
mission_poll_interval = 10  # seconds between mission checks
```

### What the Agent Reports
- **Heartbeat**: hostname, IP, OS version, agent version, online status
- **Devices**: ARP table, mDNS hostnames, open ports (top 1000)
- **Incidents**: unusual traffic, port scans, new unknown devices
- **Mission results**: output from ShadowScript commands executed locally

### Agent Process Name
`shadowcypher-guardian` or `scguardian`

## Guardian API Endpoints

All endpoints require: `Authorization: Bearer sc_live_YOUR_KEY`
Base URL: `https://api.shadowcypher.site`

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | /v1/me | Current user info + plan |
| GET | /v1/guardian/summary | Full network summary (devices, incidents, CVEs, agents) |
| POST | /v1/scans | Trigger network scan |
| GET | /v1/incidents | List all incidents |
| GET | /v1/agents | List registered agents |
| POST | /v1/agents/:id/missions | Create a ShadowScript mission |
| GET | /v1/missions | List all missions |
| GET | /v1/missions/:id | Get mission status/result |

## Guardian Dashboard (Web)

URL: shadowcypher.site (Account tab after login)

### Dashboard Cards
- **Threat Level**: Aggregate risk score (0–100)
- **Active Incidents**: Unresolved security events
- **Devices Online**: Detected network hosts
- **CVE Alerts**: Matched vulnerabilities against detected services
- **Agents**: Online/offline status of Guardian agents

## Guardian Android App

The Guardian Android app (separate from Shadow voice assistant) provides:
- Mobile dashboard: threat level, incident count, device count
- One-tap network scan trigger
- Real-time incident view
- Mission management (send ShadowScript to desktop)
- Settings: API key management

### Screens
1. **Dashboard**: summary metrics, threat level gauge, quick scan button
2. **Devices**: list of discovered LAN hosts with IP, hostname, MAC, risk level
3. **Incidents**: timeline of security events; tap for details
4. **Missions**: send ShadowScript to any online agent; view results
5. **Settings**: API key, server URL, notification preferences

## Troubleshooting Guardian

| Problem | Check |
|---------|-------|
| Agent offline | Check network, API key, firewall port 443 outbound |
| No devices showing | Run scan; check agent is on same LAN |
| Scan fails | API key permissions; check plan (Free: 5 scans/day) |
| High false positive rate | Tune incident thresholds in guardian.toml |
| Mission not executing | Agent online? Check mission_poll_interval |
