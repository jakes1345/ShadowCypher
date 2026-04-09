# 🌌 ShadowCypher: Absolute Integrity — Autonomous Offensive Suite (V4.0)

![ShadowCypher Logo](shadowcypher/ui/assets/icon.png)

> **"In the shadows, we are omniscient. In the light, we are invisible."**

ShadowCypher is a professional-grade, autonomous penetration testing platform designed for high-fidelity red team operations, deep-spectrum OSINT, and self-healing technical dominance. Engineered for elite operatives, it integrates state-of-the-art AI orchestration with a hardened, portable offensive toolbelt.

---

## 🚀 Architectural Sovereignty
ShadowCypher V4.0 has been re-engineered for **Self-Reliance**. It no longer depends on host-system configurations, providing a "War-in-a-Box" experience through its dynamic tool-discovery engine.

### 🧠 TENGU AI Orchestration (Kernel V4)
The **TENGU Core** is an agentic AI commander that autonomously plans and executes multi-stage missions.
- **Autonomous Sentinel**: Real-time vulnerability analysis and reactive mission triggering.
- **Sisyphus Protocol**: An infinite self-healing loop that audits technical debt and autonomously repairs its own source code.
- **Masterclass Loop**: Full-spectrum breach chain: Recon → Vuln-Scan → Weaponization → Exploitation → Exfiltration.

### 🏰 Domain Dominance & Lateral Pivot
Engineered for Active Directory dominance and internal network traversal.
- **Kerberoasting**: TGS ticket extraction and automated correlation.
- **SMB Relay Vault**: Coordination between Responder and MultiRelay for hash capture and lateral hops.
- **SOCKS5 Pivoting**: Stealth tunneling protocols for bypassing egress restrictions.

### 🕵️‍♂️ Omniscient OSINT
Cross-correlate digital shadows with surgical precision.
- **Sherlock & Holehe Integration**: Social media and email footprinting across 500+ platforms.
- **SteamID Intelligence**: Pivoting from gaming aliases to real-world identities and linked accounts.
- **Leak-Correlator**: Automatic matching of discovered identities with local leak databases (offline-first).

### 🐝 C2 Hive-Mind & Stealth Evasion
Long-term persistence through encrypted, agentless stagers.
- **Fernet-AES Encryption**: Payloads wrapped in AES-256 for EDR bypass and signature-less execution.
- **Webhook Smuggling**: Outbound data exfiltration via Discord/Telegram webhooks.
- **Crate Stagers**: Base64-obfuscated stubs for Python, PowerShell, and Linux ELF deployments.

---

## 🛠 Weaponized Toolbelt (Included & Integrated)
| Category | Tactical Tools |
| :--- | :--- |
| **Intelligence** | Nuclei V3, Ffuf, Subfinder, Holehe, Sherlock |
| **Exploitation** | Metasploit RPC, Searchsploit, PayloadForge |
| **Network** | Nmap, Responder, CrackMapExec, Impacket |
| **Analysis** | Binwalk, ExifTool, HashID, John the Ripper |

---

## 📦 Deployment & Hardening
ShadowCypher is designed for containerized or portable local deployment.

### 1. The Ultimate Docker Build
The provided `Dockerfile` creates a fully self-contained environment with all tools pre-staged.
```bash
docker build -t shadowcypher-elite .
docker run -it --env DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix shadowcypher-elite
```

### 2. Local Portable Installation
```bash
./run.sh # Automatically initializes venv and checks internal tool health
```

---

## 🛡 Security & Ethics
ShadowCypher is a professional security tool. The **StealthHoneypot** and **Atomic File Locking** mechanisms ensure that the suite itself remains hardened during operations. Usage for unauthorized access is strictly prohibited.

---

## 🏛️ Project Structure
```text
ShadowCypher/
├── shadowcypher/
│   ├── ai/          # Orchestrator, Sentinel, Sisyphus
│   ├── core/        # Database, Runner, Crypt, Memory
│   ├── modules/     # AD-Pivot, OSINT, Exploit, Exfil
│   └── ui/          # Obsidian-Stealth HUD (Gtk 3.0/Cairo)
├── tools/           # Self-contained offensive weapon stash
├── projects/        # Secure Loot & Mission Persistence
└── run.sh           # Master Launch Script
```

**"The hill is climbed. The debt is zero."**  
*ShadowCypher Absolute Integrity Protocol — Mission Verified.*
