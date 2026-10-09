"""ShadowCypher Module Integration Audit — Validates actual API surface."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shadowcypher.modules.firewall import Firewall
from shadowcypher.modules.forensics import Forensics
from shadowcypher.modules.network import Network
from shadowcypher.modules.osint import OSINT
from shadowcypher.modules.poc_engine import PocEngine
from shadowcypher.modules.recon import Recon
from shadowcypher.modules.vuln_scanner import VulnScanner
from shadowcypher.modules.wireless import Wireless

modules = {
    'PocEngine': PocEngine,
    'VulnScanner': VulnScanner,
    'Network': Network,
    'OSINT': OSINT,
    'Forensics': Forensics,
    'Wireless': Wireless,
    'Firewall': Firewall,
    'Recon': Recon,
}

required_methods = {
    'PocEngine': [
        'search_exploits',
        'launch_msf_exploit',
        'generate_payload',
        'auto_exploit',
    ],
    'VulnScanner': [
        'nuclei_scan',
        'sqlmap_scan',
        'nikto_scan',
        'audit_target',
        'shadow_zero_day_scan',
    ],
    'Network': [
        'get_interfaces',
        'arp_scan',
        'arp_sweep',
        'port_scan_tcp_connect',
        'port_scan_syn',
        'service_fingerprint',
        'service_scan',
        'network_os_detection',
        'packet_capture',
        'traffic_monitor',
        'dns_leak_test',
        'ai_network_audit',
    ],
    'OSINT': [
        'get_search_types',
        'ssl_cert_info',
        'http_headers',
        'tech_detect',
        'email_mx_check',
        'subnet_info',
        'zone_transfer',
        'ai_intel',
    ],
    'Forensics': [
        'analyze_file',
        'extract_metadata',
        'extract_strings',
        'binwalk_scan',
        'generate_hashes',
        'ai_investigate',
    ],
    'Wireless': [
        'list_interfaces',
        'enable_monitor',
        'disable_monitor',
        'scan_networks',
        'scan_wifi',
    ],
    'Firewall': [
        'detect_backend',
        'get_rules',
        'ipt_save',
        'ipt_flush',
        'ipt_block_ip',
        'ipt_block_port',
        'ipt_allow_port',
        'ipt_add_rule',
        'block_ip',
        'flush_rules',
    ],
    'Recon': [
        'pulse_target',
        'ai_recon',
    ],
}

total_missing = 0
total_methods = 0

print("[SYSTEM] BEGINNING_PLATFORM_INTEGRITY_AUDIT...")

for mod_name, methods in required_methods.items():
    mod_cls = modules.get(mod_name)
    missing = []
    for method in methods:
        total_methods += 1
        if not hasattr(mod_cls, method):
            missing.append(method)
            total_missing += 1

    if missing:
        print(f"  [MISSING] {mod_name:15}: {', '.join(missing)}")
    else:
        print(f"  [OK]      {mod_name:15}: All {len(methods)} methods verified.")

extended = {
    'WebSecurity': ('shadowcypher.modules.web_security', 'WebSecurity',
                   ['ffuf_dir_fuzz', 'ffuf_vhost_fuzz', 'nuclei_scan', 'nuclei_update']),
    'DeepOSINT': ('shadowcypher.modules.osint_deep', 'DeepOSINT',
                  ['social_footprint', 'email_audit', 'steam_correlate', 'leak_check']),
}

print("\nExtended Module Verification:")

for label, (mod_path, cls_name, methods) in extended.items():
    try:
        mod = __import__(mod_path, fromlist=[cls_name])
        cls = getattr(mod, cls_name)
        missing = [m for m in methods if not hasattr(cls, m)]
        if missing:
            print(f"  [MISSING] {label:15}: {', '.join(missing)}")
            total_missing += len(missing)
        else:
            print(f"  [OK]      {label:15}: All {len(methods)} methods verified.")
    except ImportError as e:
        print(f"  [ERROR]   {label:15}: {e}")
        total_missing += 1

print(f"\n{'='*60}")
print(f"Total Integrity Checks: {total_methods + len(extended)}")
print(f"Total Failures:         {total_missing}")
print(f"Status:                 {'PASS' if total_missing == 0 else 'FAIL'}")
print(f"{'='*60}")

if total_missing > 0:
    sys.exit(1)
