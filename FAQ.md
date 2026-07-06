# ShadowCypher FAQ

Frequently asked questions about ShadowCypher — the personal security platform that runs entirely on your machine.

## Table of Contents

- [Getting Started](#getting-started)
- [Installation & Setup](#installation--setup)
- [Features & Capabilities](#features--capabilities)
- [Security & Privacy](#security--privacy)
- [Performance & Resources](#performance--resources)
- [Tools & Integration](#tools--integration)
- [Troubleshooting](#troubleshooting)
- [Legal & Licensing](#legal--licensing)
- [Community & Support](#community--support)

---

## Getting Started

### What is ShadowCypher?

ShadowCypher is a personal security platform that runs entirely on your machine. It combines offensive and defensive security tools, local AI inference, network reconnaissance, vulnerability assessment, and threat intelligence into one unified GTK desktop application. Everything is local-first — no telemetry, no cloud dependencies, no subscriptions.

### Who is ShadowCypher for?

ShadowCypher is built for:
- Security researchers and penetration testers
- System administrators auditing networks and devices
- Privacy-conscious users wanting local security analysis
- DevSecOps teams validating their infrastructure
- Incident responders needing offline forensics

All offensive modules require explicit written authorization to use against target systems.

### What can I do with ShadowCypher?

ShadowCypher can:
- **Scan & Assess**: Network reconnaissance, port scanning, service fingerprinting, vulnerability assessment
- **Threat Intelligence**: CVE correlation, CISA KEV checks, EPSS scoring, reputation checks (OTX, AbuseIPDB, URLhaus)
- **OSINT**: Username searches, WHOIS, DNS enumeration, reverse IP, SSL certificate inspection
- **Penetration Testing**: Payload generation, phishing simulations, web attacks, network stress testing, wireless testing
- **AI Analysis**: Conversational AI, attack chain planning, automated security assessment, deep reasoning
- **Privacy**: Tor integration, anonymity auditing, log cleaning, anti-forensics
- **Defense**: Network monitoring, router hardening, device discovery, file integrity checking

### Is ShadowCypher free?

Yes. ShadowCypher is licensed under the Sovereign license (no corporate surveillance, no vendor lock-in). The source code is open and free to use.

---

## Installation & Setup

### What are the system requirements?

Minimum requirements:
- **OS**: Linux (recommended), macOS, or Windows (WSL2)
- **Python**: 3.12 or higher
- **RAM**: 4GB recommended (8GB+ for large scans)
- **Disk**: 2GB for installation + dependencies
- **GPU** (optional): NVIDIA/AMD for Ollama acceleration

Required packages:
- GTK 3.0 (`python3-gi`, `gir1.2-gtk-3.0`)
- Go 1.24+ (for relay compilation)
- OpenSSH, nmap, git

### How do I install ShadowCypher?

**Quick start:**
```bash
git clone https://github.com/jakes1345/ShadowCypher.git
cd ShadowCypher
pip install -r requirements.txt
python3 -m shadowcypher.app
```

**Manual launch with environment variables:**
```bash
source venv/bin/activate
export PYTHONPATH="$(pwd):$(pwd)/ai_engine:$PYTHONPATH"
export SHADOW_PORT=8888
python3 -m shadowcypher.app
```

See [INSTALLATION.md](INSTALLATION.md) for platform-specific guides (Linux, macOS, Windows/WSL2).

### Do I need Ollama installed?

Yes, Ollama is required for AI features (Shadow Synthesizer, Quantum-Core, AutoScan analysis). ShadowCypher will warn if Ollama is not detected on first launch.

**Install Ollama:**
```bash
# Linux
curl https://ollama.ai/install.sh | sh

# macOS
brew install ollama

# Then start it
ollama serve

# And pull a default model
ollama pull llama2
```

See [Ollama docs](https://github.com/ollama/ollama) for more.

### What if Ollama is not installed?

The desktop app will still launch, but:
- AI features will be disabled (Shadow Synthesizer, Quantum-Core, TreeQuest attack planning)
- Security assessment will fall back to rule-based analysis only
- AutoScan will skip AI-powered recommendations

Run `python3 -m shadowcypher.app` again once Ollama is installed.

### Can I use a different AI model?

Yes. ShadowCypher supports any Ollama-compatible model. In the **God-Panel** → **Model Settings**, you can swap between:
- Llama 2 / Llama 3 (8B–70B)
- Gemma (7B–27B)
- DeepSeek Coder (7B–67B)
- Mistral (7B)
- Phi (2.7B–14B)
- Qwen (7B–72B)

Or point to a custom Ollama-compatible API endpoint.

### How do I configure ShadowCypher?

Configuration happens in three places (in order of precedence):

1. **Environment variables** (`SHADOW_PORT`, `OLLAMA_BASE_URL`, etc.)
2. **config.json** in the project root (created on first launch)
3. **Code defaults** in `shadowcypher/config.py`

**Example config.json:**
```json
{
  "ai": {
    "model": "llama2",
    "api_base": "http://localhost:11434",
    "temperature": 0.7,
    "max_tokens": 2048
  },
  "tools": {
    "nmap_path": "/usr/bin/nmap",
    "nuclei_path": "/usr/bin/nuclei"
  },
  "identity": {
    "operator_handle": "your-handle",
    "admin_list": ["you"]
  }
}
```

See [CONFIGURATION.md](CONFIGURATION.md) for the full schema.

---

## Features & Capabilities

### What is the AutoScan pipeline?

AutoScan is an adaptive full-stack vulnerability assessment that figures out what to run on a target:

1. **Nmap service fingerprint** → identify open ports and services
2. **Domain enumeration** → if target is a domain, enumerate subdomains
3. **Web scanning** → run Nikto + Nuclei in parallel if web services found
4. **Database testing** → optional SQLmap if DB ports detected (requires confirmation)
5. **CVE correlation** → cross-reference discovered services against NVD
6. **Threat intelligence** → check IP reputation (OTX, AbuseIPDB, URLhaus, Tor exits)
7. **Security assessment** → rule-based triage and AI report synthesis

Results feed into the forensic registry and are tagged with MITRE ATT&CK technique IDs.

**Run AutoScan:**
- GUI: Vulnerability Scanner → Auto Scan tab
- CLI: `shadow-cli -p "full scan 192.168.1.100"`
- Programmatically: See [Auto Scan API](docs/api/auto_scan.md)

### What is TreeQuest attack chain planning?

TreeQuest uses Monte Carlo Tree Search (MCTS) to plan attack sequences. Instead of running individual tools, you describe your objective ("gain shell on 192.168.1.100") and TreeQuest:

1. Explores possible sequences of security actions
2. Uses local AI to predict what each action would find
3. Evaluates the best path to your objective
4. Returns an ordered plan with confidence scores

Destructive actions (SQL injection, vulnerability exploitation) require explicit confirmation before execution.

**Use TreeQuest:**
- GUI: Offensive Lab → DeepHat Apex → "Plan Attack"
- Programmatically: `tree_planner.plan(target, objective)`

### What is Sovereign Chat?

Sovereign Chat is an end-to-end encrypted chat system with forward secrecy:

- **Per-session ephemeral keys**: X25519 ECDH key exchange. Compromise of one session reveals nothing about others.
- **At-rest encryption**: AES-256-GCM with per-room derived keys
- **No cloud dependency**: SQLite persistence on your machine
- **Admin identity**: RSA-4096 challenge-response with hardware fingerprint binding

Connect via the Sovereign Chat tab in the main UI or via WebSocket API.

### What is Ghost Mode?

Ghost Mode is a one-command operational anonymity switch:

```bash
shadowcypher engage ghost-mode
```

This:
- Routes all traffic through Tor (iptables kill-switch)
- Randomizes MAC address
- Neutralizes hostname/timezone
- Prevents DNS leaks
- Creates RAM-only workspace
- Suppresses system logs

Disengage to restore normal routing:
```bash
shadowcypher disengage ghost-mode
```

### What scanning tools are included?

ShadowCypher wraps these open-source tools (optional installs):

| Tool | Purpose |
|---|---|
| **Nmap** | Port scanning, OS fingerprinting, NSE scripting |
| **Nuclei** | Template-based vulnerability scanning |
| **Nikto** | Web server scanning |
| **SQLmap** | SQL injection testing |
| **Hydra** | Network credential testing |
| **John the Ripper** | Hash cracking |
| **Hashcat** | GPU-accelerated hash cracking |
| **Aircrack-ng** | 802.11 wireless testing |
| **Ffuf** | Directory/parameter fuzzing |

All are optional. ShadowCypher will gracefully skip tools you don't have installed.

### Does ShadowCypher include an IRC bot?

Yes, the **ShadowSentinel IRC Bot** connects to external IRC (Libera) or sovereign Ergo servers. It has 20+ commands for:
- Remote mission control
- Threat intel queries
- Conversational AI (offline ELIZA + Markov chains)
- User verification via SHA-256 proof-of-work

Configure in `config.json` under `irc` section.

---

## Security & Privacy

### Is my data encrypted?

**In transit**: All WebSocket communication uses TLS/SSL with X25519 ECDH key exchange.

**At rest**: Sovereign Chat uses AES-256-GCM. The Citadel vault uses AES-256-GCM with PBKDF2 key derivation (200,000 iterations) and optional hardware fingerprint binding.

**Logs**: Stored in JSONL format. Use **Trace Eraser** to sanitize logs, shell history (12 types), and forensic artifacts.

### Does ShadowCypher phone home?

No. ShadowCypher is completely offline-first:
- No telemetry collection
- No cloud-dependent features
- Local Ollama for AI (your prompts never leave your machine)
- Free threat intel sources (CISA, NVD, URLhaus, Tor exits)
- Optional API keys for OTX and AbuseIPDB (you control the connection)

### Can I audit the source code?

Yes. ShadowCypher is open-source on GitHub. Key cryptographic operations are in:
- `shadowcypher/core/sovereign_chat.py` (X25519 + AES-256-GCM)
- `shadowcypher/core/citadel_security.py` (vault encryption)
- `shadowcypher/native/relay/` (Go WebSocket relay)

### Can I use ShadowCypher anonymously?

Yes. **Shadow Audit** validates your anonymity chain:
```bash
shadow-cli -p "am I anonymous?"
```

This checks:
- Tor connectivity and exit node location
- DNS leaks
- MAC fingerprinting
- Hostname/timezone exposure
- WireGuard config
- Browser fingerprints

**Auto-fix for failed checks:**
```bash
shadowcypher audit anonymity --fix
```

### Is this tool legal?

ShadowCypher is built for **authorized security testing, research, and education**. Every offensive module assumes you have explicit written authorization to test the target system.

**Unauthorized use** of these tools against systems you don't own or have permission to test is **illegal**. The authors assume no liability for misuse. You own your actions.

See [LICENSE](LICENSE) and the **Legal** section of the README.

---

## Performance & Resources

### How much disk space do I need?

- **ShadowCypher installation**: ~100MB (source code + Python packages)
- **Ollama models**: 5–40GB (depending on model size; 7B models are ~4GB)
- **Chroma vector DB** (knowledge graph): ~500MB–1GB (grows over time)
- **Logs and forensic data**: Depends on scan history (can be purged with Trace Eraser)

**Total minimum:** 20GB recommended.

### How much RAM does ShadowCypher use?

- **Idle**: ~200–300MB
- **Running light scan**: ~500MB–1GB
- **Full AutoScan**: ~1–2GB
- **Running Ollama with large model**: 4–8GB (depending on quantization)

Recommended: 8GB RAM minimum.

### Can I run large scans on smaller hardware?

Yes, but with limitations:

- Use smaller models (Phi 2.7B, Gemma 7B instead of Llama 70B)
- Reduce scan scope (--quick-scan instead of full)
- Run scans off-peak to avoid memory contention
- Use quantized models (4-bit, 8-bit) for lower VRAM

See [PERFORMANCE.md](PERFORMANCE.md) for tuning guidance.

### How fast is the Go relay?

The compiled Go WebSocket relay processes thousands of concurrent connections with sub-millisecond latency. It's auto-compiled from source on launch if the binary is stale.

Auto-relay handoff: ~5ms per message
Threat intel query (parallel): ~200–500ms
AutoScan (full pipeline): 2–10 minutes (depends on target and scan depth)

### How do I profile performance issues?

Enable verbose logging:
```bash
export SHADOW_DEBUG=1
export SHADOW_LOG_LEVEL=DEBUG
python3 -m shadowcypher.app
```

Check logs in `~/.shadowcypher/logs/`:
```bash
tail -f ~/.shadowcypher/logs/shadowcypher.jsonl
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for performance debugging steps.

---

## Tools & Integration

### Can I integrate ShadowCypher with other tools?

Yes. ShadowCypher exposes an **MCP server** that works with compatible AI assistants. You can route natural language queries to ShadowCypher tools through any MCP-compatible client.

**Example with Claude:**
```python
from anthropic import Anthropic

client = Anthropic(mcp_servers={
    "shadowcypher": {
        "url": "http://localhost:8888/mcp"
    }
})

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    tools=[...],  # ShadowCypher MCP tools
    messages=[{
        "role": "user",
        "content": "scan my network"
    }]
)
```

See [MCP.md](docs/mcp.md) for the full spec.

### Can I use ShadowCypher from the CLI?

Yes. **shadow-cli** is a command-line AI assistant that routes natural language to ShadowCypher tools.

**Examples:**
```bash
shadow-cli                              # Interactive mode
shadow-cli -p "scan my network"         # Discovers all devices on your LAN
shadow-cli -p "full scan 192.168.1.100" # Runs the full AutoScan pipeline
shadow-cli -p "engage ghost mode"       # Activates total anonymity
shadow-cli -p "am I anonymous?"         # Runs full anonymity audit
shadow-cli -p "audit my router"         # Checks router for vulnerabilities
```

See [shadow-cli.md](docs/shadow-cli.md) for full reference.

### Can I automate scans with ShadowScript?

Yes. **ShadowScript** is a domain-specific language for orchestrating multi-tool engagements:

```shadowscript
target = "192.168.1.100"
nmap target --service-detection
if ports.open contains 80 {
  nikto target:80
  nuclei target --severity high,critical
}
if ports.open contains 3306 {
  echo "Database port detected"
  # SQLmap requires explicit confirmation
}
report assess(findings)
```

See [ShadowScript reference](docs/shadowscript.md) for the grammar and interpreter.

### Does ShadowCypher support CI/CD integration?

Yes. You can run ShadowCypher scans as part of your DevSecOps pipeline:

```yaml
# Example: GitHub Actions
- name: Run ShadowCypher scan
  run: |
    shadow-cli -p "full scan \${{ env.DEPLOY_IP }}"
    shadow-cli -p "report vulnerability-summary"
```

See [CI_CD.md](docs/ci-cd.md) for examples (GitHub Actions, GitLab CI, Jenkins).

---

## Troubleshooting

### ShadowCypher crashes on launch

Check the logs:
```bash
cat ~/.shadowcypher/logs/shadowcypher.jsonl | jq '.'
```

Common causes:
1. **Ollama not running**: Start it with `ollama serve`
2. **GTK not installed**: Install `python3-gi` and `gir1.2-gtk-3.0`
3. **Python 3.12+ not found**: Verify with `python3 --version`
4. **Port conflict**: Change `SHADOW_PORT` if port 8888 is in use

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for full diagnostics.

### Why is AutoScan so slow?

AutoScan's speed depends on:
- **Target complexity**: More ports = longer scans
- **Nuclei template set**: Large template databases take longer
- **SQLmap confirmation**: Waits for user input
- **Threat intel queries**: Network latency

**To speed up AutoScan:**
```bash
# Quick scan (nmap + CVE + threat intel only, no web scanning)
shadow-cli -p "quick scan 192.168.1.100"

# Limit to specific ports
shadow-cli -p "scan 192.168.1.100 --ports 80,443,22"

# Skip threat intel queries
export SHADOW_SKIP_THREAT_INTEL=1
```

See [PERFORMANCE.md](PERFORMANCE.md) for tuning.

### I'm getting "Connection refused" errors

The Go relay might not be running. Check:
```bash
ps aux | grep "shadowcypher.*relay"
lsof -i :8888
```

If the relay crashed, restart it:
```bash
pkill -f "shadowcypher.*relay"
python3 -m shadowcypher.app
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for relay debugging.

### How do I report a bug?

1. **Collect diagnostics**: Run `./troubleshoot.sh` to generate a diagnostic report
2. **Check existing issues**: Search GitHub Issues
3. **File a new issue** with:
   - Diagnostic report output
   - Steps to reproduce
   - ShadowCypher version (`python3 -m shadowcypher --version`)
   - OS and Python version

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full process.

---

## Legal & Licensing

### What license is ShadowCypher under?

ShadowCypher is licensed under the **Sovereign License** — a commitment to freedom from corporate surveillance and vendor lock-in. You own your security tools.

### Can I modify and redistribute ShadowCypher?

Yes. The source is open and modifications are permitted under the Sovereign License. Redistribution requires attribution.

### Can I use ShadowCypher commercially?

Yes, for authorized security testing and research. Commercial deployment as a service requires explicit permission. See [LICENSE](LICENSE).

### Am I liable for misuse?

No. The authors assume no liability for misuse of ShadowCypher. **You own your actions.** Unauthorized access to computer systems is illegal.

---

## Community & Support

### Where can I get help?

1. **Documentation**: Check [INSTALLATION.md](INSTALLATION.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md), and [FAQ.md](FAQ.md)
2. **GitHub Issues**: Search and file issues at https://github.com/jakes1345/ShadowCypher/issues
3. **Discussions**: Join the community at https://github.com/jakes1345/ShadowCypher/discussions
4. **Discord/Slack** (if available): Check the README for community links

### How do I report a security vulnerability?

Email `security@shadowcypher.site` with:
- Vulnerability description
- Steps to reproduce
- Proposed fix (if you have one)

Do not file security issues as public GitHub issues. We'll credit you in a security advisory once patched.

### How do I contribute?

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style and conventions
- Testing requirements
- Pull request process
- Development setup

### What's the roadmap?

Key upcoming features:
- **Guardian Vault**: Local-first password/ID/TOTP vault (future release)
- **Android App**: Mobile version of ShadowCypher (in development)
- **Threat Feed**: Real-time threat intelligence (coming soon)
- **SEO Blog**: Security research and threat landscape (in progress)

See [ROADMAP.md](ROADMAP.md) for detailed timeline.

---

**Still have questions?** Open an issue or discussion on GitHub, or email `support@shadowcypher.site`.
