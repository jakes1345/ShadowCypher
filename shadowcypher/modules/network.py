"""
Network Module — Apex Intelligence Build.
Handles packet-level operations, ARP sweeps, service fingerprinting, and OS detection.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.sanitize import (
    validate_target, validate_ports, validate_interface
)
import subprocess


class Network(BaseModule):
    """The 'Ether' engine of ShadowCypher."""

    def __init__(self):
        super().__init__(module_name="network")

    @staticmethod
    def get_interfaces():
        """List all network interfaces with addresses."""
        try:
            if platform_engine.IS_LINUX:
                return subprocess.check_output(["ip", "-br", "addr"], text=True)
            elif platform_engine.IS_MACOS:
                return subprocess.check_output(["ifconfig"], text=True)
            elif platform_engine.IS_WINDOWS:
                return subprocess.check_output(["ipconfig", "/all"], text=True)
        except Exception:
            return "INTERFACE_ENUM_FAILED"

    # ── Scanning ──

    @staticmethod
    def arp_scan(interface=None, subnet=None, on_output=None, on_complete=None):
        """ARP sweep to discover live hosts on the local network."""
        from shadowcypher.core.runner import runner
        args = ["nmap", "-sn", "-PR"]
        if interface and validate_interface(interface):
            args += ["-e", interface]
        if subnet and validate_target(subnet):
            args.append(subnet)
        else:
            args.append("192.168.1.0/24")  # Sensible default
        return runner.execute_task("ARP_SCAN", args, callback=on_output)

    @staticmethod
    def port_scan_tcp_connect(target, ports="1-1024", on_output=None, on_complete=None):
        """TCP connect scan — reliable but noisy."""
        if not validate_target(target):
            return
        from shadowcypher.core.runner import runner
        args = ["nmap", "-sT", "-p", ports, "-T4", target]
        return runner.execute_task(f"TCP_SCAN_{target}", args, callback=on_output)

    @staticmethod
    def port_scan_syn(target, ports="1-65535", on_output=None, on_complete=None):
        """SYN stealth scan — fast and stealthy (requires root)."""
        if not validate_target(target):
            return
        from shadowcypher.core.runner import runner
        elev = "pkexec" if platform_engine.IS_LINUX else "sudo"
        args = [elev, "nmap", "-sS", "-p", ports, "-T4", target]
        return runner.execute_task(f"SYN_SCAN_{target}", args, callback=on_output)

    @staticmethod
    def service_fingerprint(target, ports=None, on_output=None, on_complete=None):
        """Service version detection scan."""
        if not validate_target(target):
            return
        from shadowcypher.core.runner import runner
        nmap = platform_engine.get_cmd("nmap")
        args = [nmap, "-sV", "-T4"]
        if ports:
            args += ["-p", ports]
        args.append(target)
        return runner.execute_task(f"SVC_{target}", args, callback=on_output)

    @staticmethod
    def network_os_detection(target, on_output=None, on_complete=None):
        """OS fingerprinting via nmap -O."""
        if not validate_target(target):
            return
        from shadowcypher.core.runner import runner
        elev = "pkexec" if platform_engine.IS_LINUX else "sudo"
        args = [elev, "nmap", "-O", "-T4", target]
        return runner.execute_task(f"OS_DETECT_{target}", args, callback=on_output)

    # ── Packet Capture ──

    @staticmethod
    def packet_capture(interface=None, count=100, bpf_filter=None, on_output=None, on_complete=None):
        """Live packet capture via tcpdump with Pulse spectrum injection."""
        from shadowcypher.core.runner import runner
        from shadowcypher.core.pulse import pulse
        
        iface = interface or "any"
        args = ["tcpdump", "-i", iface, "-c", str(count), "-nn", "-l"]
        if bpf_filter:
            args.append(bpf_filter)
            
        def pulse_wrapper(line):
            # Extract length if present: "... length 102"
            import re
            match = re.search(r'length (\d+)', line)
            if match:
                pulse.ingest("network_spectrum", float(match.group(1)))
            if on_output: on_output(line)

        return runner.execute_task("SNIFFER", args, callback=pulse_wrapper)

    @staticmethod
    def network_monitor(interface=None, on_output=None, on_complete=None):
        """Live traffic monitoring (long-running) with real-time Pulse auditing."""
        from shadowcypher.core.runner import runner
        from shadowcypher.core.pulse import pulse
        
        iface = interface or "any"
        args = ["tcpdump", "-i", iface, "-nn", "-l", "-c", "500"]
        
        def pulse_wrapper(line):
            import re
            match = re.search(r'length (\d+)', line)
            if match:
                pulse.ingest("network_spectrum", float(match.group(1)))
            if on_output: on_output(line)

        return runner.execute_task("NET_MONITOR", args, callback=pulse_wrapper)

    # ── DNS & Other ──

    @staticmethod
    def dns_leak_test(on_output=None, on_complete=None):
        """Test for DNS leaks by querying external resolvers."""
        from shadowcypher.core.runner import runner
        # Query a DNS leak test service
        args = ["nslookup", "whoami.akamai.net"]
        return runner.execute_task("DNS_LEAK", args, callback=on_output)

    def arp_sweep(self, subnet, interface=None, on_output=None):
        """Instance-method alias for arp_scan."""
        return Network.arp_scan(interface, subnet, on_output)

    def service_scan(self, target, ports="1-1024", on_output=None):
        """Instance-method alias for service_fingerprint."""
        return Network.service_fingerprint(target, ports, on_output)

    def ai_network_audit(self, target, on_output=None):
        """Escalate to the Swarm for deep-packet network analysis."""
        from shadowcypher.core.hub import hub
        self.log(f"AI_NETWORK_AUDIT_ENGAGED: {target}", "AI")
        return hub.dispatch_mission(
            f"Perform a complete network-layer audit of {target}. "
            "Identify hidden services and potential lateral movement paths."
        )
