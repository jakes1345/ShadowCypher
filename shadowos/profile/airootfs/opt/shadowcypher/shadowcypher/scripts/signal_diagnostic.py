#!/usr/bin/env python3
"""
ShadowCypher Signal Diagnostic — High-Fidelity Signal Integrity Probe.
Evaluates connectivity to Sovereign and External signal planes.
"""

import asyncio

from shadowcypher.core.config import config
from shadowcypher.core.sovereign import SovereignClient


async def run_diagnostic():
    print("\033[1;34m[SIGNAL_DIAGNOSTIC] Initializing Probe Sequence...\033[0m")

    # 1. Sovereign Plane Probe
    print(f"[*] Probing Sovereign Hub: {config.irc.sovereign_server}:{config.irc.sovereign_port}")
    sov = SovereignClient(
        host=config.irc.sovereign_server,
        port=config.irc.sovereign_port,
        nick="DiagnosticNode"
    )

    try:
        # We wrap the connect in a timeout
        await asyncio.wait_for(sov.connect(), timeout=5.0)
        print("\033[1;32m[+] SOVEREIGN_PLANE: OPERATIONAL (WebSocket/JSON Ready)\033[0m")
    except asyncio.TimeoutError:
        print("\033[1;31m[-] SOVEREIGN_PLANE: TIMEOUT (Check if Ergo is running)\033[0m")
    except Exception as e:
        print(f"\033[1;31m[-] SOVEREIGN_PLANE: ERROR ({e})\033[0m")

    # 2. Nexus Swarm Probe
    from shadowcypher.core.nexus import nexus
    print("[*] Probing Nexus Swarm...")
    try:
        nodes = nexus.nodes
        print(f"\033[1;32m[+] NEXUS_SWARM: {len(nodes)} active nodes discovered.\033[0m")
        for nid, data in nodes.items():
            print(f"    - {nid}: {data['host']}:{data['port']} ({data.get('status', 'ACTIVE')})")
    except Exception as e:
        print(f"\033[1;31m[-] NEXUS_SWARM: FAILURE ({e})\033[0m")

    print("\033[1;34m[SIGNAL_DIAGNOSTIC] Diagnostic Sequence Complete.\033[0m")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
