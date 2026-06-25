"""
ShadowScript — tactical pipeline DSL.

Parses arrow-chained directives like:

    TARGET '10.0.0.1' -> SCAN(1-1000) -> SHADOW(plan an exploit) -> EXPLOIT()

Each directive maps to a real module call. Stubs return honest errors so
callers know a directive is unimplemented instead of getting a silent "ok".
"""

import re
import threading
from shadowcypher.core.logger import logger


class ShadowScript:
    VERSION = "0.3"

    def __init__(self):
        self.context: dict = {}

    def execute(self, script_text: str, callback=None) -> bool:
        logger.info("shadowscript", f"EXECUTING_SCRIPT_BLOCK: {len(script_text)} chars")

        for line in script_text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for step in (s.strip() for s in line.split("->")):
                if not step:
                    continue
                res = self._run_step(step, callback)
                if not res.get("ok"):
                    err = f"SHADOWSCRIPT_FAULT: {res.get('msg')}"
                    if callback:
                        callback(err)
                    logger.error("shadowscript", err)
                    return False
        return True

    def _run_step(self, step_raw: str, callback=None) -> dict:
        match = re.search(r"([A-Z_]+)\((.*?)\)", step_raw)
        if not match:
            if step_raw.startswith("TARGET"):
                target = step_raw.split(None, 1)[1].strip("'\"")
                self.context["target"] = target
                if callback:
                    callback(f"TARGET_SET: {target}")
                return {"ok": True}
            return {"ok": False, "msg": f"Syntax error in step: {step_raw}"}

        cmd = match.group(1)
        args_raw = match.group(2)
        target = self.context.get("target")

        if cmd == "SCAN":
            if not target:
                return {"ok": False, "msg": "SCAN requires a prior TARGET directive"}
            from shadowcypher.modules.network import Network
            if callback:
                callback(f"scanning → {target}")
            threading.Thread(
                target=Network.port_scan_tcp_connect,
                args=(target, args_raw or "1-1000", callback),
                daemon=True,
            ).start()
            return {"ok": True}

        if cmd == "SWARM":
            from shadowcypher.core.ghost import ghost_orchestrator
            nodes = ghost_orchestrator.get_active_nodes()
            if not nodes:
                msg = "SWARM_SKIPPED: no Shadow Nodes currently linked"
                if callback:
                    callback(msg)
                return {"ok": True}
            ok = 0
            for node in nodes:
                if ghost_orchestrator.execute(node["fp"], args_raw):
                    ok += 1
            if callback:
                callback(f"SWARM_BROADCAST: {ok}/{len(nodes)} nodes accepted '{args_raw}'")
            return {"ok": True}

        if cmd == "SHADOW":
            from shadowcypher.ai.orchestrator import orchestrator
            prompt = args_raw.strip("'\"") or f"Plan a next-step action for target {target}."
            if callback:
                callback(f"SYNTHESIZING_AI_PAYLOAD: {prompt[:80]}")
            try:
                result = orchestrator.execute_query_sync(prompt)
            except Exception as e:
                return {"ok": False, "msg": f"SHADOW call failed: {e}"}
            self.context["last_ai"] = result
            if callback:
                for line in result.splitlines():
                    callback(line)
            return {"ok": True}

        if cmd == "EXPLOIT":
            if not target:
                return {"ok": False, "msg": "EXPLOIT requires a prior TARGET directive"}
            from shadowcypher.core.config import config
            import subprocess
            service = args_raw.strip("'\"") or target
            searchsploit = config.get_tool_path("searchsploit")
            if not searchsploit or searchsploit == "searchsploit" and not self._which("searchsploit"):
                return {"ok": False, "msg": "EXPLOIT requires searchsploit in PATH"}
            if callback:
                callback(f"SEARCHING_EXPLOITS: {service}")
            try:
                result = subprocess.run(
                    [searchsploit, "--color", "--id", service],
                    capture_output=True, text=True, timeout=30,
                )
            except (subprocess.TimeoutExpired, OSError) as e:
                return {"ok": False, "msg": f"searchsploit failed: {e}"}
            if callback:
                for line in (result.stdout or "").splitlines():
                    callback(line)
            return {"ok": True}

        if cmd == "GHOST_PERSIST":
            import os
            from shadowcypher.modules.craft_factory import CraftFactory
            lhost, sep, lport = args_raw.partition(":")
            if not lhost or not sep:
                return {"ok": False, "msg": "GHOST_PERSIST requires 'lhost:lport' args"}
            try:
                stager_b64 = CraftFactory.generate_stealth_c2_python(lhost, int(lport))
            except Exception as e:
                return {"ok": False, "msg": f"GHOST_PERSIST failed: {e}"}
            os.makedirs("payloads", exist_ok=True)
            out_path = os.path.join("payloads", f"ghost_c2_{lhost.replace('.', '_')}_{lport}.b64")
            with open(out_path, "w") as f:
                f.write(stager_b64)
            if callback:
                callback(f"STAGER_WRITTEN: {out_path}")
            self.context["last_stager"] = out_path
            return {"ok": True}

        return {"ok": False, "msg": f"Unknown directive: {cmd}"}

    @staticmethod
    def _which(name: str) -> bool:
        import shutil
        return bool(shutil.which(name))


orchestrator_script = ShadowScript()
