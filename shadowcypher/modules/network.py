"""ShadowCypher Network Operations Engine — High-Fidelity Sync (V23.1)."""

import subprocess
import shlex
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import (
    validate_target,
    validate_ports,
    validate_interface,
    sanitize_bpf_filter,
)


class Network:
    """Universal network engine. Handles ARPs, TCP scans, and real-time captures."""

    @staticmethod
    def get_interfaces():
        """List all network interfaces with their IPs."""
        try:
            return subprocess.check_output(["ip", "-br", "addr"], text=True)
        except Exception:
            return "Unable to retrieve interfaces."

    @staticmethod
    def arp_scan(interface=None, subnet=None, on_output=None, on_complete=None):
        """ARP scan a local network to discover hosts."""
        subnet = subnet or "192.168.1.0/24"
        if not validate_target(subnet):
            if on_output:
                on_output(f"[ERROR] Invalid subnet: {subnet}")
            return
        args = ["nmap", "-sn", "-PR"]
        if interface:
            if not validate_interface(interface):
                if on_output:
                    on_output(f"[ERROR] Invalid interface: {interface}")
                return
            args += ["-e", interface]
        args.append(subnet)
        return runner.execute_task(f"ARP_SCAN_{subnet}", args, callback=on_output)

    @staticmethod
    def port_scan_tcp_connect(target, ports="1-1024", on_output=None, on_complete=None):
        """TCP connect scan (no root needed)."""
        if not validate_target(target):
            if on_output:
                on_output(f"[ERROR] Invalid target: {target}")
            return
        if not validate_ports(ports):
            if on_output:
                on_output(f"[ERROR] Invalid port spec: {ports}")
            return
        return runner.execute_task(
            f"TCP_SCAN_{target}",
            ["nmap", "-sT", "-p", ports, "-T4", "--open", target],
            callback=on_output,
        )

    @staticmethod
    def port_scan_syn(target, ports="1-65535", on_output=None, on_complete=None):
        """SYN stealth scan (requires root)."""
        if not validate_target(target):
            if on_output:
                on_output(f"[ERROR] Invalid target: {target}")
            return
        if not validate_ports(ports):
            if on_output:
                on_output(f"[ERROR] Invalid port spec: {ports}")
            return
        return runner.execute_task(
            f"SYN_SCAN_{target}",
            ["nmap", "-sS", "-p", ports, "-T4", "--open", target],
            callback=on_output,
        )

    @staticmethod
    def packet_capture(
        interface=None, count=100, filter_expr="", on_output=None, on_complete=None
    ):
        """Capture packets using tcpdump."""
        args = ["tcpdump"]
        if interface:
            if not validate_interface(interface):
                if on_output:
                    on_output(f"[ERROR] Invalid interface: {interface}")
                return
            args += ["-i", interface]
        else:
            args += ["-i", "any"]
        args += ["-c", str(int(count)), "-nn", "-l"]
        if filter_expr:
            safe_filter = sanitize_bpf_filter(filter_expr)
            if not safe_filter:
                if on_output:
                    on_output(f"[ERROR] Invalid BPF filter expression.")
                return
            args.append(safe_filter)
        return runner.execute_task("PACKET_CAPTURE", args, callback=on_output)

    @staticmethod
    def network_monitor(interface=None, on_output=None, on_complete=None):
        """Monitor network traffic statistics in real-time."""
        iface = interface or "eth0"
        if not validate_interface(iface):
            if on_output:
                on_output(f"[ERROR] Invalid interface: {iface}")
            return
        cmd = f"watch -n 1 'grep {shlex.quote(iface)} /proc/net/dev'"
        return runner.execute_task_shell(f"MONITOR_{iface}", cmd, callback=on_output)

    @staticmethod
    def dns_leak_test(on_output=None, on_complete=None):
        """Basic DNS leak test."""
        return runner.execute_task(
            "DNS_LEAK_TEST",
            ["dig", "+short", "whoami.akamai.net", "@ns1-1.akamaitech.net"],
            callback=on_output,
        )

    @staticmethod
    def network_os_detection(target, on_output=None, on_complete=None):
        """Aggressive OS detection scan."""
        if not validate_target(target):
            if on_output:
                on_output(f"[ERROR] Invalid target: {target}")
            return
        return runner.execute_task(
            f"OS_DETECT_{target}",
            ["nmap", "-O", "-A", "-T4", target],
            callback=on_output,
        )

    @staticmethod
    def service_fingerprint(target, ports=None, on_output=None, on_complete=None):
        """Detailed service version detection."""
        if not validate_target(target):
            if on_output:
                on_output(f"[ERROR] Invalid target: {target}")
            return
        args = ["nmap", "-sV"]
        if ports:
            if not validate_ports(ports):
                if on_output:
                    on_output(f"[ERROR] Invalid port spec: {ports}")
                return
            args += ["-p", ports]
        args.append(target)
        return runner.execute_task(
            f"SVC_FINGERPRINT_{target}", args, callback=on_output
        )
