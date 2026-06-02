"""
Apex Runner — High-Performance Cross-Platform Execution Engine.
Standardizes command execution across Linux, macOS, and Windows.
"""

import subprocess
import threading
import uuid
import os
import shlex
from typing import Dict, List, Optional, Any, Callable, Union, Final
from shadowcypher.core.bus import bus
from shadowcypher.core.config import config
from shadowcypher.core.platform import platform_engine

class Runner:
    
    def __init__(self) -> None:
        self.active_processes: Dict[str, subprocess.Popen[str]] = {}
        self._lock: Final[threading.Lock] = threading.Lock()
        self.platform = platform_engine
        self._perf_env: Final[Dict[str, str]] = self._init_perf_env()

    def _init_perf_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        # APEX Optimization: only apply mold on Linux
        if self.platform.IS_LINUX:
            env["RUSTFLAGS"] = "-C target-cpu=native -C linker=mold"
            env['LDFLAGS'] = "-fuse-ld=mold"
        
        # STEALTH: Global Proxy Injection
        from shadowcypher.core.config import config
        proxy = config.get("stealth", "proxy_url")
        if proxy:
            env["HTTP_PROXY"] = proxy
            env["HTTPS_PROXY"] = proxy
            env["ALL_PROXY"] = proxy
            env["NO_PROXY"] = "localhost,127.0.0.1"
            
        return env

    def stop_task(self, task_id: str) -> None:
        with self._lock:
            if task_id in self.active_processes:
                proc = self.active_processes[task_id]
                try:
                    proc.terminate()
                    # SIGTERM first; escalate to SIGKILL after 2s if still alive.
                    def force_kill():
                        if proc.poll() is None:
                            proc.kill()
                    threading.Timer(2.0, force_kill).start()
                except Exception:
                    pass

    def execute_task(self, name: str, command: Union[str, List[str]], 
                     callback: Optional[Callable[[str], None]] = None, 
                     cwd: Optional[str] = None) -> str:
        task_id = f"{name[:4]}_{str(uuid.uuid4())[:4]}"
        threading.Thread(
            target=self._run, 
            args=(task_id, name, command, callback, cwd, False), 
            daemon=True
        ).start()
        return task_id

    def execute_task_shell(self, name, command, callback=None):
        task_id = f"{name[:4]}_{str(uuid.uuid4())[:4]}"
        threading.Thread(target=self._run, args=(task_id, name, command, callback, None, True), daemon=True).start()
        return task_id

    def _run(self, task_id: str, name: str, command: Union[str, List[str]], 
             callback: Optional[Callable[[str], None]], 
             cwd: Optional[str], is_shell: bool) -> None:
        try:
            # 1. Argument Normalization
            args = command if is_shell else (shlex.split(command) if isinstance(command, str) else command)
            
            # 2. Polyglot Runtime Bridge (Python 2 vs 3 vs Native)
            if not is_shell and isinstance(args, list) and args:
                potential_script = args[0]
                # Check tools/ and absolute paths
                if not os.path.exists(potential_script):
                    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    tool_path = os.path.join(proj_root, 'tools', potential_script)
                    if os.path.exists(tool_path):
                        potential_script = tool_path
                
                prefix = self.platform.resolve_runtime(potential_script)
                if prefix:
                    args = prefix + args
            
            # 3. Platform-Aware Elevation
            if not is_shell and isinstance(args, list) and args and args[0] == "sudo":
                if self.platform.IS_LINUX:
                    # sudo -n: non-interactive, fails loudly if not in sudoers instead of
                    # popping a pkexec GUI dialog that breaks terminal output streaming
                    args = ["sudo", "-n"] + args[1:]
                elif self.platform.IS_WINDOWS and len(args) > 1:
                    # Windows: wrap the target in a Start-Process RunAs invocation.
                    exe = args[1]
                    arg_list = args[2:]
                    ps_cmd = f"Start-Process -Verb RunAs -FilePath '{exe}'"
                    if arg_list:
                        joined = ",".join(f"'{a}'" for a in arg_list)
                        ps_cmd += f" -ArgumentList {joined}"
                    args = ["powershell", "-NoProfile", "-Command", ps_cmd]

            # 4. STEALTH: Proxychains Wrapping (Linux only, if privacy enforced)
            if self.platform.IS_LINUX and not is_shell and config.get("stealth", "enforce_privacy"):
                import shutil
                if shutil.which("proxychains4"):
                    args = ["proxychains4", "-q"] + args
                elif shutil.which("proxychains"):
                    args = ["proxychains", "-q"] + args

            proc = subprocess.Popen(
                args, shell=is_shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, env=self._perf_env, cwd=cwd,
                start_new_session=True
            )
            
            with self._lock:
                self.active_processes[task_id] = proc
            
            # 4. Stream Management
            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    if callback:
                        callback(line)
                    bus.publish("mission_output", {"task": task_id, "text": line})
            
            proc.wait(timeout=1800)
            if callback:
                callback(f"\n[MISSION_{name[:4]}_TERM: Return {proc.returncode}]")
        except Exception as e:
            if callback:
                callback(f"[ERROR] RUNNER_CRITICAL_FAULT: {str(e)}")
        finally:
            with self._lock:
                self.active_processes.pop(task_id, None)

runner: Final[Runner] = Runner()
