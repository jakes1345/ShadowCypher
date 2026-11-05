# ShadowCypher Guardian agent

A small Python daemon that scans your local network, checks a few things about the machine it runs on, and sends the results to your ShadowCypher dashboard at https://shadowcypher.site.

This is the last piece of Python in the project. It's still what the site installs, but new work goes into the native runtime (`shadowcypher-runtime agent-run`, see [`shadowcypher-qt/core/README.md`](../shadowcypher-qt/core/README.md)).

## Install

On Linux or macOS, `install.sh` does everything below for you. It downloads the agent into `~/.local/share/shadowcypher-agent`, creates a virtualenv with `requests`, links a `shadow-agent` wrapper into `~/.local/bin`, runs `init`, and installs the service if systemd user sessions work. Windows has `install.ps1`.

To set it up by hand you need Python 3.9 or newer and `requests`:

```bash
pip install requests
python3 shadowcypher_agent.py init    # paste the API key from your account page
# or
python3 shadowcypher_agent.py login   # approve this machine in the browser instead
```

`setup.sh` in this folder creates a local `.venv` and the `shadow-agent` wrapper if you'd rather not install `requests` globally.

## Commands

| Command | What it does |
|---|---|
| `init` | Writes `~/.shadowcypher/config.json` with the API key you paste |
| `login` | Same, but gets the key through the browser device flow |
| `run` | Runs in the foreground until stopped |
| `once` | Runs one scan cycle and exits |
| `update` | Checks GitHub releases for a newer agent |
| `install-service` | Installs and starts a service (systemd user unit, launchd or a Windows scheduled task) |
| `uninstall-service` | Removes it |
| `status` | Shows the service status |

## What it sends

| Endpoint | When | Contents |
|---|---|---|
| `POST /v1/agents/register` | First run | Hostname, OS and agent version |
| `POST /v1/agents/heartbeat` | Every 60 s | Liveness ping |
| `POST /v1/scans` | Every 10 min | Network scan (ARP cache, reverse DNS, a probe of 11 common ports, a guess at device type), plus DNS and firewall checks, router findings, and a hardening report every sixth cycle |
| `POST /v1/incidents` | When something is found | ARP anomalies, exposed router services, DNS leaks, no active firewall, hardening issues |

The API also creates a "new device" incident on its own when a scan contains a MAC address it hasn't seen before.

### Remote missions

In `run` mode the agent also polls `GET /v1/agents/<id>/missions/pending` on every heartbeat. Missions are ShadowScript, and the agent runs them only through the ShadowScript interpreter. It never hands a mission to the shell. This agent doesn't ship the interpreter, so it rejects each mission and reports `MISSION_REJECTED` with exit code 126, which clears it from the queue. Versions before 0.3.1 fell back to running the script as a shell command, so update if you're on an older one. `once` doesn't poll missions.

### Updates

`run` checks GitHub releases tagged `agent-v*` at start-up and once a day. It replaces itself only if the release has both `shadowcypher_agent.py` and a matching `shadowcypher_agent.py.sha256`.

## Config

`~/.shadowcypher/config.json`:

```json
{
  "api_base": "https://api.shadowcypher.site",
  "api_key": "sc_live_…",
  "scan_interval_sec": 600,
  "heartbeat_interval_sec": 60
}
```

The scan interval can't go below 60 seconds and the heartbeat can't go below 30. Keep the file at mode `0600` and never commit it. The state file, `~/.shadowcypher/state.json`, caches the `agent_id` so restarting doesn't register the machine again.

## Running as a service

`install-service` writes a systemd user unit called `shadowcypher-guardian`, enables it and turns on lingering so it keeps running after you log out:

```bash
shadow-agent install-service
journalctl --user -u shadowcypher-guardian -f
```

If you'd rather manage a system-wide unit yourself, something like this works:

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
