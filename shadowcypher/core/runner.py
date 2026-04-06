"""ShadowCypher Mission Runner — High-Fidelity Execution Subsystem."""

import subprocess
import shlex
import threading
import os
from shadowcypher.core.logger import logger
from shadowcypher.core.kairos import kairos

_PROCESS_TIMEOUT = 600  # 10 minute max per task


class Runner:
    """Universal task runner with Kairos proactive monitoring."""
    def __init__(self):
        self.active_processes = {}

    def execute_task(self, name, command, callback=None):
        """Execute a task. `command` can be a string or list of args.
        Lists are executed without shell; strings are split via shlex."""
        logger.info("runner", f"INITIATING_TASK: {name} >> {command}")
        thread = threading.Thread(target=self._run_process, args=(name, command, callback), daemon=True)
        thread.start()

    def _run_process(self, name, command, callback):
        import platform
        current_os = platform.system()
        
        try:
            if isinstance(command, str):
                # Privilege Escalation Interceptor (Cross-Platform OS Bridge)
                if command.strip().startswith("sudo "):
                    core_cmd = command.strip()[5:]
                    if current_os == "Linux":
                        logger.info("runner", "Intercepted sudo command, elevating via pkexec for Linux GUI auth.")
                        command = "pkexec " + core_cmd
                    elif current_os == "Darwin":
                        logger.info("runner", "Intercepted sudo command, elevating via osascript for macOS GUI auth.")
                        # Need to run shell for osascript
                        import shlex
                        command = f"osascript -e 'do shell script \"{shlex.quote(core_cmd)}\" with administrator privileges'"
                    elif current_os == "Windows":
                        logger.info("runner", "Intercepted sudo command. Stripping for Windows NT (assuming Admin console).")
                        command = core_cmd
                
                # Split string into arg list for safe execution (no shell=True)
                args = shlex.split(command)
            else:
                args = list(command)

            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.active_processes[name] = process
            for line in process.stdout:
                if callback: callback(line)
                kairos.analyze(line)
            process.wait(timeout=_PROCESS_TIMEOUT)
            if callback: callback(f"\n[COMPLETED: {process.returncode}]")
        except subprocess.TimeoutExpired:
            process.kill()
            if callback: callback("[ERROR] TASK_TIMEOUT: Process exceeded time limit.")
        except Exception as e:
            if callback: callback(f"[ERROR] TASK_FAILURE: {str(e)}")
        finally:
            self.active_processes.pop(name, None)

    def execute_task_shell(self, name, command, callback=None):
        """Execute a command that requires shell features (pipes, redirects).
        Use sparingly — prefer execute_task with arg lists."""
        logger.info("runner", f"INITIATING_SHELL_TASK: {name} >> {command}")
        thread = threading.Thread(target=self._run_shell_process, args=(name, command, callback), daemon=True)
        thread.start()

    def _run_shell_process(self, name, command, callback):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.active_processes[name] = process
            for line in process.stdout:
                if callback: callback(line)
                kairos.analyze(line)
            process.wait(timeout=_PROCESS_TIMEOUT)
            if callback: callback(f"\n[COMPLETED: {process.returncode}]")
        except subprocess.TimeoutExpired:
            process.kill()
            if callback: callback("[ERROR] TASK_TIMEOUT: Process exceeded time limit.")
        except Exception as e:
            if callback: callback(f"[ERROR] TASK_FAILURE: {str(e)}")
        finally:
            self.active_processes.pop(name, None)


runner = Runner()
