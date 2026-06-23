<p align="center">
  <img src="shadowcypher/ui/assets/icon.png" width="120" alt="ShadowCypher Logo"/>
</p>

<h1 align="center">SHADOWCYPHER</h1>
<h3 align="center">Sovereign Tactical Suite + Personal Security Platform</h3>


<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-00d4ff?style=flat-square" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/go-1.24+-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go"/>
  <img src="https://img.shields.io/badge/AI-Ollama%20(Local)-black?style=flat-square" alt="AI"/>
  <img src="https://img.shields.io/badge/crypto-AES--256--GCM%20%2B%20X25519-10b981?style=flat-square" alt="Crypto"/>
  <img src="https://img.shields.io/badge/license-Sovereign-f43f5e?style=flat-square" alt="License"/>
</p>

---

## Genesis

ShadowCypher started as shell scripts and Python wrappers written late at night while debugging real network problems. Commercial tools kept phoning home. Hosted platforms kept expiring API keys. The fix was to build something that didn't.

The goal: an operator's toolkit that answers to no one but the operator. No telemetry, no cloud dependency, no subscription that can be revoked.

It's now a GTK dashboard backed by a compiled Go signal relay, a local AI inference engine, and over 30 offensive and defensive modules. Every module exists because it was needed, not because it looked good on a feature list.

---

## Architecture Overview

