import subprocess
import time

from shadowcypher.core.logger import logger


class EgressRouter:
    """
    Enterprise Egress Rotation Manager.
    Instead of modifying local LAN IPs (which does not provide anonymity),
    this module interfaces with Tor control ports or proxychains to rotate
    the external egress IP address, ensuring operational footprint modification.
    """

    def __init__(self, tor_control_port=9051, password=""):
        self.control_port = tor_control_port
        self.password = password
        self.active = False

    def get_current_egress_ip(self):
        """Fetches the current external IP routing."""
        try:
            if self.active:
                # Route both DNS and HTTP through Tor SOCKS proxy to prevent DNS leaks
                cmd = ["curl", "-s", "--max-time", "10",
                       "--socks5-hostname", "127.0.0.1:9050",
                       "https://api.ipify.org"]
            else:
                cmd = ["curl", "-s", "--max-time", "5", "https://api.ipify.org"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return result.stdout.strip()
        except Exception as e:
            logger.error("egress", f"Failed to fetch egress IP: {e}")
            return None

    def rotate_ip(self):
        """Forces Tor to build a new circuit, effectively changing the egress IP."""
        logger.info("egress", "Requesting egress IP rotation via Tor Control Port...")
        try:
            import socket
            s = socket.socket()
            s.connect(('127.0.0.1', self.control_port))

            if self.password:
                s.send(f'AUTHENTICATE "{self.password}"\r\n'.encode('utf-8'))
            else:
                s.send(b'AUTHENTICATE ""\r\n')

            response = s.recv(1024).decode('utf-8')
            if "250 OK" not in response:
                logger.error("egress", f"Authentication failed: {response}")
                return False

            s.send(b'SIGNAL NEWNYM\r\n')
            response = s.recv(1024).decode('utf-8')

            if "250 OK" in response:
                logger.info("egress", "Signal NEWNYM accepted. Circuit rotation initiated.")
                time.sleep(3) # Wait for circuit to establish
                new_ip = self.get_current_egress_ip()
                logger.info("egress", f"New Egress IP Established: {new_ip}")
                self.active = True
                return True
            else:
                logger.error("egress", f"Failed to rotate circuit: {response}")
                return False

        except Exception as e:
            logger.error("egress", f"Egress rotation failed: {e}. Is Tor running with ControlPort enabled?")
            return False

# Initialize singleton for backwards compatibility in routing modules
egress_router = EgressRouter()
