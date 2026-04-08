# Security Policy

## Supported Versions

Currently, only the `main` branch of ShadowCypher receives security updates.

## Threat Model & Design Philosophy

ShadowCypher is a security tool that integrates local AI with offensive security binaries (like Nmap, Nikto, SQLmap). As such, its threat model differs from a standard web application.

### In-Scope Threats (We WILL fix these)
1. **Local Command Injection:** If a user input field (e.g., a target IP) can be manipulated to execute arbitrary commands on the *host* machine running ShadowCypher.
2. **AI Sandbox Escapes:** If the local AI agent can bypass the `_ALLOWED_COMMANDS` list in `orchestrator.py` or read files outside the designated safe paths.
3. **Cryptographic Failures:** Weaknesses in the RSA-OAEP ticket encryption or the Admin Identity verification logic (`identity.py`).
4. **GTK Threading Panics:** Vulnerabilities that allow remote target responses (e.g., a weird banner) to crash the local GTK UI.

### Out-of-Scope Threats (We will NOT fix these)
1. **Vulnerabilities in underlying tools:** If `sqlmap` or `nmap` has a vulnerability, that must be reported to those respective projects. ShadowCypher only orchestrates them.
2. **Physical Access Attacks:** If an attacker has physical access to the machine running ShadowCypher, or root access to the OS, the security model is already compromised.
3. **Malicious LLM Weights:** If a user manually loads a compromised, trojaned GGUF model into Ollama and authorizes it in ShadowCypher, the resulting behavior is outside our control.

## The Admin Node Concept

ShadowCypher utilizes an asymmetric cryptographic identity system. 
- The repository contains `admin_public.pem`.
- The maintainer holds `admin_private.pem` (which is never committed to Git).
- A machine is only recognized as the "Admin Node" if it can cryptographically prove possession of the private key matching the public key. 

Generating a new, random private key will **not** grant Admin access, as the derived public key will not match the shipped repository key.

## Reporting a Vulnerability

If you discover a vulnerability that falls within the "In-Scope Threats", please do **NOT** open a public GitHub issue. 

Instead, utilize the **Secure Comm-Link** built into ShadowCypher:
1. Open ShadowCypher.
2. Navigate to the **Support & Ticketing** tab.
3. Write your vulnerability report.
4. Click "Transmit".
5. Click "Copy Last Ticket" (or locate the JSON file in the `tickets/` directory).
6. Email the encrypted JSON payload or Base64 string to: `[YOUR EMAIL HERE]`

The message is RSA-encrypted. Only the Admin Node can decrypt it. You will receive a response regarding validation and timelines for a patch.