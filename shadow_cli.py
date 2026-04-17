#!/usr/bin/env python3
"""
ShadowCLI — The High-Velocity Tactical Terminal Bridge.
Direct access to the MetaChain Orchestrator for sovereign mission engagement.
"""

import os
import sys
import threading
import time
import json
from shadowcypher.ai.orchestrator import orchestrator
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

# Terminal Aesthetics
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_banner():
    banner = f"""
{CYAN}{BOLD}███████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ██╗    ██╗ ██████╗██╗   ██╗██████╗ ██╗  ██╗███████╗██████╗ 
██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██║    ██║██╔════╝╚██╗ ██╔╝██╔══██╗██║  ██║██╔════╝██╔══██╗
███████╗███████║███████║██║  ██║██║   ██║██║ █╗ ██║██║      ╚████╔╝ ██████╔╝███████║█████╗  ██████╔╝
╚════██║██╔══██║██╔══██║██║  ██║██║   ██║██║███╗██║██║       ╚██╔╝  ██╔═══╝ ██╔══██║██╔══╝  ██╔══██╗
███████║██║  ██║██║  ██║██████╔╝╚██████╔╝╚███╔███╔╝╚██████╗   ██║   ██║     ██║  ██║███████╗██║  ██║
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚══╝╚══╝  ╚═════╝   ╚═╝   ╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝{RESET}
                         {GRAY}[ TACTICAL CORE v4.0 - HKUDS-2025 ]{RESET}
    """
    print(banner)

def stream_callback(msg: str):
    """Dynamic progress output for the CLI."""
    clean = msg.strip()
    if not clean: return
    if clean.startswith("["):
        print(f"{GRAY}{clean}{RESET}")
    else:
        # Standard AI output
        print(f"{GREEN}{clean}{RESET}", end="", flush=True)

def engage_terminal():
    print_banner()
    
    # Subscribe to tactical bus to show background logs in real-time
    def _bus_listener():
        while True:
            # We use a simple bus logic here to show peer events
            pass
            
    threading.Thread(target=_bus_listener, daemon=True).start()

    while True:
        try:
            print(f"\n{CYAN}shadow@{BOLD}heretic{RESET}:{GRAY}# {RESET}", end="")
            query = input().strip()
            
            if not query: continue
            if query.lower() in ["exit", "quit", "disconnect"]:
                print(f"{RED}ABORT_SIGNAL: Terminating tactical bridge...{RESET}")
                break
            
            print(f"{GRAY}[PLANNING_CYCLE_START]{RESET}")
            
            event = threading.Event()
            
            def on_complete(res):
                print(f"\n{BOLD}{CYAN}--- FINAL_SOLUTION ---{RESET}")
                print(f"{GREEN}{res}{RESET}")
                event.set()

            orchestrator.execute_query_async(
                query, 
                callback=stream_callback, 
                on_complete=on_complete,
                agent_role="commander"
            )
            
            # Show spinner while waiting for final synthesis if needed
            while not event.is_set():
                time.sleep(1)

        except KeyboardInterrupt:
            print(f"\n{RED}INTERRUPT: Session paused. Type 'exit' to fully terminate.{RESET}")
        except Exception as e:
            print(f"{RED}CRITICAL_FAULT: {e}{RESET}")

if __name__ == "__main__":
    engage_terminal()
