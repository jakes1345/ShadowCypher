<p align="center">
  <img src="shadowcypher/ui/assets/icon.png" width="120" alt="ShadowCypher Logo"/>
</p>

<h1 align="center">SHADOWCYPHER</h1>
<h3 align="center">A personal security platform that runs entirely on your machine</h3>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-00d4ff?style=flat-square" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/go-1.24+-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go"/>
  <img src="https://img.shields.io/badge/AI-Ollama%20(Local)-black?style=flat-square" alt="AI"/>
  <img src="https://img.shields.io/badge/crypto-AES--256--GCM%20%2B%20X25519-10b981?style=flat-square" alt="Crypto"/>
  <img src="https://img.shields.io/badge/license-Sovereign-f43f5e?style=flat-square" alt="License"/>
</p>

---

## Why This Exists

ShadowCypher started as shell scripts and Python wrappers written late at night while debugging real network problems. Commercial tools kept phoning home. Hosted platforms kept expiring API keys. The fix was to build something that didn't.

The goal is an operator's toolkit that answers to no one but the operator — no telemetry, no cloud dependency, no subscription that can be revoked. It's now a GTK desktop application backed by a compiled Go signal relay, a local AI inference engine, and over 30 offensive and defensive modules. Everything that's in here exists because it was actually needed.

---

## How It's Built

The application is split into two runtimes that talk over a local WebSocket:

