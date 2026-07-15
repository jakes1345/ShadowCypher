"""ShadowCypher Control (Session) Engine — High-Fidelity Sync (V23.2)."""

import subprocess

from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_filepath


class Session:
    """The 'Control' engine. Handles active reverse shells and remote links."""

    @staticmethod
    def list_active_sessions():
        """List active sessions (ss based)."""
        try:
            return subprocess.check_output(
                ["ss", "-tlnp"], text=True, timeout=5
            )
        except Exception:
            return "No active remote sessions detected."

    @staticmethod
    def terminate_session(sid, on_output=None, on_complete=None):
        """Terminate a specific session by SID (PID)."""
        # Validate SID is a numeric PID
        try:
            pid = int(sid)
        except (ValueError, TypeError):
            if on_output:
                on_output(f"[ERROR] Invalid session ID (must be numeric): {sid}")
            return
        runner.execute_task(f"KILL_SESSION_{pid}", ["kill", "-9", str(pid)], callback=on_output)

    @staticmethod
    def interact_session(sid, on_output=None, on_complete=None):
        """Interact with a specific session via GNOME Terminal bridge."""
        if on_output:
            on_output(f"[SESSION] ATTEMPTING_INTERACTIVE_BRIDGE: {sid}...\n")

        # Professional Depth: Spawn a real terminal window for the interactive shell
        # We use netcat to bridge to the session port (if detected) or just a manual command.
        cmd = ["gnome-terminal", "--", "bash", "-c",
               f'echo "[SHADOWCYPHER] EMBEDDED_SESSION_BRIDGE: {sid}"; ncat -v -l -p {sid}; exec bash']
        return runner.execute_task(f"INTERACT_{sid}", cmd, callback=on_output)

    @staticmethod
    def upload_to_session(sid, local_file, remote_file, on_output=None, on_complete=None):
        """Upload a file to an active session."""
        if not validate_filepath(local_file):
            if on_output:
                on_output(f"[ERROR] Invalid local file path: {local_file}")
            return
        runner.execute_task(f"UPLOAD_TO_{sid}", ["scp", local_file, remote_file], callback=on_output)
