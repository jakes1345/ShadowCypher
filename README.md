# SHADOWCYPHER // BUILD_4.6.2
### [ SOVEREIGN_CONTROL_PLANE // OFFLINE_OFFENSIVE_ORCHESTRATION ]

![Build Status](https://img.shields.io/badge/CI-GREEN-success?style=for-the-badge&logo=github)
![Version](https://img.shields.io/badge/VERSION-4.6.2-blueviolet?style=for-the-badge)
![Engine](https://img.shields.io/badge/AI-CLASSIC_BRAIN_OFFLINE-red?style=for-the-badge)
![License](https://img.shields.io/badge/LICENSE-MIT-blue?style=for-the-badge)

---

## // THE_SOVEREIGN_ASSERTION

In an era of hardware-level telemetry and cloud-bound LLMs, **ShadowCypher** is the assertion of absolute digital sovereignty. No API keys. No outbound inference. No third-party prompt logs. Just a hardened GTK workstation, an offline conversational engine, and a bot that answers only to the people who actually own the keys.

ShadowCypher fuses a **Heterogeneous Polyglot Bridge (HPB)** for legacy + modern tooling with a **Classic Brain** conversational engine — ELIZA-style reflection, keyword intents, and a self-training Markov chain. Runs on a laptop in airplane mode. Gets smarter the more you talk to it.

---

## // UNDER_THE_HOOD

### 1. The Obsidian Citadel Architecture
A decoupled, event-driven orchestration hub.
- **Signal-Space bus** for module-to-module pub/sub telemetry
- **Sovereign Ergo IRC** — local coordination channel, zero cloud dependency
- **RSA-4096 Vault** with cryptographic admin gating (the private key stays on your machine — everyone else earns access)

### 2. Classic Brain (No LLMs, No Tokens, No Leaks)
- ELIZA-style Rogerian reflection for conversational depth
- Keyword intent dispatch with persona-weighted responses
- Per-user memory + self-training Markov chain persisted to disk
- Drop-in replacement for any LLM provider

### 3. Trinity Audit Engine
Autonomous gatekeeper for locked files and privileged commands.
- SHA-256 Proof-of-Compute challenge (difficulty scales with user reputation)
- CTCP VERSION + WHOIS forensic fingerprinting
- Three-agent heuristic consensus (Judge / Hunter / Architect) — **no network calls**
- Pass → access code issued. Fail → threat registry entry + ticket.

### 4. Polyglot Execution Path
- Auto-resolver identifies shebangs and signatures, wraps execution in the right runtime
- Python 2.7 ↔ 3.12 parity for legacy and modern offensive tools in a single session

---

## // PLATFORM_SUPPORT

| Platform | Status | Installer | Notes |
|----------|--------|-----------|-------|
| **Linux** (Debian/Ubuntu/Kali) | Full | `./install.sh` | Native target — everything works |
| **macOS** (12+) | Good | `./install-macos.sh` | GUI + IRC + Classic Brain work. Some offensive modules require `brew install` of their tools |
| **Windows 10/11** | Partial | `.\install-windows.ps1` | GUI runs. For full offensive module support use **WSL2 + Kali** |
| **Docker** | Full | `docker compose up` | Headless / server-side operator mode |

Offensive modules that shell out to Linux-only tools (`iptables`, `aircrack-ng`, `tcpdump`, etc.) will display a "tool not available" message on other platforms instead of crashing.

---

## // MISSION_READY_BOOTSTRAP

```bash
# Linux (Debian / Ubuntu / Kali)
git clone https://github.com/jakes1345/ShadowCypher.git && cd ShadowCypher
./install.sh && shadowcypher

# macOS
./install-macos.sh && python3 -m shadowcypher.app

# Windows (elevated PowerShell)
.\install-windows.ps1
python -m shadowcypher.app
```

First launch opens a welcome dialog — pick a handle, the rest is configured automatically. No `config.json` hand-editing, no API keys to paste.

**Sovereign IRC** (local Ergo server for cross-module bot coordination) is **off by default**. Enable by setting `irc.sovereign_enabled: true` in `config.json` and running your own Ergo daemon. Everyone else just uses external IRC (Libera by default).

---

## // THE_OATH

> **"if it phones home it isnt yours. if you cant pull the plug and have it still work its not yours either. build the thing. own the keys. trust nobody including me."**
>
> — anon, somewhere

---

### [ MISSION_CONTROL // jakes1345 ]
**Engineered for the Unseen. Built for the Sovereign. Owned by you alone.**
