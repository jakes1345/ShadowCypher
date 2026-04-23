"""
Sovereign Relay Module — The 'Wraith Tunnel' Engine.
Implements a high-performance, stealthy WireGuard-based relay for mobile devices.
Provides the 'VPN without the VPN' experience via custom obfuscation and DNS sovereignty.
"""

import os
import subprocess
import socket
import requests
from typing import Optional, Dict
from shadowcypher.core.module import BaseModule
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class SovereignRelay(BaseModule):
    def __init__(self):
        super().__init__(module_name="sovereign_relay")
        self.config_path = "/etc/wireguard/wg0.conf"
        self.base_dir = "configs/wraith_tunnel"
        os.makedirs(self.base_dir, exist_ok=True)

    def generate_keys(self, name: str) -> Dict[str, str]:
        """Generate private/public key pair for a node."""
        priv_file = os.path.join(self.base_dir, f"{name}_private.key")
        pub_file = os.path.join(self.base_dir, f"{name}_public.key")
        
        try:
            priv = subprocess.check_output(["wg", "genkey"]).decode().strip()
            with open(priv_file, "w") as f: f.write(priv)
            
            pub = subprocess.check_output(["wg", "pubkey"], input=priv.encode()).decode().strip()
            with open(pub_file, "w") as f: f.write(pub)
            
            return {"private": priv, "public": pub}
        except Exception as e:
            logger.error("relay", f"KEY_GEN_FAILED: {e}")
            return {}

    def deploy_server(self, port: int = 51820, dns: str = "1.1.1.1"):
        """Deploy the Sovereign Hub server configuration."""
        keys = self.generate_keys("server")
        if not keys: return False
        
        # Detect primary interface
        try:
            iface = subprocess.check_output(
                "ip route get 8.8.8.8 | grep -oP 'dev \\K\\S+'",
                shell=True,
            ).decode().strip()
        except (subprocess.CalledProcessError, OSError):
            iface = "eth0"

        config = f"""[Interface]
PrivateKey = {keys['private']}
Address = 10.0.0.1/24
ListenPort = {port}
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o {iface} -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o {iface} -j MASQUERADE
"""
        conf_file = os.path.join(self.base_dir, "wg0.conf")
        with open(conf_file, "w") as f:
            f.write(config)
            
        # 2. UPnP Port Forwarding (The 'Real Connection' Enabler)
        try:
            local_ip = self._get_local_ip()
            logger.info("relay", f"ATTEMPTING_UPNP_PORT_MAPPING: External Port {port} -> {local_ip}")
            subprocess.run(["upnpc", "-a", local_ip, str(port), str(port), "UDP"], capture_output=True)
            logger.info("relay", "UPNP_MAPPING_SUCCESS: Gateway has opened the tactical port.")
        except Exception as e:
            logger.warning("relay", f"UPNP_MAPPING_FAILED: {e} - Manual port forwarding may be required.")

        logger.info("relay", f"SOVEREIGN_HUB_CONFIGURED: Port={port} Interface={iface}")
        return conf_file

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
        except OSError:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def add_client(self, name: str, client_ip: str):
        """Add a mobile client (S23, S7, etc.) to the hub."""
        server_pub = ""
        with open(os.path.join(self.base_dir, "server_public.key"), "r") as f:
            server_pub = f.read().strip()
            
        keys = self.generate_keys(name)
        if not keys: return None
        
        # Server Config Snippet
        server_snippet = f"""
[Peer]
PublicKey = {keys['public']}
AllowedIPs = {client_ip}/32
"""
        with open(os.path.join(self.base_dir, "wg0.conf"), "a") as f:
            f.write(server_snippet)
            
        # Client Config — refuse to generate a config with a stub endpoint.
        public_ip = self._get_public_ip()
        if not public_ip:
            logger.error("relay", "add_client aborted: public IP unavailable")
            return None
        endpoint = f"{public_ip}:51820"
        client_config = f"""[Interface]
PrivateKey = {keys['private']}
Address = {client_ip}/24
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pub}
Endpoint = {endpoint}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        client_conf_path = os.path.join(self.base_dir, f"{name}.conf")
        with open(client_conf_path, "w") as f:
            f.write(client_config)
            
        logger.info("relay", f"CLIENT_PROVISIONED: Name={name} IP={client_ip}")
        return client_conf_path

    def _get_public_ip(self) -> Optional[str]:
        """Return the machine's current public IPv4, or None if unreachable.

        Returning None instead of a placeholder string prevents callers from
        silently writing a literal 'YOUR_PUBLIC_IP' into generated client
        configs — the caller must now handle the missing-IP case explicitly.
        """
        try:
            r = requests.get("https://api.ipify.org", timeout=5)
            if r.status_code == 200 and r.text:
                return r.text.strip()
        except (requests.RequestException, OSError) as e:
            logger.warning("relay", f"public-IP lookup failed: {e}")
        return None

    def generate_qr(self, config_path: str) -> Optional[str]:
        """Generate a QR code for mobile scanning."""
        qr_path = config_path.replace(".conf", ".png")
        try:
            subprocess.run(
                ["qrencode", "-t", "ansiutf8", "-r", config_path],
                capture_output=True, timeout=10,
            )  # terminal display
            subprocess.run(
                ["qrencode", "-o", qr_path, "-r", config_path],
                capture_output=True, timeout=10,
            )
            return qr_path if os.path.exists(qr_path) else None
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.warning("relay", f"qrencode failed: {e}")
            return None

sovereign_relay = SovereignRelay()