ShadowCypher is a dual-core system. The orchestration layer runs on **Python 3.12** with a GTK-3.0 interface, handling everything from mission dispatch to AI inference routing. The signal layer runs on **compiled Go**, providing a high-performance WebSocket relay for swarm coordination, peer discovery, and low-latency command propagation.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        SHADOWCYPHER v3.0.0                               │
├──────────────────────┬──────────────────────┬────────────────────────────┤
│   GTK-3.0 UI         │   AI Engine          │   Native Core (Go)         │
│   ───────────────    │   ──────────         │   ─────────────────────    │
│   Cairo Gauges       │   Ollama (GPU)       │   WebSocket Relay          │
│   Page Router        │   MetaChain Agent    │   Swarm Discovery          │
│   TacticalTerminal   │   TreeQuest MCTS     │   Token Auth               │
│   Sidebar Nav        │   Intent→Execute     │   Stealth Module           │
├──────────────────────┴──────────────────────┴────────────────────────────┤
│                          EVENT BUS (ShadowBus)                           │
│                   Thread-safe pub/sub + async dispatch                   │
├────────────────────────┬─────────────────────┬───────────────────────────┤
│  Intelligence Layer    │  Analysis Layer      │  Core Engine              │
│  ──────────────────    │  ──────────────      │  ────────────             │
│  CISA KEV (1627 CVEs)  │  Security Assessor  │  Config (Pydantic)        │
│  EPSS Scoring          │  MITRE ATT&CK Tags  │  Knowledge Graph          │
│  OTX AlienVault        │  Rule-based Triage  │  AES-256-GCM / X25519    │
│  AbuseIPDB             │  Pattern Matching   │  Logger (JSONL)           │
│  URLhaus (malware)     │  Remediation Plans  │  Runner / Forensics       │
│  Tor Exit Blocklist    │                     │                           │
└────────────────────────┴─────────────────────┴───────────────────────────┘
```

### Why This Stack

| Decision | Rationale |
|---|---|
| **GTK-3.0** over Electron | 40MB footprint vs 400MB. Native rendering. No Chromium tax on your GPU during an engagement. |
| **Go relay** over pure Python | WebSocket handling at 10,000+ concurrent connections. Python's GIL makes this impossible natively. |
| **Local Ollama** over cloud APIs | Your prompts never leave your machine. Model weights live on your GPU. No rate limits, no shared logs, nothing to subpoena. |
| **Pydantic config** over YAML | Type validation at load time. Environment variable injection. No more "why is my port a string" debugging at 2 AM. |
| **AES-256-GCM + X25519** | AEAD encryption with forward-secret key exchange. Every chat session generates ephemeral keys that die when the session ends. |

---

## Tactical Divisions

### NEXUS-COMMAND — Situational Awareness & AI Operations

The nerve center. Everything an operator needs to understand the state of their environment and issue directives.

| Module | What It Does |
|---|---|
| **Central Command HUD** | Real-time operational dashboard built with Cairo vector graphics. Three arc gauges (CPU, RAM, Disk) with dynamic color shifting at 65% and 85% thresholds. Arsenal status grid showing which tools are installed on the host. Live mission telemetry feed. Refreshes every 1.5 seconds with zero socket overhead. |
| **Shadow-Synthesizer** | Local AI conversational interface. Supports any Ollama-compatible model (Gemma, LLaMA, DeepSeek, Mistral, Phi, Qwen). Streaming token output. Conversation history with per-session context. Backend switching between Ollama REST and llama-cpp-python for maximum hardware compatibility. |
| **Quantum-Core** | Deep-analysis AI mode. When a task requires multi-step reasoning—analyzing a packet capture, decomposing a binary, or planning a multi-phase engagement—Quantum-Core engages the local model with a specialized system prompt that forces step-by-step reasoning and self-verification. Runs entirely through your local Ollama instance. No external dependencies. |
| **Spectre War-Map** | Network topology visualization. Renders discovered nodes on an interactive canvas with connection state, latency indicators, and geographic approximation via GeoIP. Integrated with the Nexus Relay for real-time peer discovery. |
| **ShadowScript Lab** | Custom tactical scripting language with a hand-written lexer, recursive descent parser, and tree-walking interpreter. Designed for orchestrating complex multi-tool engagements in a domain-specific syntax. Includes a reference grammar bible. |

### COVERT-INTEL — Reconnaissance & Intelligence Gathering

Passive and active intelligence collection across every layer of the stack.

| Module | What It Does |
|---|---|
| **Signal Analysis** | Deep network reconnaissance powered by Nmap. Service version detection, OS fingerprinting, script scanning, and traceroute in a unified GTK interface. Results are parsed and fed into the forensic registry for correlation. MITRE ATT&CK technique IDs automatically tagged on all findings. |
| **Spectral Intelligence** | OSINT toolkit. Sherlock-based username enumeration across 300+ platforms. WHOIS lookups. DNS record enumeration (A, AAAA, MX, NS, TXT, SOA). Reverse IP resolution. All results are stored in the local forensic database. |
| **Infrastructure Recon** | Full-stack host discovery. ARP scanning for local network mapping. TCP/UDP port sweeps. Banner grabbing. SSL certificate inspection. Designed to build a complete picture of a target environment before engagement. |
| **Vulnerability Sweep** | Nuclei-based vulnerability scanning with severity filtering and tag-based targeting. Custom template support. Results are cross-referenced with Exploit-DB via SearchSploit for immediate actionability. |
| **CVE Intelligence** | Live NVD API v2 integration with 6-hour cache. Correlates discovered service banners against the National Vulnerability Database. Automatically enriched with **EPSS scores** (first.org — probability of exploitation in next 30 days) and **CISA KEV membership** (1,627 known exploited CVEs). KEV hits surface as `[KEV]` with federal due dates. |
| **Threat Intel** | Multi-source IP/domain/hash reputation. **OTX AlienVault** (pulse count + malicious indicators), **AbuseIPDB** (confidence score 0–100), **URLhaus** (live malware delivery URLs, no auth), **Tor exit list** (torproject.org bulk list, local set lookup). All sources queried in parallel; results merged into a unified verdict. Ingested into the knowledge graph. |
| **Gaming Asset Audit** | Steam/gaming platform security analysis. Account exposure checking, session token validation, and platform-specific vulnerability assessment. |

### AI INTELLIGENCE PIPELINE — Intent → Execute → Analyze

ShadowCypher's AI layer uses a three-stage pipeline borrowed from production security tooling. Small local models (7B–14B) don't reliably emit tool-call JSON, so rather than trusting the model to invoke tools correctly, the pipeline detects intent from the user's message directly, runs the real tool first, and then feeds the actual output to the AI for analysis.

```
User Query
    │
    ▼
Intent Detector (14 patterns: nmap / nuclei / nikto / sqlmap / threat-intel / OSINT / ...)
    │
    ├── Tool with target detected? ──YES──▶ Execute real tool (nmap, OTX, CVE lookup, ...)
    │                                              │
    │                                              ▼
    │                                    Inject real output into AI prompt
    │                                              │
    └── General query? ─────────────────▶ Route to specialist agent
                                                   │
                                                   ▼
                                          AI analyzes actual scan data
                                          (not hallucinated results)
