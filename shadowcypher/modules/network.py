"""ShadowCypher Network Operations Engine — High-Fidelity Sync (V23.1)."""

import subprocess
import os
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class Network:
    """Universal network engine. Handles ARPs, TCP scans, and real-time captures."""
    
    @staticmethod
    def get_interfaces():
        """List all network interfaces with their IPs."""
        try:
            return subprocess.check_output("ip -br addr", shell=True, text=True)
        except:
            return "Unable to retrieve interfaces."

    @staticmethod
    def arp_scan(interface=None, subnet=None, on_output=None, on_complete=None):
        """ARP scan a local network to discover hosts."""
        subnet = subnet or "192.168.1.0/24"
        iface_flag = f"-e {interface}" if interface else ""
        cmd = f"nmap -sn -PR {iface_flag} {subnet}"
        runner.execute_task(f"ARP_SCAN_{subnet}", cmd, callback=on_output)

    @staticmethod
    def port_scan_tcp_connect(target, ports="1-1024", on_output=None, on_complete=None):
        """TCP connect scan (no root needed)."""
        cmd = f"nmap -sT -p {ports} -T4 --open {target}"
        runner.execute_task(f"TCP_SCAN_{target}", cmd, callback=on_output)

    @staticmethod
    def port_scan_syn(target, ports="1-65535", on_output=None, on_complete=None):
        """SYN stealth scan (requires root)."""
        cmd = f"nmap -sS -p {ports} -T4 --open {target}"
        # Note: This may require sudo, but the runner handles shell=True
        runner.execute_task(f"SYN_SCAN_{target}", cmd, callback=on_output)

    @staticmethod
    def packet_capture(interface=None, count=100, filter_expr="", on_output=None, on_complete=None):
        """Capture packets using tcpdump."""
        iface_flag = f"-i {interface}" if interface else "-i any"
        filter_part = f" '{filter_expr}'" if filter_expr else ""
        cmd = f"tcpdump {iface_flag} -c {count} -nn -l {filter_part}"
        runner.execute_task("PACKET_CAPTURE", cmd, callback=on_output)

    @staticmethod
    def network_monitor(interface=None, on_output=None, on_complete=None):
        """Monitor network traffic statistics in real-time."""
        iface = interface or "eth0"
        script = f"watch -n 1 'grep {iface} /proc/net/dev | awk \"{{print \\$1, \\$2, \\$10}}\"'"
        runner.execute_task(f"MONITOR_{iface}", script, callback=on_output)

    @staticmethod
    def dns_leak_test(on_output=None, on_complete=None):
        """Basic DNS leak test."""
        cmd = "dig +short whoami.akamai.net @ns1-1.akamaitech.net"
        runner.execute_task("DNS_LEAK_TEST", cmd, callback=on_output)

    @staticmethod
    def network_os_detection(target, on_output=None, on_complete=None):
        """Aggressive OS detection scan."""
        cmd = f"nmap -O -A -T4 {target}"
        runner.execute_task(f"OS_DETECT_{target}", cmd, callback=on_output)

    @staticmethod
    def service_fingerprint(target, ports=None, on_output=None, on_complete=None):
        """Detailed service version detection."""
        port_arg = f"-p {ports}" if ports else ""
        cmd = f"nmap -sV {port_arg} {target}"
        runner.execute_task(f"SVC_FINGERPRINT_{target}", cmd, callback=on_output)
