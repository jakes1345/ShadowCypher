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
# Categorized Tactical Toolsets
# ══════════════════════════════════════════════════════════════

TACTICAL_TOOLSETS = {
    "CORE": {
        "list_project_tree": "{\"depth\": 2} — Show project file structure",
        "read_file": "{\"path\": \"relative/path.py\"} — Read a file's contents",
        "search_codebase": "{\"query\": \"search term\"} — Grep the codebase",
        "command": "{\"cmd\": \"whoami\"} — Execute a shell command"
    },
    "RECON": {
        "arp_scan": "{\"interface\": \"eth0\"} — Discover local hosts",
        "port_scan": "{\"target\": \"10.0.0.1\", \"ports\": \"1-1000\"} — TCP connect scan",
        "syn_scan": "{\"target\": \"10.0.0.1\", \"ports\": \"1-1000\"} — SYN stealth scan",
        "os_detect": "{\"target\": \"10.0.0.1\"} — OS fingerprinting",
        "service_fingerprint": "{\"target\": \"10.0.0.1\", \"ports\": \"22,80\"} — Service versioning",
        "nmap_vuln_scan": "{\"target\": \"10.0.0.1\"} — Script-based vuln check"
    },
    "OFFENSIVE": {
        "hydra_brute": "{\"target\": \"10.0.0.1\", \"service\": \"ssh\", ...} — Brute-force login",
        "hashcat_crack": "{\"hash_file\": \"hashes.txt\", ...} — GPU hash cracking",
        "searchsploit": "{\"query\": \"apache\"} — Search Exploit-DB",
        "nuclei_scan": "{\"target\": \"https://ex.com\"} — Template-based scanning",
        "kerberoast": "{\"domain\": \"corp.local\", ...} — AD Kerberoasting",
        "smb_relay": "{\"target_list\": \"targets.txt\"} — SMB relay attack"
    },
    "WIRELESS": {
        "wifi_scan": "{\"interface\": \"wlan0\"} — Scan nearby networks",
        "wifi_deauth": "{\"interface\": \"wlan0\", \"bssid\": \"...\"} — Deauth attack",
        "wifi_capture": "{\"interface\": \"wlan0\", \"bssid\": \"...\"} — Handshake capture"
    },
    "STEALTH": {
        "stealth_fetch": "{\"url\": \"...\", \"level\": 1} — Advanced antibot bypass (L0-L4)",
        "dns_leak_test": "{} — Test for network leaks",
        "firewall_status": "{} — Show tactical firewall rules"
    }
}


