"""ShadowCypher Mission Runner — High-Fidelity Execution Subsystem."""

import subprocess
import threading
import os
from shadowcypher.core.logger import logger
from shadowcypher.core.kairos import kairos

class Runner:
    """Universal task runner with Kairos proactive monitoring."""
    def __init__(self):
        self.active_processes = {}

    def execute_task(self, name, command, callback=None):
        logger.info("runner", f"INITIATING_TASK: {name} >> {command}")
        thread = threading.Thread(target=self._run_process, args=(name, command, callback), daemon=True)
        thread.start()

    def _run_process(self, name, command, callback):
        try:
            # Privilege Escalation Interceptor
            if command.strip().startswith("sudo "):
                logger.info("runner", "Intercepted sudo command, elevating via pkexec for GUI auth.")
                command = "pkexec " + command.strip()[5:]

            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.active_processes[name] = process
            for line in process.stdout:
                if callback: callback(line)
                kairos.analyze(line)
            process.wait()
            if callback: callback(f"\n[COMPLETED: {process.returncode}]")
        except Exception as e:
            if callback: callback(f"[ERROR] TASK_FAILURE: {str(e)}")
        finally:
            self.active_processes.pop(name, None)

runner = Runner()
