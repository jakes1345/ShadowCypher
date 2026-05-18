# CWE Top 25 Most Dangerous Software Weaknesses (2023)

Source: MITRE CWE Top 25 2023

## The List

| Rank | CWE ID | Name | Category |
|------|--------|------|----------|
| 1 | CWE-787 | Out-of-bounds Write | Memory |
| 2 | CWE-79 | Cross-site Scripting (XSS) | Web |
| 3 | CWE-89 | SQL Injection | Injection |
| 4 | CWE-416 | Use After Free | Memory |
| 5 | CWE-78 | OS Command Injection | Injection |
| 6 | CWE-20 | Improper Input Validation | Validation |
| 7 | CWE-125 | Out-of-bounds Read | Memory |
| 8 | CWE-22 | Path Traversal | Filesystem |
| 9 | CWE-352 | Cross-Site Request Forgery (CSRF) | Web |
| 10 | CWE-434 | Unrestricted Upload of File with Dangerous Type | Web |
| 11 | CWE-862 | Missing Authorization | Access Control |
| 12 | CWE-476 | NULL Pointer Dereference | Memory |
| 13 | CWE-287 | Improper Authentication | Auth |
| 14 | CWE-190 | Integer Overflow | Memory |
| 15 | CWE-502 | Deserialization of Untrusted Data | Injection |
| 16 | CWE-77 | Command Injection | Injection |
| 17 | CWE-119 | Improper Restriction of Buffer Operations | Memory |
| 18 | CWE-798 | Use of Hard-coded Credentials | Credentials |
| 19 | CWE-918 | Server-Side Request Forgery (SSRF) | Web |
| 20 | CWE-306 | Missing Authentication for Critical Function | Auth |
| 21 | CWE-362 | Race Condition | Concurrency |
| 22 | CWE-269 | Improper Privilege Management | Access Control |
| 23 | CWE-94 | Code Injection | Injection |
| 24 | CWE-863 | Incorrect Authorization | Access Control |
| 25 | CWE-276 | Incorrect Default Permissions | Config |

## Key Weakness Details

### CWE-79: Cross-Site Scripting (XSS)
- **Stored XSS**: malicious script saved to database, served to all users
- **Reflected XSS**: payload in URL/form, reflected immediately
- **DOM-based XSS**: client-side JS reads attacker-controlled source into sink
- Prevention: output encoding (HTML entities), CSP headers, DOMPurify for HTML, avoid `innerHTML`

### CWE-89: SQL Injection
- Attacker-controlled input interpolated into SQL query
- Variants: UNION-based (exfil data), Error-based (enumerate), Blind (boolean/time)
- Prevention: parameterized queries / prepared statements ONLY; ORMs help but not immune; WAF supplemental only
- Example fix:
  ```python
  # WRONG
  cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
  # RIGHT
  cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
  ```

### CWE-78: OS Command Injection
- User input passed to shell command
- Prevention: avoid shell=True in Python subprocess; use argument arrays; validate/allowlist inputs
- Example:
  ```python
  # WRONG
  os.system(f"ping {host}")
  subprocess.run(f"ls {directory}", shell=True)
  # RIGHT
  subprocess.run(["ping", "-c", "1", host], shell=False)
  ```

### CWE-22: Path Traversal
- `../../../etc/passwd` to read files outside intended directory
- Prevention: `os.path.realpath()` + check prefix; avoid user-controlled paths in file operations
- Example:
  ```python
  import os
  safe_dir = "/var/uploads"
  user_path = os.path.realpath(os.path.join(safe_dir, user_input))
  if not user_path.startswith(safe_dir):
      raise ValueError("Path traversal detected")
  ```

### CWE-352: CSRF
- Forged request from attacker's site using victim's cookies
- Prevention: SameSite=Strict or Lax cookies; CSRF tokens; verify Origin/Referer header

### CWE-502: Insecure Deserialization
- Deserializing untrusted data can execute arbitrary code
- Affected: Java (ObjectInputStream), Python (pickle), PHP (unserialize), Ruby (Marshal)
- Prevention: never deserialize untrusted data with native deserializers; use JSON/Protobuf; HMAC-sign serialized data

### CWE-918: SSRF
- Server makes request to attacker-controlled URL
- Allows access to internal services, cloud metadata (AWS 169.254.169.254)
- Prevention: allowlist of valid URLs/IPs; block link-local, loopback, private ranges; use DNS rebinding protection

### CWE-787/125: Buffer Over-read/Overwrite
- C/C++ classic: write/read past array bounds
- Prevention: bounds checking, safe string functions, memory-safe languages (Rust, Go)
- Mitigations: ASLR, stack canaries, NX/DEP, AddressSanitizer in CI

### CWE-798: Hard-coded Credentials
- Passwords/keys in source code
- Detection: `truffleHog`, `gitleaks`, `detect-secrets`
- Prevention: environment variables, secrets managers (HashiCorp Vault, AWS Secrets Manager)

## OWASP Top 10 (2021) Mapping

| OWASP A-Number | OWASP Name | Related CWEs |
|----------------|-----------|-------------|
| A01 | Broken Access Control | CWE-862, CWE-863, CWE-284 |
| A02 | Cryptographic Failures | CWE-311, CWE-327, CWE-326 |
| A03 | Injection | CWE-89, CWE-79, CWE-78 |
| A04 | Insecure Design | CWE-209, CWE-256 |
| A05 | Security Misconfiguration | CWE-276, CWE-16 |
| A06 | Vulnerable Components | CWE-1035, CWE-937 |
| A07 | Auth & Session Failures | CWE-287, CWE-384 |
| A08 | Software Integrity Failures | CWE-502, CWE-829 |
| A09 | Logging Failures | CWE-778, CWE-117 |
| A10 | SSRF | CWE-918 |
