import json
import re
import os
import requests
import subprocess
import threading
import time
import base64
from datetime import datetime
from shadowcypher.core.logger import logger
from shadowcypher.core.context import context

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
        self._lock = threading.Lock()
        
    def _encode_image(self, image_path):
        """Encodes local image to base64 for Ollama vision."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error("ai", f"Image encoding failed: {e}")
            return None

    def execute_query_async(self, query, images=None, callback=None, on_complete=None, agent_role="commander", intensity=None):
        """Tactical Non-Blocking Mission Dispatch with Vision Support."""
        mission_id = f"MSN_{int(time.time())}"
        def _mission_wrapper():
            result = self.execute_query(query, images=images, callback=callback, agent_role=agent_role, intensity=intensity)
            if on_complete: on_complete(result)
        threading.Thread(target=_mission_wrapper, daemon=True).start()
        return mission_id

    def execute_query(self, query, images=None, callback=None, agent_role="commander", intensity=None):
        self.conversation_history = [] 
        
        # Injected project tree for baseline context
        project_tree = context.list_project_tree(depth=2)
        
        from shadowcypher.ai.prompts import get_team_prompt
        system_prompt = get_team_prompt(agent_role)
        
        system_prompt += f"\n\n[WORKSPACE_CONTEXT]\n{project_tree}\n"
        
        conversation = f"SYSTEM: {system_prompt}\nUSER: {query}\n"
        b64_images = []
        if images:
            for img in images:
                encoded = self._encode_image(img)
                if encoded: b64_images.append(encoded)

        for cycle in range(_MAX_CYCLES):
            payload = {
                "model": self.model,
                "prompt": conversation,
                "images": b64_images if cycle == 0 else [], # Only send images in first turn for efficiency
                "stream": False,
                "options": {"temperature": 0.05, "num_ctx": 16384, "stop": ["USER:", "[TOOL_RESULT]"]}
            }
            
            try:
                resp = requests.post(self.base_url, json=payload, timeout=180)
                ai_raw = resp.json().get("response", "")
                
                tool_match = re.search(r"<TOOL_CALL>(.*?)</TOOL_CALL>", ai_raw, re.DOTALL)
                if tool_match:
                    js = self._fuzzy_json_repair(tool_match.group(1))
                    if js:
                        t_name, t_args = js.get("tool"), js.get("args", {})
                        if callback: callback(f"[TENGU] Executing Tool: {t_name}")
                        output = self._execute_tool(t_name, t_args, callback, intensity=intensity)
                        conversation += f"AI: {ai_raw}\n[TOOL_RESULT]: {output}\n"
                        continue
                
                return ai_raw
            except Exception as e:
                return f"CRITICAL_EXCEPTION: {str(e)}"
        
        return "TIMEOUT: Mission reached max cycles."

    def _execute_tool(self, name, args, callback=None):
        try:
            # 1. SPECIAL CASE: DELEGATION TO AUTO-ORCHESTRATOR
            if name == "run_masterclass" or args.get("intensity") == "MAX":
                from shadowcypher.ai.auto_orchestrator import auto_orch
                if callback: callback("[SYSTEM] ESCALATING_TO_METACHAIN_ENGINE...")
                auto_orch.execute_mission(
                    args.get("target") or args.get("query"),
                    callback=callback,
                    on_complete=lambda res: callback(f"[METACHAIN_COMPLETE] {res}")
                )
                return "ESCALATION_SUCCESS: Mission handed over to MetaChain Autonomous Loop."

            # 2. CORE CONTEXT TOOLS (Grouping!)
            if name == "list_project_tree":
                return context.list_project_tree(depth=args.get("depth", 3))
            elif name == "read_file":
                return context.read_file_content(args.get("path"))
            elif name == "search_codebase":
                q = args.get("query", "")
                return subprocess.check_output(["grep", "-r", "-i", q, self.project_root], text=True)[:4000]
            elif name == "command":
                from shadowcypher.core.shell import ShadowShell
                res = ShadowShell.execute(args.get("cmd"))
                return res.get("output", "SUCCESS")
                
            # 3. OFFENSIVE SUITE TOOLS
            elif name == "nmap_scan":
                from shadowcypher.modules.recon import Recon
                return Recon.pulse_target(args.get("target"), args.get("type", "Quick Port Scan"), on_output=callback)
            elif name == "nuclei_scan":
                from shadowcypher.modules.web_attacks import WebAttacks
                return WebAttacks.nuclei_scan(args.get("target"), on_output=callback)
            
            return f"ERROR: Tool '{name}' not found."
        except Exception as e:
            return f"TOOL_ERROR: {str(e)}"

    def _fuzzy_json_repair(self, raw):
        try:
            clean = re.sub(r'^```(json)?\n?|```$', '', raw, flags=re.MULTILINE).strip()
            return json.loads(clean)
        except: return None
"
