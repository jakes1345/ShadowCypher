import subprocess
import shlex
import threading
import os
import uuid
import time
from shadowcypher.core.logger import logger

_PROCESS_TIMEOUT = 1200  # 20 minute max per task


class Runner:
    """Universal task runner with persistent job-tracking and cancellation."""

    def __init__(self):
        self.active_processes = {}

    def execute_task(self, name, command, callback=None, cwd=None):
        """
        Execute a tactical mission task.
        Returns a unique 'task_id' for cancellation support.
        """
        task_id = str(uuid.uuid4())[:8]
        full_name = f"{name}_{task_id}"

        logger.info("runner", f"INITIATING_TASK: {full_name} >> {command} [CWD={cwd}]")
        thread = threading.Thread(
            target=self._run_process,
            args=(task_id, full_name, command, callback, cwd),
            daemon=True,
        )
        thread.start()
        return task_id

    def cancel(self, task_id):
        """Force-terminate an active mission task."""
        if task_id in self.active_processes:
            proc = self.active_processes[task_id]
            logger.warn("runner", f"MANUAL_CANCELLATION: Terminating task_id {task_id}")
            try:
                proc.terminate()
                time.sleep(0.5)
                if proc.poll() is None:
                    proc.kill()
            except Exception as e:
                logger.error("runner", f"CANCELLATION_FAILURE: {e}")
            return True
        return False

    def _run_process(self, task_id, name, command, callback, cwd=None):
        import platform

        current_os = platform.system()

        try:
            if isinstance(command, str):
                # Privilege Escalation Bridge
                if command.strip().startswith("sudo "):
                    core_cmd = command.strip()[5:]
                    if current_os == "Linux":
                        command = "pkexec " + core_cmd
                    elif current_os == "Darwin":
                        command = f"osascript -e 'do shell script \"{shlex.quote(core_cmd)}\" with administrator privileges'"
                args = shlex.split(command)
            else:
                args = list(command)

            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line-buffered for real-time OSINT
                universal_newlines=True,
                cwd=cwd,
            )

            self.active_processes[task_id] = process

            for line in process.stdout:
                if callback:
                    callback(line)
                try:
                    from shadowcypher.core.kairos import kairos

                    kairos.analyze(line)
                except Exception:
                    pass

            process.wait(timeout=_PROCESS_TIMEOUT)
            if callback:
                callback(f"\n[MISSION_EXIT_CODE: {process.returncode}]")

        except subprocess.TimeoutExpired:
            if task_id in self.active_processes:
                self.active_processes[task_id].kill()
            if callback:
                callback("[ERROR] MISSION_TIMEOUT: Command exceeded safety duration.")
        except Exception as e:
            if callback:
                callback(f"[ERROR] MISSION_FAILURE: {str(e)}")
        finally:
            self.active_processes.pop(task_id, None)

    def execute_task_shell(self, name, command, callback=None):
        """Shell execution with task ID support."""
        task_id = str(uuid.uuid4())[:8]
        thread = threading.Thread(
            target=self._run_shell_process,
            args=(task_id, f"{name}_{task_id}", command, callback),
            daemon=True,
        )
        thread.start()
        return task_id

    def _run_shell_process(self, task_id, name, command, callback):
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            self.active_processes[task_id] = process
            for line in process.stdout:
                if callback:
                    callback(line)
                try:
                    from shadowcypher.core.kairos import kairos

                    kairos.analyze(line)
                except Exception:
                    pass
            process.wait(timeout=_PROCESS_TIMEOUT)
            if callback:
                callback(f"\n[MISSION_EXIT_CODE: {process.returncode}]")
        except Exception as e:
            if callback:
                callback(f"[ERROR] MISSION_FAILURE: {str(e)}")
        finally:
            self.active_processes.pop(task_id, None)


runner = Runner()
