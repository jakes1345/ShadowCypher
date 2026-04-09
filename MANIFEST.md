# ShadowCypher Project Manifest (AI Context Map)

## Core Architecture
- `shadowcypher/app.py`: Main GTK entry point. Handles routing and sidebar.
- `shadowcypher/core/runner.py`: The task execution engine. Runs shell commands.
- `shadowcypher/ai/orchestrator.py`: The Big League ReAct brain.

## Native Modules
- `recon.py`: Nmap/Traceroute tools.
- `vuln_scanner.py`: SQLmap/Nmap-Scanner bridge.
- `phishing.py`: (PORTED) ShadowPhish artifacts and PHP server.
- `exploit.py`: Metasploit/Sliver bridge.
- `credentials.py`: Credential logging and hash cracking.

## External Bridges (The "Patchwork")
- `ai_engine/`: HKUDS/AutoAgent clone. Used for "Masterclass" missions.
- `ShadowPhish/`: Social engineering submodule (Templates & Backend).

## AI Models
- `gemma-4-heretic`: Primary unrestricted coder/hacker brain.
- `DeepHat-V1`: Secondary offensive strategist.
- `deepseek-r1`: Logical refactoring and UI polishing.

## Current Objectives
1. Eliminate all `[PLACEHOLDER]` tags in modules.
2. Ensure `shadowcypher/modules/phishing.py` uses the actual PHP templates.
3. Fix the `RouterInspector` import error (FIXED in recon.py).
4. Update Dockerfile to maintain tool modernity (DONE).