class AIOrchestrator:
    def __init__(self):
        self.project_root = str(config.project_root)
        self.conversation_history = []
        self._lock = threading.Lock()
        self._use_agent_routing = True  # Enable Claude Code-style agent fleet

    def _encode_image(self, image_path):
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error("ai", f"Image encoding failed: {e}")
            return None

    def execute_query_async(self, query, images=None, callback=None,
                            on_complete=None, agent_role="commander", intensity=None, history=None):
        mission_id = f"MSN_{int(time.time())}"

        def _mission():
            result = self.execute_query(query, images=images, callback=callback,
                                        agent_role=agent_role, intensity=intensity, history=history)
            if on_complete:
                on_complete(result)

        threading.Thread(target=_mission, daemon=True).start()
        return mission_id

    def queue_mission(self, query: str, agent_role: str = "red_team"):
        """Asynchronously queues a mission for the autonomous hive mind."""
        logger.info("ai", f"MISSION_QUEUED: {query[:64]}...")
        self.execute_query_async(query, agent_role=agent_role)

    def execute_sync(self, query, **kwargs):
        """Synchronous wrapper for execute_query."""
        return self.execute_query(query, **kwargs)

    def execute_query(self, query, images=None, callback=None,
                      agent_role="commander", intensity=None, history=None, model=None):
        """Main autonomous loop — routes through provider system or agent fleet."""
        from shadowcypher.ai.providers import provider_registry
        from shadowcypher.ai.prompts import get_team_prompt
        try:
            from shadowcypher.ai.memory import shadow_memory
        except ImportError:
            shadow_memory = None

        # Agent Fleet routing — if enabled and conditions are right, route through
        # the specialist agent fleet (Claude Code-style delegation)
        if (self._use_agent_routing and not images and not history
                and intensity != "MAX" and not model):
            try:
                from shadowcypher.ai.agents import agent_router
                role_map = {
                    "red_team": "security",
                    "blue_team": "analyst",
                    "devops": "coder",
                    "sisyphus": "coder",
                }
                force = role_map.get(agent_role)
                return agent_router.dispatch(
                    query, callback=callback,
                    force_agent=force,
                    use_ai_routing=(force is None),
                )
            except Exception as e:
                logger.error("orchestrator", f"Agent fleet fallback: {e}")

        provider = provider_registry.active
        if not provider or not provider.is_configured:
            return "ERROR: No AI provider configured. Go to Tactical Swarm AI → \u2699 Settings."

        # Support per-request model override (e.g. for ShadowSentinel bot)
        original_model = provider.model
        if model:
            provider.model = model

        try:
            # 1. PEAK INTEL RECALL (mem0 Integration)
            relevant_memories = shadow_memory.recall(query) if shadow_memory else []
            mem_str = "\n".join([f"- {m['text']}" for m in relevant_memories]) if relevant_memories else "None"

            # 2. Dynamic Tool Injection Strategy
            relevant_tools = {}
            relevant_tools.update(TACTICAL_TOOLSETS["CORE"])
            relevant_tools.update(TACTICAL_TOOLSETS["STEALTH"])
            
            # Context-Aware Swarm: Only inject heavy tools if the role matches
            if "red_team" in agent_role or "offensive" in query.lower():
                relevant_tools.update(TACTICAL_TOOLSETS["OFFENSIVE"])
                relevant_tools.update(TACTICAL_TOOLSETS["RECON"])
            elif "wifi" in query.lower():
                relevant_tools.update(TACTICAL_TOOLSETS["WIRELESS"])
                relevant_tools.update(TACTICAL_TOOLSETS["RECON"])
            
            tool_str = "\n".join([f"- {n}: {d}" for n, d in relevant_tools.items()])

            # 3. Agentic Partnership Prompting
            project_tree = context.list_project_tree(depth=1) # Shallow tree for context
            system_prompt = get_team_prompt(agent_role)
            system_prompt += f"\n\n[ARSENAL_HUD (Categorized Tools)]\n{tool_str}\n"
            system_prompt += f"\n[TACTICAL_WORKSPACE]\n{project_tree}\n"
            system_prompt += f"\n[TACTICAL_MEMORY (RECALL)]\n{mem_str}\n"
            
            system_prompt += """
            MISSION_PROTOCOL:
            - You are SHADOW-AI, the user's personalized tactical partner.
            - Answer questions with 'Big League' clarity. Explain your reasoning professionally.
            - Do NOT just dump scripts. Provide tactical context: Why this tool? What is the risk?
            - Prioritize answering the user's CORE intent. Tool calls are SECONDARY execution steps.
            - Format tool calls meticulously: <TOOL_CALL>{"tool":"name","args":{}}</TOOL_CALL>
            - maintain a cold, professional, and authoritative 'Hacker Elite' tone.
            """

            messages = [{"role": "system", "content": system_prompt}]
            
            # Inject history if provided
            if history:
                for msg in history:
                    messages.append(msg)

            # 3. QUANTUM ESCALATION (Claude-Code dev-full handoff)
            if intensity == "MAX":
                if callback: callback("QUANTUM_ESCALATION: Strategy handed to 88-feature core...")
                from shadowcypher.ai.engine import ai_engine
                return ai_engine.execute_quantum_task(query, on_output=callback)

            # Handle images (base64 in first user message for vision models)
            user_content = query
            if images:
                encoded = [self._encode_image(img) for img in images if img]
                if encoded and any(encoded):
                    user_content += f"\n[ATTACHED_IMAGES: {len([e for e in encoded if e])} file(s)]"
            
            messages.append({"role": "user", "content": user_content})

            for cycle in range(_MAX_CYCLES):
                try:
                    # For multi-turn, use messages format if provider supports it
                    if len(messages) > 2:
                        # Build full conversation as prompt for models that don't support message lists natively
                        conv_text = "\n".join(
                            f"{m['role'].upper()}: {m['content']}" for m in messages
                        )
                        ai_raw = provider.generate(
                            prompt=conv_text,
                            system_prompt=system_prompt, # Keep system prompt in the call
                            max_tokens=4096,
                            temperature=0.1,
                        )
                    else:
                        ai_raw = provider.generate(
                            prompt=messages[-1]["content"],
                            system_prompt=system_prompt,
                            max_tokens=4096,
                            temperature=0.1,
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
        finally:
            provider.model = original_model


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
                    client_mac=args.get("client_mac"),
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
                    username=args.get("user_list", "admin"),
                    passlist=args.get("pass_list"),
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
                    wordlist=args.get("wordlist"),
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
                    args.get("port", ""), protocol=args.get("protocol", "tcp"), on_output=callback
                )
            elif name == "firewall_allow_port":
                from shadowcypher.modules.firewall import Firewall
                return Firewall.ipt_allow_port(
                    args.get("port", ""), protocol=args.get("protocol", "tcp"), on_output=callback
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
                    use_tunnel=args.get("use_tunnel", False)
                )
            elif name == "generate_payload_pdf":
                from shadowcypher.modules.phishing import Phishing
                p = Phishing()
                return p.generate_pdf(args.get("url", ""))

            # ── DEEPHAT APEX ──
            elif name == "forge_weapon":
                from shadowcypher.modules.deephat import deephat
                return deephat.forge_weapon(
                    args.get("target_desc", ""),
                    category=args.get("category", "exploit"),
                    language=args.get("language", "python")
                )
            elif name == "execute_weapon":
                from shadowcypher.modules.deephat import deephat
                return deephat.execute_payload(args.get("filename", ""))

            # ── SYSTEM CONTROL ──
            elif name == "system_audit":
                from shadowcypher.ai.sisyphus import sisyphus
                return sisyphus.audit_report()
            elif name == "terminate_task":
                from shadowcypher.core.runner import runner
                runner.stop_task(args.get("task_id", ""))
                return "TERMINATION_SIGNAL_SENT"

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
                return json.dumps(results, indent=2)
            elif name == "steam_deals":
                from shadowcypher.modules.gaming_osint import GamingAssetScraper
                g = GamingAssetScraper()
                results = g.get_featured_deals()
                return json.dumps(results, indent=2)
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
                self._current_report.add_finding(
                    title=args.get("title", "Untitled"),
                    severity=args.get("severity", "Info"),
                    description=args.get("description", ""),
                    evidence=args.get("evidence", ""),
                    remediation=args.get("remediation", ""),
                    module=args.get("module", "orchestrator"),
                    target=args.get("target", ""),
                )
                return f"Finding added: [{args.get('severity', 'Info')}] {args.get('title', 'Untitled')}"
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
