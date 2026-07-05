"""
Recon Module — Enterprise Sovereign Build.
High-fidelity cross-platform discovery and service mapping.
"""

import re
import os
import shutil
import subprocess
from shadowcypher.core.module import BaseModule
from shadowcypher.core.mitre import mitre
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
        _stype_tool = {
            "Quick Port Scan": "nmap_port", "Full Port Scan": "nmap_port",
            "OS Detection": "nmap_os", "Service Fingerprint": "nmap_service",
            "Deep Recon": "nmap_deep", "UDP Scan": "nmap_port",
        }
        if on_output:
            tool_key = _stype_tool.get(stype, "nmap_port")
            on_output(f"[RECON] ATT&CK: {mitre.format_tags(mitre.tag(tool_key))}\n")
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
        if on_output:
            on_output(f"[RECON] ATT&CK: {mitre.format_tags(mitre.tag('subdomain_enum'))}\n")
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

    def amass_enum(self, domain, passive=True, on_output=None):
        """Deep subdomain/asset enumeration via OWASP Amass — broader source
        coverage than subfinder (certificate transparency, scraping, APIs,
        recursive brute-forcing). Slower; best for a thorough one-off sweep."""
        require_stealth(on_output=on_output)
        if not validate_target(domain):
            return
        self.log(f"AMASS_ENUM: {domain}")
        if on_output:
            on_output(f"[RECON] ATT&CK: {mitre.format_tags(mitre.tag('amass_enum'))}\n")
        amass = self.get_tool_path("amass")
        if not shutil.which(amass) and not os.path.isabs(amass):
            if on_output:
                on_output("[RECON] amass not found — install: pacman -S amass / apt install amass\n")
            return
        mode = "enum" if passive else "enum -active -brute"
        args = [amass] + mode.split() + ["-d", domain, "-timeout", "10"]
        return self.execute(f"AMASS_{domain}", args, callback=on_output)

    def naabu_scan(self, target, ports=None, top_ports=1000, on_output=None):
        """Ultra-fast SYN port discovery via naabu — a lighter, faster first
        pass than nmap for wide port ranges before running a detailed
        Service Fingerprint scan on whatever comes back open."""
        require_stealth(on_output=on_output)
        if not validate_target(target):
            return
        self.log(f"NAABU_SCAN: {target}")
        if on_output:
            on_output(f"[RECON] ATT&CK: {mitre.format_tags(mitre.tag('naabu_scan'))}\n")
        naabu = self.get_tool_path("naabu")
        if not shutil.which(naabu) and not os.path.isabs(naabu):
            if on_output:
                on_output("[RECON] naabu not found — install: go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest\n")
            return
        args = [naabu, "-host", target, "-silent"]
        args += ["-p", ports] if ports else ["-top-ports", str(top_ports)]
        return self.execute(f"NAABU_{target}", args, callback=on_output)

    def katana_crawl(self, url, depth=3, js_crawl=True, on_output=None):
        """Crawl a web target via katana to enumerate endpoints/JS assets
        before targeted fuzzing (ffuf) or vuln scanning (nuclei)."""
        require_stealth(on_output=on_output)
        if not validate_target(url):
            return
        self.log(f"KATANA_CRAWL: {url}")
        if on_output:
            on_output(f"[RECON] ATT&CK: {mitre.format_tags(mitre.tag('katana_crawl'))}\n")
        katana = self.get_tool_path("katana")
        if not shutil.which(katana) and not os.path.isabs(katana):
            if on_output:
                on_output("[RECON] katana not found — install: go install github.com/projectdiscovery/katana/cmd/katana@latest\n")
            return
        target = url if "://" in url else f"https://{url}"
        args = [katana, "-u", target, "-silent", "-depth", str(depth)]
        if js_crawl:
            args.append("-jc")
        return self.execute(f"KATANA_{url}", args, callback=on_output)

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
