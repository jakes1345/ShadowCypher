"""
ShadowCypher Auto-Updater — checks GitHub releases, downloads, and applies updates.
Runs in background on startup; also callable from CLI: shadowcypher --update
"""

import json
import os
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

GITHUB_REPO = "jakes1345/ShadowCypher"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION_FILE = Path(__file__).parent.parent.parent / "VERSION"


def current_version() -> str:
    try:
        return CURRENT_VERSION_FILE.read_text().strip()
    except Exception:
        return "0.0.0"


def _fetch_latest() -> dict | None:
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={"User-Agent": "ShadowCypher-Updater/3.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _version_tuple(v: str):
    return tuple(int(x) for x in v.lstrip("v").split(".") if x.isdigit())


def check_for_update() -> dict | None:
    """Returns release info dict if an update is available, else None."""
    release = _fetch_latest()
    if not release:
        return None
    latest = release.get("tag_name", "").lstrip("v")
    if not latest:
        return None
    if _version_tuple(latest) > _version_tuple(current_version()):
        return {
            "version": latest,
            "url": release.get("html_url", ""),
            "notes": release.get("body", "")[:500],
            "assets": release.get("assets", []),
        }
    return None


def apply_update_git(project_root: Path):
    """Pull latest from git main branch (dev installs)."""
    try:
        subprocess.run(
            ["git", "pull", "--ff-only", "origin", "main"],
            cwd=project_root,
            check=True,
            capture_output=True,
        )
        return True, "Updated via git pull."
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode()


def apply_update_deb(deb_url: str) -> tuple[bool, str]:
    """Download and install a .deb release asset."""
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as tmp:
            urllib.request.urlretrieve(deb_url, tmp.name)
            subprocess.run(
                ["sudo", "-A", "dpkg", "-i", tmp.name],
                check=True,
            )
        os.unlink(tmp.name)
        return True, "Installed via .deb package."
    except Exception as e:
        return False, str(e)


def run_background_check(on_update_available=None):
    """Spawn a daemon thread that checks for updates silently."""
    def _worker():
        info = check_for_update()
        if info and on_update_available:
            on_update_available(info)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


if __name__ == "__main__":
    info = check_for_update()
    if not info:
        print(f"Already up to date (v{current_version()}).")
        sys.exit(0)
    print(f"Update available: v{info['version']}")
    print(f"Release notes:\n{info['notes']}\n")
    ans = input("Apply update now? [y/N] ").strip().lower()
    if ans == "y":
        root = Path(__file__).parent.parent.parent
        ok, msg = apply_update_git(root)
        print(msg)
        if ok:
            print("Restart ShadowCypher to apply.")