- **Python 3.12** handles the GTK interface, AI inference, mission orchestration, and all tool wrappers
- **Compiled Go** handles the WebSocket relay — concurrent connections without Python's GIL getting in the way

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        SHADOWCYPHER v3.0.0                               │
├──────────────────────┬──────────────────────┬────────────────────────────┤
│   GTK-3.0 Interface  │   AI Engine          │   Native Core (Go)         │
│                      │                      │                            │
│   Cairo gauges       │   Ollama (local GPU) │   WebSocket relay          │
│   Page routing       │   MetaChain agent    │   Swarm discovery          │
│   TacticalTerminal   │   TreeQuest MCTS     │   Token authentication     │
│   Sidebar nav        │   Intent→Execute     │   Stealth transport        │
│   Auto Scan tab      │   AutoScan pipeline  │                            │
├──────────────────────┴──────────────────────┴────────────────────────────┤
│                          EVENT BUS (ShadowBus)                           │
│                   Thread-safe pub/sub + async dispatch                   │
├────────────────────────┬─────────────────────┬───────────────────────────┤
│  Intelligence Layer    │  Analysis Layer      │  Core Engine              │
│                        │                      │                           │
│  CISA KEV (1627 CVEs)  │  Security Assessor  │  Config (Pydantic)        │
│  EPSS scoring          │  MITRE ATT&CK tags  │  Knowledge graph          │
│  OTX AlienVault        │  Rule-based triage  │  AES-256-GCM / X25519    │
│  AbuseIPDB             │  Pattern matching   │  Logger (JSONL)           │
│  URLhaus (malware)     │  Remediation plans  │  Runner / forensics       │
│  Tor exit blocklist    │                     │                           │
└────────────────────────┴─────────────────────┴───────────────────────────┘
```

### Stack Decisions

| Decision | Reason |
|---|---|
| **GTK-3.0** instead of Electron | 40MB vs 400MB. No Chromium process eating GPU during a scan. |
| **Go relay** instead of pure Python | WebSocket concurrency without the GIL. The relay handles thousands of connections; Python handles the logic. |
| **Local Ollama** instead of cloud APIs | Your prompts never leave your machine. No rate limits. Nothing to subpoena. |
| **Pydantic config** instead of raw JSON/YAML | Type validation at load time, environment variable injection, and clear error messages when something is misconfigured. |
| **AES-256-GCM + X25519** | AEAD encryption with forward-secret key exchange. Every chat session generates ephemeral keys that die when the session ends. |

---

## What It Does

### Situational Awareness & AI Operations

The main dashboard and AI interface.

| Module | Description |
|---|---|
| **Command HUD** | Real-time system dashboard with Cairo vector gauges (CPU, RAM, Disk). Color thresholds at 65% and 85%. Live status grid for installed tools. Mission feed. Refreshes every 1.5 seconds. |
| **Shadow Synthesizer** | Conversational AI interface backed by any Ollama-compatible model (Gemma, LLaMA, DeepSeek, Mistral, Phi, Qwen). Streaming output. Session history. Works with Ollama REST or llama-cpp-python. |
| **Quantum-Core** | Deep-analysis AI mode with a specialized system prompt that forces step-by-step reasoning and self-verification. For when you need the model to actually think through something rather than riff on it. |
| **Spectre War-Map** | Network topology canvas. Renders discovered nodes with connection state, latency, and GeoIP approximation. Updates in real time via the Nexus relay. |
| **ShadowScript Lab** | A domain-specific scripting language for orchestrating multi-tool engagements. Hand-written lexer, recursive descent parser, and tree-walking interpreter. Includes a reference grammar. |

### Reconnaissance & Intelligence

Passive and active collection across every layer of the stack.

| Module | Description |
|---|---|
| **Signal Analysis** | Network reconnaissance via Nmap. Service version detection, OS fingerprinting, script scanning, traceroute — all in one interface. Results feed into the forensic registry and get tagged with MITRE ATT&CK technique IDs. |
| **Spectral Intelligence** | OSINT toolkit: Sherlock username search across 300+ platforms, WHOIS, DNS record enumeration (A, AAAA, MX, NS, TXT, SOA), reverse IP resolution. |
| **Infrastructure Recon** | Host discovery via ARP and nmap. TCP/UDP port sweeps. Banner grabbing. SSL certificate inspection. |
| **Vulnerability Sweep** | Nuclei-based scanning with severity filtering and tag-based template targeting. Results cross-referenced with Exploit-DB via SearchSploit. |
| **CVE Intelligence** | Live NVD API v2 feed (6-hour cache). Correlates discovered service banners against the National Vulnerability Database. Automatically enriched with **EPSS scores** (probability of exploitation in next 30 days from first.org) and **CISA KEV membership** (1,627 known exploited CVEs). KEV hits are flagged with federal remediation due dates. |
| **Threat Intel** | Multi-source reputation checks. **OTX AlienVault** (pulse count + malicious indicators), **AbuseIPDB** (confidence 0–100), **URLhaus** (live malware delivery URLs, no auth needed), **Tor exit list** (local set for O(1) lookup before hitting paid APIs). All sources queried in parallel, merged into a single verdict, ingested into the knowledge graph. |
| **Gaming Asset Audit** | Steam and gaming platform security: account exposure, session token validation, platform-specific vulnerability assessment. |

### AI Intelligence Pipeline

This is the part that makes the AI useful for security work.

Small local models (7B–14B parameters) don't reliably emit structured tool-call JSON. So instead of trusting the model to invoke tools correctly, the pipeline detects intent from the user's message, runs the real tool, and then feeds the actual output to the AI for analysis.

```
User query
    │
    ▼
Intent Detector (15 patterns: nmap / nuclei / nikto / sqlmap / auto_scan / threat-intel / OSINT / ...)
    │
    ├── Specific tool + target? ──▶ Execute the real tool first
    │                                       │
    │                                       ▼
    │                              Inject real output into AI prompt
    │                                       │
    └── General query? ──────────▶ Route to specialist agent
                                            │
                                            ▼
                                   AI analyzes real scan data
                                   (not hallucinated output)
```

**AutoScan Pipeline** — the adaptive full-stack scanner. Point it at a target and it figures out what to run:

1. Nmap service fingerprint → parse open ports and classify (web / database / SSH / etc.)
2. Domain target? → subdomain enumeration
3. Web surface found? → Nikto + Nuclei run in parallel
4. Database port or form URLs found? → SQLmap (requires explicit operator confirmation before running)
5. CVE correlation against every discovered service banner
6. Threat intel on the IP (OTX + AbuseIPDB + URLhaus + Tor check)
7. Rule-based security assessment → knowledge graph ingestion → AI report synthesis

Results from each phase feed decisions for the next. If Nikto finds form URLs, SQLmap targets those specifically instead of just the homepage. If nmap finds nothing web-related, web scanning phases are skipped entirely. Accessible from the "Auto Scan" tab in the Vulnerability Scanner, or programmatically:

```python
from shadowcypher.ai.auto_scan import auto_scan

