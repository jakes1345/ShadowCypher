"""ShadowCypher Universal Module Registry — Tactical Build (V26.3 / v2.0)."""

def _safe_import(name, attr):
    try:
        import importlib
        mod = importlib.import_module(name)
        return getattr(mod, attr, None)
    except Exception:
        return None

# ── Original modules ──────────────────────────────────────────────────────────
Recon          = _safe_import("shadowcypher.modules.recon",           "Recon")
Network        = _safe_import("shadowcypher.modules.network",         "Network")
Credentials    = _safe_import("shadowcypher.modules.secret_audit",     "Credentials")
Wireless       = _safe_import("shadowcypher.modules.wireless",        "Wireless")
Forensics      = _safe_import("shadowcypher.modules.forensics",       "Forensics")
Firewall       = _safe_import("shadowcypher.modules.firewall",        "Firewall")
OSINT          = _safe_import("shadowcypher.modules.osint",           "OSINT")
VulnScanner    = _safe_import("shadowcypher.modules.vuln_scanner",    "VulnScanner")
PocEngine        = _safe_import("shadowcypher.modules.poc_engine",         "PocEngine")
WebForge       = _safe_import("shadowcypher.modules.web_forge",  "WebForge")
WebSecurity    = _safe_import("shadowcypher.modules.web_security",    "WebSecurity")
SSHTunnel      = _safe_import("shadowcypher.modules.ssh_tunnel",      "SSHTunnel")
Layer7         = _safe_import("shadowcypher.modules.app_layer",          "Layer7")
HTTPSIntercept = _safe_import("shadowcypher.modules.https_intercept", "HTTPSIntercept")
PrivAudit        = _safe_import("shadowcypher.modules.privilege_audit",         "PrivAudit")
AgentRelay    = _safe_import("shadowcypher.modules.agent_relay",              "AgentRelay")

# ── v2.0 modules ──────────────────────────────────────────────────────────────
CVEFeed        = _safe_import("shadowcypher.modules.cve_feed",        "cve_feed")   # singleton
cve_feed       = _safe_import("shadowcypher.modules.cve_feed",        "cve_feed")
StaticAnalyzer = _safe_import("shadowcypher.modules.static_analyzer", "StaticAnalyzer")
static_analyzer= _safe_import("shadowcypher.modules.static_analyzer", "static_analyzer")
StegoEngine    = _safe_import("shadowcypher.modules.stego",           "StegoEngine")
stego          = _safe_import("shadowcypher.modules.stego",           "stego")
BLERadar       = _safe_import("shadowcypher.modules.ble_radar",       "BLERadar")
ble_radar      = _safe_import("shadowcypher.modules.ble_radar",       "ble_radar")
GitHubRelay    = _safe_import("shadowcypher.modules.github_relay",       "GitHubRelay")
github_relay   = _safe_import("shadowcypher.modules.github_relay",       "github_relay")
SessionMonitor = _safe_import("shadowcypher.modules.session_monitor",    "SessionMonitor")
session_monitor= _safe_import("shadowcypher.modules.session_monitor",    "session_monitor")
