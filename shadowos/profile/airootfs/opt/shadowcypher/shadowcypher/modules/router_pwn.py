"""
Local Gateway Diagnostics Module — Enterprise Telemetry.
Specialized in identifying local gateway exposure and TR-069 management protocols.
"""

import socket
import subprocess
import requests
import re
import os
from typing import Optional, Dict
from shadowcypher.core.module import BaseModule
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class GatewayDiagnostics(BaseModule):
    def __init__(self):
        super().__init__(module_name="gateway_diagnostics")

    def get_gateway_ip(self) -> Optional[str]:
        """Resolve the default gateway IP address via local routing tables."""
        try:
            res = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True)
            match = re.search(r"via ([\d\.]+)", res.stdout)
            if match:
                return match.group(1)
        except Exception:
            pass
        return None

    def fingerprint_router(self, ip: str) -> Dict[str, str]:
        """Perform HTTP header analysis to identify gateway hardware vendor."""
        info = {"ip": ip, "manufacturer": "UNKNOWN", "model": "UNKNOWN", "headers": {}}
        
        try:
            resp = requests.get(f"http://{ip}/", timeout=3, allow_redirects=True, verify=False)  # nosec B501
            info["headers"] = dict(resp.headers)
            server = resp.headers.get("Server", "").lower()
            auth_header = resp.headers.get("WWW-Authenticate", "").lower()
            
            if "tplink" in server or "tplink" in auth_header:
                info["manufacturer"] = "TP-Link"
            elif "asus" in server or "asus" in auth_header:
                info["manufacturer"] = "ASUS"
            elif "linksys" in server:
                info["manufacturer"] = "Linksys"
            elif "netgear" in auth_header:
                info["manufacturer"] = "Netgear"
            elif "micro_httpd" in server:
                info["manufacturer"] = "Generic (BusyBox/micro_httpd)"
        except Exception:
            pass
            
        return info

    def audit_management_ports(self, ip: str, on_output=None):
        """Scan local gateway for exposed remote management interfaces."""
        common_ports = [80, 443, 22, 23, 7547, 8080, 53, 5353]
        if on_output:
            on_output(f"[*] AUDITING_EXPOSURES: {ip}...")
        
        open_ports = []
        for port in common_ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((ip, port)) == 0:
                    open_ports.append(port)
                    if on_output:
                        on_output(f"    [!] EXPOSED_PORT: {port} ({self._port_desc(port)})")
        
        if 7547 in open_ports:
            if on_output:
                on_output("\033[1;31m[CRITICAL] TR-069 (CWMP) DETECTED. Remote ISP management is active.\033[0m")
        
        return open_ports

    def discover_upnp(self, on_output=None):
        """Perform SSDP multicast to identify UPnP-enabled devices on the subnet."""
        if on_output:
            on_output("[*] scanning for UPnP devices...")
        msg = (
            'M-SEARCH * HTTP/1.1\r\n'
            'HOST: 239.255.255.250:1900\r\n'
            'MAN: "ssdp:discover"\r\n'
            'MX: 2\r\n'
            'ST: ssdp:all\r\n'
            '\r\n'
        )
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(2)
                s.sendto(msg.encode(), ('239.255.255.250', 1900))
                devices = []
                while True:
                    try:
                        data, addr = s.recvfrom(65507)
                        if addr[0] not in devices:
                            devices.append(addr[0])
                            if on_output:
                                on_output(f"    [!] UPNP_DEVICE: {addr[0]}")
                    except socket.timeout:
                        break
                return devices
        except Exception as e:
            if on_output:
                on_output(f"[-] SSDP_ERROR: {e}")
            return []

    def _port_desc(self, port: int) -> str:
        descs = {
            80: "HTTP (Web GUI)",
            443: "HTTPS (Web GUI)",
            22: "SSH",
            23: "Telnet",
            7547: "TR-069 (ISP Management)",
            8080: "HTTP-Proxy/Alt GUI",
            53: "DNS",
            5353: "mDNS"
        }
        return descs.get(port, "Unknown")

    def suggest_unmanagement_tactics(self, info: Dict):
        """Provide local network hygiene and hardening recommendations."""
        logger.warning("gateway", f"HARDENING_REQUIRED: Recommendations for {info.get('manufacturer')}")
        
        tactics = []
        if info.get("manufacturer") == "TP-Link":
            tactics.append("Disable 'Remote Management' in Web GUI.")
        
        # General hardening
        tactics.append("Filter inbound traffic on port 7547 to disable TR-069 remote provisioning.")
        tactics.append("Configure upstream DNS to utilize DNS-over-HTTPS (DoH) via local Unbound resolver.")
        tactics.append("Implement layer-2 MAC rotation for localized operational security.")
        
        return tactics

# Maintain legacy naming for internal module imports
router_pwn = GatewayDiagnostics()