```

**TreeQuest Attack Chain Planner** (Sakana AI): When you need to plan a full assessment rather than a single tool run, `tree_planner.plan(target, context)` uses Monte Carlo Tree Search (MCTS) to explore sequences of security actions. The local AI predicts what each action would find at each branch; the tree search finds the highest-value path. Returns an ordered action plan with confidence scores. Dangerous actions (`sql_injection`, `vuln_scan`) require explicit operator confirmation before execution.

**Security Assessor**: After any scan session, `assessor.assess_findings(cves, threat_intel, ports)` produces instant rule-based triage in <1ms — no LLM required. Eight security combination patterns fire advisory text when matched (e.g. `KEV_exploited + high_EPSS + port_open` → "CRITICAL CHAIN — patch immediately"). Output includes threat level, pattern matches, lead CVE/indicator, and prioritized remediation steps.

**MITRE ATT&CK Coverage**: 65 ATT&CK technique IDs mapped across all scan/exploit tool outputs. Every finding is automatically tagged with relevant technique IDs and tactics. Mission reports include a full coverage matrix grouped by tactic.

---

### OFFENSIVE-LAB — Exploitation & Payload Engineering

Purpose-built tools for authorized penetration testing and red team operations.

| Module | What It Does |
|---|---|
| **DeepHat Apex** | AI-powered offensive script synthesis. The MetaChain autonomous agent decomposes a high-level objective ("find and exploit the FTP vulnerability on 10.0.0.5") into discrete tool invocations, executes them sequentially, and synthesizes the results. Powered by the AutoAgent framework with a 30+ tool registry. |
| **Ghost Factory** | Multi-platform payload generation. Wraps `msfvenom` for Meterpreter payloads across Linux, Windows, and macOS. Supports ELF, EXE, Mach-O, raw, and Python output formats. Tracks generated payloads with mutation history. |
| **Phishing Synthesis** | Social engineering campaign forge. Template-based phishing page generation with automated Cloudflare tunnel exposure for instant HTTPS. Let's Encrypt integration for custom domain deployments. Credential capture and relay. |
| **Ghost-Hose** | Network stress testing engine. Five attack modes: UDP flood, TCP SYN, Layer 7 HTTP, Slowloris, and Mixed. Configurable thread count, duration limits, and real-time throughput reporting. Built for authorized lab environments and sacrificial gauntlets only. |
| **Web Layer Attacks** | SQL injection, XSS, SSRF, and directory fuzzing (ffuf) in a unified interface. Supports both automated scanning and manual injection with custom payloads. |
| **Key Harvester** | Credential attack suite. Hydra for network brute-forcing (SSH, FTP, RDP, SMB, HTTP). John the Ripper and Hashcat for offline hash cracking with GPU acceleration. Wordlist management and custom rule generation. |
| **Wireless Saturation** | 802.11 attack toolkit. Aircrack-ng integration for WPA/WPA2 cracking, deauthentication attacks, and wireless network enumeration. Monitor mode management. |

### SOVEREIGN-OPS — Communication, Defense & System Integrity

The infrastructure that keeps you connected, encrypted, and invisible.

| Module | What It Does |
|---|---|
| **Sovereign Chat** | Production-grade WebSocket communication hub replacing legacy IRC. Multi-room support with presence tracking. **AES-256-GCM encryption at rest** with per-room derived keys. **X25519 ECDH ephemeral key exchange** on every session for forward secrecy. If a session key is compromised, past and future sessions remain secure. SQLite message persistence with configurable retention. |
| **Go Signal Relay** | Compiled native binary (9.2MB) handling WebSocket connections for swarm coordination. Token-based authentication. Sub-millisecond message relay. Runs as a background process, automatically compiled from source by the launcher if the binary is stale. |
| **ShadowSentinel (IRC Bot)** | Skybot-style modular IRC bot with 20+ commands. Connects to both external IRC (Libera) and sovereign Ergo servers. Per-user conversation memory via the Classic Brain (ELIZA + Markov chain, zero network, fully offline). SHA-256 Proof-of-Work challenges for user verification. CTCP fingerprint capture and WHOIS correlation for forensic profiling. |
| **Wraith Protocol** | Emergency lockdown interface. Spectre Flash-Wipe purges all ephemeral mission data, session keys, and forensic artifacts in a single action. Tunnel termination kills all active processes. Log purge removes operational traces. Confirmation dialogs prevent accidental activation. |
| **God-Panel** | Full-spectrum system control. Live subsystem matrix showing the status of every service (Ollama, Go Relay, Sovereign Chat, Sisyphus, IRC Sentinel) with real-time latency probes. AI model hot-swapping. Integrity baseline regeneration. Process termination. Threat registry viewer. |
| **Sisyphus Sentinel** | Continuous integrity monitoring. SHA-256 hashes every Python source file in the project on a 60-second cycle. Detects unauthorized modifications, syntax corruption, and dependency tampering. Broadcasts alerts via the event bus when violations are detected. |
| **Citadel Security** | AES-256-GCM vault encryption with PBKDF2 key derivation (200,000 iterations). RSA-OAEP asymmetric ticket encryption for admin-user communication. Hardware fingerprinting for machine-level identity verification. SSH honeypot (port 2222) that mimics OpenSSH 7.4 to bait and log adversaries. |

### GHOST-PROTOCOL — Operational Anonymity & Anti-Forensics

Total operational invisibility for when you absolutely cannot be seen.

| Module | What It Does |
|---|---|
| **Ghost Mode** | One-command total invisibility. 8 layers: iptables kill-switch (forces ALL traffic through Tor), MAC randomization, hostname/timezone neutralization, DNS leak prevention, RAM-only workspace, system log suppression. Full state restore on disengage. |
| **Shadow Audit** | Comprehensive anonymity chain validator. Tests Tor, DNS leaks, MAC fingerprinting, hostname/timezone exposure, firewall rules, mesh key permissions, WireGuard config, browser fingerprints. Returns an anonymity score with auto-fix capability. |
| **Traffic Mirage** | Deep packet inspection evasion. obfs4 bridge configuration (makes Tor look like HTTPS), realistic cover traffic generation, DNS tunneling setup, traffic timing obfuscation via `tc netem` to defeat correlation attacks. |
| **Dead Drop** | Anti-forensics toolkit. 7-pass secure file shredding with random rename before unlink, swap partition sanitization, free-space wiping, LUKS-encrypted USB dead drop creation, and emergency PANIC button that destroys all keys, databases, configs, and logs instantly. |
| **Trace Eraser** | Deep forensic log cleaner. Scrubs shell histories (12 types), system logs (auth, syslog, kern, daemon), application traces, systemd journal, wtmp/btmp/lastlog, thumbnail caches, and recently-used files. Timestamp obfuscation mode randomizes file access times. |
| **Tor Cloak** | Full Tor lifecycle manager. Start/stop/verify Tor, circuit rotation via ControlPort, torified fetch and shell sessions, IP protection hardening (DNS redirect, WebRTC leak info, MAC check). |

### GUARDIAN — Personal Device Security

Protect everything you own. Phones, PCs, tablets, routers, TVs, IoT devices.

| Module | What It Does |
|---|---|
| **Network Scan** | Discovers every device on your network via ARP/nmap. Fingerprints ports, identifies OS, flags dangerous services (Telnet, SMB, TR-069, UPnP). Risk assessment per device. |
| **Router Audit** | Audits your home router for exposed management ports, ISP remote access (TR-069), UPnP, and weak DNS config. Provides actionable hardening recommendations. |
| **Device Monitor** | Continuous 24/7 threat monitoring. Detects new devices joining your network, ARP spoofing attacks, and device disappearances. Real-time alerting. |
| **Auto-Harden** | One-command machine hardening: unattended security updates, SSH root login disable, iptables default-DROP policy, core dump disable, sensitive file permission lockdown. |
| **Deep Audit** | Local machine security audit: SUID binary check, SSH configuration review, world-writable file scan, failed login analysis, listening service inventory. |

---

## shadow-cli — AI Security Assistant

ShadowCypher ships with `shadow-cli`, an AI-powered command-line security assistant that can call all ShadowCypher tools through natural language.

```bash
shadow-cli                              # Interactive mode
shadow-cli -p "scan my network"         # Discovers all devices on your LAN
shadow-cli -p "engage ghost mode"       # Activates total invisibility
shadow-cli -p "am I anonymous?"         # Runs full anonymity audit
shadow-cli -p "audit my router"         # Checks router for vulnerabilities
shadow-cli -p "check my traffic"        # Analyzes network traffic patterns
```

Powered by an MCP (Model Context Protocol) server that exposes 9 security tools to any compatible AI assistant.

---

## Security Architecture

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

- **Forward Secrecy**: Ephemeral X25519 keys per session. Compromise of one session reveals nothing about past or future sessions.
- **At-Rest Encryption**: All stored messages are AES-256-GCM encrypted with per-room derived keys.
- **Admin Identity**: RSA-4096 key pair verification with challenge-response. Hardware fingerprint binding locks admin privileges to a specific machine.

---

## Event-Driven Architecture

ShadowCypher's modules are decoupled through the **ShadowBus**, a thread-safe, async-aware publish/subscribe event backbone. This eliminates circular imports and allows any module to react to events from any other module without direct dependencies.

```python
# Any module can broadcast
bus.publish("forensic_update", {"handle": "attacker", "risk": "HIGH"})

