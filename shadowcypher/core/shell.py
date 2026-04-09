"""
ShadowShell — Unified Execution Core.
Handles all tactical commands with performance optimization and logging.
"""

import subprocess
import os
import time
from shadowcypher.core.logger import logger

class ShadowShell:
    """The Apex execution engine for ShadowCypher."""

    @staticmethod
    def execute(cmd: str, capture_output: bool = True, timeout: int = 300) -> dict:
        """Executes a command with performance optimizations (mold/lld)."""
        start_time = time.time()
        logger.info("shell", f"EXECUTING: {cmd}")

        # Inject performance linkers if we are compiling
        env = os.environ.copy()
        if "cargo" in cmd or "gcc" in cmd or "g++" in cmd:
            env["RUSTFLAGS"] = "-C linker=mold"
            env["LDFLAGS"] = "-fuse-ld=mold"

        try:
            if capture_output:
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    env=env,
                    timeout=timeout
                )
                duration = time.time() - start_time
                
                if result.returncode == 0:
                    logger.info("shell", f"SUCCESS: {cmd} ({duration:.2f}s)")
                    return {"status": "success", "output": result.stdout, "duration": duration}
                else:
                    logger.error("shell", f"FAILURE: {cmd} - {result.stderr}")
                    return {"status": "error", "output": result.stderr, "duration": duration}
            else:
                # Fire and forget / Background
                subprocess.Popen(cmd, shell=True, env=env)
                return {"status": "dispatched"}
        except subprocess.TimeoutExpired:
            logger.error("shell", f"TIMEOUT: {cmd}")
            return {"status": "timeout", "output": "Execution timed out."}
        except Exception as e:
            logger.error("shell", f"CRITICAL_ERROR: {str(e)}")
            return {"status": "exception", "output": str(e)}

    @staticmethod
    def async_execute(cmd: str, on_output=None):
        """Asynchronously stream output from a command."""
        import threading
        def run():
            process = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in process.stdout:
                if on_output:
                    on_output(line)
            process.wait()
        
        threading.Thread(target=run, daemon=True).start()
