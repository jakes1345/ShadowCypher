<div align="center">
  <img src="https://via.placeholder.com/150/010204/00ffff?text=ShadowCypher+OMNI-HEAL" alt="ShadowCypher Core">
  <h1>S H A D O W C Y P H E R</h1>
  <p><b>Elite Penetration Testing & AI Orchestration Platform [Build V33 OMNI-HEAL]</b></p>
</div>

---

**ShadowCypher** is a professional-grade, multi-vertical offensive security platform engineered for zero-latency tactical engagement. Built entirely on a hardware-accelerated **Cairo-GTK3/4** foundation, the suite merges manual enumeration with an autonomous Swarm AI protocol (Tengu AI). 

Every line of code and every visual interface has been synthesized under the **Obsidian Glass Black** design philosophy—deep-matte `#010204` styling, cyan pulses, and indestructible thread-safe background processing. It is built to run natively on Linux, MacOS, and Windows subsystems.

---

## ⚠️ Legal & Ethical Disclaimer

**ShadowCypher is strictly for educational purposes, authorized security auditing, and defensive research.**

The creators, contributors, and maintainers of ShadowCypher assume **NO LIABILITY** for any misuse, damage, or illegal activities conducted with this software. By downloading, installing, or using ShadowCypher, you explicitly agree that:
1. You have explicit, written authorization to scan, test, and interact with the networks and systems you target.
2. You will not use this software for malicious, unauthorized, or illegal activities.
3. You bear full responsibility for your actions and the consequences of utilizing offensive security tooling.

---

## 🎯 The Architecture: OMNI-Runner Core
ShadowCypher does not freeze. Every offensive scan, payload generation, and packet capture is securely outsourced to the asynchronous **Shadow-Runner Architecture**.
- **Non-Blocking IO**: Deep-threaded execution means you can run a Hydra brute-force on your Credential Hub while capturing a WPA handshake on your Wireless Tab, all while the 60FPS overlay renders system telemetry.
- **Obsidian Terminal VOID**: Every output stream is piped instantly back into a custom GTK TextView locked into the `Obsidian Black` theme. Zero white boxes. Zero cliches. 

---

## 🛡️ Security Hardening & The Admin Node

When dealing with offensive tools and autonomous AI, security is paramount. ShadowCypher implements multiple layers of defense-in-depth:

### 1. The Trust Model: Admin Node vs. Operator Node
ShadowCypher implements a unique cryptographic identity system to differentiate the project maintainer (Admin) from open-source users (Operators):
- The repository ships with an `admin_public.pem`.
- To unlock the **Admin Sector** (and the ability to decrypt secure support tickets), the machine must possess the mathematically corresponding `admin_private.pem`.
- The system runs a live cryptographic challenge-response at startup. You cannot simply generate a random private key to bypass this; it must match the shipped public key footprint.
- **Result:** Anyone can clone the repo and use the tool fully ("Operator" mode), but only the verified maintainer has "Admin" access.

### 2. Secure Comm-Link (Ticketing)
Operators who find bugs or need support can use the **Secure Comm-Link**.
- **100% Offline:** The system makes zero network connections.
- **End-to-End Encrypted:** Messages are encrypted locally using RSA-OAEP (SHA-256) against the Admin's public key.
- **Privacy First:** It generates a `.json` file containing the Base64 ciphertext. The Operator manually sends this file to the Admin via any channel (Discord, Email, etc.). IPs are never tracked or transmitted.

### 3. AI Sandboxing & Process Isolation
- **AI Sandboxing:** The AI Orchestrator cannot run arbitrary bash commands. It uses `execvp` (bypassing the shell entirely) and validates all executions against a strict allowlist of known security tools (e.g., `nmap`, `dig`, `whois`).
- **Input Sanitization:** All user inputs (IPs, MAC addresses, ports) passed to underlying tools are rigorously validated (`core/sanitize.py`) to prevent OS command injection.
- **Thread Safety:** The SQLite database uses explicit threading locks, and all UI updates from background processes utilize `GLib.idle_add` to prevent GTK thread collisions.

---

## 🦾 Tactical Dashboards & Toolkits

ShadowCypher is categorized into 12 high-fidelity tactical boards. Every button is live, weaponized, and directly synchronized with native operating system binaries (`nmap`, `iptables`, `john`, `aircrack-ng`).

### 📊 Operational Overview (HUD)
Your real-time mission telemetry. Features a spinning radar pulse tracking your system's heartbeat, CPU allocation, memory burn-rate, and raw TX/RX signal data. Total battlefield awareness.

### 🤖 Tactical Swarm AI (Tengu Core)
The autonomous brain of ShadowCypher. Designed to integrate directly with local LLMs (via Ollama or custom model hubs). Put the AI into "Active Pulse" to dynamically analyze Nmap outputs, reverse engineer binaries, or generate custom exploitation vectors—fully air-gapped and secure.

### 🛡️ Autonomous Audit Engine (Project Overlord)
The suite's self-healing heart. Project Overlord runs continuous background audits to ensure UI stability, resource optimization, and security integrity. If a distortion or process failure is detected, the engine autonomously restores the system state, ensuring zero-downtime operations.

