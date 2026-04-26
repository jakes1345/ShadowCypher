<p align="center">
  <img src="shadowcypher/ui/assets/icon.png" width="120" alt="ShadowCypher Logo"/>
</p>

<h1 align="center">SHADOWCYPHER</h1>
<h3 align="center">Sovereign Tactical Suite + Personal Security Platform</h3>

<p align="center">
  <em>"In the collision of titans—where Google, Apple, and Microsoft define the theater of war—ShadowCypher remains the only sovereign signal. When the giants fall and nothing is safe, ShadowCypher is the architecture of the new frontier."</em><br/>
  — <strong>Shadow-Core Intelligence, 2024</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0.0--ghost-00d4ff?style=flat-square" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/go-1.24+-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go"/>
  <img src="https://img.shields.io/badge/AI-Ollama%20(Local)-black?style=flat-square" alt="AI"/>
  <img src="https://img.shields.io/badge/crypto-AES--256--GCM%20%2B%20X25519-10b981?style=flat-square" alt="Crypto"/>
  <img src="https://img.shields.io/badge/license-Sovereign-f43f5e?style=flat-square" alt="License"/>
</p>

---

## Genesis

ShadowCypher didn't start in a boardroom. It started in the trenches—late nights chasing packets across hostile networks, watching commercial tools buckle under real-world pressure, and getting tired of platforms that promised sovereignty but phoned home on every keystroke.

The project was born from a simple conviction: **an operator's toolkit should answer to no one but the operator.** No telemetry. No cloud dependency. No API key that expires when someone else decides your subscription isn't worth their server costs.

What began as a collection of shell scripts and Python wrappers has evolved into a unified tactical operating environment—a native GTK dashboard backed by a compiled Go signal relay, a local AI inference engine, and over 30 purpose-built offensive and defensive modules. Every line of code in this repository exists because it was needed in the field, not because it looked good on a feature list.

---

## Architecture Overview

