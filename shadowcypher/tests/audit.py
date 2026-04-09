import sys
sys.path.append('/home/jack/ShadowCypher')
import shadowcypher.modules as mods

modules = {
    'Exploit': mods.exploit.Exploit,
    'VulnScanner': mods.vuln_scanner.VulnScanner,
    'Network': mods.network.Network,
    'OSINT': mods.osint.OSINT,
    'Credentials': mods.credentials.Credentials,
    'Forensics': mods.forensics.Forensics,
    'Wireless': mods.wireless.Wireless,
    'Firewall': mods.firewall.Firewall,
    'Recon': mods.recon.Recon,
}

required_methods = {
    'Forensics': ['file_info', 'file_hashes', 'strings_extract', 'hex_dump', 'exif_data', 'stego_detect', 'binwalk_extract', 'pdf_analysis'],
    'Firewall': ['detect_backend', 'get_rules', 'ipt_save', 'ipt_flush', 'ipt_block_ip', 'ipt_block_port', 'ipt_allow_port', 'ipt_add_rule'],
    'Wireless': ['list_interfaces', 'enable_monitor', 'disable_monitor', 'scan_networks', 'capture_handshake', 'deauth', 'crack_wpa'],
    'VulnScanner': ['nikto_scan', 'sqlmap_scan', 'sqlmap_enumerate', 'nmap_vuln_scan', 'nmap_smb_vuln', 'nmap_ssl_scan', 'searchsploit', 'full_assessment'],
    'Network': ['get_interfaces', 'arp_scan', 'port_scan_tcp_connect', 'port_scan_syn', 'service_fingerprint', 'packet_capture', 'network_monitor', 'dns_leak_test', 'network_os_detection'],
    'Exploit': ['get_shell_types', 'reverse_shell', 'PAYLOAD_TEMPLATES', 'OUTPUT_FORMATS', 'ENCODERS', 'generate_payload', 'start_listener'],
    'Credentials': ['hydra_brute_force', 'crack_hash', 'identify_hash', 'get_hash_formats', 'get_services', 'hunt_credentials', 'generate_wordlist'], 
    'OSINT': ['ssl_cert_info', 'http_headers', 'tech_detect', 'email_mx_check', 'subnet_info', 'zone_transfer', 'get_search_types'],
    'Recon': ['pulse_target', 'traceroute', 'get_scan_types', 'discover_hosts']
}

missing = {}
for mod_name, methods in required_methods.items():
    mod_cls = modules.get(mod_name)
    missing[mod_name] = []
    for method in methods:
        if not hasattr(mod_cls, method):
             missing[mod_name].append(method)

for mod, misses in missing.items():
    if misses:
        print(f"[MISSING] {mod}: {', '.join(misses)}")
    else:
        print(f"[OK] {mod} is fully synced.")
