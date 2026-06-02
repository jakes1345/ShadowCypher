#!/usr/bin/env python3
"""
ShadowCypher UI & Module Integrity Verification.
Validates that all critical UI pages and core modules can be imported
without crashing. Run before deployment to catch missing deps.
"""

import sys
import os
import time
import traceback

# Ensure project root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

PASS = "\033[1;32m[+]\033[0m"
FAIL = "\033[1;31m[-]\033[0m"
WARN = "\033[1;33m[~]\033[0m"

results = {"pass": 0, "fail": 0, "warn": 0}


def check(name: str, import_path: str, cls_name: str = None):
    """Try to import a module and optionally instantiate a class."""
    try:
        mod = __import__(import_path, fromlist=[cls_name or ""])
        if cls_name:
            getattr(mod, cls_name)  # Verify class exists
        print(f"  {PASS} {name}")
        results["pass"] += 1
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        results["fail"] += 1


def check_tool(name: str, binary: str):
    """Check if an external tool is available."""
    import shutil
    if shutil.which(binary):
        print(f"  {PASS} {name}: {binary}")
        results["pass"] += 1
    else:
        print(f"  {WARN} {name}: {binary} not found")
        results["warn"] += 1


print()
print("\033[1;36m╔═══════════════════════════════════════════════════╗")
print("║  SHADOWCYPHER INTEGRITY VERIFICATION ENGINE v3  ║")
print("╚═══════════════════════════════════════════════════╝\033[0m")
print()

# ── GTK Foundation ──
print("\033[1;33m[*] GTK Foundation\033[0m")
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    print(f"  {PASS} Gtk 3.0")
    results["pass"] += 1
except Exception as e:
    print(f"  {FAIL} Gtk 3.0: {e}")
    results["fail"] += 1
    print("\n\033[1;31mFATAL: GTK3 unavailable. Cannot verify UI pages.\033[0m")
    sys.exit(1)

# ── Core Modules ──
print("\n\033[1;33m[*] Core Modules\033[0m")
core_modules = [
    ("Logger", "shadowcypher.core.logger", "logger"),
    ("Bus", "shadowcypher.core.bus", "bus"),
    ("Config", "shadowcypher.core.config", "config"),
    ("Hub", "shadowcypher.core.hub", "hub"),
    ("Identity", "shadowcypher.core.identity", "identity"),
    ("Runner", "shadowcypher.core.runner", "runner"),
    ("Platform", "shadowcypher.core.platform", "platform_engine"),
    ("Sanitize", "shadowcypher.core.sanitize", None),
    ("SovereignClient", "shadowcypher.core.sovereign", "SovereignClient"),
    ("Audit", "shadowcypher.core.audit", "auditor"),
]
for name, path, cls in core_modules:
    check(name, path, cls)

# ── Offensive Modules ──
print("\n\033[1;33m[*] Offensive Modules\033[0m")
offensive_modules = [
    ("Recon", "shadowcypher.modules.recon", "Recon"),
    ("Network", "shadowcypher.modules.network", "Network"),
    ("Wireless", "shadowcypher.modules.wireless", "Wireless"),
    ("PocEngine", "shadowcypher.modules.poc_engine", "PocEngine"),
    ("PrivAudit", "shadowcypher.modules.privilege_audit", "PrivAudit"),
    ("CraftFactory", "shadowcypher.modules.craft_factory", "CraftFactory"),
    ("WebSecurity", "shadowcypher.modules.web_security", "WebSecurity"),
    ("GhostHose", "shadowcypher.modules.ghost_hose", "GhostHose"),
    ("ShadowSwarm", "shadowcypher.modules.shadow_swarm", "ShadowSwarm"),
    ("C2", "shadowcypher.modules.agent_relay", "AgentRelay"),
]
for name, path, cls in offensive_modules:
    check(name, path, cls)

# ── Compiler ──
print("\n\033[1;33m[*] Compiler\033[0m")
check("Lexer", "shadowcypher.compiler.lexer", "ShadowLexer")
check("Interpreter", "shadowcypher.compiler.interpreter", "ShadowInterpreter")

# ── UI Pages ──
print("\n\033[1;33m[*] UI Pages\033[0m")
ui_pages = [
    ("Dashboard", "shadowcypher.ui.dashboard", "DashboardPage"),
    ("SupportPage", "shadowcypher.ui.support_page", "SupportPage"),
    ("GhostDeck", "shadowcypher.ui.ghost_page", "GhostDeck"),
    ("VaultPage", "shadowcypher.ui.vault_page", "ShadowVaultPage"),
    ("ReconPage", "shadowcypher.ui.recon_page", "ReconPage"),
    ("NetworkPage", "shadowcypher.ui.network_page", "NetworkPage"),
    ("CombatDeck", "shadowcypher.ui.combat_page", "CombatDeck"),
    ("AdminPage", "shadowcypher.ui.admin_page", "AdminPage"),
    ("Animations", "shadowcypher.ui.animations", None),
    ("ChatPage", "shadowcypher.ui.chat_page", "ChatPage"),
]
for name, path, cls in ui_pages:
    check(name, path, cls)

# ── External Tools ──
print("\n\033[1;33m[*] External Tools\033[0m")
tools = [
    ("Nmap", "nmap"), ("Hydra", "hydra"), ("John", "john"),
    ("Hashcat", "hashcat"), ("Aircrack-ng", "aircrack-ng"),
    ("Tcpdump", "tcpdump"), ("Searchsploit", "searchsploit"),
    ("Ffuf", "ffuf"), ("Nuclei", "nuclei"), ("Curl", "curl"),
    ("Sherlock", "sherlock"), ("Whois", "whois"),
]
for name, binary in tools:
    check_tool(name, binary)

# ── Python Dependencies ──
print("\n\033[1;33m[*] Python Dependencies\033[0m")
py_deps = [
    ("websockets", "websockets"),
    ("aiohttp", "aiohttp"),
    ("cryptography", "cryptography"),
    ("requests", "requests"),
    ("pydantic", "pydantic"),
]
for name, mod in py_deps:
    check(name, mod)

# ── Summary ──
print()
print("═" * 55)
total = results["pass"] + results["fail"] + results["warn"]
print(f"  {PASS} Passed: {results['pass']}")
print(f"  {FAIL} Failed: {results['fail']}")
print(f"  {WARN} Warnings: {results['warn']}")
print(f"  Total: {total}")
print("═" * 55)

if results["fail"] == 0:
    print(f"\n\033[1;32m  ✅ ALL CRITICAL CHECKS PASSED\033[0m\n")
else:
    print(f"\n\033[1;31m  ❌ {results['fail']} CRITICAL FAILURE(S) DETECTED\033[0m\n")
    sys.exit(1)