# Any module can subscribe
bus.subscribe("forensic_update", lambda data: firewall.block(data["handle"]))
```

Key event channels: `mission_output`, `module_log`, `pulse_anomaly`, `forensic_update`, `security_lockdown`, `new_chat_msg`, `sovereign_chat`, `mission_archived`.

---

## Installation

### Prerequisites

| Dependency | Purpose | Required |
|---|---|---|
| Python 3.12+ | Core runtime | ✅ |
| GTK 3.0 (`python3-gi`, `gir1.2-gtk-3.0`) | Desktop interface | ✅ |
| Go 1.24+ | Native relay compilation | ✅ |
| Ollama | Local AI inference (auto-started) | ✅ |
| `cryptography` (Python) | AES-256-GCM, X25519, RSA | ✅ |
| `pydantic`, `pydantic-settings` | Configuration engine | ✅ |
| `aiohttp` | WebSocket chat + Nexus API | ✅ |
| `psutil` | System metrics | ✅ |
| nmap, hydra, john, hashcat | Offensive tools | Optional |
| nuclei, ffuf, aircrack-ng | Scanning & wireless | Optional |
| proxychains4, tor | Anonymization | Optional |

### Quick Start

```bash
# Clone the repository
git clone https://github.com/jakes1345/ShadowCypher.git
cd ShadowCypher

