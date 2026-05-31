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
        "arsenal": "shadowcypher/arsenal/primitives",
        "assets": "assets",
    }

    @classmethod
    def resolve_path(cls, component: str, *parts: str) -> str:
        """Resolve paths for tactical components (dev tree + /opt/shadowcypher install)."""
        base = cls.COMPONENTS.get(component, "")
        primary = os.path.join(cls.ROOT, base, *parts)
        if os.path.exists(primary):
            return primary
        # Installed layout: /opt/shadowcypher/assets/… (repo-root assets/ copied at build)
        if component == "assets":
            for alt in (
                os.path.join(cls.ROOT, "assets", *parts),
                os.path.join("/opt/shadowcypher", "assets", *parts),
            ):
                if os.path.exists(alt):
                    return alt
        return primary

    @classmethod
    def get_master_key_path(cls) -> str:
        """Locates the master cryptographic key based on the host OS."""
        if cls.IS_WINDOWS:
            return "C:\\ProgramData\\ShadowCypher\\master.key"
        return "/etc/shadowcypher/master.key"

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
                # Robust memory check
                mem_total = 0
                mem_avail = 0
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal" in line:
                            mem_total = int(line.split()[1])
                        elif "MemAvailable" in line:
                            mem_avail = int(line.split()[1])
                        if mem_total and mem_avail:
                            break
                if mem_total:
                    vitals["mem"] = (1 - mem_avail / mem_total) * 100
                    cpu_count = os.cpu_count() or 1
                    vitals["cpu"] = (vitals["p_load"] / cpu_count) * 100
        except (OSError, ValueError):
            pass
        return vitals

    @staticmethod
    def detect_virtualization() -> str:
        if os.path.exists("/.dockerenv"): return "DOCKER"
        return "HOST"

    @staticmethod
    def get_net_info_cmd() -> List[str]:
        """Return the platform-native command that prints routing info."""
        if ShadowPlatform.IS_LINUX:
            return ["ip", "route"]
        if ShadowPlatform.IS_MACOS:
            return ["netstat", "-rn"]
        if ShadowPlatform.IS_WINDOWS:
            return ["route", "print"]
        return ["netstat", "-rn"]

    @staticmethod
    def audit_tool_path(tool_name: str) -> Optional[str]:
        """Return the absolute path to `tool_name` if installed, else None.

        Checks, in order: the system PATH (shutil.which) and the local
        project `tools/` directory. Unlike `config.get_tool_path`, this
        returns None on miss so callers can use truthy checks.
        """
        import shutil
        sys_path = shutil.which(tool_name)
        if sys_path:
            return sys_path
        local_dir = os.path.join(ShadowPlatform.ROOT, "tools")
        if os.path.isdir(local_dir):
            for root, _, files in os.walk(local_dir):
                for f in files:
                    if f.lower() == tool_name.lower() or f.lower() == f"{tool_name.lower()}.sh":
                        return os.path.join(root, f)
        return None

    @staticmethod
    def get_firewall_backend() -> str:
        """Detects the primary firewall backend for the current platform."""
        if ShadowPlatform.IS_LINUX:
            try:
                # Check for nftables first (modern standard)
                if subprocess.call(["which", "nft"], stdout=subprocess.DEVNULL) == 0:
                    return "NFTABLES"
                # Check for legacy iptables
                if subprocess.call(["which", "iptables"], stdout=subprocess.DEVNULL) == 0:
                    return "IPTABLES"
                return "GENERIC_LINUX"
            except (OSError, FileNotFoundError):
                return "UNSUPPORTED"
        elif ShadowPlatform.IS_WINDOWS:
            return "WINDOWS_DEFENDER"
        elif ShadowPlatform.IS_MACOS:
            return "PF"
        return "UNKNOWN"

platform_engine = ShadowPlatform()
