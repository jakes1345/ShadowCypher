"""
Sovereign Platform Engine — Cross-Platform Abstraction for ShadowCypher.
Abstracts OS-specific commands (Windows, Linux, macOS) to ensure Apex parity.
"""

import sys
import os
import subprocess
import platform

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
        }
        return mappings.get(key, {}).get(ShadowPlatform.SYSTEM, key)

    @staticmethod
    def get_net_info_cmd() -> list[str]:
        """Returns the platform-specific routing/interface command."""
        if ShadowPlatform.IS_LINUX: return ["ip", "route", "show", "default"]
        if ShadowPlatform.IS_MACOS: return ["netstat", "-rn"]
        if ShadowPlatform.IS_WINDOWS: return ["route", "print"]
        return []

    @staticmethod
    def get_firewall_backend() -> str:
        if ShadowPlatform.IS_LINUX: return "iptables"
        if ShadowPlatform.IS_MACOS: return "pfctl"
        if ShadowPlatform.IS_WINDOWS: return "netsh"
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
        except: return "GENERIC_APEX_PROCESSOR"
        return "UNKNOWN"

platform_engine = ShadowPlatform()
