"""
ShadowCypher AI Orchestrator — Routes through provider system, full tool registry.

The orchestrator is the autonomous brain. It sends queries to the active AI provider,
parses <TOOL_CALL> responses, executes the matching module method, feeds results back,
and loops until the AI produces a final answer or hits max cycles.
"""

import json
import re
import os
import subprocess
import threading
import time
import base64
from datetime import datetime
from shadowcypher.core.logger import logger
from shadowcypher.core.context import context
from shadowcypher.core.config import config

_MAX_CYCLES = 25
_MAX_OUTPUT_CHARS = 8000

# ══════════════════════════════════════════════════════════════
# Tool Definitions — this is what the AI sees and can call
# ══════════════════════════════════════════════════════════════

TOOL_DEFINITIONS = """
Available tools (use <TOOL_CALL>{"tool":"name","args":{...}}</TOOL_CALL> to invoke):

CONTEXT / FILESYSTEM:
- list_project_tree: {"depth": 2} — Show project file structure
- read_file: {"path": "relative/path.py"} — Read a file's contents
- search_codebase: {"query": "search term"} — Grep the codebase
- command: {"cmd": "whoami"} — Execute a shell command

NETWORK / RECON:
- arp_scan: {"interface": "eth0"} — Discover hosts on local network
- port_scan: {"target": "10.0.0.1", "ports": "1-1000"} — TCP connect scan
- syn_scan: {"target": "10.0.0.1", "ports": "1-1000"} — SYN stealth scan (needs root)
- os_detect: {"target": "10.0.0.1"} — OS fingerprinting via nmap
- service_fingerprint: {"target": "10.0.0.1", "ports": "22,80,443"} — Service version scan
- dns_leak_test: {} — Check for DNS leaks
- packet_capture: {"interface": "eth0", "count": 100, "filter": "tcp port 80"} — tcpdump capture

WIRELESS:
- wifi_interfaces: {} — List wireless interfaces
- wifi_monitor_on: {"interface": "wlan0"} — Enable monitor mode
- wifi_monitor_off: {"interface": "wlan0mon"} — Disable monitor mode
- wifi_scan: {"interface": "wlan0mon"} — Scan nearby networks
- wifi_deauth: {"interface": "wlan0mon", "bssid": "AA:BB:CC:DD:EE:FF", "channel": "6"} — Deauth attack
- wifi_capture: {"interface": "wlan0mon", "bssid": "AA:BB:CC:DD:EE:FF", "channel": "6"} — Capture handshake
- wifi_crack: {"capture_file": "capture.cap", "wordlist": "wordlists/common.txt"} — Crack WPA

CREDENTIALS:
- hydra_brute: {"target": "10.0.0.1", "service": "ssh", "user_list": "users.txt", "pass_list": "wordlists/common.txt"} — Brute force login
- hashcat_crack: {"hash_file": "hashes.txt", "hash_type": "0", "wordlist": "wordlists/common.txt"} — GPU hash cracking
- john_crack: {"hash_file": "hashes.txt", "format": "raw-md5"} — CPU hash cracking
- identify_hash: {"hash_string": "5f4dcc3b..."} — Identify hash type

EXPLOIT / VULN:
- searchsploit: {"query": "apache 2.4"} — Search Exploit-DB
- nmap_vuln_scan: {"target": "10.0.0.1"} — Vulnerability scan via nmap scripts
- nuclei_scan: {"target": "https://example.com"} — Template-based vuln scan

OSINT:
- sherlock_search: {"username": "targetuser"} — Search username across 300+ sites
- email_audit: {"email": "user@example.com"} — Check email registration across sites

FIREWALL:
- firewall_status: {} — Show current firewall rules
- firewall_block_ip: {"ip": "1.2.3.4"} — Block an IP address
- firewall_block_port: {"port": "4444", "chain": "INPUT"} — Block a port
- firewall_allow_port: {"port": "80", "chain": "INPUT"} — Allow a port
- firewall_flush: {} — Flush all rules (dangerous!)

AD / LATERAL:
- kerberoast: {"domain": "corp.local", "dc_ip": "10.0.0.1"} — Extract TGS tickets
- smb_relay: {"target_list": "targets.txt", "interface": "eth0"} — SMB relay attack
- crackmapexec: {"target": "10.0.0.1", "protocol": "smb"} — CrackMapExec enum

PHISHING:
- phishing_serve: {"template": "linkedin", "port": 8080} — Serve a phishing page
- generate_payload_pdf: {"url": "http://attacker/payload"} — Create PDF payload

FORENSICS:
- file_metadata: {"path": "/path/to/file"} — Extract file metadata
- file_strings: {"path": "/path/to/file"} — Extract strings from binary
- file_hashes: {"path": "/path/to/file"} — Generate MD5/SHA1/SHA256/SHA512

GAMING OSINT:
- steam_free_games: {} — Find free-to-keep games across all platforms
- steam_deals: {} — Get current Steam featured deals
- steam_search: {"query": "game name"} — Search Steam store

REPORTING:
- add_finding: {"title": "SQLi in login", "severity": "Critical", "description": "...", "evidence": "...", "target": "10.0.0.1"} — Add a finding to the report
- generate_report: {"project": "Client Pentest", "target": "10.0.0.0/24"} — Generate HTML report

STEALTH WEB (anti-bot bypass):
- stealth_fetch: {"url": "https://target.com", "level": null} — Auto-escalating stealth fetch (L0-L4). Set level=1 for TLS impersonation, level=2 for Tor, level=3 for proxy rotation, level=4 for headless browser
- stealth_search: {"query": "search terms"} — Stealth DuckDuckGo search
- web_capabilities: {} — Check available stealth levels (curl_cffi, Tor, proxies, playwright)
- refresh_proxies: {} — Scrape and validate free proxy pool for L3 rotation
"""


