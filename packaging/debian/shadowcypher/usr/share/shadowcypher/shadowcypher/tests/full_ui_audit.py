import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import sys, os
import traceback

# Setup environment
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)

# Mock Gtk.Application if needed
class MockApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.shadowcypher.audit")

def audit_ui():
    pages = {
        "Operational Overview": "shadowcypher.ui.dashboard.DashboardPage",
        "Tactical Swarm AI": "shadowcypher.ui.ai_page.AIPage",
        "Signal Recon": "shadowcypher.ui.recon_page.ReconPage",
        "Offensive PocEngine": "shadowcypher.ui.poc_page.PocPage",
        "Vulnerability Pulse": "shadowcypher.ui.vuln_page.VulnScannerPage",
        "Stealth Network": "shadowcypher.ui.network_page.NetworkPage",
        "Digital Analysis": "shadowcypher.ui.forensics_page.ForensicsPage",
        "OSINT Intelligence": "shadowcypher.ui.osint_page.OSINTPage",
        "Credential Hub": "shadowcypher.ui.secrets_page.SecretsPage",
        "Master Asset Discovery": "shadowcypher.ui.steam_page.SteamAuditPage",
        "Firewall Defense": "shadowcypher.ui.firewall_page.FirewallPage",
        "Wireless Signals": "shadowcypher.ui.wireless_page.WirelessPage",
        "System Control": "shadowcypher.ui.session_page.SessionPage",
        "Support & Ticketing": "shadowcypher.ui.support_page.SupportPage"
    }
    
    results = []
    print("[UI_AUDIT] Initiating Tactical Handoff...")
    
    for name, class_path in pages.items():
        try:
            mod_path, cls_name = ".".join(class_path.split(".")[:-1]), class_path.split(".")[-1]
            mod = __import__(mod_path, fromlist=[cls_name])
            cls = getattr(mod, cls_name)
            
            # Attemping instantiation (without a full Gtk loop)
            instance = cls()
            results.append(f"[OK] {name}: Instance Verified.")
        except Exception as e:
            results.append(f"[FAIL] {name}: {str(e)}")
            # traceback.print_exc()
            
    print("\n".join(results))
    return results

if __name__ == "__main__":
    audit_ui()
