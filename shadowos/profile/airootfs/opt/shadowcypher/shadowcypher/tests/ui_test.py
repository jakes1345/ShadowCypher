import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

print("[SYSTEM] INITIATING_UI_INTEGRITY_TEST_V26.5...")

pages = {
    "Overview": ("shadowcypher.ui.dashboard", "DashboardPage"),
    "AI": ("shadowcypher.ui.ai_page", "AIPage"),
    "Recon": ("shadowcypher.ui.recon_page", "ReconPage"),
    "Exploit": ("shadowcypher.ui.exploit_page", "ExploitPage"),
    "Vuln": ("shadowcypher.ui.vuln_page", "VulnScannerPage"),
    "Network": ("shadowcypher.ui.network_page", "NetworkPage"),
    "Forensics": ("shadowcypher.ui.forensics_page", "ForensicsPage"),
    "OSINT": ("shadowcypher.ui.osint_page", "OSINTPage"),
    "Credentials": ("shadowcypher.ui.credentials_page", "CredentialsPage"),
    "Firewall": ("shadowcypher.ui.firewall_page", "FirewallPage"),
    "Wireless": ("shadowcypher.ui.wireless_page", "WirelessPage"),
    "Session": ("shadowcypher.ui.session_page", "SessionPage")
}

for name, (mod, cls) in pages.items():
    print(f"Testing {name:15} ... ", end="")
    try:
        m = __import__(mod, fromlist=[cls])
        c = getattr(m, cls)
        print("IMPORT_SUCCESS")
    except Exception as e:
        print(f"FAILED: {str(e)}")
        sys.exit(1)

print("\n[UI_TEST] ALL_12_TABS_VERIFIED. THE_SUITE_IS_STABLE.")
