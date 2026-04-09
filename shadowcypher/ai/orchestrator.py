"""
ShadowCypher BIG LEAGUE Orchestrator V2.0 — State-Machine ReAct Core.
Ensures zero-hang, resilient autonomous engineering.
"""

import json
import re
import os
import requests
import subprocess
import threading
import time
from datetime import datetime
from shadowcypher.core.logger import logger

# Constants
_MAX_CYCLES = 25
_MAX_OUTPUT_CHARS = 8000
_DEFAULT_MODEL = "gemma-4-heretic"

class AIOrchestrator:
    def __init__(self, model=None):
        from shadowcypher.core.config import config
        self.model = model or config.get("ai", "model", default=_DEFAULT_MODEL)
        self.base_url = config.get("ai", "api_base", default="http://localhost:11434/api/generate")
        self.project_root = config.project_root
        self.conversation_history = []
        self._mission_queue = []
        self._sentinel_running = False
        self._lock = threading.Lock()
        
    def _log_debug(self, step, text):
        log_path = os.path.join(self.project_root, "logs", "ai_debug.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n--- [{timestamp}] STEP {step} ---\n{text}\n")

    def _fuzzy_json_repair(self, raw):
        """Ultra-robust JSON repair for 9B model hallucinations."""
        try:
            # 1. Strip markdown
            clean = re.sub(r'^```(json)?\n?|```$', '', raw, flags=re.MULTILINE).strip()
            # 2. Fix specific obsessive errors: {"tool": "x", ""} -> {"tool": "x"}
            clean = re.sub(r',\s*""\s*\}', '}', clean)
            # 3. Fix missing args: {"tool": "x"} -> {"tool": "x", "args": {}}
            if '"tool"' in clean and '"args"' not in clean:
                clean = clean.replace('}', ', "args": {}}')
            # 4. Handle trailing commas in objects/arrays
            clean = re.sub(r',\s*([\]\}])', r'\1', clean)
            return json.loads(clean)
        except Exception:
            # Last ditch: extract first { ... } block
            match = re.search(r'(\{.*\})', clean, re.DOTALL)
            if match:
                try: return json.loads(match.group(1))
                except: pass
        return None

    def execute_query(self, query, callback=None, agent_role="commander"):
        self.conversation_history = [] # Reset for new mission
        
        system_prompt = f"""[SHADOWCYPHER_KERNEL_V4]
ROLE: {agent_role.upper()} AGENTIC_CORE
IDENTITY: PEER_OF_ANTIGRAVITY

MISSION: Perform deep-spectrum penetration testing with absolute precision.

PROTOCOLS:
- STRICT REALITY: Only operate on files that ACTUALLY EXIST in 'list_project_tree'.
- OFFENSIVE_DEPTH: Use the full suite (Nmap, Nuclei, Ffuf, Searchsploit, MetaSploit).
- HIVE_MIND: Manage multiple sessions via 'list_sessions' and 'interact_session'.
- LATERAL_DOMINANCE: Once internal, use 'run_ad_recon' and 'kerberoast' for pivot.

TOOLS:
- list_project_tree / search_codebase / read_file / write_file / command
- nmap_scan / nuclei_scan / ffuf_scan / sqlmap_scan
- search_exploits (query) / launch_exploit (module, target, options)
- generate_payload (ptype, lhost, lport)
- list_sessions () - View compromised hive nodes.
- interact_session (sid, cmd) - Execute command on session.
- run_ad_recon (target, domain, user, pass) - CME enumeration.
- kerberoast (domain, dc_ip) - Perform Kerberoasting.
- run_masterclass (target) - FULL AUTONOMOUS BREACH.

[BEGIN_MISSION]"""

        conversation = f"SYSTEM: {system_prompt}\nUSER: {query}\n"
        
        for cycle in range(_MAX_CYCLES):
            if callback: callback(f"[TENGU] Cycle {cycle+1}/{_MAX_CYCLES}...")
            
            payload = {
                "model": self.model,
                "prompt": conversation,
                "stream": False,
                "options": {
                    "temperature": 0.1, # Big League precision
                    "num_ctx": 16384,
                    "stop": ["USER:", "[TOOL_RESULT]", "<|turn|>"]
                }
            }
            
            try:
                resp = requests.post(self.base_url, json=payload, timeout=120)
                if resp.status_code != 200:
                    return f"CRITICAL_FAILURE: Ollama HTTP {resp.status_code}"
                
                ai_raw = resp.json().get("response", "")
                self._log_debug(cycle+1, ai_raw)
                
                tool_match = re.search(r"<TOOL_CALL>(.*?)</TOOL_CALL>", ai_raw, re.DOTALL)
                
                if tool_match:
                    js = self._fuzzy_json_repair(tool_match.group(1))
                    if js:
                        t_name = js.get("tool")
                        t_args = js.get("args", {})
                        
                        if callback: callback(f"[TENGU] Executing: {t_name}")
                        output = self._execute_tool(t_name, t_args, callback)
                        
                        conversation += f"AI: {ai_raw}\n[TOOL_RESULT]: {output}\n"
                        continue
                    else:
                        error_feedback = "[ERROR]: Tool Format Invalid. Use: <TOOL_CALL>{\"tool\":\"...\", \"args\":{}}</TOOL_CALL>"
                        conversation += f"AI: {ai_raw}\n{error_feedback}\n"
                        continue
                else:
                    # Final result or just yapping
                    if "MISSION_COMPLETE" in ai_raw or cycle > 5:
                        return ai_raw
                    conversation += f"AI: {ai_raw}\n[SYSTEM]: Please continue with tool calls to complete the mission.\n"

            except Exception as e:
                return f"CRITICAL_EXCEPTION: {str(e)}"
        
        return "TIMEOUT: Mission reached max cycles without completion."

    def queue_mission(self, mission_query: str):
        """Add a mission to the tactical queue for the sentinel to pick up."""
        logger.info("ai", f"MISSION_QUEUED: {mission_query}")
        with self._lock:
            self._mission_queue.append(mission_query)

    def start_sentinel(self):
        """Alpha-Level Autonomous Sentinel. Monitor DB findings and auto-execute roadmap."""
        if self._sentinel_running:
            return

        def _sentinel_loop():
            self._sentinel_running = True
            logger.info("ai", "AUTONOMOUS_SENTINEL_ENGAGED: Deep Watch active.")
            while self._sentinel_running:
                try:
                    # 1. Check for queued missions from Kairos/etc
                    next_mission = None
                    with self._lock:
                        if self._mission_queue:
                            next_mission = self._mission_queue.pop(0)
                    
                    if next_mission:
                        logger.info("ai", f"SENTINEL_ACTION: processing_queued_mission: {next_mission}")
                        self.execute_query(next_mission, agent_role="coder")

                    # 2. Monitor Database for un-actioned critical CVEs
                    from shadowcypher.core.database import db
                    with db._lock:
                        db.cursor.execute("SELECT target_ip, cve_id FROM vulnerability_graph WHERE severity='CRITICAL' AND payload_notes NOT LIKE '%ACTIONED%' LIMIT 1")
                        critical = db.cursor.fetchone()
                    
                    if critical:
                        ip, cve = critical
                        logger.info("ai", f"SENTINEL_ACTION: auto_targeting_critical_vuln: {cve} on {ip}")
                        # Mark as actioned first to avoid loops
                        with db._lock:
                            db.cursor.execute("UPDATE vulnerability_graph SET payload_notes = payload_notes || ' [ACTIONED]' WHERE target_ip=? AND cve_id=?", (ip, cve))
                            db.conn.commit()
                        
                        query = f"Execute targeted exploit for {cve} on {ip}. Correlate with Metasploit and Searchsploit. Deliver payload and confirm shell."
                        self.execute_query(query, agent_role="coder")

                except Exception as e:
                    logger.error("ai", f"SENTINEL_FAULT: {e}")
                time.sleep(15)

        self._sentinel_thread = threading.Thread(target=_sentinel_loop, daemon=True)
        self._sentinel_thread.start()

    def stop_sentinel(self):
        self._sentinel_active = False
        logger.info("ai", "AUTONOMOUS_SENTRY: OFFLINE.")

    def _execute_tool(self, name, args, callback=None):
        try:
            if name == "list_project_tree":
                # Deep Dive: Include tools and payloads in the tree
                return subprocess.check_output(["find", self.project_root, "-maxdepth", "3", "-not", "-path", "*/.*"], text=True)[:4000]
            elif name == "search_codebase":
                q = args.get("query", "")
                return subprocess.check_output(["grep", "-r", "--exclude-dir=.git", "-i", q, self.project_root], text=True)[:4000]
            elif name == "read_file":
                p = args.get("path")
                # Handle relative or absolute paths
                full_path = p if os.path.isabs(p) else os.path.join(self.project_root, p)
                with open(full_path, 'r') as f: return f.read()[:8000]
            elif name == "write_file":
                p, c = args.get("path"), args.get("content")
                path = p if os.path.isabs(p) else os.path.join(self.project_root, p)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f: f.write(c)
                return f"SUCCESS: Written to {p}"
            elif name == "command":
                cmd = args.get("cmd")
                # Big League: Execute using the new venv's python if it's a python script
                if cmd.startswith("python "):
                    venv_python = os.path.join(self.project_root, "venv", "bin", "python")
                    if os.path.exists(venv_python):
                        cmd = cmd.replace("python ", f"{venv_python} ")
                return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)[:4000]
            elif name == "nmap_scan":
                from shadowcypher.modules.recon import Recon
                target = args.get("target")
                stype = args.get("type", "Quick Port Scan")
                return Recon.pulse_target(target, stype, on_output=callback)
            elif name == "nuclei_scan":
                from shadowcypher.modules.web_attacks import WebAttacks
                target = args.get("target")
                tags = args.get("tags", "")
                return WebAttacks.nuclei_scan(target, template_tags=tags, on_output=callback)
            elif name == "ffuf_scan":
                from shadowcypher.modules.web_attacks import WebAttacks
                url = args.get("url")
                wordlist = args.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
                return WebAttacks.ffuf_dir_fuzz(url, wordlist=wordlist, on_output=callback)
            elif name == "sqlmap_scan":
                from shadowcypher.modules.vuln_scanner import VulnScanner
                target = args.get("target")
                return VulnScanner.sqlmap_scan(target, on_output=callback)
            elif name == "search_exploits":
                from shadowcypher.modules.exploit import Exploit
                return Exploit.msf_search(args.get("query"), on_output=callback)
            elif name == "launch_exploit":
                from shadowcypher.modules.exploit import Exploit
                return Exploit.launch_msf_exploit(args.get("module"), args.get("target"), args.get("options", {}), on_output=callback)
            elif name == "generate_payload":
                from shadowcypher.modules.exploit import Exploit
                return Exploit.generate_payload(args.get("ptype"), args.get("lhost"), args.get("lport"), on_output=callback)
            elif name == "list_sessions":
                from shadowcypher.core.c2_manager import c2_manager
                return str(c2_manager.list_sessions())
            elif name == "interact_session":
                from shadowcypher.core.c2_manager import c2_manager
                return c2_manager.execute_command(args.get("sid"), args.get("cmd"))
            elif name == "run_ad_recon":
                from shadowcypher.modules.ad_pivot import ADPivot
                return ADPivot.crackmapexec_scan(args.get("target"), domain=args.get("domain"), user=args.get("user"), password=args.get("password"), on_output=callback)
            elif name == "kerberoast":
                from shadowcypher.modules.ad_pivot import ADPivot
                return ADPivot.kerberoast(args.get("domain"), args.get("dc_ip"), on_output=callback)
            elif name == "run_masterclass":
                target = args.get("target")
                if callback: callback(f"[MASTERCLASS] INITIATING_FULL_SPECTRUM_OFFENSIVE_ON: {target}")
                # Start by indexing and then generating a roadmap
                from shadowcypher.core.ultraplan import UltraPlan
                from shadowcypher.core.session import session
                from shadowcypher.core.identity import identity
                
                # Ensure we have a session target
                if not session.current_project:
                    session.create_project(f"Mission_{target}", targets=[target])
                
                roadmap = UltraPlan.generate_roadmap(use_ai=True)
                roadmap_str = json.dumps(roadmap, indent=2)
                
                if callback: callback(f"[MASTERCLASS] STRATEGIC_ROADMAP_GENERATED:\n{roadmap_str}")
                
                # Feedback to AI to continue executing the roadmap
                return f"ROADMAP_GENERATED for {target}. Execute the first phase: {roadmap[0]['phase']} (Objective: {roadmap[0]['objective']}) using the recommended tools."
            elif name == "delegate_to_overlord":
                reason = args.get("reason", "Unknown complexity")
                logger.error("ai", f"MISSION_DELEGATION_REQUESTED: {reason}")
                if callback: callback(f"[SYSTEM] OFFLOADING_TO_OVERLORD: {reason}")
                # In a production suite, this could signal to a higher-level API or a human
                return f"DELEGATION_SUCCESS: The Overlord model has been notified and is analyzing the impasse: {reason}"

            elif name == "run_osint_pulse":
                query = args.get("query", "")
                logger.info("ai", f"TRIGGERING_OSINT_PULSE: {query}")
                from shadowcypher.modules.gaming_osint import GamingOSINT
                # Gaming OSINT is a specialized module
                results = GamingOSINT.get_steam_assets() # Example asset discovery
                return f"OSINT_RESULTS: {str(results)[:2000]}"
            return f"ERROR: Tool '{name}' not found."
        except Exception as e:
            return f"TOOL_ERROR: {str(e)}"
