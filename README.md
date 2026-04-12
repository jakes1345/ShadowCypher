# ShadowCypher — DEEPHAT APEX Edition

> **Version 4.5.0-DEEPHAT** | GTK3 Desktop Application | Python 3.12+
> 
> **The Obsidian Citadel Protocol**: A high-performance, autonomous offensive platform equipped with Google-grade signal intelligence and **DeepHat Ultima** weapon synthesis.

ShadowCypher is a modular, autonomous penetration testing suite with AI-powered offensive operations, hardened WebSocket command servers, and multi-file weapon synthesis.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [First Launch & Licensing](#first-launch--licensing)
5. [Application Overview](#application-overview)
6. [Module Guide](#module-guide)
7. [AI Engine Setup](#ai-engine-setup)
8. [Gaming OSINT (Steam Integration)](#gaming-osint-steam-integration)
9. [Support & Communications](#support--communications)
10. [Admin Guide](#admin-guide)
11. [Configuration](#configuration)
12. [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/jakes1345/ShadowCypher.git
cd ShadowCypher

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch
python3 -m shadowcypher.app
```

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Linux (primary), macOS, Windows |
| **Python** | 3.10 or higher |
| **GTK** | GTK 3.0 (via PyGObject / `gi`) |
| **RAM** | 4 GB minimum, 8 GB recommended |
| **GPU** | Optional — for AI model acceleration and hashcat |
| **Network** | Required for OSINT, Steam integration, and deal scanning |

### Python Dependencies

```
PyGObject          # GTK3 bindings
requests           # HTTP client
psutil             # System monitoring
cryptography       # RSA/AES encryption for Support & Admin
pycairo            # Dashboard HUD rendering
```

### Optional External Tools

These are standard pentesting tools. ShadowCypher auto-detects them in your `$PATH` or in the `tools/` directory:

| Tool | Used By |
|------|---------|
| `nmap` | Network Ops, Recon, Vulnerability Pulse |
| `hydra` | Credential Assault |
| `john` / `hashcat` | Hash Cracking |
| `aircrack-ng` suite | Wireless Assault |
| `tcpdump` | Network Capture |
| `sherlock` | Deep OSINT |
| `searchsploit` | Exploit Search |
| `responder` | AD Attacks |
| `crackmapexec` | AD Infiltration |
| `nuclei` | Web Assault, Vuln Scanning |

---

## Installation

### Linux (Debian/Ubuntu)

```bash
# System dependencies
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 libcairo2-dev

# Python dependencies
pip install -r requirements.txt

# Optional: Install pentesting tools
sudo apt install nmap hydra john hashcat aircrack-ng tcpdump nikto
```

### macOS

```bash
brew install gtk+3 pygobject3 cairo
pip install -r requirements.txt
```

### Windows

Install [MSYS2](https://www.msys2.org/) and use its package manager:
```bash
pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-python-gobject
pip install -r requirements.txt
```

---

## First Launch & Licensing

### Step 1 — Launch the Application

```bash
cd ShadowCypher
python3 -m shadowcypher.app
```

The application opens with the **Operational Overview** dashboard showing real-time system metrics (CPU, RAM, Disk, Network) and a live mission feed.

### Step 2 — License Activation

ShadowCypher requires a valid license key to unlock the full arsenal. On first launch, you will be prompted for a key stored in `.session-secret`.

**To obtain a license key:**
1. Navigate to **Support & Comms** in the sidebar
2. Enter your operator handle (alias)
3. Type a message requesting access
4. Click **Transmit** — your message is RSA-encrypted and saved as a ticket
5. Contact the admin (see below) to process your request
6. Once approved, the admin will provide an AES-256 license key
7. Save the key to `.session-secret` in the project root

> **Note:** Only the admin can decrypt your support messages. No one else — not even someone with the source code — can read them without the admin's private key.

---

## Application Overview

### Sidebar Navigation

Click any item in the left sidebar to switch between modules. The sidebar is organized into sections:

| Section | Modules |
|---------|---------|
| **APEX COMMAND** | Dashboard, Tactical Swarm AI |
| **RECON & INTEL** | Signal Recon, Deep OSINT Hub, Network Ops, Wireless Assault |
| **OFFENSIVE STRIKE** | Web Assault, Offensive Exploit, Vulnerability Pulse, Credential Assault |
| **ADVANCED OPS** | AD Infiltration, AD Attacks (Impacket), Phishing Lab, Payload Forge, Digital Forensics |
| **SYSTEM OPS** | Firewall Control, Session Manager, Gaming OSINT, Support & Comms, Admin Panel |

### Status Bar

The bottom bar shows:
- **Role** — `ADMIN` or `OPERATOR` (cryptographic verified identity)
- **Active Missions** — Counter of concurrent autonomous operations
- **Spectrum Pulse** — Real-time anomaly status from the ShadowPulse engine
- **Uptime** — Application session duration

---

## V3 Core Architecture: The Obsidian Citadel

ShadowCypher V3 moves beyond simple tool-wrapping into a **Self-Aware Offensive Ecosystem**.

### 1. ShadowPulse SIGINT Engine
The "mathematical sixth sense" of the platform. Using **Wavelet Scattering Transforms (WST)**, the Pulse engine analyzes temporal transients in network traffic, command execution speed, and authentication latency.
- **Anomaly Detection**: Automatically identifies non-stationary signals (covert channels, EDR interference).
- **Tactical Throttling**: When anomalies are sensed, the platform autonomously injects micro-delays (1.5s+) to reduce its temporal footprint and evade adaptive defenses.

### 2. Kairos Intelligence Monitor
An asynchronous, passive analyzer that pipes all tactical output into a real-time intelligence fusion loop.
- **Target Topography**: Auto-maps IP ranges and discovered services.
- **Spectrum Feeding**: Feeds packet and line-length metadata directly into ShadowPulse.

### 3. ShadowHub Mission Director
The central brain that orchestrates the **AI Swarm**.
- **Reactive Dispatch**: When ShadowPulse flags an anomaly, the Hub autonomously spawns a new mission to investigate the source of the interference.
- **Mission Isolation**: Ensures 100% clean state between concurrent operations.

### 4. Sisyphus Sentinel
The autonomous "High Priest of Integrity" that monitors the health of the entire workstation.
- **Autonomous Governance**: Evaluates system vitals and proactively reports on performance bottlenecks.
- **AI-Consumable Audits**: Provides real-time health JSON to the Orchestrator for self-regulating intensity.

### 5. Sovereign Hub (Hardened Command)
A dual-port WebSocket server (8888 Primary / 44444 Ghost) for external control and AI-bridging.
- **HMAC Enforcement**: All connections require an `HMAC-SHA256` handshake signed with `SHADOW_MASTER_SECRET_2026`.
- **Ghost Port Redundancy**: An emergency ingress on port 44444 for mission-critical recovery.

### 6. DeepHat Apex Synthesis
A raw, unconstrained offensive engine utilizing the **Gemma-4-Heretic** model.
- **Weapon Synthesis**: Forges real, multi-file codebases (Exploits, DDoS, Doxing) with zero safety guardrails.
- **Artifact Extraction**: Automatically parses, saved, and grants executable permissions to AI-generated payload shards.

---

## Module Guide

### 📊 Operational Overview (Dashboard)

The main HUD with:
- **Tactical Radar** — Animated cyber radar visualization with real-time OSINT pings
- **System Metrics** — CPU, RAM, Disk, active missions (updated every 2 seconds)
- **Live Mission Feed** — Real-time log of all module activity

### 🤖 Tactical Swarm AI

AI-powered offensive operations using local or cloud AI models. Send natural language commands and the AI orchestrates multi-step attacks. Supports 10+ providers including Ollama, OpenAI, Claude, Gemini, and more.

**Setup:** Click ⚙ Settings inside the Tactical Swarm AI tab to configure your provider (see [AI Engine Setup](#ai-engine-setup))

### 📡 Signal Recon

Quick reconnaissance against a target:
- Port scanning, service detection
- Gateway discovery (auto-detects OS and uses appropriate commands)
- CPU/system info enumeration

### 🕵 Deep OSINT Hub

Cross-platform intelligence gathering:
- **Sherlock** — Username search across 300+ social networks
- **Holehe** — Email registration checks across 100+ sites
- **Steam Correlation** — Link gaming profiles to real identities
- **Leak Check** — Local credential database search

### 🌐 Network Ops

Full network toolkit:
- **ARP Scan** — Discover live hosts on local network
- **TCP Connect Scan** — Reliable port scanning
- **SYN Stealth Scan** — Fast, stealthy scanning (requires root)
- **OS Detection** — Remote OS fingerprinting via nmap
- **Service Fingerprint** — Version detection on open ports
- **Packet Capture** — Live tcpdump with BPF filters
- **Traffic Monitor** — Real-time traffic analysis
- **DNS Leak Test** — Check for DNS leaks

### 📶 Wireless Assault

Aircrack-ng suite integration:
- **List Interfaces** — Show wireless adapters
- **Enable/Disable Monitor** — Toggle monitor mode
- **Scan Networks** — Discover nearby APs with airodump-ng
- **Capture Handshake** — Target specific BSSID + channel
- **Deauth Attack** — Send deauthentication frames
- **Crack WPA** — Dictionary attack on captured handshakes

### 🌐 Web Assault

Web application testing:
- **Directory Fuzzing** — ffuf-powered directory discovery
- **Virtual Host Fuzzing** — Discover hidden vhosts
- **Nuclei Scan** — Template-based vulnerability scanning
- **Nuclei Update** — Keep templates current

### ⚡ Offensive Exploit (DeepHat Peak)

Exploit search and AI-powered tool synthesis:
- **DeepHat Ultima** — Autonomous synthesis of custom exploits and multi-stage stagers.
- **SearchSploit** — Search Exploit-DB locally.
- **Metasploit Integration** — Mission-aware MSF automation.
- **Payload Generation** — Real-time obfuscated droppers (ELF/EXE/PS1).
- **Auto Exploit** — AI-driven decision engine for target compromise.

### 🔑 Credential Assault

Brute force and hash cracking:
- **Hydra Tab** — Multi-protocol brute force (SSH, FTP, RDP, SMB, HTTP, MySQL, etc.)
- **Hash Cracking Tab** — Hashcat (GPU) or John (CPU) with 11 hash type presets
- **Hash Identify Tab** — Automatic hash format detection via hashid

### 🏰 AD Infiltration & AD Attacks

Active Directory operations:
- **Kerberoasting** — Extract TGS tickets for offline cracking
- **SMB Relay** — Responder + MultiRelay pipeline
- **SOCKS5 Pivot Tunnels** — SSH dynamic forwarding
- **CrackMapExec** — Automated SMB/LDAP enumeration
- **Impacket Suite** — psexec, secretsdump, Responder

### 🎣 Phishing Lab

Social engineering toolkit:
- Template-based phishing page generation
- PDF payload embedding
- Obfuscated PowerShell droppers
- HTML smuggling payloads
- Fake reCAPTCHA pages
- Professional bait document generation

### 🔧 Payload Forge

Custom payload creation:
- **Evasive ELF** — Linux shellcode payloads
- **Stealth PowerShell** — Base64-encoded Windows payloads
- **C2 Python** — Python reverse shells with obfuscation
- **Obfuscated Python** — Multi-layer encoded Python payloads

### 🔬 Digital Forensics

File analysis and evidence collection:
- File metadata extraction (exiftool)
- String extraction
- Binwalk firmware analysis
- Cryptographic hash generation (MD5, SHA1, SHA256, SHA512)
- AI-assisted investigation

### 🛡️ Firewall Control

Cross-platform firewall management:
- **Linux** — iptables rules (view, add, block IP/port, flush, save)
- **macOS** — pfctl integration
- **Windows** — netsh advfirewall commands
- Custom rule builder with chain selection

### 📁 Session Manager

Manage active exploitation sessions:
- List running sessions
- Interact with sessions
- Upload files to compromised hosts
- Terminate sessions

### 🎮 Gaming OSINT

Full Steam integration and multi-platform deal tracking (see [detailed section](#gaming-osint-steam-integration)).

---

## AI Engine Setup

ShadowCypher supports **10 AI providers** out of the box. Use a free local model or connect to premium cloud APIs for maximum capability.

### Supported Providers

| Provider | Free? | Env Variable | Default Model |
|----------|:-----:|-------------|---------------|
| **Ollama** (Local) | ✅ | — | gemma3 |
| **OpenAI** | ❌ | `OPENAI_API_KEY` | gpt-4o |
| **Anthropic Claude** | ❌ | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514 |
| **Google Gemini** | ❌ | `GOOGLE_API_KEY` | gemini-2.5-pro |
| **OpenRouter** | ❌ | `OPENROUTER_API_KEY` | claude-sonnet-4-20250514 |
| **Groq** | ✅ | `GROQ_API_KEY` | llama-3.3-70b-versatile |
| **Mistral AI** | ❌ | `MISTRAL_API_KEY` | mistral-large-latest |
| **Together AI** | ❌ | `TOGETHER_API_KEY` | Llama-3.1-70B-Instruct |
| **DeepSeek** | ❌ | `DEEPSEEK_API_KEY` | deepseek-chat |
| **Custom Endpoint** | ✅ | `CUSTOM_API_KEY` | Any (vLLM, LM Studio) |

### Option 1: Local AI with Ollama (Free, Recommended)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull gemma3

# ShadowCypher auto-connects — no key needed
```

### Option 2: Cloud AI Providers (Better Quality)

**In-app setup (easiest):**
1. Open **Tactical Swarm AI** tab
2. Click **⚙ Settings**
3. Select your provider from the dropdown
4. Paste your API key
5. Choose a model (or keep the default)
6. Click **💾 Save & Activate**
7. Click **🔌 Test Connection** to verify

**Or via environment variables:**
```bash
# Example: Use Claude
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Example: Use GPT-4o
export OPENAI_API_KEY="sk-..."

# Example: Use OpenRouter (200+ models)
export OPENROUTER_API_KEY="sk-or-v1-..."
```

### Option 3: Custom OpenAI-Compatible Endpoint

For self-hosted models (vLLM, text-generation-inference, LM Studio, etc.):
1. Select **Custom Endpoint** in the provider dropdown
2. Enter your base URL (e.g., `http://192.168.1.100:8000/v1`)
3. Enter model name and optional API key
4. Save & activate

### Switching Providers at Runtime

You can switch providers anytime without restarting the app. Navigate to **Tactical Swarm AI → ⚙ Settings**, select a different provider, and click Save. The change takes effect immediately for the next message.

### Config File

All provider settings persist in `config.json`:
```json
{
  "ai": {
    "active_provider": "anthropic",
    "providers": {
      "anthropic": {
        "api_key": "sk-ant-...",
        "model": "claude-sonnet-4-20250514"
      },
      "openai": {
        "api_key": "sk-...",
        "model": "gpt-4o"
      }
    }
  }
}
```

---

## Gaming OSINT (Steam Integration)

### Features

| Feature | API Key Needed? |
|---------|:---------------:|
| Local library scan (installed games, disk usage) | ❌ |
| Steam Store search | ❌ |
| Featured deals & specials | ❌ |
| Free game finder (100% off promotions) | ❌ |
| Multi-platform free games (Reddit, Epic, GOG, Prime) | ❌ |
| Owned games library (full playtime history) | ✅ |
| Player profile lookup | ✅ |
| Recently played games | ✅ |
| Friends list | ✅ |
| Wishlist deal sniping | Steam ID only |

### Setup

1. **Steam ID (64-bit)** — Find yours at [steamid.io](https://steamid.io)
   - Looks like: `76561198xxxxxxxxx`

2. **Steam Web API Key** — Get one free at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)

3. Enter both in the Gaming OSINT tab's config panel and click **Save**, or set environment variables:
   ```bash
   export STEAM_API_KEY="your_key_here"
   export STEAM_ID="76561198xxxxxxxxx"
   ```

### Using the Gaming Tab

- **🔍 Scan Free Games** — Crawls Reddit r/FreeGameFindings and Steam for free-to-keep games across all platforms
- **📚 Sync Library** — Reads local Steam install to find all installed games and disk usage
- **🔥 Steam Deals** — Shows current specials, top sellers, and new releases with prices
- **💰 Wishlist Deals** — Finds games on your wishlist that are currently on sale
- **🎮 My Profile** — Shows your full library with playtime (requires API key)
- **🔎 Search Store** — Search the Steam store by keyword

Click any game row to open it in your browser.

---

## Support & Communications

### How It Works

The Support & Comms system uses **RSA-OAEP asymmetric encryption**. This means:

- **Users** encrypt messages using the admin's **public key** (shipped with the app)
- **Only the admin** can decrypt messages using the matching **private key** (never leaves the admin's machine)
- Messages are saved as JSON ticket files in the `tickets/` directory

### Sending a Support Message (Users)

1. Go to **Support & Comms** in the sidebar
2. Enter your operator handle (any alias you choose)
3. Type your message in the text field
4. Click **Transmit** or press Enter
5. The message is encrypted with RSA-OAEP and saved as `tickets/ticket_TIMESTAMP.json`
6. Use **Copy Last Ticket** to copy the encrypted data to clipboard
7. Send the ticket file to the admin via any channel (email, Discord, etc.)

### Reading Support Messages (Admin Only)

**On the Admin's machine (where `admin_private.pem` exists):**

1. **Via Support & Comms tab:**
   - Click **Load Ticket File**
   - Select the `.json` ticket file
   - Click **🗝 Decrypt Loaded Ticket**
   - The plaintext message appears in the chat

2. **Via Admin Panel tab:**
   - Paste the Base64 encrypted string directly
   - Click **Execute Neural Decryption**
   - The decrypted message appears below

### Responding to Users

The admin generates a license key via the **Admin Panel → Forge New License Key** button and sends the AES-256 key back to the user through any channel.

---

## Admin Guide

### How Admin Identity Works

Admin status is determined **cryptographically**, not by configuration:

1. The app ships with `shadowcypher/core/admin_public.pem` (the admin's public key)
2. The admin's machine has `admin_private.pem` in the project root
3. On startup, the app performs a **challenge-response** verification:
   - Signs random data with the private key
   - Verifies the signature against the shipped public key
   - If they match → `is_admin = True`
4. Simply creating a random private key will **fail** — it must be the exact matching key

### Admin Capabilities

| Feature | Admin | Operator |
|---------|:-----:|:--------:|
| All offensive modules | ✅ | ✅ |
| Decrypt support tickets | ✅ | ❌ |
| Generate license keys | ✅ | ❌ |
| Admin Panel tab extras | ✅ | Limited |

### Generating a New Keypair

If you need to create a new admin keypair (this will invalidate old tickets):

```bash
# Generate new RSA-4096 keypair
openssl genrsa -out admin_private.pem 4096
openssl rsa -in admin_private.pem -pubout -out shadowcypher/core/admin_public.pem
```

Keep `admin_private.pem` **secret** — never commit it to git.

---

## Configuration

### config.json

Located in the project root. Auto-created on first run:

```json
{
  "ai": {
    "model": "gemma3",
    "n_ctx": 4096,
    "n_gpu_layers": 35,
    "api_base": "http://localhost:11434/api/generate"
  },
  "tools": {
    "nmap_path": "nmap",
    "hydra_path": "hydra",
    "john_path": "john",
    "hashcat_path": "hashcat"
  },
  "wordlists": {
    "default": "wordlists/rockyou.txt"
  }
}
```

### Tool Resolution Order

When a module needs a tool (e.g., `nmap`), ShadowCypher searches:

1. **config.json** override (e.g., `tools.nmap_path`)
2. **`tools/` directory** in the project (recursive search)
3. **System `$PATH`** via `which`
4. **Fallback** to the tool name (will error if not found)

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `STEAM_API_KEY` | Steam Web API key for gaming features |
| `STEAM_ID` | Your Steam 64-bit ID |
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o, o1) |
| `ANTHROPIC_API_KEY` | Anthropic API key (Claude) |
| `GOOGLE_API_KEY` | Google AI API key (Gemini) |
| `OPENROUTER_API_KEY` | OpenRouter API key (multi-model) |
| `GROQ_API_KEY` | Groq API key (fast inference) |
| `MISTRAL_API_KEY` | Mistral AI API key |
| `TOGETHER_API_KEY` | Together AI API key |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `CUSTOM_API_KEY` | Custom endpoint API key |

---

## Troubleshooting

### App won't launch

```bash
# Check GTK is installed
python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('GTK OK')"

# Check all dependencies
pip install -r requirements.txt
```

### Tabs show "Module Load Failed"

Check the terminal output for `[NAV] CRASH loading` messages. Common causes:
- Missing Python dependency (`pip install cryptography psutil pycairo`)
- Missing GTK module (`sudo apt install gir1.2-gtk-3.0`)

### Tools not found

Install the required tool or add it to `tools/`:
```bash
sudo apt install nmap    # Example
```

### AI not responding

1. Ensure Ollama is running: `ollama serve`
2. Check the model is pulled: `ollama list`
3. Verify the endpoint in config.json

### Support tickets can't be decrypted

- Only the machine with `admin_private.pem` can decrypt
- Ensure the private key matches the shipped public key
- Check: `openssl rsa -in admin_private.pem -pubout | diff - shadowcypher/core/admin_public.pem`

---

## Project Structure

```
ShadowCypher/
├── shadowcypher/
│   ├── app.py              # Main application window + sidebar routing
│   ├── core/
│   │   ├── config.py       # Configuration engine (auto-detects project root)
│   │   ├── hub.py          # Central mission orchestration (singleton)
│   │   ├── bus.py          # Event bus for decoupled communication
│   │   ├── runner.py       # Process execution engine
│   │   ├── platform.py     # OS detection + cross-platform tool mapping
│   │   ├── identity.py     # Admin identity verification (RSA challenge-response)
│   │   ├── logger.py       # Centralized logging
│   │   └── admin_public.pem
│   ├── ui/
│   │   ├── base_page.py    # Base class for all module pages
│   │   ├── components.py   # TacticalTerminal, DataPod, TacticalHeader
│   │   ├── dashboard.py    # Main HUD with radar visualization
│   │   ├── *_page.py       # Individual module pages (20 total)
│   │   └── themes.py       # Dark theme CSS
│   ├── modules/
│   │   ├── network.py      # ARP, port scanning, OS detection, packet capture
│   │   ├── wireless.py     # Aircrack-ng suite integration
│   │   ├── credentials.py  # Hydra, hashcat, john the ripper
│   │   ├── firewall.py     # iptables/pfctl/netsh management
│   │   ├── gaming_osint.py # Steam API, deal tracking, free game discovery
│   │   └── ...             # 15+ additional modules
│   ├── ai/
│   │   ├── engine.py       # LLM integration router (local + cloud)
│   │   ├── providers.py    # Multi-provider registry (10 backends)
│   │   ├── orchestrator.py # Autonomous mission orchestration
│   │   └── sisyphus.py     # Autonomous self-healing loop
│   └── tests/
│       └── audit.py        # Module integrity test suite
├── config.json             # User configuration
├── admin_private.pem       # Admin only (NEVER commit to git)
├── .session-secret          # License key file
├── tickets/                 # Encrypted support tickets
└── tools/                   # Local tool installations
```

---

## License

See [LICENSE](LICENSE) for details.

## Security

ShadowCypher is an offensive security tool intended for **authorized penetration testing and security research only**. Unauthorized use against systems you do not own or have permission to test is illegal.
