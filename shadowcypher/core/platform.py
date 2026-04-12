"""
Sovereign Platform Engine — Cross-Platform Abstraction for ShadowCypher.
Abstracts OS-specific commands (Windows, Linux, macOS) to ensure Apex parity.
"""

import sys, os, subprocess, platform
from typing import Dict, List, Optional, Any

class ShadowPlatform:
    """The Cross-Platform brain of ShadowCypher."""
    
    SYSTEM = platform.system() # 'Linux', 'Darwin', 'Windows'
    IS_LINUX = SYSTEM == "Linux"
    IS_MACOS = SYSTEM == "Darwin"
    IS_WINDOWS = SYSTEM == "Windows"

    @staticmethod
    def get_cmd(key: str) -> str:
        """Map generic tool keys to platform-specific binaries/commands."""
        mappings = {
            "nmap": {"Linux": "nmap", "Darwin": "nmap", "Windows": "nmap.exe"},
            "nuclei": {"Linux": "nuclei", "Darwin": "nuclei", "Windows": "nuclei.exe"},
            "msf": {"Linux": "msfconsole", "Darwin": "msfconsole", "Windows": "msfconsole.bat"},
            "sudo": {"Linux": "sudo", "Darwin": "sudo", "Windows": "runas"},
            "shell": {"Linux": "/bin/bash", "Darwin": "/bin/zsh", "Windows": "powershell.exe"},
            "ifconfig": {"Linux": "ip link", "Darwin": "ifconfig", "Windows": "ipconfig /all"},
            "keychain": {"Darwin": "security"},
        }
        return mappings.get(key, {}).get(ShadowPlatform.SYSTEM, key)

    @staticmethod
    def get_net_info_cmd() -> list[str]:
        """Returns the platform-specific routing/interface command."""
        if ShadowPlatform.IS_LINUX:
            return ["ip", "route", "show", "default"]
        if ShadowPlatform.IS_MACOS:
            return ["networksetup", "-listallnetworkservices"]
        if ShadowPlatform.IS_WINDOWS:
            return ["route", "print"]
        return []

    @staticmethod
    def get_firewall_backend() -> str:
        if ShadowPlatform.IS_LINUX:
            return "iptables"
        if ShadowPlatform.IS_MACOS:
            return "pfctl"
        if ShadowPlatform.IS_WINDOWS:
            return "netsh"
        return "GENERIC"

    @staticmethod
    def get_cpu_info() -> str:
        try:
            if ShadowPlatform.IS_LINUX:
                return subprocess.check_output(['grep', '-m1', 'model name', '/proc/cpuinfo'], text=True).split(': ')[1].strip()
            if ShadowPlatform.IS_MACOS:
                return subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True).strip()
            if ShadowPlatform.IS_WINDOWS:
                return subprocess.check_output(['wmic', 'cpu', 'get', 'name'], text=True).split('\n')[1].strip()
        except:
            return "GENERIC_APEX_PROCESSOR"
        return "UNKNOWN"

    @staticmethod
    def resolve_runtime(file_path: str) -> list[str]:
        """Detects and returns the mandatory execution prefix for a given script.
        
        Analyzes shebang headers and file extensions to ensure compatibility across
        Python 2.7, Python 3.x, and native shell environments.
        """
        if not os.path.exists(file_path):
            return []

        # 1. Extension Check
        if file_path.endswith(".py"):
            # Check shebang for python2 requirement
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    first_line = f.readline()
                    if "python2" in first_line:
                        return ["python2"]
            except: pass
            return ["python3"]
        
        if file_path.endswith(".sh"): return ["bash"]
        if file_path.endswith(".ps1"): return ["powershell", "-File"]
        
        # 2. Binary / Compiled Check
        if os.access(file_path, os.X_OK):
            return [] # Execute directly
            
        return []

    @staticmethod
    def audit_tool_path(tool_name: str) -> Optional[str]:
        """Locates and validates the execution integrity of a system tool.
        
        Args:
            tool_name: The binary name or path.
            
        Returns:
            The absolute path to the verified binary, or None.
        """
        import shutil
        path = shutil.which(tool_name)
        if path and os.access(path, os.X_OK):
            return path
        return None

    @staticmethod
    def get_system_vitals() -> Dict[str, Any]:
        """Fetches high-fidelity system telemetry via native OS calls.
        
        Avoids library overhead by querying /proc or system-specific binaries.
        """
        vitals = {"cpu": 0.0, "mem": 0.0, "p_load": 0.0}
        try:
            if ShadowPlatform.IS_LINUX:
                with open("/proc/loadavg", "r") as f:
                    vitals["p_load"] = float(f.read().split()[0])
                # CPU usage calculation (simplified for core health)
                with open("/proc/stat", "r") as f:
                    line = f.readline()
                    parts = [float(x) for x in line.split()[1:]]
                    vitals["cpu"] = sum(parts[:3]) / sum(parts) * 100
        except Exception:
            pass
        return vitals

platform_engine = ShadowPlatform()
