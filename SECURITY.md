# Security Policy

## Supported Versions

Only the `main` branch of ShadowCypher receives security updates.

## Threat Model & Design Philosophy

ShadowCypher is a security tool that integrates local AI with offensive security binaries (Nmap, Nikto, SQLmap, etc.). Its threat model differs from a standard web application.

### In-Scope Threats (We WILL fix these)

1. **Local Command Injection:** If a user input field (e.g., a target IP) can be manipulated to execute arbitrary commands on the *host* machine running ShadowCypher.
2. **ShadowScript Safety Bypasses:** If a mission can run `!sys`, `!pipe` or a native function outside an `UNSAFE { }` block, pass its arguments through a shell, or get past the runtime's timeout, output, loop and `LOAD` limits (`shadowcypher-qt/core/`).
3. **Cryptographic Failures:** Weaknesses in the AES-256-GCM chat encryption, the split-password login, or the handling of OpenPGP identity keys (`www/js/identity.js`).
4. **UI/IPC Injection:** Vulnerabilities that allow a remote target's response (e.g., a crafted banner) to crash the Qt6 desktop UI or inject commands through the local IPC socket.

### Out-of-Scope Threats (We will NOT fix these)

1. **Vulnerabilities in underlying tools:** If `sqlmap` or `nmap` has a vulnerability, report it to those projects. ShadowCypher only orchestrates them.
2. **Physical Access Attacks:** If an attacker has physical access to the machine running ShadowCypher, the security model is already compromised.
3. **Malicious LLM Weights:** If a user manually loads a compromised GGUF model into Ollama and authorizes it, the resulting behavior is outside our control.

## Architecture Overview

ShadowCypher is a multi-layer platform:

| Layer | Technology |
|-------|-----------|
| Desktop UI | Qt6 C++ (`shadowcypher-qt/`) — dark JetBrains Mono theme, QProcess tool invocation |
| Desktop daemon | `shadowcypher-qt/daemon/` — C++ background service (scans, incidents, CVE feed); Ghost mode changes the firewall only through a `pkexec` helper |
| Cloud API | Cloudflare Worker (`backend/api/`) — TypeScript, Supabase auth, KV/R2 storage |
| OS integration | ShadowOS Arch Linux ISO (`shadowos/`) — Ollama, hardened kernel |

## Reporting a Vulnerability

If you discover an in-scope vulnerability, do **NOT** open a public GitHub issue.

Send a plaintext heads-up to `security@shadowcypher.site` with no exploit details, and request secure follow-up instructions. We will provide an encrypted channel for the full disclosure.

## Security Response SLAs

| Severity | Acknowledgement | Fix Target |
|----------|----------------|------------|
| Critical / High | 72 hours | As fast as possible, typically ≤ 14 days |
| Medium | 72 hours | Next stable maintenance window |
| Low | 7 days | Next stable maintenance window |
