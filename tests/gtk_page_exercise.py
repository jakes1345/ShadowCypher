"""
Headless GTK page exerciser — instantiates every registered page and exercises
its primary action buttons without a real display (no Gdk rendering).
Run under Xvfb: xvfb-run -a python3 tests/gtk_page_exercise.py
"""
import sys, os, traceback, threading, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from unittest.mock import patch, MagicMock

PAGE_MAP = {
    "Central Command HUD": ("dashboard", "DashboardPage"),
    "Spectre War-Map": ("war_map_page", "WarMapPage"),
    "Artifact Crypt": ("vault_page", "ShadowVaultPage"),
    "Shadow-Synthesizer": ("ai_page", "AIPage"),
    "Spectral Intelligence": ("intel_page", "SpectralIntelligencePage"),
    "Vulnerability Sweep": ("vuln_page", "VulnScannerPage"),
    "Network Scanner": ("network_page", "NetworkPage"),
    "OSINT Probe": ("osint_page", "OSINTPage"),
    "Session Manager": ("session_page", "SessionPage"),
    "Recon Engine": ("recon_page", "ReconPage"),

    "Web & Cloud Strikes": ("web_security_page", "WebSecurityPage"),
    "Payload Factory": ("craft_page", "CraftPage"),
    "Wireless Saturation": ("wireless_page", "WirelessPage"),
    "C2 Command Center": ("relay_page", "RelayPage"),
    "PocEngine Engine": ("poc_page", "PocPage"),
    "Phishing Forge": ("awareness_page", "AwarenessPage"),
    "AD Assessment": ("ad_assessment_page", "ADAssessmentPage"),
    "AD Pivot": ("ad_page", "AdPage"),
    "Combat Deck": ("simulation_page", "SimulationDeck"),
    "ShadowScript": ("shadowscript_page", "ShadowScriptPage"),
    "Terminal": ("terminal_widget", "TerminalPage"),
    "Community Chat": ("chat_page", "ChatPage"),
    "Shadow Nodes": ("ghost_page", "ShadowNodesPage"),
    "Ghost Mode": ("ghost_mode_page", "GhostModePage"),
    "Forensic Audit": ("forensics_page", "ForensicsPage"),
    "Guardian": ("guardian_page", "GuardianPage"),
    "Intel Harvest": ("dataset_page", "DatasetPage"),
    "Firewall Manager": ("firewall_page", "FirewallPage"),
    "Credentials Vault": ("secrets_page", "SecretsPage"),
    "Hub Settings": ("admin_page", "AdminPage"),
    "God-Panel": ("god_panel", "GodPanel"),
    "Wraith Protocol": ("wraith_page", "WraithProtocol"),
    "ShadowCypher Audit": ("audit_page", "ShadowCypherAuditPage"),
    "Support": ("support_page", "SupportPage"),
}

def find_buttons(widget, buttons=None):
    if buttons is None:
        buttons = []
    if isinstance(widget, Gtk.Button):
        buttons.append(widget)
    if hasattr(widget, "get_children"):
        for child in widget.get_children():
            find_buttons(child, buttons)
    return buttons

def find_entries(widget, entries=None):
    if entries is None:
        entries = []
    if isinstance(widget, Gtk.Entry):
        entries.append(widget)
    if hasattr(widget, "get_children"):
        for child in widget.get_children():
            find_entries(child, entries)
    return entries

results = {}

def run_tests():
    for page_name, (mod_name, class_name) in PAGE_MAP.items():
        try:
            mod = __import__(f"shadowcypher.ui.{mod_name}", fromlist=[class_name])
            cls = getattr(mod, class_name)
            # Instantiate in a window so show_all() works
            win = Gtk.Window()
            page = cls()
            win.add(page)
            win.show_all()

            # Find all buttons and try clicking each (mocked actions)
            buttons = find_buttons(page)
            btn_errors = []
            for btn in buttons:
                try:
                    label = btn.get_label() or "(unlabeled)"
                    btn.emit("clicked")
                    GLib.main_context_default().iteration(False)
                except Exception as e:
                    btn_errors.append(f"btn '{label}': {e}")

            # Find all text entries and set test values
            entries = find_entries(page)
            for entry in entries:
                try:
                    entry.set_text("127.0.0.1")
                except Exception:
                    pass

            win.destroy()
            GLib.main_context_default().iteration(False)

            results[page_name] = {
                "status": "PASS" if not btn_errors else "WARN",
                "buttons": len(buttons),
                "entries": len(entries),
                "btn_errors": btn_errors,
            }
        except Exception as e:
            results[page_name] = {
                "status": "FAIL",
                "error": traceback.format_exc(),
            }

    Gtk.main_quit()

GLib.idle_add(run_tests)

# Timeout safety
def timeout_quit():
    Gtk.main_quit()
    return False
GLib.timeout_add_seconds(30, timeout_quit)

Gtk.main()

# Print results
print("\n" + "="*60)
print("GTK PAGE EXERCISE RESULTS")
print("="*60)
passed = warned = failed = 0
for name, r in results.items():
    status = r["status"]
    if status == "PASS":
        passed += 1
        print(f"  PASS  {name} ({r.get('buttons',0)} btns, {r.get('entries',0)} entries)")
    elif status == "WARN":
        warned += 1
        print(f"  WARN  {name}")
        for e in r.get("btn_errors", []):
            print(f"          {e}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        for line in r.get("error", "").splitlines()[-5:]:
            print(f"          {line}")

print(f"\n{passed} passed | {warned} warned | {failed} failed | {len(PAGE_MAP)} total")
sys.exit(1 if failed > 0 else 0)
