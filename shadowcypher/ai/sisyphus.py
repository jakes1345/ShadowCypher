"""
ShadowCypher Sisyphus Protocol — The Self-Healing Infinite Loop.
Monitors the codebase for regressions, bugs, and "bullshit" code, then auto-fixes them.
"""

import os
import time
import threading
import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.ai.orchestrator import AIOrchestrator

class Sisyphus:
    """The 'Self-Healing' engine. An eternal loop of project refinement."""

    def __init__(self, project_root="/home/jack/ShadowCypher"):
        self.project_root = project_root
        self.orchestrator = AIOrchestrator()
        self._active = False
        self._thread = None

    def start(self):
        """Initiate the Sisyphus loop in a background thread."""
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("sisyphus", "SISYPHUS_PROTOCOL: ACTIVE. The hill is being climbed.")

    def stop(self):
        """Halt the Sisyphus loop."""
        self._active = False
        logger.info("sisyphus", "SISYPHUS_PROTOCOL: HALTED.")

    def _run_loop(self):
        """The eternal loop of analysis and repair."""
        while self._active:
            try:
                # 1. Audit for "bullshit" (pass, TODO, NotImplemented)
                logger.info("sisyphus", "AUDITING_CODEBASE_FOR_WEAKNESSES...")
                weaknesses = self._find_weaknesses()
                
                if not weaknesses:
                    logger.info("sisyphus", "ZERO_WEAKNESSES_DETECTED. Resting for 60s.")
                    time.sleep(60)
                    continue

                for file_path, issue in weaknesses[:3]: # Fix 3 at a time to prevent token burn
                    if not self._active: break
                    
                    logger.warn("sisyphus", f"REPAIRING_{file_path}: {issue}")
                    self._repair_file(file_path, issue)
                
                time.sleep(10) # Cooldown between repair sprints
            except Exception as e:
                logger.error("sisyphus", f"SISYPHUS_FAULT: {e}")
                time.sleep(30)

    def _find_weaknesses(self):
        """Scan for technical debt and placeholders."""
        findings = []
        patterns = ["pass", "TODO", "NotImplementedError", "FIXME"]
        
        for root, dirs, files in os.walk(self.project_root):
            if "venv" in root or ".git" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    with open(path, 'r') as file:
                        lines = file.readlines()
                        for i, line in enumerate(lines):
                            for p in patterns:
                                if p in line:
                                    findings.append((path, f"Line {i+1}: Placeholder '{p}' detected."))
        return findings

    def _repair_file(self, file_path, issue):
        """Invoke the Orchestrator to solve the specific code issue."""
        with open(file_path, 'r') as f:
            content = f.read()

        query = f"""
I have found a technical debt issue in '{file_path}': {issue}
The current content is:
---
{content}
---
Please rewrite this file and provide a FULL WORKING IMPLEMENTATION that removes the placeholder and solves the logic. 
Output ONLY the tool call 'write_file' to save the fixed code.
"""
        # Execute the repair mission
        self.orchestrator.execute_query(query, callback=self._log_fix)

    def _log_fix(self, msg):
        if "[TENGU]" in msg:
            logger.info("sisyphus", f"REPAIR_STATUS: {msg}")

# Global Instance
sisyphus = Sisyphus()