# Full pipeline
result = auto_scan.run("192.168.1.100", on_output=print)

# With confirmation callback for destructive tests
result = auto_scan.run(
    "192.168.1.100",
    on_output=print,
    confirm_fn=lambda tool, target: input(f"Run {tool} on {target}? [y/N] ").lower() == "y"
)

# Non-blocking
auto_scan.run_async("192.168.1.100", on_output=print, on_complete=lambda r: print(r.summary()))

# Quick scan — nmap + CVE + threat intel only
result = auto_scan.quick_scan("192.168.1.100")
```

**TreeQuest Attack Chain Planner** (Sakana AI): When you need to plan a full assessment rather than run a single tool, `tree_planner.plan(target, context)` uses Monte Carlo Tree Search to explore sequences of security actions. The local AI predicts what each action would find; the tree search finds the highest-value path. Returns an ordered plan with confidence scores. Destructive actions (`sql_injection`, `vuln_scan`) require explicit confirmation before execution.

**Security Assessor**: After any scan, `assessor.assess_findings(cves, threat_intel, ports)` produces rule-based triage in under 1ms — no LLM needed. Eight security combination patterns fire advisory text when matched (e.g. `KEV_exploited + high_EPSS + open_port` → "CRITICAL CHAIN — patch immediately"). Output includes threat level, matched patterns, lead CVE/indicator, and prioritized remediation steps.

**MITRE ATT&CK Coverage**: 65 technique IDs mapped across all tool outputs. Every finding is tagged automatically. Reports include a coverage matrix grouped by tactic.

### Offensive Lab

Tools for authorized penetration testing. All of these assume you own the target or have written authorization to test it.

| Module | Description |
|---|---|
| **DeepHat Apex** | AI-powered offensive workflow. The MetaChain agent takes a high-level objective, breaks it into tool invocations, runs them in sequence, and synthesizes the findings. Backed by a 30+ tool registry. |
| **Ghost Factory** | Payload generation via msfvenom. Linux, Windows, macOS targets. ELF, EXE, Mach-O, raw, and Python output formats. Payload history tracking. |
| **Phishing Synthesis** | Phishing campaign toolkit: template-based page generation, automated Cloudflare tunnel for instant HTTPS, credential capture. Strictly for authorized social engineering engagements. |
| **Ghost-Hose** | Network stress testing. Five modes: UDP flood, TCP SYN, Layer 7 HTTP, Slowloris, and Mixed. Configurable threads and duration limits. Lab and authorized gauntlet use only. |
| **Web Layer Attacks** | SQL injection, XSS, SSRF, directory fuzzing (ffuf). Automated scanning and manual injection with custom payloads. |
| **Key Harvester** | Hydra for network protocol brute-forcing (SSH, FTP, RDP, SMB, HTTP). John the Ripper and Hashcat for offline hash cracking with GPU support. |
| **Wireless Saturation** | 802.11 testing via Aircrack-ng. WPA/WPA2 cracking, deauth attacks, network enumeration, monitor mode management. |

### Communication, Defense & System Integrity

| Module | Description |
|---|---|
| **Sovereign Chat** | End-to-end encrypted chat. AES-256-GCM at rest with per-room derived keys. X25519 ECDH ephemeral key exchange every session — compromise of one session reveals nothing about any other. SQLite persistence. |
| **Go Signal Relay** | 9.2MB compiled binary for WebSocket swarm coordination. Token authentication. Sub-millisecond relay. Auto-compiled from source on launch if the binary is stale. |
| **ShadowSentinel IRC Bot** | Modular IRC bot with 20+ commands. Connects to external IRC (Libera) and sovereign Ergo servers. Offline conversational AI via ELIZA + Markov chain. SHA-256 proof-of-work user verification. |
| **Wraith Protocol** | Emergency wipe interface. Flash-Wipe purges session keys, ephemeral mission data, and forensic artifacts in one action. Confirmation dialogs prevent accidents. |
| **God-Panel** | System control panel. Live status matrix for every service (Ollama, Go relay, Sovereign Chat, Sisyphus, IRC bot) with real-time latency probes. AI model hot-swapping. Threat registry viewer. |
| **Sisyphus Sentinel** | Continuous integrity monitoring. SHA-256 hashes every Python source file on a 60-second cycle. Detects unauthorized modifications, syntax corruption, and dependency tampering. |
| **Citadel Security** | AES-256-GCM vault. PBKDF2 key derivation (200,000 iterations). RSA-OAEP asymmetric ticket encryption. Hardware fingerprint binding. SSH honeypot on port 2222 that mimics OpenSSH 7.4. |

### Operational Anonymity

| Module | Description |
|---|---|
| **Ghost Mode** | One-command invisibility: iptables kill-switch routing all traffic through Tor, MAC randomization, hostname/timezone neutralization, DNS leak prevention, RAM-only workspace, system log suppression. Full restore on disengage. |
| **Shadow Audit** | Anonymity chain validator. Tests Tor, DNS leaks, MAC fingerprinting, hostname/timezone exposure, firewall rules, WireGuard config, browser fingerprints. Returns a score with auto-fix for failed checks. |
| **Traffic Mirage** | DPI evasion. obfs4 bridge configuration (makes Tor look like HTTPS), cover traffic generation, DNS tunneling, timing obfuscation via `tc netem`. |
| **Dead Drop** | Anti-forensics: 7-pass file shredding with random rename before unlink, swap sanitization, free-space wiping, LUKS-encrypted USB dead drop creation, PANIC button that destroys keys/databases/configs/logs. |
| **Trace Eraser** | Forensic log cleaner. Shell histories (12 types), system logs, systemd journal, wtmp/btmp/lastlog, thumbnail caches, recently-used files. Timestamp obfuscation mode. |
| **Tor Cloak** | Full Tor lifecycle manager. Start/stop/verify, circuit rotation via ControlPort, torified shell sessions, IP protection hardening. |

### Guardian — Personal Device Security

| Module | Description |
|---|---|
| **Network Scan** | ARP/nmap device discovery. OS fingerprinting. Flags dangerous services (Telnet, SMB, TR-069, UPnP). Per-device risk assessment. |
| **Router Audit** | Checks home routers for exposed management ports, ISP remote access (TR-069), UPnP, and weak DNS. Actionable hardening steps. |
| **Device Monitor** | Continuous monitoring: new devices joining the network, ARP spoofing, device disappearances. Real-time alerting. |
| **Auto-Harden** | One-command hardening: unattended updates, SSH root disable, iptables default-DROP, core dump disable, file permission lockdown. |
| **Deep Audit** | Local machine audit: SUID binary check, SSH config review, world-writable file scan, failed login analysis, listening service inventory. |

---

## shadow-cli

A command-line AI assistant that routes natural language to ShadowCypher tools.

```bash
shadow-cli                              # Interactive mode
shadow-cli -p "scan my network"         # Discovers all devices on your LAN
shadow-cli -p "full scan 192.168.1.100" # Runs the full AutoScan pipeline
shadow-cli -p "engage ghost mode"       # Activates total anonymity
shadow-cli -p "am I anonymous?"         # Runs full anonymity audit
shadow-cli -p "audit my router"         # Checks router for vulnerabilities
```

Backed by an MCP server that exposes security tools to any compatible AI assistant.

---

## Encryption Architecture

```
Client                          Server (Sovereign Chat)
  │                                │
  │── auth { nick, x25519_pub } ──▶│
  │                                │── Generate ephemeral X25519 keypair
  │                                │── ECDH: shared_secret = server_priv × client_pub
  │                                │── HKDF-SHA256(shared_secret) → AES-256 session key
  │◀── auth_ok { x25519_srv_pub }──│
  │                                │
  │── ECDH: shared = cli_priv × srv_pub
  │── HKDF-SHA256(shared) → same AES-256 key
  │                                │
  │══════ AES-256-GCM Encrypted Channel ══════│
