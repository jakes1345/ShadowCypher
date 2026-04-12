"""
Apex Runner — High-Performance Cross-Platform Execution Engine.
Standardizes command execution across Linux, macOS, and Windows.
"""

import subprocess
import threading
import uuid
import os
import shlex
from shadowcypher.core.bus import bus
from shadowcypher.core.platform import platform_engine

class Runner:
    """The central execution artery of ShadowCypher."""
    
    def __init__(self):
        self.active_processes = {}
        self._lock = threading.Lock()
        self.platform = platform_engine
        self._perf_env = self._init_perf_env()

    def _init_perf_env(self):
        env = os.environ.copy()
        # APEX Optimization: only apply mold on Linux
        if self.platform.IS_LINUX:
            env["RUSTFLAGS"] = "-C target-cpu=native -C linker=mold"
            env["LDFLAGS"] = "-fuse-ld=mold"
        return env

    def stop_task(self, task_id):
        """Emergency Kill Switch for autonomous tasks."""
        with self._lock:
            if task_id in self.active_processes:
                proc = self.active_processes[task_id]
                try:
                    proc.terminate()
                    # Force kill if still breathing after 2s
                    threading.Timer(2, lambda: proc.kill() if proc.poll() is None else None).start()
                except Exception as e:
                    pass

    def execute_task(self, name, command, callback=None, cwd=None):
        task_id = f"{name[:4]}_{str(uuid.uuid4())[:4]}"
        threading.Thread(target=self._run, args=(task_id, name, command, callback, cwd, False), daemon=True).start()
        return task_id

    def execute_task_shell(self, name, command, callback=None):
        task_id = f"{name[:4]}_{str(uuid.uuid4())[:4]}"
        threading.Thread(target=self._run, args=(task_id, name, command, callback, None, True), daemon=True).start()
        return task_id

    def _run(self, task_id, name, command, callback, cwd, is_shell):
        try:
            # 1. CROSS-PLATFORM ELEVATION
            if not is_shell and isinstance(command, list) and command[0] == "sudo":
                if self.platform.IS_LINUX:
                    command = ["pkexec"] + command[1:]
                elif self.platform.IS_WINDOWS:
                    command = ["powershell", "Start-Process", "-Verb", "runAs"] + command[1:]
                # macOS stays sudo for now (Gtk-based GUI sudo is complex)

            # 2. BINARY SUFFIXING (Windows)
            if self.platform.IS_WINDOWS and not is_shell and isinstance(command, list):
                if not command[0].endswith(".exe") and not command[0].endswith(".bat"):
                    command[0] += ".exe"

            args = command if is_shell else (shlex.split(command) if isinstance(command, str) else command)
            
            proc = subprocess.Popen(
                args, shell=is_shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, env=self._perf_env, cwd=cwd,
                start_new_session=True
            )
            
            with self._lock:
                self.active_processes[task_id] = proc
            
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    if callback: callback(line)
                    bus.publish("mission_output", {"task": task_id, "text": line})
            
            proc.wait(timeout=1200)
            if callback: callback(f"\n[MISSION_{name[:4]}_EXIT: {proc.returncode}]")
        except Exception as e:
            if callback: callback(f"[ERROR] APEX_RUNNER_FAULT: {e}")
        finally:
            with self._lock:
                self.active_processes.pop(task_id, None)

runner = Runner()
