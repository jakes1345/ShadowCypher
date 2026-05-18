"""ShadowCypher Universal Module Registry — Tactical Build (V26.3)."""

def _safe_import(name, attr):
    try:
        import importlib
        mod = importlib.import_module(name)
        return getattr(mod, attr, None)
    except Exception:
        return None

Recon          = _safe_import("shadowcypher.modules.recon",           "Recon")
Network        = _safe_import("shadowcypher.modules.network",         "Network")
Credentials    = _safe_import("shadowcypher.modules.credentials",     "Credentials")
Wireless       = _safe_import("shadowcypher.modules.wireless",        "Wireless")
Forensics      = _safe_import("shadowcypher.modules.forensics",       "Forensics")
Firewall       = _safe_import("shadowcypher.modules.firewall",        "Firewall")
OSINT          = _safe_import("shadowcypher.modules.osint",           "OSINT")
VulnScanner    = _safe_import("shadowcypher.modules.vuln_scanner",    "VulnScanner")
Exploit        = _safe_import("shadowcypher.modules.exploit",         "Exploit")
WebForge       = _safe_import("shadowcypher.modules.web_exploit_v2",  "WebForge")
SSHTunnel      = _safe_import("shadowcypher.modules.ssh_tunnel",      "SSHTunnel")
Layer7         = _safe_import("shadowcypher.modules.layer7",          "Layer7")
HTTPSIntercept = _safe_import("shadowcypher.modules.https_intercept", "HTTPSIntercept")
PrivEsc        = _safe_import("shadowcypher.modules.privesc",         "PrivEsc")
C2Framework    = _safe_import("shadowcypher.modules.c2",              "C2Framework")
