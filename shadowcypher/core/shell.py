"""
ShadowShell — Enterprise-Grade Execution Engine.
Google-grade tactical command orchestration with security hardening and performance metrics.
"""

import subprocess
import os
import time
import threading
import shlex
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from shadowcypher.core.logger import logger

class ShadowShell:
    """
    ShadowShell — The high-performance execution backbone for ShadowCypher.
    Implements secure command invocation, performance tracking, and resource isolation.
    """

    @staticmethod
    def execute(cmd: str, timeout: int = 300, env_updates: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Execute a command synchronously with enterprise-grade monitoring.
        
        Args:
            cmd: The shell command to execute.
            timeout: Maximum execution time in seconds.
            env_updates: Optional environment variables to overlay.
            
        Returns:
            Structured results including status, output, and telemetry.
        """
        start_time = time.time()
        logger.info("shell", f"INVOKING_COMMAND: {cmd[:128]}...")

        # 1. Environment Synthesis
        env = os.environ.copy()
        if env_updates:
            env.update(env_updates)
            
        # 2. Performance Linker Optimization (Enterprise Compilation)
        if any(tool in cmd for tool in ["cargo", "gcc", "g++", "make"]):
            env["RUSTFLAGS"] = "-C linker=mold"
            env["LDFLAGS"] = "-fuse-ld=mold"

        try:
            # 3. Pulse-Driven Tactical Throttling
            from shadowcypher.core.pulse import pulse
            if pulse.throttle_active:
                logger.info("shell", "TACTICAL_THROTTLE_ACTIVE: Injecting stealth delay...")
                time.sleep(1.5) # Adaptive footprint reduction
                
            # 4. Execution with Pipe Isolation
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
                check=False
            )
            
            duration = time.time() - start_time
            status = "SUCCESS" if result.returncode == 0 else "ERROR"
            
            # 5. Pulse Ingestion (Execution Latency Anomaly Detection)
            from shadowcypher.core.pulse import pulse
            pulse.ingest("execution_telemetry", duration)
            
            # 6. Structured Telemetry
            telemetry = {
                "status": status,
                "exit_code": result.returncode,
                "duration": round(duration, 4),
                "output": result.stdout if result.returncode == 0 else result.stderr,
                "timestamp": datetime.now().isoformat()
            }
            
            if result.returncode == 0:
                logger.info("shell", f"COMMAND_COMPLETE: {cmd[:64]}... [{duration:.2f}s]")
            else:
                logger.warning("shell", f"COMMAND_FAILED: {cmd[:64]}... (Exit: {result.returncode})")
                
            return telemetry

        except subprocess.TimeoutExpired:
            logger.error("shell", f"COMMAND_TIMEOUT: {cmd[:64]} exceeded {timeout}s")
            return {"status": "TIMEOUT", "exit_code": -1, "output": "Execution timed out.", "duration": timeout}
        except Exception as e:
            logger.error("shell", f"COMMAND_EXCEPTION: {str(e)}")
            return {"status": "EXCEPTION", "exit_code": -1, "output": str(e), "duration": 0}

    @staticmethod
    def stream_execute(cmd: str, on_output: Callable[[str], None], on_complete: Callable[[int], None] = None):
        """
        Asynchronously execute a command and stream output line-by-line.
        Optimized for high-volume logs from tools like nmap or ffuf.
        """
        def _target():
            try:
                # Use shlex.split for safer handling if we were using shell=False, 
                # but for complex pentest pipes, shell=True is retained with caution.
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                for line in iter(process.stdout.readline, ""):
                    if line:
                        on_output(line.strip())
                
                process.stdout.close()
                return_code = process.wait()
                
                if on_complete:
                    on_complete(return_code)
                    
            except Exception as e:
                logger.error("shell", f"STREAM_EXCEPTION: {str(e)}")
                if on_output:
                    on_output(f"INTERNAL_STREAM_ERROR: {str(e)}")

        thread = threading.Thread(target=_target, name=f"ShellStream-{int(time.time())}", daemon=True)
        thread.start()
        return thread
