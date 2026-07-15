#!/usr/bin/env python3
"""
INTEL HARVEST — Dataset scraper for fine-tuning a security-focused LLM.

Sources:
  1. ExploitDB    — paginated exploit listings + code
  2. Metasploit   — modules/ tree from rapid7/metasploit-framework
  3. GitHub       — red-team / pentest / exploit / payload / offensive-security repos
  4. Nuclei       — local YAML templates (~/.local/nuclei-templates)

Output: JSONL (one document per line), deduplicated by content hash.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Optional deps
try:
    import requests
except ImportError:
    print("[FATAL] 'requests' is required. pip install requests", file=sys.stderr)
    sys.exit(2)

try:
    from bs4 import BeautifulSoup  # noqa: F401
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

UA = "ShadowCypher-IntelHarvest/1.0 (+https://shadowcypher.local)"
REQ_DELAY = 0.5  # seconds between requests


def progress(iterable, desc="", total=None):
    if HAS_TQDM:
        return tqdm(iterable, desc=desc, total=total, unit="doc")
    # plain fallback
    if total:
        print(f"[{desc}] {total} items")
    return iterable


def log(msg, tag="INFO"):
    print(f"[{tag}] {msg}", flush=True)


def hsh(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


class Writer:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.fp = path.open("w", encoding="utf-8")
        self.seen: set = set()
        self.counts: dict = {}
        self.bytes_written = 0

    def write(self, doc: dict) -> bool:
        text = doc.get("text") or ""
        if not text or len(text) < 32:
            return False
        h = hsh(text)
        if h in self.seen:
            return False
        self.seen.add(h)
        line = json.dumps(doc, ensure_ascii=False) + "\n"
        self.fp.write(line)
        self.bytes_written += len(line.encode("utf-8"))
        src = doc.get("source", "unknown")
        self.counts[src] = self.counts.get(src, 0) + 1
        return True

    def close(self):
        self.fp.close()


def http_get(url: str, headers=None, timeout=30, session=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    s = session or requests
    r = s.get(url, headers=h, timeout=timeout)
    return r


# ────────────────────────────────────────────────────────────────────────────
# 1. ExploitDB
# ────────────────────────────────────────────────────────────────────────────

EXPLOITDB_CSV = "https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_exploits.csv"
EXPLOITDB_RAW = "https://gitlab.com/exploit-database/exploitdb/-/raw/main/exploits/{path}"


def scrape_exploitdb(writer: Writer, limit: int):
    """
    Use the official exploit-database mirror (CSV index + raw files).
    The exploit-db.com site is Cloudflare-gated; the GitLab mirror is the
    canonical data source and is what offsec themselves publish.
    """
    log("ExploitDB: fetching index CSV...", "EDB")
    try:
        r = http_get(EXPLOITDB_CSV, timeout=60)
        if r.status_code != 200:
            log(f"ExploitDB index returned {r.status_code}", "EDB")
            return
        lines = r.text.splitlines()
    except Exception as e:
        log(f"ExploitDB index failed: {e}", "EDB")
        return

    import csv
    reader = csv.DictReader(lines)
    count = 0
    rows = list(reader)
    if limit:
        rows = rows[:limit]

    for row in progress(rows, desc="ExploitDB", total=len(rows)):
        if count >= limit:
            break
        path = row.get("file") or ""
        title = row.get("description") or row.get("title") or ""
        platform = row.get("platform") or ""
        cve = row.get("codes") or ""  # codes column has CVEs
        if not path:
            continue
        url = EXPLOITDB_RAW.format(path=path)
        try:
            time.sleep(REQ_DELAY)
            rr = http_get(url, timeout=30)
            if rr.status_code != 200:
                continue
            code = rr.text
        except Exception as e:
            log(f"  fetch fail {path}: {e}", "EDB")
            continue

        text = f"# {title}\n# Platform: {platform}\n# CVE: {cve}\n\n{code}"
        ok = writer.write({
            "source": "exploitdb",
            "title": title,
            "cve": cve,
            "platform": platform,
            "text": text,
            "type": "exploit",
        })
        if ok:
            count += 1

    log(f"ExploitDB: collected {count} exploits", "EDB")


# ────────────────────────────────────────────────────────────────────────────
# 2. Metasploit
# ────────────────────────────────────────────────────────────────────────────

MSF_TREE = "https://api.github.com/repos/rapid7/metasploit-framework/git/trees/master?recursive=1"
MSF_RAW = "https://raw.githubusercontent.com/rapid7/metasploit-framework/master/{path}"


def parse_msf_metadata(code: str) -> dict:
    """Extract Name/Description/References from a Metasploit Ruby module."""
    out = {"name": "", "description": "", "references": ""}
    m = re.search(r"['\"]Name['\"]\s*=>\s*['\"]([^'\"]+)['\"]", code)
    if m:
        out["name"] = m.group(1)
    # multi-line description (single or %q{})
    m = re.search(r"['\"]Description['\"]\s*=>\s*%q\{([^}]+)\}", code, re.DOTALL)
    if not m:
        m = re.search(r"['\"]Description['\"]\s*=>\s*['\"]([^'\"]+)['\"]", code, re.DOTALL)
    if m:
        out["description"] = m.group(1).strip()
    m = re.search(r"['\"]References['\"]\s*=>\s*\[(.*?)\]\s*,", code, re.DOTALL)
    if m:
        out["references"] = m.group(1).strip()
    return out


def scrape_metasploit(writer: Writer, limit: int, gh_headers: dict):
    log("Metasploit: fetching repo tree...", "MSF")
    try:
        r = http_get(MSF_TREE, headers=gh_headers, timeout=60)
        if r.status_code != 200:
            log(f"MSF tree returned {r.status_code}", "MSF")
            return
        tree = r.json().get("tree", [])
    except Exception as e:
        log(f"MSF tree failed: {e}", "MSF")
        return

    rb_paths = [
        n["path"] for n in tree
        if n.get("type") == "blob"
        and n.get("path", "").startswith("modules/")
        and n.get("path", "").endswith(".rb")
    ]
    if limit:
        rb_paths = rb_paths[:limit]

    count = 0
    for path in progress(rb_paths, desc="Metasploit", total=len(rb_paths)):
        if count >= limit:
            break
        try:
            time.sleep(REQ_DELAY)
            rr = http_get(MSF_RAW.format(path=path), timeout=30)
            if rr.status_code != 200:
                continue
            code = rr.text
        except Exception as e:
            log(f"  fetch fail {path}: {e}", "MSF")
            continue

        meta = parse_msf_metadata(code)
        title = meta["name"] or os.path.basename(path)
        platform = path.split("/")[1] if "/" in path else ""
        text = (
            f"# Metasploit Module: {title}\n"
            f"# Path: {path}\n"
            f"# Description: {meta['description']}\n"
            f"# References: {meta['references']}\n\n"
            f"{code}"
        )
        ok = writer.write({
            "source": "metasploit",
            "title": title,
            "cve": "",
            "platform": platform,
            "text": text,
            "type": "msf_module",
        })
        if ok:
            count += 1

    log(f"Metasploit: collected {count} modules", "MSF")


# ────────────────────────────────────────────────────────────────────────────
# 3. GitHub red-team repos
# ────────────────────────────────────────────────────────────────────────────

GH_SEARCH = "https://api.github.com/search/repositories"
GH_TOPICS = ["red-team", "pentest", "exploit", "payload", "offensive-security"]
TEXT_EXTS = {".py", ".sh", ".md", ".markdown", ".txt", ".rst"}
SKIP_NAMES = {"LICENSE", "LICENCE"}


def scrape_github(writer: Writer, limit: int, gh_headers: dict):
    log("GitHub: searching red-team repos...", "GH")
    per_topic = max(1, limit // len(GH_TOPICS))
    repos = []

    for topic in GH_TOPICS:
        try:
            time.sleep(REQ_DELAY)
            r = http_get(
                GH_SEARCH,
                headers=gh_headers,
                timeout=30,
            )
            # actual call w/ params
            r = requests.get(
                GH_SEARCH,
                params={"q": f"topic:{topic}", "sort": "stars", "per_page": min(per_topic, 50)},
                headers={"User-Agent": UA, **gh_headers},
                timeout=30,
            )
            if r.status_code != 200:
                log(f"  topic {topic} → {r.status_code}", "GH")
                continue
            for item in r.json().get("items", []):
                repos.append(item["full_name"])
        except Exception as e:
            log(f"  search fail {topic}: {e}", "GH")
            continue

    repos = list(dict.fromkeys(repos))  # dedupe, preserve order
    log(f"GitHub: {len(repos)} candidate repos", "GH")

    count = 0
    for full_name in progress(repos, desc="GitHub", total=len(repos)):
        if count >= limit:
            break
        try:
            time.sleep(REQ_DELAY)
            tree_url = f"https://api.github.com/repos/{full_name}/git/trees/HEAD?recursive=1"
            tr = requests.get(tree_url, headers={"User-Agent": UA, **gh_headers}, timeout=30)
            if tr.status_code != 200:
                continue
            files = tr.json().get("tree", [])
        except Exception as e:
            log(f"  tree fail {full_name}: {e}", "GH")
            continue

        for node in files:
            if count >= limit:
                break
            if node.get("type") != "blob":
                continue
            path = node.get("path", "")
            base = os.path.basename(path)
            ext = os.path.splitext(path)[1].lower()
            if base in SKIP_NAMES:
                continue
            if ext not in TEXT_EXTS:
                continue
            size = node.get("size", 0) or 0
            if size > 200_000:  # skip big
                continue

            raw = f"https://raw.githubusercontent.com/{full_name}/HEAD/{path}"
            try:
                time.sleep(REQ_DELAY)
                rr = requests.get(raw, headers={"User-Agent": UA}, timeout=30)
                if rr.status_code != 200:
                    continue
                # crude binary sniff
                if "\x00" in rr.text[:1024]:
                    continue
                content = rr.text
            except Exception:
                continue

            text = f"# Repo: {full_name}\n# Path: {path}\n\n{content}"
            ok = writer.write({
                "source": "github",
                "title": f"{full_name}/{path}",
                "cve": "",
                "platform": ext.lstrip("."),
                "text": text,
                "type": "redteam_repo",
            })
            if ok:
                count += 1

    log(f"GitHub: collected {count} files", "GH")


# ────────────────────────────────────────────────────────────────────────────
# 4. Nuclei templates
# ────────────────────────────────────────────────────────────────────────────

def scrape_nuclei(writer: Writer, limit: int):
    if not shutil.which("nuclei"):
        log("Nuclei: binary not found, skipping.", "NUC")
        return

    log("Nuclei: updating templates...", "NUC")
    try:
        subprocess.run(
            ["nuclei", "-update-templates"],
            check=False, capture_output=True, timeout=300
        )
    except Exception as e:
        log(f"  update warn: {e}", "NUC")

    candidates = [
        Path.home() / ".local" / "nuclei-templates",
        Path.home() / "nuclei-templates",
    ]
    root = next((p for p in candidates if p.exists()), None)
    if not root:
        log("Nuclei: template dir not found.", "NUC")
        return

    yaml_files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith((".yaml", ".yml")):
                yaml_files.append(Path(dirpath) / fn)
    if limit:
        yaml_files = yaml_files[:limit]

    count = 0
    for fp in progress(yaml_files, desc="Nuclei", total=len(yaml_files)):
        if count >= limit:
            break
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # extract id/name from YAML header (lightweight)
        title = fp.name
        m = re.search(r"^\s*name:\s*(.+)$", content, re.MULTILINE)
        if m:
            title = m.group(1).strip().strip("\"'")
        cve = ""
        m = re.search(r"(CVE-\d{4}-\d{4,7})", content, re.IGNORECASE)
        if m:
            cve = m.group(1).upper()
        platform = fp.relative_to(root).parts[0] if root in fp.parents else ""

        ok = writer.write({
            "source": "nuclei",
            "title": title,
            "cve": cve,
            "platform": platform,
            "text": content,
            "type": "nuclei_template",
        })
        if ok:
            count += 1

    log(f"Nuclei: collected {count} templates", "NUC")


# ────────────────────────────────────────────────────────────────────────────
# Entry
# ────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="ShadowCypher INTEL HARVEST — security corpus scraper")
    ap.add_argument("--sources", default="exploitdb,metasploit,github,nuclei",
                    help="comma-separated: exploitdb,metasploit,github,nuclei")
    ap.add_argument("--output", default="./data/security_corpus.jsonl")
    ap.add_argument("--limit", type=int, default=1000, help="max docs per source")
    ap.add_argument("--github-token", default=None,
                    help="GitHub PAT (falls back to $GITHUB_TOKEN)")
    args = ap.parse_args()

    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    output = Path(args.output).expanduser().resolve()
    token = args.github_token or os.environ.get("GITHUB_TOKEN")

    gh_headers = {"Accept": "application/vnd.github+json"}
    if token:
        gh_headers["Authorization"] = f"Bearer {token}"
        log("GitHub token: present", "INIT")
    else:
        log("GitHub token: NOT set (rate-limited to 60/hr)", "INIT")

    log(f"Sources: {sources}", "INIT")
    log(f"Output:  {output}", "INIT")
    log(f"Limit:   {args.limit} per source", "INIT")

    writer = Writer(output)
    t0 = time.time()

    runners = {
        "exploitdb":  lambda: scrape_exploitdb(writer, args.limit),
        "metasploit": lambda: scrape_metasploit(writer, args.limit, gh_headers),
        "github":     lambda: scrape_github(writer, args.limit, gh_headers),
        "nuclei":     lambda: scrape_nuclei(writer, args.limit),
    }

    for src in sources:
        if src not in runners:
            log(f"Unknown source: {src}", "WARN")
            continue
        try:
            runners[src]()
        except KeyboardInterrupt:
            log("Interrupted by user.", "STOP")
            break
        except Exception as e:
            log(f"Source {src} crashed: {e}", "ERROR")
            continue

    writer.close()
    dt = time.time() - t0

    print()
    print("═" * 60)
    print("  INTEL HARVEST — FINAL STATS")
    print("═" * 60)
    total = 0
    for src, n in sorted(writer.counts.items()):
        print(f"  {src:<14} {n:>6} docs")
        total += n
    print("─" * 60)
    print(f"  {'TOTAL':<14} {total:>6} docs")
    print(f"  Size          {writer.bytes_written/1_048_576:>6.2f} MiB")
    print(f"  Elapsed       {dt:>6.1f} s")
    print(f"  Output        {output}")
    print("═" * 60)


if __name__ == "__main__":
    main()