```

- **Forward secrecy**: Ephemeral X25519 keys per session. A compromised session key reveals nothing about past or future sessions.
- **At-rest encryption**: Stored messages are AES-256-GCM encrypted with per-room derived keys.
- **Admin identity**: RSA-4096 challenge-response with hardware fingerprint binding.

---

## Event Architecture

Modules communicate through **ShadowBus**, a thread-safe pub/sub backbone. This eliminates circular imports and lets any module react to events from any other without direct dependencies.

```python
# Any module can broadcast
bus.publish("forensic_update", {"handle": "attacker", "risk": "HIGH"})

# Any module can subscribe
bus.subscribe("forensic_update", lambda data: firewall.block(data["handle"]))
```

Key channels: `mission_output`, `module_log`, `pulse_anomaly`, `forensic_update`, `security_lockdown`, `new_chat_msg`, `sovereign_chat`, `mission_archived`.

---

## Installation

### Requirements

| Dependency | Purpose | Required |
|---|---|---|
| Python 3.12+ | Core runtime | ✅ |
| GTK 3.0 (`python3-gi`, `gir1.2-gtk-3.0`) | Desktop interface | ✅ |
| Go 1.24+ | Native relay compilation | ✅ |
| Ollama | Local AI inference | ✅ |
| `cryptography` | AES-256-GCM, X25519, RSA | ✅ |
| `pydantic`, `pydantic-settings` | Configuration | ✅ |
| `aiohttp` | WebSocket + Nexus API | ✅ |
| `psutil` | System metrics | ✅ |
| `treequest>=0.3.2` | MCTS attack chain planner | ✅ |
| nmap, nuclei, nikto, sqlmap | Scanning tools | Optional |
| hydra, john, hashcat | Credential testing | Optional |
| proxychains4, tor | Anonymization | Optional |

### Quick Start

```bash
git clone https://github.com/jakes1345/ShadowCypher.git
cd ShadowCypher
pip install -r requirements.txt
python3 -m shadowcypher.app
```

### Manual Launch

```bash
source venv/bin/activate
export PYTHONPATH="$(pwd):$(pwd)/ai_engine:$PYTHONPATH"
export SHADOW_PORT=8888
python3 -m shadowcypher.app
```

---

## Project Structure

```
ShadowCypher/
├── shadowcypher/
│   ├── app.py                 # GTK application entry point
│   ├── core/
│   │   ├── hub.py             # Mission orchestrator + relay bridge + dispatch_auto_scan()
│   │   ├── mitre.py           # MITRE ATT&CK database (65 technique IDs)
│   │   ├── knowledge_graph.py # SQLite tactical intelligence graph
│   │   ├── assessor.py        # Rule-based security situation assessor
│   │   ├── sovereign_chat.py  # WebSocket chat (X25519 + AES-256-GCM)
│   │   └── ...
│   ├── ai/
│   │   ├── auto_scan.py       # Adaptive multi-phase security assessment pipeline
│   │   ├── intent.py          # Intent detector (15 security tool patterns)
│   │   ├── tree_planner.py    # TreeQuest MCTS attack chain planner
│   │   ├── agents.py          # Agent fleet + Intent→Execute→Analyze dispatch
│   │   ├── orchestrator.py    # MetaChain autonomous agent
│   │   ├── adversary_sim.py   # Autonomous red team simulation engine
│   │   ├── classic_brain.py   # Offline ELIZA + Markov conversational AI
│   │   ├── sisyphus.py        # File integrity sentinel
│   │   └── ...
│   ├── ui/
│   │   ├── vuln_page.py       # Vulnerability Scanner (Auto Scan tab + Nikto / SQLmap / NSE)
│   │   └── ...                # 40+ other pages
│   ├── modules/
│   │   ├── cve_feed.py        # NVD CVE feed + EPSS + CISA KEV enrichment
│   │   ├── threat_intel.py    # OTX + AbuseIPDB + URLhaus + Tor exits
│   │   ├── recon.py           # Nmap + subdomain enum + HTTP probing
│   │   ├── vuln_scanner.py    # Nuclei + Nikto + SQLmap wrappers
│   │   └── ...
│   ├── native/relay/          # Go WebSocket relay (compiled binary)
│   └── compiler/              # ShadowScript lexer + interpreter
├── ai_engine/autoagent/       # MetaChain autonomous agent framework
├── config.json                # Runtime configuration (gitignored — never pushed)
└── requirements.txt
```

---

## Configuration

Three-tier resolution: environment variables → `config.json` → code defaults.

| Section | Controls |
|---|---|
| `ai` | Model name, API base, temperature, token limits, GPU layer count |
| `tools` | Paths to nmap, hydra, john, hashcat, and other offensive tools |
| `irc` | Server, port, channel, SASL auth, bot personality |
| `identity` | Operator handle, admin list, hardware fingerprint |
| `stealth` | Proxy URL, privacy enforcement, Nexus relay endpoint |
| `intel` | API keys for OTX and AbuseIPDB |

### API Keys

| Source | Config key | Free tier |
|---|---|---|
| OTX AlienVault | `intel.otx_api_key` | Anonymous (rate-limited) |
| AbuseIPDB | `intel.abuseipdb_api_key` | 1,000 checks/day |
| URLhaus | *(none)* | Unlimited, no auth |
| Tor exit list | *(none)* | Unlimited, no auth |
| CISA KEV | *(none)* | Unlimited, no auth |
| EPSS (first.org) | *(none)* | Unlimited, no auth |

---

## ShadowOS

An Arch Linux-based live/installable ISO with ShadowCypher pre-installed. Hyprland, a custom Plymouth boot, pentest tools, dev environment, and gaming — all in one hardened OS.

| Layer | What ships |
|---|---|
| **Kernel** | linux-hardened + sysctl hardening |
| **Compositor** | Hyprland (Wayland) + Waybar + Wofi + Hyprlock |
| **Pentest** | nmap, sqlmap, hydra, metasploit, aircrack-ng, bettercap, rustscan, ffuf, nuclei, impacket, netexec, wireshark |
| **Dev** | VSCode, neovim, docker, podman, kubectl, rustup, go, nodejs, lazygit, Distrobox |
| **Gaming** | Steam, Heroic, Lutris, PrismLauncher, MangoHUD, GameScope, wine-staging |
| **Privacy** | Tor, dnscrypt-proxy, MAC randomization, AppArmor, ufw |
| **Modes** | `shadow-mode <normal/dev/pentest/privacy/ghost/undercover>` — hot-swap firewall, DNS, autostart |

**Status: v0.1.0 — ISOs verified, ~7.4 GB**

```bash
# Build (Arch host)
sudo pacman -S archiso
cd shadowos && sudo ./build.sh

# Build (Docker, any host)
cd shadowos && ./build-docker.sh

# Test in QEMU
qemu-system-x86_64 -enable-kvm -m 4G -cdrom out/shadowos-*.iso -vga virtio
```

Default live credentials: `shadow` / `shadow`. Reset by the installer.

---

## Legal

ShadowCypher is built for authorized security testing, research, and education. Every offensive module assumes the operator has explicit written authorization to test the target system. Unauthorized use of these tools against systems you don't own or have permission to test is illegal.

The authors assume no liability for misuse. You own your actions.

---

<p align="center">
  <strong>ShadowCypher v3.0.0</strong> · Python + Go + Cairo
</p>

<p align="center">
  <a href="https://shadowcypher.site">shadowcypher.site</a> · <a href="https://github.com/jakes1345/ShadowCypher">GitHub</a>
</p>
