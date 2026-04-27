# ShadowCypher Guardian Agent

Tiny Python daemon that scans your local network, fingerprints devices, detects ARP anomalies, and ships everything to your ShadowCypher dashboard at https://shadowcypher.site.

## Install

```bash
# Requires Python 3.10+
pip install requests

# Get your API key from https://shadowcypher.site → Account → COPY
python3 shadowcypher_agent.py init   # paste key when prompted
```

## Run

```bash
# Foreground
python3 shadowcypher_agent.py run

# One-shot (cron / systemd one-shot timer)
python3 shadowcypher_agent.py once
```

## What it sends

| Endpoint | Frequency | Purpose |
|---|---|---|
| `POST /v1/agents/register` | Once per install | Identifies this machine to your account |
| `POST /v1/agents/heartbeat` | Every 60s | "still alive" ping |
| `POST /v1/scans` | Every 10 min | Full network scan (ARP + reverse DNS + light port probe) |
| `POST /v1/incidents` | On anomaly | ARP spoof, duplicate IP/MAC detection |

The Worker auto-creates "new device" incidents server-side when an unknown MAC appears in your scan. You see them on the dashboard incident feed.

## Config (`~/.shadowcypher/config.json`)

```json
{
  "api_base": "https://shadowcypher-api.shadowcypher.workers.dev",
  "api_key": "sc_live_…",
  "scan_interval_sec": 600,
  "heartbeat_interval_sec": 60
}
```

`mode 0600`. Never commit. The state file (`~/.shadowcypher/state.json`) caches `agent_id` so re-registers are idempotent.

## systemd unit (optional)

Save as `/etc/systemd/system/shadowcypher-agent.service`:

```ini
[Unit]
Description=ShadowCypher Guardian Agent
After=network-online.target

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/bin/python3 /opt/shadowcypher/agent/shadowcypher_agent.py run
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then: `sudo systemctl enable --now shadowcypher-agent`.