# Install Python dependencies
pip install -r requirements.txt

# Launch
python3 -m shadowcypher.app
```

### Manual Launch

```bash
# Activate the virtual environment
source ai_engine/meta-venv/bin/activate   # Primary
# or: source venv/bin/activate            # Fallback

# Set environment
export PYTHONPATH="$(pwd):$(pwd)/ai_engine:$PYTHONPATH"
export SHADOW_PORT=8888

# Run
python3 -m shadowcypher.app
```

### System Command (if installed globally)

```bash
shadowcypher
```

---

## Project Structure

```
ShadowCypher/
├── shadowcypher/              # Core Python package
│   ├── app.py                 # GTK application entry point
│   ├── core/                  # Hub, Config, Bus, Runner, Identity, Security
│   │   ├── hub.py             # Mission orchestrator + relay bridge
│   │   ├── mitre.py           # MITRE ATT&CK database (65 technique IDs)
│   │   ├── knowledge_graph.py # SQLite tactical intelligence graph
│   │   ├── assessor.py        # Rule-based security situation assessor
│   │   ├── sovereign_chat.py  # WebSocket chat (X25519 + AES-256-GCM)
│   │   ├── irc_bot.py         # ShadowSentinel IRC bot (20+ commands)
│   │   └── ...
│   ├── ai/                    # AI subsystem
│   │   ├── intent.py          # Intent detector (14 security tool patterns)
│   │   ├── tree_planner.py    # Sakana AI TreeQuest attack chain planner
│   │   ├── agents.py          # Agent fleet + Intent→Execute→Analyze dispatch
│   │   ├── orchestrator.py    # MetaChain autonomous agent
│   │   ├── auto_orchestrator.py # Unified mission dispatch bridge
│   │   ├── adversary_sim.py   # Autonomous red team simulation engine
│   │   ├── classic_brain.py   # Offline ELIZA + Markov conversational AI
│   │   ├── sisyphus.py        # File integrity sentinel
│   │   └── ...
│   ├── ui/                    # GTK pages (40+ tactical interfaces)
│   ├── modules/               # Offensive/defensive tool wrappers (40+)
│   │   ├── cve_feed.py        # NVD CVE feed + EPSS + CISA KEV enrichment
│   │   ├── threat_intel.py    # OTX + AbuseIPDB + URLhaus + Tor exits
│   │   ├── recon.py           # Nmap + subdomain enum + HTTP probing
│   │   ├── vuln_scanner.py    # Nuclei + Nikto + SQLmap wrappers
│   │   └── ...
│   ├── native/relay/          # Go WebSocket relay (compiled binary)
│   └── compiler/              # ShadowScript lexer + interpreter
├── ai_engine/autoagent/       # MetaChain autonomous agent framework
├── tools/                     # Bundled third-party tools
├── scripts/                   # Setup and utility scripts
├── config.json                # Runtime configuration
└── requirements.txt           # Python dependencies
```

---

## Configuration

ShadowCypher uses a Pydantic-based configuration engine with three-tier resolution:

1. **Environment Variables** — `SC_AI__MODEL=gemma4` overrides `config.ai.model`
2. **config.json** — Persistent configuration file in project root
3. **Code Defaults** — Sensible defaults for every setting

Key configuration sections:

| Section | Controls |
|---|---|
| `ai` | Model name, API base, temperature, token limits, GPU layer count |
| `tools` | Paths to nmap, hydra, john, hashcat, and 14 other offensive tools |
| `irc` | Server, port, channel, SASL auth, sovereign mode, bot personality |
| `identity` | Operator handle, admin list, master hardware fingerprint |
| `stealth` | Proxy URL, privacy enforcement, Nexus relay endpoint |
| `intel` | Threat intel API keys: `otx_api_key`, `abuseipdb_api_key` |

### API Keys (optional — all sources have free/no-key tiers)

| Source | Key Variable | Free Tier | Get Key |
|---|---|---|---|
| OTX AlienVault | `intel.otx_api_key` | Anonymous (rate-limited) | otx.alienvault.com |
| AbuseIPDB | `intel.abuseipdb_api_key` | 1,000 checks/day | abuseipdb.com/register |
| URLhaus | *(none)* | Unlimited | abuse.ch (no auth) |
| Tor Exit List | *(none)* | Unlimited | torproject.org (no auth) |
| CISA KEV | *(none)* | Unlimited | cisa.gov (no auth) |
| EPSS (first.org) | *(none)* | Unlimited | first.org (no auth) |

---

## Contributing

ShadowCypher is a sovereign project. Contributions are welcome from those who understand the mission:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-module`)
3. Write real implementations (no placeholders, no stubs, no "TODO" comments)
4. Test against the `ShadowAudit` diagnostic suite (`from shadowcypher.core.audit import auditor; auditor.run_full_diagnostic()`)
5. Submit a pull request with a clear description of what the code does and why it exists