### 📡 Signal Reconnaissance
The mapping engine. Traces exact paths to the target gateway and generates comprehensive network topographies.
- **Active Hooks:** Quick Port Scans, UDP Sweeps, OS Detection, Subnet Discovery, Traceroute.

### 💣 Offensive Exploit
The weapons payload bay. Synchronizes with local Metasploit instances to generate tailored backdoors.
- **Active Hooks:** Remote Reverse Shell Generation, Payload Encoding (x86/shikata_ga_nai), Listener activation, privilege escalation probes.

### 🎯 Vulnerability Pulse
Automated weakness intelligence. The Scanner dashboard integrates standard industry tools to hunt for misconfigurations.
- **Active Hooks:** Nikto Scans, automated SQLMap injection probes, Nmap CVE scripts, Searchsploit integrations.

### 🌐 Stealth Network
Lower OSI-level interception and monitoring. Monitors network-wide packet flows and captures raw traffic for subsequent analysis.
- **Active Hooks:** ARP Poison/Scans, SYN TCP connective sweeps, Service Fingerprinting, DNS Leak analysis, live PCAP interception.

### 🕵️ Digital Analysis (Forensics)
Deep-file extraction and reverse engineering. Tear apart binaries and discover hidden payloads without leaving the suite.
- **Active Hooks:** Binwalk Extraction, Steghide Steganography detection, Hex Dumps, EXIF Meta-stripping, malicious PDF Analysis. 

### 🔍 OSINT / Intelligence
Information dominance. Scrape, scrape, and scrape. Expose the public footprint of domains and organizations.
- **Active Hooks:** Deep SSL Certificate probing, email MX/SPF validation, Subnet/ASN extraction, HTTP architecture detection, Zone Transfers.

### 🎮 Gaming OSINT (The Nexus)
Cross-platform intelligence gathering. Discover the digital fingerprints of targets across gaming ecosystems.
- **Active Hooks:** Steam Profile Recon, Xbox Live Activity tracking, cross-platform username correlation, achievement-based behavioral profiling.

### 🏰 AD Attacks (The Citadel)
Domain dominance and enterprise-level exploitation.
- **Active Hooks:** Kerberoasting, AS-REP Roasting, Domain Controller enumeration, LDAP reconnaissance, GPO auditing.

### 🕸️ Web Attacks (The Weaver)
High-precision web application vulnerability discovery.
- **Active Hooks:** Automated XSS Probing, SQL Injection automation, Path Traversal discovery, HTTP Request Smuggling tests, API fuzzer integration.

### 🔑 Credential Hub (Identity Engine)
Your password dominance module. Crack standard hashes or perform live-fire network brute forces.
- **Active Hooks:** Hydra network brute forces (SSH, FTP, HTTP), John the Ripper hash cracking, hash identification, localized wordlist generation (CUPP).

### 🛡️ Firewall Defense (The Shield)
You cannot attack if you are vulnerable. The Shield synchronizes directly into `iptables` and `nftables` to lock down your machine on the fly.
- **Active Hooks:** Instant Rule Flushing, Global Saves, specific IP/Port Blackholing. 

### 📶 Wireless Signals (Air-Gap)
Physical layer disruption. Hooks into `airmon-ng` and `aireplay` for complete WiFi spectrum dominance.
- **Active Hooks:** Interface monitor switching, Airodump-ng network tracking, Client Deauth disruption, WPA Handshake interception, WPA Cracking.

### ⚙️ System Control
Killswitches and deeper configuration overrides. Manages your background jobs, handles API key input for any cloud-synced modules, and toggles global suite themes.

---

## 🛠️ Installation & Engagement

**Prerequisites:** Python 3.10+, PyGObject, local system security tools (`nmap`, `wireshark`, `binwalk`, `exiftool`, `john`, `hydra`, `aircrack-ng`).

### Option A: Native Linux Deployment
```bash
# 1. Clone the Arsenal
git clone https://github.com/jakes1345/ShadowCypher.git
cd ShadowCypher

# 2. Synchronize Dependencies (Debian/Ubuntu example)
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
pip install -r requirements.txt

# 3. Launch OMNI-Build
DISPLAY=:0 python3 -m shadowcypher.app
```

### Option B: Rapid Docker Deployment
Deploy the entire suite in minutes using the pre-configured containerized environment:
```bash
# Launch via Docker Compose
docker-compose up -d --build
```

---

## 🚀 The Release Philosophy (Branch Management)

ShadowCypher's development is governed by three strict, version-controlled tiers.

*   **`main` (The Core)**: The absolute, rock-solid core. Only receives merges from `beta` when a feature has been 100% verified and stress-tested. If you clone `main`, it works flawlessly.
*   **`beta` (The Forge)**: Used for integrating features and testing UI/engine synchronization. We merge features here from `alpha` once they are functionally complete, but might need final aesthetic polish or broader integration tests.
*   **`alpha` (The Void)**: The bleeding edge. New exploits, untested AI orchestration hooks, and radical UI overhauls live here. Expected to break. This is where we build the new weapons.

---
<div align="center">
  <i>"Control the flow of information, and you control the war."</i>
</div>