ShadowCypher is a dual-core system. The orchestration layer runs on **Python 3.12** with a GTK-3.0 interface, handling everything from mission dispatch to AI inference routing. The signal layer runs on **compiled Go**, providing a high-performance WebSocket relay for swarm coordination, peer discovery, and low-latency command propagation.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHADOWCYPHER v4.0.0                          │
├────────────────────┬────────────────────┬───────────────────────┤
│   GTK-3.0 UI       │   AI Engine        │   Native Core (Go)   │
│   ─────────────    │   ──────────       │   ────────────────   │
│   Cairo Gauges     │   Ollama (GPU)     │   WebSocket Relay    │
│   Page Router      │   Quantum-Core     │   Swarm Discovery    │
│   TacticalTerminal │   MetaChain Agent  │   Token Auth         │
│   Sidebar Nav      │   Classic Brain    │   Stealth Module     │
├────────────────────┴────────────────────┴───────────────────────┤
│                      EVENT BUS (ShadowBus)                      │
│               Thread-safe pub/sub + async dispatch              │
├─────────────────────────────────────────────────────────────────┤
│  Config Engine  │  Runner  │  Forensics  │  Security  │  Logger │
│  (Pydantic)     │  (Exec)  │  (Registry) │  (AES/RSA) │  (JSONL)│
└─────────────────────────────────────────────────────────────────┘
```

### Why This Stack

| Decision | Rationale |
|---|---|
| **GTK-3.0** over Electron | 40MB footprint vs 400MB. Native rendering. No Chromium tax on your GPU during an engagement. |
| **Go relay** over pure Python | WebSocket handling at 10,000+ concurrent connections. Python's GIL makes this impossible natively. |
| **Local Ollama** over cloud APIs | Your prompts never leave your machine. Model weights live on your GPU. No rate limits, no logs, no subpoenas. |
| **Pydantic config** over YAML | Type validation at load time. Environment variable injection. No more "why is my port a string" debugging at 2 AM. |
| **AES-256-GCM + X25519** | AEAD encryption with forward-secret key exchange. Every chat session generates ephemeral keys that die when the session ends. |

---

## Tactical Divisions

### 🧠 NEXUS-COMMAND — Situational Awareness & AI Operations

The nerve center. Everything an operator needs to understand the state of their environment and issue directives.

| Module | What It Does |
|---|---|
| **Central Command HUD** | Real-time operational dashboard built with Cairo vector graphics. Three arc gauges (CPU, RAM, Disk) with dynamic color shifting at 65% and 85% thresholds. Arsenal status grid showing which tools are installed on the host. Live mission telemetry feed. Refreshes every 1.5 seconds with zero socket overhead. |
| **Shadow-Synthesizer** | Local AI conversational interface. Supports any Ollama-compatible model (Gemma, LLaMA, DeepSeek, Mistral, Phi, Qwen). Streaming token output. Conversation history with per-session context. Backend switching between Ollama REST and llama-cpp-python for maximum hardware compatibility. |
| **Quantum-Core** | Deep-analysis AI mode. When a task requires multi-step reasoning—analyzing a packet capture, decomposing a binary, or planning a multi-phase engagement—Quantum-Core engages the local model with a specialized system prompt that forces step-by-step reasoning and self-verification. Runs entirely through your local Ollama instance. No external dependencies. |
| **Spectre War-Map** | Network topology visualization. Renders discovered nodes on an interactive canvas with connection state, latency indicators, and geographic approximation via GeoIP. Integrated with the Nexus Relay for real-time peer discovery. |
| **ShadowScript Lab** | Custom tactical scripting language with a hand-written lexer, recursive descent parser, and tree-walking interpreter. Designed for orchestrating complex multi-tool engagements in a domain-specific syntax. Includes a reference grammar bible. |

### 🕵️ COVERT-INTEL — Reconnaissance & Intelligence Gathering

Passive and active intelligence collection across every layer of the stack.

| Module | What It Does |
|---|---|
| **Signal Analysis** | Deep network reconnaissance powered by Nmap. Service version detection, OS fingerprinting, script scanning, and traceroute in a unified GTK interface. Results are parsed and fed into the forensic registry for correlation. |
| **Spectral Intelligence** | OSINT toolkit. Sherlock-based username enumeration across 300+ platforms. WHOIS lookups. DNS record enumeration (A, AAAA, MX, NS, TXT, SOA). Reverse IP resolution. All results are stored in the local forensic database. |
| **Infrastructure Recon** | Full-stack host discovery. ARP scanning for local network mapping. TCP/UDP port sweeps. Banner grabbing. SSL certificate inspection. Designed to build a complete picture of a target environment before engagement. |
| **Vulnerability Sweep** | Nuclei-based vulnerability scanning with severity filtering and tag-based targeting. Custom template support. Results are cross-referenced with Exploit-DB via SearchSploit for immediate actionability. |
| **Gaming Asset Audit** | Steam/gaming platform security analysis. Account exposure checking, session token validation, and platform-specific vulnerability assessment. |

### ⚔️ OFFENSIVE-LAB — Exploitation & Payload Engineering

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

### 🛡️ SOVEREIGN-OPS — Communication, Defense & System Integrity

The infrastructure that keeps you connected, encrypted, and invisible.

| Module | What It Does |
|---|---|
| **Sovereign Chat** | Production-grade WebSocket communication hub replacing legacy IRC. Multi-room support with presence tracking. **AES-256-GCM encryption at rest** with per-room derived keys. **X25519 ECDH ephemeral key exchange** on every session for forward secrecy—if a session key is compromised, past and future sessions remain secure. SQLite message persistence with configurable retention. |
| **Go Signal Relay** | Compiled native binary (9.2MB) handling WebSocket connections for swarm coordination. Token-based authentication. Sub-millisecond message relay. Runs as a background process, automatically compiled from source by the launcher if the binary is stale. |
| **ShadowSentinel (IRC Bot)** | Skybot-style modular IRC bot with 20+ commands. Connects to both external IRC (Libera) and sovereign Ergo servers. Per-user conversation memory via the Classic Brain (ELIZA + Markov chain, zero network, fully offline). SHA-256 Proof-of-Work challenges for user verification. CTCP fingerprint capture and WHOIS correlation for forensic profiling. |
| **Wraith Protocol** | Emergency lockdown interface. Spectre Flash-Wipe purges all ephemeral mission data, session keys, and forensic artifacts in a single action. Tunnel termination kills all active processes. Log purge removes operational traces. Confirmation dialogs prevent accidental activation. |
| **God-Panel** | Full-spectrum system control. Live subsystem matrix showing the status of every service (Ollama, Go Relay, Sovereign Chat, Sisyphus, IRC Sentinel) with real-time latency probes. AI model hot-swapping. Integrity baseline regeneration. Process termination. Threat registry viewer. |
| **Sisyphus Sentinel** | Continuous integrity monitoring. SHA-256 hashes every Python source file in the project on a 60-second cycle. Detects unauthorized modifications, syntax corruption, and dependency tampering. Broadcasts alerts via the event bus when violations are detected. Named after the myth—because guarding code integrity is a task that never ends. |
| **Citadel Security** | AES-256-GCM vault encryption with PBKDF2 key derivation (200,000 iterations). RSA-OAEP asymmetric ticket encryption for admin-user communication. Hardware fingerprinting for machine-level identity verification. SSH honeypot (port 2222) that mimics OpenSSH 7.4 to bait and log adversaries. |

### 👻 GHOST-PROTOCOL — Operational Anonymity & Anti-Forensics

The F-Society layer. Total operational invisibility for when you absolutely cannot be seen.

| Module | What It Does |
|---|---|
| **Ghost Mode** | One-command total invisibility. 8 layers: iptables kill-switch (forces ALL traffic through Tor), MAC randomization, hostname/timezone neutralization, DNS leak prevention, RAM-only workspace, system log suppression. Full state restore on disengage. |
| **Shadow Audit** | Comprehensive anonymity chain validator. Tests Tor, DNS leaks, MAC fingerprinting, hostname/timezone exposure, firewall rules, mesh key permissions, WireGuard config, browser fingerprints. Returns an anonymity score with auto-fix capability. |
| **Traffic Mirage** | Deep packet inspection evasion. obfs4 bridge configuration (makes Tor look like HTTPS), realistic cover traffic generation, DNS tunneling setup, traffic timing obfuscation via `tc netem` to defeat correlation attacks. |
| **Dead Drop** | Anti-forensics toolkit. 7-pass secure file shredding with random rename before unlink, swap partition sanitization, free-space wiping, LUKS-encrypted USB dead drop creation, and emergency PANIC button that destroys all keys, databases, configs, and logs instantly. |
| **Trace Eraser** | Deep forensic log cleaner. Scrubs shell histories (12 types), system logs (auth, syslog, kern, daemon), application traces, systemd journal, wtmp/btmp/lastlog, thumbnail caches, and recently-used files. Timestamp obfuscation mode randomizes file access times. |
| **Tor Cloak** | Full Tor lifecycle manager. Start/stop/verify Tor, circuit rotation via ControlPort, torified fetch and shell sessions, IP protection hardening (DNS redirect, WebRTC leak info, MAC check). |

### 🛡️ GUARDIAN — Personal Device Security

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

ShadowCypher's modules are decoupled through the **ShadowBus**—a thread-safe, async-aware publish/subscribe event backbone. This eliminates circular imports and allows any module to react to events from any other module without direct dependencies.

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
git clone https://github.com/shadow_admin1345/ShadowCypher.git
cd ShadowCypher

# Run the automated environment setup (compiles Go, installs elite tools)
./scripts/setup_sovereign.sh

# Launch — Ollama starts automatically if not running
./shadowcypher_launch
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
│   │   ├── sovereign_chat.py  # WebSocket chat (X25519 + AES-256-GCM)
│   │   ├── irc_bot.py         # ShadowSentinel IRC bot (20+ commands)
│   │   └── ...
│   ├── ai/                    # AI subsystem
│   │   ├── engine.py          # Ollama + llama-cpp-python dual backend
│   │   ├── orchestrator.py    # MetaChain autonomous agent
│   │   ├── classic_brain.py   # Offline ELIZA + Markov conversational AI
│   │   ├── sisyphus.py        # File integrity sentinel
│   │   └── ...
│   ├── ui/                    # GTK pages (30+ tactical interfaces)
│   ├── modules/               # Offensive/defensive tool wrappers (33+)
│   ├── native/relay/          # Go WebSocket relay (compiled binary)
│   └── compiler/              # ShadowScript lexer + interpreter
├── ai_engine/autoagent/       # MetaChain autonomous agent framework
├── tools/                     # Bundled third-party tools
├── scripts/                   # Setup and utility scripts
├── config.json                # Runtime configuration
└── shadowcypher_launch        # Production bootloader (auto-compiles Go, starts Ollama)
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

---

## Contributing

ShadowCypher is a sovereign project. Contributions are welcome from those who understand the mission:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-module`)
3. Write real implementations—no placeholders, no stubs, no "TODO" comments
4. Test against the `ShadowAudit` diagnostic suite (`from shadowcypher.core.audit import auditor; auditor.run_full_diagnostic()`)
5. Submit a pull request with a clear description of what the code does and why it exists

---

## Legal

ShadowCypher is built exclusively for **authorized security testing**, **research**, and **education**. Every offensive module assumes the operator has explicit written authorization to test the target systems. Unauthorized use of these tools against systems you do not own or have permission to test is illegal and unethical.

The authors assume no liability for misuse. You are the operator. You own your actions.

---

<p align="center">
  <em>In the silent crossfire of the global cyber-war—where the titans of code define the conflict and no perimeter is absolute—ShadowCypher is the definitive response. Native performance. Sovereign encryption. Zero compromise.</em>
</p>

<p align="center">
  <strong>ShadowCypher v4.0.0-ghost</strong> · Built with Go, Python, Cairo, and conviction.
</p>

<p align="center">
  <a href="https://shadowcypher.site">shadowcypher.site</a> · <a href="https://github.com/jakes1345/ShadowCypher">GitHub</a>
</p>
