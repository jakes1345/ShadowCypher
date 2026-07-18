#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // SOURCE CODE DATA SANITIZER
# ==============================================================================
# Scrubs secrets out of source files before public release.
# Secrets are loaded from .scrub_secrets.local (gitignored) — NEVER hardcoded.
#
# Usage:
#   1. Create .scrub_secrets.local in repo root (one secret per line: PATTERN=REPLACEMENT)
#   2. Run: python3 shadowcypher/scripts/deep_scrub.py [--dry-run]
#
# Secret file format (treated as literal strings, regex-escaped automatically):
#   shadow_admin1328!@=ADMIN_PASSWORD
#   97.243.145.96=MASTER_NODE_IP
#   192.168.1.1=GATEWAY_IP

import argparse
import logging
import os
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | [%(levelname)s] | %(message)s', datefmt='%H:%M:%S')

EXTENSIONS = (".py", ".js", ".json", ".sh", ".md", ".conf", ".shadow", ".html", ".css", ".yml", ".yaml", ".toml")
EXCLUDE_DIRS = {".git", "venv", "meta-venv", "__pycache__", "logs", "payloads", "configs",
                "node_modules", ".pytest_cache", "phish_data", ".gemini"}
SECRET_FILE = ".scrub_secrets.local"


def load_secrets(repo_root: Path) -> dict:
    """Load PATTERN=REPLACEMENT pairs from .scrub_secrets.local (literal strings)."""
    secret_path = repo_root / SECRET_FILE
    if not secret_path.exists():
        logging.error(f"Secret file missing: {secret_path}")
        logging.error("Create it with one PATTERN=REPLACEMENT per line. This file MUST be gitignored.")
        sys.exit(2)
    if (secret_path.stat().st_mode & 0o077) != 0:
        logging.warning(f"{SECRET_FILE} has world/group readable bits — chmod 600 recommended.")
    secrets = {}
    for raw in secret_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            logging.warning(f"Skipping malformed line: {line!r}")
            continue
        pattern, replacement = line.split("=", 1)
        pattern = pattern.strip()
        replacement = replacement.strip()
        if not pattern or not replacement:
            continue
        # Refuse to substitute a secret with itself (catches the old no-op bug)
        if pattern == replacement:
            logging.warning(f"No-op redaction skipped (pattern == replacement): {pattern!r}")
            continue
        secrets[re.escape(pattern)] = replacement
    if not secrets:
        logging.error("No valid redactions loaded — aborting.")
        sys.exit(2)
    logging.info(f"Loaded {len(secrets)} redaction patterns.")
    return secrets


def sanitize_file(filepath: Path, secrets: dict, dry_run: bool) -> int:
    """Apply all redactions to a single file. Returns number of substitutions."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logging.error(f"Read failed {filepath}: {e}")
        return 0

    total_subs = 0
    new_content = content
    for pattern, replacement in secrets.items():
        new_content, n = re.subn(pattern, replacement, new_content, flags=re.IGNORECASE)
        total_subs += n

    if total_subs > 0 and new_content != content:
        if dry_run:
            logging.info(f"[DRY-RUN] would redact {total_subs} match(es) in {filepath}")
        else:
            filepath.write_text(new_content, encoding="utf-8")
            logging.info(f"Redacted {total_subs} match(es) in {filepath}")
    return total_subs


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrub secrets from source tree.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing.")
    parser.add_argument("--root", default=os.getcwd(), help="Repo root (default: cwd).")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    print("\n" + "=" * 78)
    print(" SHADOWCYPHER // SOURCE CODE DATA SANITIZER")
    print(f" Root: {repo_root}   Mode: {'DRY-RUN' if args.dry_run else 'WRITE'}")
    print("=" * 78 + "\n")

    secrets = load_secrets(repo_root)

    file_count = 0
    modified_count = 0
    sub_count = 0

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if not f.endswith(EXTENSIONS):
                continue
            # Never touch the secrets file itself or this script
            if f == SECRET_FILE or f == "deep_scrub.py":
                continue
            path = Path(root) / f
            file_count += 1
            n = sanitize_file(path, secrets, args.dry_run)
            if n:
                modified_count += 1
                sub_count += n

    print("\n" + "=" * 78)
    print(f" [SUCCESS] SANITIZATION {'PREVIEW' if args.dry_run else 'COMPLETE'}")
    print("=" * 78)
    print(f"  Files analyzed: {file_count}")
    print(f"  Files modified: {modified_count}")
    print(f"  Total redactions: {sub_count}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
