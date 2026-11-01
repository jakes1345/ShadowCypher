"""
Secret Audit Module — Credential & Secret Scanner
Scans files and directories for exposed secrets, API keys, tokens, and credentials.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from shadowcypher.core.module import BaseModule

# Regex patterns — specific/high-confidence patterns listed before generic ones
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AWS_ACCESS_KEY",     re.compile(r"(?i)(AKIA[0-9A-Z]{16})")),
    ("AWS_SECRET_KEY",     re.compile(r"(?i)(aws[_\- ]?secret[_\- ]?(?:access[_\- ]?)?key[\s:=]+['\"]?([A-Za-z0-9/+]{40})['\"]?)")),
    ("GITHUB_TOKEN",       re.compile(r"(?i)(gh[pousr]_[A-Za-z0-9_]{36,255})")),
    ("PRIVATE_KEY_HEADER", re.compile(r"-----BEGIN (EC |RSA |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("STRIPE_KEY",         re.compile(r"(sk_live_[A-Za-z0-9]{24,99})")),
    ("SENDGRID_KEY",       re.compile(r"(SG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43})")),
    ("SLACK_TOKEN",        re.compile(r"(xox[bpoa]-[A-Za-z0-9\-]{10,255})")),
    ("DATABASE_URL",       re.compile(r"(?i)(postgres|mysql|mongodb|redis):\/\/[^\s\"'<>]{8,256}")),
    ("BEARER_TOKEN",       re.compile(r"(?i)bearer\s+([A-Za-z0-9\-_\.]{20,512})")),
    ("API_KEY_GENERIC",    re.compile(r"(?i)api[_\- ]?key[\s:=]+['\"]?([A-Za-z0-9_\-]{20,64})['\"]?")),
    ("PASSWORD_ASSIGN",    re.compile(r"(?i)(?:password|passwd|pwd)[\s:=]+['\"]([^'\"]{6,128})['\"]")),
    ("SECRET_ASSIGN",      re.compile(r"(?i)(?:secret|token)[\s:=]+['\"]([A-Za-z0-9_\-\.]{12,128})['\"]")),
    ("HIGH_ENTROPY_HEX",   re.compile(r"(?<![A-Za-z0-9])[0-9a-fA-F]{40,64}(?![A-Za-z0-9])")),
]

_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe",
    ".pdf", ".mp3", ".mp4", ".avi", ".bin",
}
_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox"}


class SecretAudit(BaseModule):
    """Scans files and directories for exposed secrets and credentials."""

    def __init__(self):
        super().__init__(module_name="secret_audit")

    def scan_file(self, path: str | Path, on_output=None) -> list[dict[str, Any]]:
        """Scan a single file for exposed secrets. Returns list of findings."""
        path = Path(path)
        findings: list[dict[str, Any]] = []

        if path.suffix.lower() in _SKIP_EXTENSIONS:
            return findings

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            return findings

        for line_no, line in enumerate(text.splitlines(), 1):
            for secret_type, pattern in _PATTERNS:
                match = pattern.search(line)
                if match:
                    finding = {
                        "file": str(path),
                        "line": line_no,
                        "type": secret_type,
                        "snippet": line.strip()[:120],
                    }
                    findings.append(finding)
                    if on_output:
                        on_output(f"[SECRET_AUDIT] {secret_type} at {path}:{line_no}\n")
                    break

        return findings

    def scan_directory(
        self,
        directory: str | Path,
        max_files: int = 2000,
        on_output=None,
    ) -> dict[str, Any]:
        """
        Recursively scan a directory for exposed secrets.
        Returns summary with all findings grouped by type.
        """
        directory = Path(directory)
        all_findings: list[dict[str, Any]] = []
        files_scanned = 0

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for fname in files:
                if files_scanned >= max_files:
                    break
                fpath = Path(root) / fname
                findings = self.scan_file(fpath, on_output=on_output)
                all_findings.extend(findings)
                files_scanned += 1

        by_type: dict[str, list[dict]] = {}
        for f in all_findings:
            by_type.setdefault(f["type"], []).append(f)

        summary = {
            "directory": str(directory),
            "files_scanned": files_scanned,
            "total_findings": len(all_findings),
            "findings_by_type": {k: len(v) for k, v in by_type.items()},
            "findings": all_findings,
        }

        self.log(f"SCAN_COMPLETE: {files_scanned} files, {len(all_findings)} secrets found")
        return summary

    def audit_git_history(
        self,
        repo_path: str | Path,
        on_output=None,
    ) -> list[dict[str, Any]]:
        """
        Scan recent git diff output for committed secrets.
        Uses `git log -p --all --since=90.days` under the hood.
        """
        import subprocess
        repo_path = Path(repo_path)
        findings: list[dict[str, Any]] = []

        try:
            result = subprocess.run(
                ["git", "log", "-p", "--all", "--since=90.days", "--unified=0"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            diff_text = result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return findings

        for line_no, line in enumerate(diff_text.splitlines(), 1):
            if not line.startswith("+"):
                continue
            for secret_type, pattern in _PATTERNS:
                match = pattern.search(line)
                if match:
                    finding = {
                        "source": "git_history",
                        "line": line_no,
                        "type": secret_type,
                        "snippet": line.strip()[:120],
                    }
                    findings.append(finding)
                    if on_output:
                        on_output(f"[GIT_AUDIT] {secret_type} in git history (line {line_no})\n")
                    break

        return findings
