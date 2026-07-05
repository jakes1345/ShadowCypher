"""
YARA Malware/Threat Pattern Scanner — Enterprise Defensive Build.
Scans files or directories on the OPERATOR'S OWN machine against YARA rule
sets to detect known malware signatures, webshells, and suspicious binary
patterns. Purely a detection/defensive tool — never used to author malware.

Rules are user- or distro-managed under an XDG data directory (no rules are
auto-downloaded from a hardcoded URL — point `rules_dir` at whatever rule
pack you trust: Neo23x0/signature-base, Yara-Rules/rules, your own).
"""

import os
import shutil
from pathlib import Path
from typing import Callable, Optional

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_filepath


def default_rules_dir() -> Path:
    """Resolve the operator's YARA rules directory (XDG data home, matching
    the project's per-user state convention)."""
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(xdg) / "shadowcypher" / "yara_rules"


class YaraScan(BaseModule):
    """The 'Watchtower' engine — YARA-based malware pattern detection."""

    def __init__(self):
        super().__init__(module_name="yara_scan")

    def _resolve_rules(self, rules_dir: Optional[str]) -> Optional[Path]:
        path = Path(rules_dir) if rules_dir else default_rules_dir()
        if not path.exists() or not any(path.rglob("*.yar*")):
            return None
        return path

    def scan_file(self, filepath: str, rules_dir: str = None,
                  on_output: Callable = None) -> Optional[str]:
        """Scan a single file against the configured YARA rule set."""
        if not validate_filepath(filepath) or not os.path.isfile(filepath):
            if on_output:
                on_output(f"[YARA] Invalid or missing file: {filepath}\n")
            return None
        return self._run_scan([filepath], rules_dir, on_output, label=os.path.basename(filepath))

    def scan_directory(self, dirpath: str, rules_dir: str = None,
                        recursive: bool = True, on_output: Callable = None) -> Optional[str]:
        """Scan every file in a directory against the configured YARA rule
        set. Recursive by default (matches how rkhunter/lynis treat a
        filesystem sweep)."""
        if not validate_filepath(dirpath) or not os.path.isdir(dirpath):
            if on_output:
                on_output(f"[YARA] Invalid or missing directory: {dirpath}\n")
            return None
        return self._run_scan([dirpath], rules_dir, on_output,
                               label=os.path.basename(dirpath.rstrip("/")), recursive=recursive)

    def _run_scan(self, targets: list[str], rules_dir: Optional[str],
                  on_output: Callable, label: str, recursive: bool = True) -> Optional[str]:
        yara = self.get_tool_path("yara")
        if not shutil.which(yara):
            if on_output:
                on_output("[YARA] yara not found — install: pacman -S yara / apt install yara\n")
            return None

        rules_path = self._resolve_rules(rules_dir)
        if rules_path is None:
            if on_output:
                on_output(
                    f"[YARA] No rule files (*.yar/*.yara) found under "
                    f"{rules_dir or default_rules_dir()} — drop a trusted rule "
                    f"pack there first (e.g. Neo23x0/signature-base).\n"
                )
            return None

        self.log(f"YARA_SCAN: {label} against {rules_path}")
        args = [yara]
        if recursive:
            args.append("-r")
        args += ["-w"]  # suppress warnings about slow rules, keep signal clean

        rule_files = sorted(str(p) for p in rules_path.rglob("*.yar*"))
        args += rule_files
        args += targets
        return self.execute(f"YARA_{label}", args, callback=on_output)

    def rule_count(self, rules_dir: str = None) -> int:
        """Count how many *.yar/*.yara rule files are available locally."""
        path = Path(rules_dir) if rules_dir else default_rules_dir()
        if not path.exists():
            return 0
        return len(list(path.rglob("*.yar*")))


yara_scan = YaraScan()
