"""
Network Module — Apex Intelligence Build.
Handles packet-level operations, ARP sweeps, and service fingerprinting.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import (
    validate_target, validate_ports, validate_interface
)
import subprocess

class Network(BaseModule):
    """The 'Ether' engine of ShadowCypher."""
    
    def __init__(self):
        super().__init__(module_name="network")

    def get_interfaces(self):
        try:
            return subprocess.check_output(["ip", "-br", "addr"], text=True)
        except: return "INTERFACE_ENUM_FAILED"

    def arp_sweep(self, subnet, interface=None, on_output=None):
        if not validate_target(subnet): return
        self.log(f"INITIATING_ARP_SWEEP: {subnet}")
        
        args = ["nmap", "-sn", "-PR"]
        if interface and validate_interface(interface):
            args += ["-e", interface]
        args.append(subnet)
        
        return self.execute(f"ARP_{subnet}", args, callback=on_output)

    def packet_capture(self, interface="any", count=100, on_output=None):
        self.log(f"PACKET_CAPTURE_START: {interface} [COUNT={count}]")
        args = ["tcpdump", "-i", interface, "-c", str(count), "-nn", "-l"]
        return self.execute("SNIFFER", args, callback=on_output)

    def service_scan(self, target, ports="1-1024", on_output=None):
        if not validate_target(target): return
        self.log(f"SERVICE_SCAN_INIT: {target} [PORTS={ports}]")
        
        nmap = self.get_tool_path("nmap")
        args = [nmap, "-sV", "-p", ports, "-T4", target]
        return self.execute(f"SVC_{target}", args, callback=on_output)

    def ai_network_audit(self, target, on_output=None):
        """Escalate to the Swarm for deep-packet network analysis."""
        from shadowcypher.core.hub import hub
        self.log(f"AI_NETWORK_AUDIT_ENGAGED: {target}", "AI")
        return hub.register_mission(f"Perform a complete network-layer audit of {target}. Identify hidden services and potential lateral movement paths.")
