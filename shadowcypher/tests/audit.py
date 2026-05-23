"""ShadowCypher Module Integration Audit — Validates actual API surface."""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# ── Module Registry (matches modules/__init__.py + extras) ──

from shadowcypher.modules.exploit import Exploit
from shadowcypher.modules.vuln_scanner import VulnScanner
from shadowcypher.modules.network import Network
from shadowcypher.modules.osint import OSINT
from shadowcypher.modules.credentials import Credentials
from shadowcypher.modules.forensics import Forensics
from shadowcypher.modules.wireless import Wireless
from shadowcypher.modules.firewall import Firewall
from shadowcypher.modules.recon import Recon

modules = {
    'Exploit': Exploit,
    'VulnScanner': VulnScanner,
    'Network': Network,
    'OSINT': OSINT,
    'Credentials': Credentials,
    'Forensics': Forensics,
    'Wireless': Wireless,
    'Firewall': Firewall,
    'Recon': Recon,
}

# ── Required Methods (synced to 4.5.8 ULTIMA implementations) ──

required_methods = {
    'Exploit': [
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
        'shadow_zero_day_scan', # NEW
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
    'Credentials': [
        'brute_force',
        'hydra_attack',
        'identify_hash',
        'hashcat_crack',
        'hashcat_crack_string',
        'hashcat_benchmark',
        'john_crack',
        'john_crack_string',
        'audit_macos_keychain',
        'ai_crack',
        'deep_leak_correlation', # NEW
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
        'capture_handshake',
        'deauth',
        'deauth_target',
        'ai_jammer',
        'deauth_swarm', # NEW
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

# ── Audit Execution ──

total_missing = 0
total_methods = 0

print(f"[SYSTEM] BEGINNING_PLATFORM_INTEGRITY_AUDIT_v4.5.8...")

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

# ── Extended Modules Check (non-__init__ modules) ──

print(f"\nExtended Module Verification:")

extended = {
    'ADAttacks': ('shadowcypher.modules.ad_attacks', 'ADAttacks',
                  ['impacket_psexec', 'impacket_secretsdump', 'run_responder', 'golden_ticket_forge']), # NEW
    'ADPivot': ('shadowcypher.modules.ad_pivot', 'ADPivot',
                ['kerberoast', 'smb_relay_start', 'setup_pivot_tunnel', 'crackmapexec_scan']),
    'Phishing': ('shadowcypher.modules.phishing', 'SocialEngineeringAssessment',
                 ['generate_pdf', 'generate_obfuscated_ps1', 'start_phishing_server',
                  'generate_fake_recaptcha', 'generate_html_smuggling', 'start_zphisher',
                  'generate_professional_bait', 'start_secure_tunnel']), # NEW
    'PayloadFactory': ('shadowcypher.modules.payload_factory', 'PayloadFactory',
                       ['generate_evasive_elf', 'generate_stealth_powershell',
                        'generate_stealth_c2_python', 'generate_obfuscated_python']),
    'Exfiltration': ('shadowcypher.modules.exfiltration', 'Exfiltration',
                     ['exfiltrate_via_webhook', 'exfiltrate_via_dns', 'encrypt_archive']),
    'WebAttacks': ('shadowcypher.modules.web_attacks', 'WebAttacks',
                   ['ffuf_dir_fuzz', 'ffuf_vhost_fuzz', 'nuclei_scan', 'nuclei_update']),
    'DeepOSINT': ('shadowcypher.modules.osint_deep', 'DeepOSINT',
                  ['social_footprint', 'email_audit', 'steam_correlate', 'leak_check']),
    'Session': ('shadowcypher.modules.session', 'Session',
                ['list_active_sessions', 'terminate_session', 'interact_session', 'upload_to_session']),
}

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
