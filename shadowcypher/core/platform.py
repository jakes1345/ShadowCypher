"""
Sovereign Platform Engine — Cross-Platform Abstraction for ShadowCypher.
Abstracts OS-specific commands (Windows, Linux, macOS) to ensure Apex parity.
"""

import sys, os, subprocess, platform
from typing import Dict, List, Optional, Any

class ShadowPlatform:
    """The Cross-Platform brain of ShadowCypher."""
    
    SYSTEM = platform.system()
    IS_LINUX = SYSTEM == "Linux"
    IS_MACOS = SYSTEM == "Darwin"
    IS_WINDOWS = SYSTEM == "Windows"

    # --- PHASE SIGMA: Autonomous Pathing ---
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    COMPONENTS = {
        "core": "shadowcypher",
        "script": "shadowscript",
        "agent": "ai_engine/autoagent",
        "phish": "ShadowPhish",
        "native": "shadowcypher/native",
        "data": "data",
        "findings": "findings",
        "arsenal": "shadowcypher/arsenal/primitives"
    }

    @classmethod
    def resolve_path(cls, component: str, *parts: str) -> str:
        """Butter-smooth path resolution for all tactical components."""
        base = cls.COMPONENTS.get(component, "")
        return os.path.join(cls.ROOT, base, *parts)

    @classmethod
    def get_component_status(cls) -> Dict[str, bool]:
        """Catalogs which ecosystem modules are currently available."""
        return {k: os.path.exists(cls.resolve_path(k)) for k in cls.COMPONENTS}

    @staticmethod
    def get_cmd(key: str) -> str:
        mappings = {
            "nmap": {"Linux": "nmap", "Darwin": "nmap", "Windows": "nmap.exe"},
            "nuclei": {"Linux": "nuclei", "Darwin": "nuclei", "Windows": "nuclei.exe"},
            "msf": {"Linux": "msfconsole", "Darwin": "msfconsole", "Windows": "msfconsole.bat"},
            "sudo": {"Linux": "sudo", "Darwin": "sudo", "Windows": "runas"},
            "shell": {"Linux": "/bin/bash", "Darwin": "/bin/zsh", "Windows": "powershell.exe"},
            "ifconfig": {"Linux": "ip link", "Darwin": "ifconfig", "Windows": "ipconfig /all"},
        }
        return mappings.get(key, {}).get(ShadowPlatform.SYSTEM, key)

    @staticmethod
    def resolve_runtime(file_path: str) -> list[str]:
        if not os.path.exists(file_path): return []

        if file_path.endswith(".shadow"):
            shadow_bin = ShadowPlatform.resolve_path("script", "bin", "shadow")
            if os.path.exists(shadow_bin): return [shadow_bin]

        if file_path.endswith(".py"):
            return ["python3"]
        
        if file_path.endswith(".sh"): return ["bash"]
        if os.access(file_path, os.X_OK): return []
        return []

    @staticmethod
    def get_system_vitals() -> Dict[str, Any]:
        vitals = {"cpu": 0.0, "mem": 0.0, "p_load": 0.0, "virt": "NONE"}
        vitals["virt"] = ShadowPlatform.detect_virtualization()
        try:
            if ShadowPlatform.IS_LINUX:
                with open("/proc/loadavg", "r") as f:
                    vitals["p_load"] = float(f.read().split()[0])
                # Simplified memory check for performance
                with open("/proc/meminfo", "r") as f:
                    for _ in range(3): # Just need the first few lines
                        line = f.readline()
                        if "MemTotal" in line: total = int(line.split()[1])
                        if "MemAvailable" in line: avail = int(line.split()[1])
                    vitals["mem"] = (1 - avail / total) * 100
        except: pass
        return vitals

    @staticmethod
    def detect_virtualization() -> str:
        if os.path.exists("/.dockerenv"): return "DOCKER"
        return "HOST"

platform_engine = ShadowPlatform()
