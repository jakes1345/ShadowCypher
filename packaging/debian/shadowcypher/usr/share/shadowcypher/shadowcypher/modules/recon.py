"""
Recon Module — Enterprise Sovereign Build.
High-fidelity cross-platform discovery and service mapping.
"""

import re
import shutil
import subprocess
from shadowcypher.core.module import BaseModule
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.sanitize import validate_target
from shadowcypher.core.stealth import require_stealth


class Recon(BaseModule):
    """The 'Signal' engine of ShadowCypher."""

    def __init__(self):
        super().__init__(module_name="recon")
        self.gateway = self._detect_gateway()

    def _detect_gateway(self):
        try:
            cmd = platform_engine.get_net_info_cmd()
            res = subprocess.check_output(cmd, text=True)
            if platform_engine.IS_LINUX:
                match = re.search(r"default via ([\d\.]+)", res)
            elif platform_engine.IS_MACOS:
                match = re.search(r"default\s+([\d\.]+)", res)
            elif platform_engine.IS_WINDOWS:
                match = re.search(r"0\.0\.0\.0\s+0\.0\.0\.0\s+([\d\.]+)", res)
            else:
                match = None
            return match.group(1) if match else "127.0.0.1"
        except (subprocess.CalledProcessError, OSError, AttributeError):
            return "127.0.0.1"

    # ── Port Scanning ──

    def pulse_target(self, target, stype="Quick Port Scan", on_output=None):
        require_stealth(on_output=on_output)
        if not validate_target(target):
            return
        self.log(f"PULSING_TARGET: {target} [OS={platform_engine.SYSTEM}]")
        nmap = platform_engine.get_cmd("nmap")
        flag_map = {
            "Quick Port Scan":    ["-F", "--open"],
            "Full Port Scan":     ["-p-", "--open"],
            "OS Detection":       ["-O", "--open"],
            "Service Fingerprint": ["-sV", "--open"],
            "Deep Recon":         ["-Pn", "-sV", "-sC", "-O", "--open"],
            "UDP Scan":           ["-sU", "--top-ports", "200"],
        }
        flags = flag_map.get(stype, ["-F", "--open"])
        return self.execute(f"PULSE_{target}", [nmap] + flags + [target], callback=on_output)

    def masscan(self, target, ports="0-65535", rate=1000, on_output=None):
        """Fast port discovery via masscan — finds open ports before nmap detail pass."""
        require_stealth(on_output=on_output)
        if not validate_target(target):
            return
        if not shutil.which("masscan"):
            if on_output:
                on_output("[RECON] masscan not found — falling back to nmap\n")
            return self.pulse_target(target, "Full Port Scan", on_output=on_output)
        self.log(f"MASSCAN: {target} ports={ports} rate={rate}")
        args = ["masscan", target, "-p", ports, "--rate", str(rate), "--open-only"]
        return self.execute(f"MASSCAN_{target}", args, callback=on_output)

    def quick_scan(self, target, on_output=None):
        return self.pulse_target(target, "Quick Port Scan", on_output=on_output)

    def deep_recon(self, target, on_output=None):
        return self.pulse_target(target, "Deep Recon", on_output=on_output)

    # ── Subdomain Enumeration ──

    def subdomain_enum(self, domain, on_output=None):
        """Enumerate subdomains using subfinder (primary) with passive DNS sources."""
        require_stealth(on_output=on_output)
        if not validate_target(domain):
            return
        self.log(f"SUBDOMAIN_ENUM: {domain}")
        if shutil.which("subfinder"):
            args = ["subfinder", "-d", domain, "-silent", "-all"]
            return self.execute(f"SUBFINDER_{domain}", args, callback=on_output)
        # Fallback: host + dig brute
        if on_output:
            on_output("[RECON] subfinder not found — running passive DNS only\n")
        script = (
            f"for sub in www mail ftp api dev staging admin vpn remote; do "
            f"  host $sub.{domain} 2>/dev/null | grep 'has address' && echo $sub.{domain}; "
            f"done"
        )
        return self.execute(f"DNS_BRUTE_{domain}", ["bash", "-c", script], callback=on_output)

    # ── HTTP Probing ──

    def http_probe(self, targets_file_or_domain, on_output=None):
        """Probe hosts/domains for live HTTP/HTTPS services using httpx."""
        require_stealth(on_output=on_output)
        self.log(f"HTTP_PROBE: {targets_file_or_domain}")
        if shutil.which("httpx"):
            args = [
                "httpx", "-silent",
                "-status-code", "-title", "-tech-detect", "-follow-redirects",
                "-no-color",
            ]
            # If it's a file use -l, otherwise -u
            import os
            if os.path.isfile(targets_file_or_domain):
                args += ["-l", targets_file_or_domain]
            else:
                args += ["-u", targets_file_or_domain if "://" in targets_file_or_domain
                         else f"https://{targets_file_or_domain}"]
            return self.execute(f"HTTPX_{targets_file_or_domain}", args, callback=on_output)
        if on_output:
            on_output("[RECON] httpx not found — install: go install github.com/projectdiscovery/httpx/cmd/httpx@latest\n")

    # ── AI-driven ──

    def ai_recon(self, target, on_output=None):
        from shadowcypher.core.hub import hub
        return hub.dispatch_mission(
            f"Map the network surface of {target}. Use OS-specific reconnaissance tools for {platform_engine.SYSTEM}."
        )
