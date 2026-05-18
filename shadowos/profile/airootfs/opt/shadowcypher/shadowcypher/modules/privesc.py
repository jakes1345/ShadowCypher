"""
Privilege Escalation Module — Local Enumeration & Exploit Engine.
SUID binaries, kernel exploits, sudo misconfigs, cron abuse, capabilities,
and automated LinPEAS integration.
"""

import os
import subprocess
import tempfile
from typing import Optional, Callable

from shadowcypher.core.module import BaseModule
from shadowcypher.core.runner import runner
from shadowcypher.core.platform import platform_engine


class PrivEsc(BaseModule):
    """Local privilege escalation enumeration and exploitation."""

    def __init__(self):
        super().__init__(module_name="privesc")

    # ── SUID Binaries ──

    @staticmethod
    def find_suid_binaries(on_output: Optional[Callable] = None):
        """Find all SUID binaries on the system — classic privesc vector."""
        return runner.execute_task(
            "SUID_SCAN",
            ["bash", "-c", "find / -perm -4000 -type f -not -path '*/proc/*' 2>/dev/null"],
            callback=on_output,
        )

    @staticmethod
    def find_sgid_binaries(on_output: Optional[Callable] = None):
        """Find all SGID binaries."""
        return runner.execute_task(
            "SGID_SCAN",
            ["bash", "-c", "find / -perm -2000 -type f -not -path '*/proc/*' 2>/dev/null"],
            callback=on_output,
        )

    # ── Writable Directories ──

    @staticmethod
    def find_writable_dirs(on_output: Optional[Callable] = None):
        """Find world-writable directories (potential for hijacking)."""
        return runner.execute_task(
            "WRITABLE_DIRS",
            ["bash", "-c", "find / -writable -type d -not -path '*/proc/*' -not -path '*/sys/*' 2>/dev/null | head -50"],
            callback=on_output,
        )

    @staticmethod
    def find_writable_files(on_output: Optional[Callable] = None):
        """Find writable files outside home and tmp."""
        return runner.execute_task(
            "WRITABLE_FILES",
            ["bash", "-c",
             "find / -writable -type f -not -path '*/proc/*' -not -path '*/sys/*' "
             "-not -path '/tmp/*' -not -path '/home/*' 2>/dev/null | head -50"],
            callback=on_output,
        )

    # ── Sudo ──

    @staticmethod
    def check_sudo_nopasswd(on_output: Optional[Callable] = None):
        """Check sudo -l for NOPASSWD entries and misconfigurations."""
        return runner.execute_task(
            "SUDO_CHECK",
            ["sudo", "-l"],
            callback=on_output,
        )

    # ── Kernel Exploits ──

    @staticmethod
    def check_kernel_exploits(on_output: Optional[Callable] = None):
        """Get kernel version and search for known exploits via searchsploit."""
        script = (
            "echo '=== Kernel Info ==='; "
            "uname -a; "
            "echo ''; "
            "echo '=== Searching exploits ==='; "
            "KVER=$(uname -r); "
            "if command -v searchsploit &>/dev/null; then "
            "  searchsploit \"linux kernel $KVER\" --colour; "
            "else "
            "  echo 'searchsploit not installed (apt install exploitdb)'; "
            "  echo \"Kernel: $KVER — search manually at exploit-db.com\"; "
            "fi"
        )
        return runner.execute_task(
            "KERNEL_EXPLOIT_CHECK",
            ["bash", "-c", script],
            callback=on_output,
        )

    # ── Cron Jobs ──

    @staticmethod
    def check_cron_jobs(on_output: Optional[Callable] = None):
        """Enumerate all cron jobs and check for writable cron paths."""
        script = (
            "echo '=== System Crontabs ==='; "
            "cat /etc/crontab 2>/dev/null; "
            "echo ''; "
            "echo '=== Cron Directories ==='; "
            "ls -la /etc/cron.* 2>/dev/null; "
            "echo ''; "
            "echo '=== User Crontabs ==='; "
            "for user in $(cut -f1 -d: /etc/passwd); do "
            "  crontab -l -u $user 2>/dev/null && echo \"^^^ $user ^^^\" ; "
            "done; "
            "echo ''; "
            "echo '=== Writable Cron Paths ==='; "
            "find /etc/cron* /var/spool/cron -writable -type f 2>/dev/null"
        )
        return runner.execute_task(
            "CRON_ENUM",
            ["bash", "-c", script],
            callback=on_output,
        )

    # ── Capabilities ──

    @staticmethod
    def check_capabilities(on_output: Optional[Callable] = None):
        """Enumerate file capabilities — cap_setuid, cap_net_raw, etc."""
        return runner.execute_task(
            "CAP_ENUM",
            ["bash", "-c", "getcap -r / 2>/dev/null"],
            callback=on_output,
        )

    # ── Interesting Files ──

    @staticmethod
    def find_sensitive_files(on_output: Optional[Callable] = None):
        """Search for passwords, SSH keys, config files with credentials."""
        script = (
            "echo '=== SSH Keys ==='; "
            "find / -name 'id_rsa' -o -name 'id_ecdsa' -o -name 'id_ed25519' "
            "  -o -name '*.pem' -o -name 'authorized_keys' 2>/dev/null; "
            "echo ''; "
            "echo '=== Password Files ==='; "
            "find / -name '*.conf' -o -name '*.cfg' -o -name '*.ini' "
            "  -o -name '.env' -o -name 'wp-config.php' 2>/dev/null | "
            "  xargs grep -l -i 'password\\|passwd\\|secret\\|api_key' 2>/dev/null | head -30; "
            "echo ''; "
            "echo '=== History Files ==='; "
            "find /home -name '.*_history' -o -name '.bash_history' 2>/dev/null"
        )
        return runner.execute_task(
            "SENSITIVE_FILES",
            ["bash", "-c", script],
            callback=on_output,
        )

    # ── LinPEAS ──

    @staticmethod
    def run_linpeas(on_output: Optional[Callable] = None):
        """Download and run LinPEAS for comprehensive privilege escalation audit."""
        script = (
            "LPEAS=/tmp/.linpeas.sh; "
            "if [ ! -f $LPEAS ]; then "
            "  echo '[*] Downloading LinPEAS...'; "
            "  curl -sL https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh -o $LPEAS; "
            "  chmod +x $LPEAS; "
            "fi; "
            "echo '[*] Running LinPEAS...'; "
            "bash $LPEAS -a -q 2>&1"
        )
        return runner.execute_task(
            "LINPEAS",
            ["bash", "-c", script],
            callback=on_output,
        )

    # ── Linux Exploit Suggester ──

    @staticmethod
    def run_les(on_output: Optional[Callable] = None):
        """Download and run Linux Exploit Suggester."""
        script = (
            "LES=/tmp/.les.sh; "
            "if [ ! -f $LES ]; then "
            "  echo '[*] Downloading Linux Exploit Suggester...'; "
            "  curl -sL https://raw.githubusercontent.com/mzet-/linux-exploit-suggester/master/linux-exploit-suggester.sh -o $LES; "
            "  chmod +x $LES; "
            "fi; "
            "echo '[*] Running LES...'; "
            "bash $LES 2>&1"
        )
        return runner.execute_task(
            "LES",
            ["bash", "-c", script],
            callback=on_output,
        )

    # ── PATH Hijacking ──

    @staticmethod
    def check_path_hijacking(on_output: Optional[Callable] = None):
        """Check for writable directories in PATH (path hijacking vector)."""
        script = (
            "echo '=== PATH directories ==='; "
            "echo $PATH | tr ':' '\\n'; "
            "echo ''; "
            "echo '=== Writable PATH entries ==='; "
            "for dir in $(echo $PATH | tr ':' '\\n'); do "
            "  [ -w \"$dir\" ] && echo \"WRITABLE: $dir\"; "
            "done"
        )
        return runner.execute_task(
            "PATH_HIJACKING",
            ["bash", "-c", script],
            callback=on_output,
        )

    # ── Full Audit ──

    def full_audit(self, on_output: Optional[Callable] = None):
        """Run all privilege escalation checks sequentially."""
        self.log("FULL_PRIVESC_AUDIT_ENGAGED", "CRITICAL")

        checks = [
            ("SUID Binaries", self.find_suid_binaries),
            ("SGID Binaries", self.find_sgid_binaries),
            ("Sudo Config", self.check_sudo_nopasswd),
            ("Kernel Exploits", self.check_kernel_exploits),
            ("Cron Jobs", self.check_cron_jobs),
            ("Capabilities", self.check_capabilities),
            ("Writable Dirs", self.find_writable_dirs),
            ("Sensitive Files", self.find_sensitive_files),
            ("PATH Hijacking", self.check_path_hijacking),
        ]

        task_ids = []
        for name, func in checks:
            if on_output:
                on_output(f"\n{'='*60}\n[*] {name}\n{'='*60}")
            tid = func(on_output=on_output)
            if tid:
                task_ids.append(tid)

        return task_ids
