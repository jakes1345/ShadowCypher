"""ShadowCypher Control (Session) Engine — High-Fidelity Sync (V23.2)."""

import os
import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class Session:
    """The 'Control' engine. Handles active reverse shells and remote links."""
    
    @staticmethod
    def list_active_sessions():
        """List active sessions (netstat/ss based)."""
        try:
            # We look for connections on common listener ports (4444, 1337, etc)
            return subprocess.check_output("ss -tlnp | grep -E '(4444|1337|8080|9001)'", shell=True, text=True)
        except:
            return "No active remote sessions detected."

    @staticmethod
    def terminate_session(sid, on_output=None, on_complete=None):
        """Terminate a specific session by SID (PID)."""
        cmd = f"kill -9 {sid}"
        runner.execute_task(f"KILL_SESSION_{sid}", cmd, callback=on_output)

    @staticmethod
    def interact_session(sid, on_output=None, on_complete=None):
        """Interact with a specific session (tty)."""
        cmd = f"conpty {sid}" # Assuming a terminal interface for interactions
        runner.execute_task(f"INTERACT_{sid}", cmd, callback=on_output)

    @staticmethod
    def upload_to_session(sid, local_file, remote_file, on_output=None, on_complete=None):
        """Upload a file to an active session."""
        cmd = f"scp {local_file} {remote_file}"
        runner.execute_task(f"UPLOAD_TO_{sid}", cmd, callback=on_output)
