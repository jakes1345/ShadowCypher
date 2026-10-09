"""
ShadowScript — pipeline DSL.

Parses arrow-chained directives like:

    TARGET '10.0.0.1' -> SCAN(1-1000) -> SHADOW(summarize findings)

Each directive maps to a real module call.
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

        return {"ok": False, "msg": f"Unknown directive: {cmd}"}

    @staticmethod
    def _which(name: str) -> bool:
        import shutil
        return bool(shutil.which(name))


orchestrator_script = ShadowScript()