class AIOrchestrator:
    def __init__(self):
        self.project_root = str(config.project_root)
        self.conversation_history = []
        self._lock = threading.Lock()

    def _encode_image(self, image_path):
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error("ai", f"Image encoding failed: {e}")
            return None

    def execute_query_async(self, query, images=None, callback=None,
                            on_complete=None, agent_role="commander", intensity=None):
        mission_id = f"MSN_{int(time.time())}"

        def _mission():
            result = self.execute_query(query, images=images, callback=callback,
                                        agent_role=agent_role, intensity=intensity)
            if on_complete:
                on_complete(result)

        threading.Thread(target=_mission, daemon=True).start()
        return mission_id

    def execute_query(self, query, images=None, callback=None,
                      agent_role="commander", intensity=None):
        """Main autonomous loop — routes through provider system."""
        from shadowcypher.ai.providers import provider_registry
        from shadowcypher.ai.prompts import get_team_prompt

        provider = provider_registry.active
        if not provider or not provider.is_configured:
            return "ERROR: No AI provider configured. Go to Tactical Swarm AI → ⚙ Settings."

        # Build system prompt with tool definitions and project context
        project_tree = context.list_project_tree(depth=2)
        system_prompt = get_team_prompt(agent_role)
        system_prompt += f"\n\n{TOOL_DEFINITIONS}\n\n[WORKSPACE]\n{project_tree}\n"
        system_prompt += "\nWhen you need to use a tool, wrap it in <TOOL_CALL>{...}</TOOL_CALL> tags."
        system_prompt += "\nWhen you have the final answer, respond normally without tool calls."

        messages = [{"role": "system", "content": system_prompt}]

        # Handle images (base64 in first user message for vision models)
        user_content = query
        if images:
            encoded = [self._encode_image(img) for img in images if img]
            if encoded and any(encoded):
                user_content += f"\n[ATTACHED_IMAGES: {len([e for e in encoded if e])} file(s)]"
        messages.append({"role": "user", "content": user_content})

        for cycle in range(_MAX_CYCLES):
            try:
                ai_raw = provider.generate(
                    prompt=messages[-1]["content"] if len(messages) == 2 else "",
                    system_prompt=system_prompt if len(messages) == 2 else "",
                    max_tokens=4096,
                    temperature=0.05,
                )

                # For multi-turn, use messages format if provider supports it
                if len(messages) > 2:
                    # Build full conversation as prompt
                    conv_text = "\n".join(
                        f"{m['role'].upper()}: {m['content']}" for m in messages
                    )
                    ai_raw = provider.generate(
                        prompt=conv_text,
                        system_prompt="",
                        max_tokens=4096,
                        temperature=0.05,
                    )

                # Check for tool calls
                tool_match = re.search(r"<TOOL_CALL>(.*?)</TOOL_CALL>", ai_raw, re.DOTALL)
                if tool_match:
                    js = self._fuzzy_json_repair(tool_match.group(1))
                    if js:
                        t_name = js.get("tool", "")
                        t_args = js.get("args", {})
                        if callback:
                            callback(f"[TOOL] Executing: {t_name}")
                        output = self._execute_tool(t_name, t_args, callback)
                        if len(output) > _MAX_OUTPUT_CHARS:
                            output = output[:_MAX_OUTPUT_CHARS] + "\n[TRUNCATED]"
                        messages.append({"role": "assistant", "content": ai_raw})
                        messages.append({"role": "user", "content": f"[TOOL_RESULT]\n{output}"})
                        if callback:
                            callback(f"[TOOL] {t_name} complete ({len(output)} chars)")
                        continue

                # No tool call = final answer
                if callback:
                    callback(ai_raw)
                return ai_raw

            except Exception as e:
                err = f"CRITICAL_EXCEPTION: {e}"
                if callback:
                    callback(err)
                return err

        return "TIMEOUT: Mission reached max cycles."

    def _execute_tool(self, name, args, callback=None):
        """Execute a tool by name. Returns string output."""
        try:
            # ── CONTEXT / FILESYSTEM ──
            if name == "list_project_tree":
                return context.list_project_tree(depth=args.get("depth", 3))
            elif name == "read_file":
                return context.read_file_content(args.get("path", ""))
            elif name == "search_codebase":
                q = args.get("query", "")
                out = subprocess.check_output(
                    ["grep", "-r", "-i", "-n", q, self.project_root],
                    text=True, timeout=30
                )
                return out[:4000]
            elif name == "command":
                from shadowcypher.core.shell import ShadowShell
                res = ShadowShell.execute(args.get("cmd", "echo no command"))
                return res.get("output", "") or res.get("status", "")

            # ── NETWORK / RECON ──
            elif name == "arp_scan":
                from shadowcypher.modules.network import Network
                return Network.arp_scan(args.get("interface", "eth0"), on_output=callback)
            elif name == "port_scan":
                from shadowcypher.modules.network import Network
                return Network.port_scan_tcp_connect(
                    args.get("target", ""), args.get("ports", "1-1000"), on_output=callback
                )
            elif name == "syn_scan":
                from shadowcypher.modules.network import Network
                return Network.port_scan_syn(
                    args.get("target", ""), args.get("ports", "1-1000"), on_output=callback
                )
            elif name == "os_detect":
                from shadowcypher.modules.network import Network
                return Network.network_os_detection(args.get("target", ""), on_output=callback)
            elif name == "service_fingerprint":
                from shadowcypher.modules.network import Network
                return Network.service_fingerprint(
                    args.get("target", ""), args.get("ports", ""), on_output=callback
                )
            elif name == "dns_leak_test":
                from shadowcypher.modules.network import Network
                return Network.dns_leak_test(on_output=callback)
            elif name == "packet_capture":
                from shadowcypher.modules.network import Network
                return Network.packet_capture(
                    args.get("interface", "eth0"),
                    count=args.get("count", 100),
                    bpf_filter=args.get("filter", ""),
                    on_output=callback,
                )
            elif name == "nmap_vuln_scan":
                from shadowcypher.modules.vuln_scanner import VulnScanner
                v = VulnScanner()
                return v.audit_target(args.get("target", ""), on_output=callback)

            # ── WIRELESS ──
            elif name == "wifi_interfaces":
                from shadowcypher.modules.wireless import Wireless
                return Wireless.list_interfaces(on_output=callback)
            elif name == "wifi_monitor_on":
                from shadowcypher.modules.wireless import Wireless
                return Wireless.enable_monitor(args.get("interface", "wlan0"), on_output=callback)
            elif name == "wifi_monitor_off":
                from shadowcypher.modules.wireless import Wireless
                return Wireless.disable_monitor(args.get("interface", "wlan0mon"), on_output=callback)
            elif name == "wifi_scan":
                from shadowcypher.modules.wireless import Wireless
                return Wireless.scan_networks(args.get("interface", "wlan0mon"), on_output=callback)
            elif name == "wifi_deauth":
                from shadowcypher.modules.wireless import Wireless
                return Wireless.deauth(
                    args.get("interface", "wlan0mon"),
                    args.get("bssid", ""),
                    args.get("channel", ""),
                    on_output=callback,
                )
            elif name == "wifi_capture":
                from shadowcypher.modules.wireless import Wireless
                return Wireless.capture_handshake(
                    args.get("interface", "wlan0mon"),
                    args.get("bssid", ""),
                    args.get("channel", ""),
                    on_output=callback,
                )
            elif name == "wifi_crack":
                from shadowcypher.modules.wireless import Wireless
                return Wireless.crack_wpa(
                    args.get("capture_file", ""),
                    args.get("wordlist", ""),
                    on_output=callback,
                )

            # ── CREDENTIALS ──
            elif name == "hydra_brute":
                from shadowcypher.modules.credentials import Credentials
                c = Credentials()
                return c.hydra_attack(
                    target=args.get("target", ""),
                    service=args.get("service", "ssh"),
                    user_list=args.get("user_list", ""),
                    pass_list=args.get("pass_list", ""),
                    on_output=callback,
                )
            elif name == "hashcat_crack":
                from shadowcypher.modules.credentials import Credentials
                c = Credentials()
                return c.hashcat_crack(
                    hash_file=args.get("hash_file", ""),
                    hash_type=args.get("hash_type", "0"),
                    wordlist=args.get("wordlist", ""),
                    on_output=callback,
                )
            elif name == "john_crack":
                from shadowcypher.modules.credentials import Credentials
                c = Credentials()
                return c.john_crack(
                    hash_file=args.get("hash_file", ""),
                    format_type=args.get("format", ""),
                    on_output=callback,
                )
            elif name == "identify_hash":
                from shadowcypher.modules.credentials import Credentials
                c = Credentials()
                return c.identify_hash(args.get("hash_string", ""))

            # ── EXPLOIT / VULN ──
            elif name == "searchsploit":
                from shadowcypher.modules.exploit import Exploit
                e = Exploit()
                return e.search_exploits(args.get("query", ""), on_output=callback)
            elif name == "nuclei_scan":
                from shadowcypher.modules.vuln_scanner import VulnScanner
                v = VulnScanner()
                return v.nuclei_scan(args.get("target", ""), on_output=callback)

            # ── OSINT ──
            elif name == "sherlock_search":
                from shadowcypher.modules.osint_deep import DeepOSINT
                return DeepOSINT.social_footprint(args.get("username", ""), on_output=callback)
            elif name == "email_audit":
                from shadowcypher.modules.osint_deep import DeepOSINT
                return DeepOSINT.email_audit(args.get("email", ""), on_output=callback)

            # ── FIREWALL ──
            elif name == "firewall_status":
                from shadowcypher.modules.firewall import Firewall
                return Firewall.ipt_save(on_output=callback)
            elif name == "firewall_block_ip":
                from shadowcypher.modules.firewall import Firewall
                return Firewall.ipt_block_ip(args.get("ip", ""), on_output=callback)
            elif name == "firewall_block_port":
                from shadowcypher.modules.firewall import Firewall
                return Firewall.ipt_block_port(
                    args.get("port", ""), args.get("chain", "INPUT"), on_output=callback
                )
            elif name == "firewall_allow_port":
                from shadowcypher.modules.firewall import Firewall
                return Firewall.ipt_allow_port(
                    args.get("port", ""), args.get("chain", "INPUT"), on_output=callback
                )
            elif name == "firewall_flush":
                from shadowcypher.modules.firewall import Firewall
                return Firewall.ipt_flush(on_output=callback)

            # ── AD / LATERAL ──
            elif name == "kerberoast":
                from shadowcypher.modules.ad_pivot import ADPivot
                return ADPivot.kerberoast(
                    args.get("domain", ""), args.get("dc_ip", ""), on_output=callback
                )
            elif name == "smb_relay":
                from shadowcypher.modules.ad_pivot import ADPivot
                return ADPivot.smb_relay_start(
                    args.get("target_list", ""), args.get("interface", "eth0"), on_output=callback
                )
            elif name == "crackmapexec":
                from shadowcypher.modules.ad_pivot import ADPivot
                return ADPivot.crackmapexec_scan(
                    args.get("target", ""),
                    protocol=args.get("protocol", "smb"),
                    domain=args.get("domain"),
                    user=args.get("user"),
                    password=args.get("password"),
                    on_output=callback,
                )

            # ── PHISHING ──
            elif name == "phishing_serve":
                from shadowcypher.modules.phishing import Phishing
                p = Phishing()
                return p.start_phishing_server(
                    args.get("template", "generic"),
                    port=args.get("port", 8080),
                    on_output=callback,
                )
            elif name == "generate_payload_pdf":
                from shadowcypher.modules.phishing import Phishing
                p = Phishing()
                return p.generate_pdf(
                    args.get("url", ""), on_output=callback
                )

            # ── FORENSICS ──
            elif name == "file_metadata":
                from shadowcypher.modules.forensics import Forensics
                f = Forensics()
                return f.extract_metadata(args.get("path", ""), on_output=callback)
            elif name == "file_strings":
                from shadowcypher.modules.forensics import Forensics
                f = Forensics()
                return f.extract_strings(args.get("path", ""), on_output=callback)
            elif name == "file_hashes":
                from shadowcypher.modules.forensics import Forensics
                f = Forensics()
                return f.generate_hashes(args.get("path", ""), on_output=callback)

            # ── GAMING OSINT ──
            elif name == "steam_free_games":
                from shadowcypher.modules.gaming_osint import GamingAssetScraper
                g = GamingAssetScraper()
                results = g.fetch_global_assets()
                return json.dumps(results[:20], indent=2)
            elif name == "steam_deals":
                from shadowcypher.modules.gaming_osint import GamingAssetScraper
                g = GamingAssetScraper()
                results = g.get_featured_deals()
                return json.dumps(results[:15], indent=2)
            elif name == "steam_search":
                from shadowcypher.modules.gaming_osint import GamingAssetScraper
                g = GamingAssetScraper()
                results = g.search_store(args.get("query", ""))
                return json.dumps(results[:10], indent=2)

            # ── REPORTING ──
            elif name == "add_finding":
                from shadowcypher.core.reporting import Finding, Report
                if not hasattr(self, "_current_report"):
                    self._current_report = Report(
                        target=args.get("target", ""),
                        project_name=args.get("project", "ShadowCypher Assessment"),
                    )
                finding = Finding(
                    title=args.get("title", "Untitled"),
                    severity=args.get("severity", "Info"),
                    description=args.get("description", ""),
                    evidence=args.get("evidence", ""),
                    remediation=args.get("remediation", ""),
                    module=args.get("module", "orchestrator"),
                    target=args.get("target", ""),
                )
                self._current_report.add_finding(finding)
                return f"Finding added: [{finding.severity}] {finding.title}"
            elif name == "generate_report":
                from shadowcypher.core.reporting import Report
                if not hasattr(self, "_current_report"):
                    return "No findings collected yet. Use add_finding first."
                path = self._current_report.generate_html()
                return f"Report generated: {path}"

            # ── STEALTH WEB ──
            elif name == "stealth_fetch":
                from shadowcypher.core.web import stealth_web
                level = args.get("level")
                html = stealth_web.fetch(
                    args.get("url", ""),
                    stealth_level=level,
                    on_status=callback,
                )
                if html:
                    return stealth_web.extract_text(html)[:_MAX_OUTPUT_CHARS]
                return "FETCH_FAILED: All stealth levels exhausted."
            elif name == "stealth_search":
                from shadowcypher.core.web import stealth_web
                import requests as _req
                q = args.get("query", "")
                url = f"https://html.duckduckgo.com/html/?q={_req.utils.quote(q)}"
                html = stealth_web.fetch(url, stealth_level=0)
                if html:
                    return stealth_web.extract_text(html)[:5000]
                return "SEARCH_FAILED"
            elif name == "web_capabilities":
                from shadowcypher.core.web import stealth_web
                return json.dumps(stealth_web.get_capabilities(), indent=2)
            elif name == "refresh_proxies":
                from shadowcypher.core.web import stealth_web
                stealth_web.refresh_proxy_pool(on_status=callback)
                return f"Proxy pool: {len(stealth_web._proxy_pool)} valid proxies"

            else:
                return f"ERROR: Unknown tool '{name}'. Check available tools."

        except Exception as e:
            logger.error("orchestrator", f"Tool {name} failed: {e}")
            return f"TOOL_ERROR: {name} → {e}"

    def _fuzzy_json_repair(self, raw):
        try:
            clean = re.sub(r"^```(json)?\n?|```$", "", raw, flags=re.MULTILINE).strip()
            return json.loads(clean)
        except Exception:
            return None
