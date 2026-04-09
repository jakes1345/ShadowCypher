"""
ShadowCypher C2 Session Manager — The Hive Mind.
Manages multi-session shells (Reverse, Bind, Meterpreter) and AI context switching.
"""

import threading
import time
from datetime import datetime
from shadowcypher.core.logger import logger

class C2Session:
    """A single high-fidelity shell session."""
    def __init__(self, session_id, target_ip, session_type, transport="tcp"):
        self.session_id = session_id
        self.target_ip = target_ip
        self.session_type = session_type
        self.transport = transport
        self.created_at = datetime.now()
        self.last_seen = datetime.now()
        self.status = "ACTIVE"
        self.cmd_history = []
        self.is_interactive = False

    def to_dict(self):
        return {
            "id": self.session_id,
            "target": self.target_ip,
            "type": self.session_type,
            "status": self.status,
            "last_seen": self.last_seen.isoformat()
        }

class C2Manager:
    """The 'Brain' for controlling multiple compromised nodes."""
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.sessions = {}
            cls._instance._lock = threading.Lock()
            cls._instance.active_session_id = None
        return cls._instance

    def register_session(self, target_ip, stype="reverse_shell"):
        """Register a new incoming shell session."""
        with self._lock:
            sid = f"SH-{len(self.sessions) + 1:03d}"
            session = C2Session(sid, target_ip, stype)
            self.sessions[sid] = session
            self.active_session_id = sid
            logger.info("c2", f"NEW_SESSION_ACQUIRED: {sid} from {target_ip}")
            return sid

    def get_session(self, sid):
        return self.sessions.get(sid)

    def list_sessions(self):
        return [s.to_dict() for s in self.sessions.values()]

    def execute_command(self, sid, cmd):
        """Execute a command on a specific session (Simulated logic for now)."""
        session = self.get_session(sid)
        if not session:
            return "[ERROR] SESSION_NOT_FOUND"
        
        session.last_seen = datetime.now()
        session.cmd_history.append(cmd)
        logger.info("c2", f"EXEC_CMD_SESSION_{sid}: {cmd}")
        # In a real implementation, this would write to the shell's stdin
        return f"[MOCK_OUTPUT] Execution of '{cmd}' on {session.target_ip} complete."

    def terminate_session(self, sid):
        with self._lock:
            if sid in self.sessions:
                self.sessions[sid].status = "TERMINATED"
                logger.warn("c2", f"SESSION_TERMINATED: {sid}")
                return True
        return False

# Global Singleton
c2_manager = C2Manager()