---

## ShadowOS

An Arch Linux-based live/installable ISO: the ShadowCypher operating environment. Pentest tools, developer workstation, and gaming, all in one hardened OS with Hyprland, a custom Plymouth boot sequence, and ShadowCypher pre-installed at `/opt/shadowcypher`.

| Layer | What ships |
|-------|-----------|
| **Kernel** | linux-hardened + sysctl hardening |
| **Compositor** | Hyprland (Wayland) + Waybar + Wofi + Hyprlock |
| **Pentest** | nmap, sqlmap, hydra, metasploit, aircrack-ng, bettercap, rustscan, ffuf, nuclei, impacket, netexec, wireshark, and more |
| **Dev** | VSCode, neovim, docker, podman, kubectl, rustup, go, nodejs, lazygit, Distrobox |
| **Gaming** | Steam, Heroic, Lutris, PrismLauncher, MangoHUD, GameScope, wine-staging |
| **Privacy** | Tor, dnscrypt-proxy, MAC randomization, AppArmor, ufw |
| **Modes** | `shadow-mode <normal/dev/pentest/privacy/ghost/undercover>` — hot-swap firewall, DNS, autostart |
| **AI** | ShadowCypher GTK app + Ollama pre-loaded |

**Status: v0.1.0 — ISOs verified, ~7.4 GB**

### Build

```bash
# Native (Arch host)
sudo pacman -S archiso
cd shadowos && sudo ./build.sh
# → out/shadowos-<date>-x86_64.iso

# Docker (any host)
cd shadowos && ./build-docker.sh
```

### Test in QEMU

```bash
qemu-system-x86_64 -enable-kvm -m 4G -cdrom out/shadowos-*.iso -vga virtio
```

Default live credentials: `shadow` / `shadow` (user + root). Reset by the installer.

---

## Legal

ShadowCypher is built exclusively for **authorized security testing**, **research**, and **education**. Every offensive module assumes the operator has explicit written authorization to test the target systems. Unauthorized use of these tools against systems you do not own or have permission to test is illegal and unethical.

The authors assume no liability for misuse. You are the operator. You own your actions.

---

<p align="center">
  <strong>ShadowCypher v3.0.0</strong> · Built with Go, Python, and Cairo.
</p>

<p align="center">
  <a href="https://shadowcypher.site">shadowcypher.site</a> · <a href="https://github.com/jakes1345/ShadowCypher">GitHub</a>
</p>
