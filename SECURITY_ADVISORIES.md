# Security Advisories

This document tracks past and current security advisories for ShadowCypher and its components. All reported vulnerabilities are listed here with remediation guidance.

---

## CVE-2024-9547 - Authentication Bypass in Guardian Module

**Severity:** High (CVSS 7.5)  
**CVE ID:** CVE-2024-9547  
**Affected Versions:** Guardian <= 2.1.4  
**Published:** 2024-11-15  
**Fixed In:** Guardian 2.1.5  

### Vulnerability Description
An authentication bypass vulnerability was discovered in the Guardian module's session token validation logic. Due to improper type coercion in the token comparison function, an attacker could craft a token that would match legitimate tokens without proper cryptographic verification.

### Impact
- Unauthorized access to Guardian audit logs
- Potential exposure of security assessment data
- Risk of privilege escalation to admin user level

### Remediation Steps
1. Upgrade Guardian module to version 2.1.5 or later
2. Audit all authentication logs for suspicious token patterns
3. Review recent session tokens for anomalies
4. Force re-authentication for all active users
5. Rotate master authentication keys

### Timeline
- **2024-10-22:** Vulnerability reported by security researcher
- **2024-11-01:** Root cause identified and patch developed
- **2024-11-15:** CVE assigned and advisory published
- **2024-11-15:** Version 2.1.5 released with fix

---

## CVE-2024-8921 - Denial of Service in Chroma Vector Database

**Severity:** Medium (CVSS 6.5)  
**CVE ID:** CVE-2024-8921  
**Affected Versions:** Chroma <= 0.4.2  
**Published:** 2024-10-08  
**Fixed In:** Chroma 0.4.3  

### Vulnerability Description
A denial of service vulnerability in Chroma's query handler allows an attacker to send specially crafted vector queries that cause excessive memory allocation and CPU usage, potentially crashing the database service.

### Impact
- Service unavailability
- Interruption of threat analysis and assessment workflows
- Data access delays during attacks

### Remediation Steps
1. Update Chroma to version 0.4.3 or later
2. Implement rate limiting on vector queries
3. Monitor database CPU and memory usage
4. Add query timeout enforcement (recommend 30s max)
5. Consider implementing request volume restrictions

### Timeline
- **2024-09-15:** DoS issue discovered during load testing
- **2024-09-28:** Root cause identified in query optimizer
- **2024-10-08:** CVE assigned, version 0.4.3 released
- **2024-10-15:** Recommended update period expires

---

## CVE-2024-7634 - Cryptographic Key Exposure in Arsenal Toolkit

**Severity:** Critical (CVSS 9.8)  
**CVE ID:** CVE-2024-7634  
**Affected Versions:** Arsenal <= 1.3.2  
**Published:** 2024-09-05  
**Fixed In:** Arsenal 1.3.3  

### Vulnerability Description
A critical vulnerability in the Arsenal toolkit's key derivation function caused encryption keys to be predictable based on minimal entropy input. This allowed attackers to brute-force cryptographic keys used for sensitive data encryption.

### Impact
- Complete compromise of encrypted Guardian assessments
- Exposure of all threat intelligence data
- Potential decryption of historical security records
- Loss of data confidentiality across the platform

### Remediation Steps
1. **URGENT:** Upgrade Arsenal to version 1.3.3 immediately
2. Rotate all encryption keys derived from Arsenal < 1.3.3
3. Re-encrypt all sensitive data using the fixed key derivation
4. Audit logs for unauthorized decryption attempts
5. Notify any users who may have exported encrypted data
6. Perform full security assessment of affected installations

### Timeline
- **2024-08-10:** Vulnerability discovered by internal security team
- **2024-08-20:** Patch developed and tested
- **2024-09-05:** CVE assigned and advisory published
- **2024-09-05:** Arsenal 1.3.3 released with comprehensive fix

---

## CVE-2024-6789 - SQL Injection in Policy Engine

**Severity:** High (CVSS 8.2)  
**CVE ID:** CVE-2024-6789  
**Affected Versions:** PolicyEngine <= 3.2.1  
**Published:** 2024-08-20  
**Fixed In:** PolicyEngine 3.2.2  

### Vulnerability Description
An SQL injection vulnerability exists in the Policy Engine's filter parsing logic. User-supplied policy filters were not properly sanitized before being passed to database queries, allowing attackers to execute arbitrary SQL.

### Impact
- Unauthorized read access to security policy data
- Potential modification of security policies
- Information disclosure about system configuration
- Possible authentication data exposure

### Remediation Steps
1. Update PolicyEngine to version 3.2.2 or later
2. Review all custom policies created in the past 90 days
3. Audit database access logs for suspicious queries
4. Validate all policies using the new validation tool
5. Run security scan: `bulletin-check.sh --deep-scan`

### Timeline
- **2024-07-25:** SQL injection reported via security@shadowcypher.site
- **2024-08-05:** Patch completed and tested
- **2024-08-20:** CVE assigned, version 3.2.2 released
- **2024-08-20:** Security advisory published

---

## CVE-2024-5412 - XSS in Audit Report Dashboard

**Severity:** Medium (CVSS 5.3)  
**CVE ID:** CVE-2024-5412  
**Affected Versions:** Dashboard <= 2.1.0  
**Published:** 2024-07-10  
**Fixed In:** Dashboard 2.1.1  

### Vulnerability Description
Stored cross-site scripting vulnerability in audit report comments allows users to inject JavaScript that executes in the browsers of other users viewing the same report.

### Impact
- Session hijacking of other users
- Malicious code execution in user browsers
- Potential credential theft
- Report data exfiltration

### Remediation Steps
1. Update Dashboard to version 2.1.1 or later
2. Audit all audit reports for suspicious comments
3. Clear browser cache and restart sessions
4. Review user activity logs for unusual patterns
5. Run client-side security audit tools

### Timeline
- **2024-06-15:** XSS vulnerability discovered in testing
- **2024-06-28:** Patch developed using OWASP recommendations
- **2024-07-10:** Version 2.1.1 released
- **2024-07-10:** Security advisory published

---

## CVE-2024-4156 - Information Disclosure in Error Messages

**Severity:** Low (CVSS 3.7)  
**CVE ID:** CVE-2024-4156  
**Affected Versions:** Core <= 1.2.3  
**Published:** 2024-06-05  
**Fixed In:** Core 1.2.4  

### Vulnerability Description
Detailed error messages in API responses inadvertently exposed information about internal system architecture, database schema, and configuration paths.

### Impact
- Information disclosure about system internals
- Potential aid to reconnaissance attacks
- Exposure of file paths and internal structures

### Remediation Steps
1. Update Core to version 1.2.4 or later
2. Review API logs for information disclosure attempts
3. Implement error message sanitization in custom endpoints
4. Test error responses for sensitive information leakage

### Timeline
- **2024-05-10:** Information disclosure noted in error responses
- **2024-05-25:** Fix implemented with generic error messages
- **2024-06-05:** Version 1.2.4 released
- **2024-06-05:** Advisory published

---

## CVE-2024-3389 - Race Condition in File Upload Handler

**Severity:** Medium (CVSS 6.1)  
**CVE ID:** CVE-2024-3389  
**Affected Versions:** FileHandler <= 1.1.1  
**Published:** 2024-05-20  
**Fixed In:** FileHandler 1.1.2  

### Vulnerability Description
A race condition in the file upload handler allows multiple simultaneous uploads to create duplicate files with escalated permissions, potentially leading to unauthorized file access.

### Impact
- Unauthorized file access
- Potential code execution via uploaded files
- System resource exhaustion
- Data integrity issues

### Remediation Steps
1. Upgrade FileHandler to version 1.1.2
2. Implement atomic file operations
3. Add mutex locks to file creation routines
4. Audit uploaded files for integrity
5. Review file permissions across the system

### Timeline
- **2024-04-15:** Race condition identified during stress testing
- **2024-05-05:** Fix implemented with proper file locking
- **2024-05-20:** Version 1.1.2 released
- **2024-05-20:** Security advisory published

---

## CVE-2024-2745 - Weak Password Hashing Algorithm

**Severity:** Medium (CVSS 6.2)  
**CVE ID:** CVE-2024-2745  
**Affected Versions:** Auth <= 2.0.1  
**Published:** 2024-04-12  
**Fixed In:** Auth 2.0.2  

### Vulnerability Description
Legacy password hashing algorithm with insufficient iteration count allowed faster password brute-force attacks. New installations used stronger parameters, but existing hashes remained vulnerable.

### Impact
- Easier password cracking for accounts created before version 2.0.2
- Potential account compromise
- Risk of credential reuse across services

### Remediation Steps
1. Update Auth to version 2.0.2 or later
2. Force password reset for all user accounts
3. Verify use of bcrypt with min 12 rounds (bcrypt2)
4. Monitor failed login attempts
5. Enable multi-factor authentication for all accounts

### Timeline
- **2024-03-20:** Weak hashing identified in security audit
- **2024-03-30:** Upgrade path designed and tested
- **2024-04-12:** Version 2.0.2 released with bcrypt2 migration
- **2024-04-12:** Advisory published and user notification sent

---

## CVE-2024-1923 - Insecure Deserialization in Arsenal

**Severity:** High (CVSS 7.8)  
**CVE ID:** CVE-2024-1923  
**Affected Versions:** Arsenal <= 1.2.5  
**Published:** 2024-03-08  
**Fixed In:** Arsenal 1.2.6  

### Vulnerability Description
Unsafe object deserialization in the Arsenal toolkit's data import function allows arbitrary code execution when processing malicious serialized objects.

### Impact
- Remote code execution
- Complete system compromise
- Data theft and manipulation
- Lateral movement risk

### Remediation Steps
1. **URGENT:** Update Arsenal to version 1.2.6 immediately
2. Disable data import functionality until patched
3. Audit system for signs of code execution
4. Review all imported datasets for validity
5. Perform forensic analysis of security logs
6. Reset all API credentials and tokens

### Timeline
- **2024-02-10:** Unsafe deserialization discovered in code review
- **2024-02-25:** Patch developed using safe deserialization
- **2024-03-08:** CVE assigned, version 1.2.6 released
- **2024-03-08:** URGENT advisory published

---

## CVE-2024-0567 - Default Credentials in Admin Panel

**Severity:** Critical (CVSS 9.9)  
**CVE ID:** CVE-2024-0567  
**Affected Versions:** AdminPanel <= 1.0.2  
**Published:** 2024-02-01  
**Fixed In:** AdminPanel 1.0.3  

### Vulnerability Description
Default administrative credentials (admin:shadowcypher2023) were shipped with installations and not forced to change on first login, allowing unauthorized administrative access.

### Impact
- Unauthorized administrative access
- Complete system compromise
- Ability to modify security policies
- Access to all user data and assessments

### Remediation Steps
1. **CRITICAL:** Update AdminPanel to version 1.0.3 immediately
2. Change all administrative passwords immediately
3. Audit all administrative actions in the past 90 days
4. Verify no unauthorized accounts were created
5. Force password change on next login
6. Enable admin action logging and alerting

### Timeline
- **2024-01-15:** Default credentials discovered in testing
- **2024-01-20:** Forced password change logic implemented
- **2024-02-01:** Version 1.0.3 released
- **2024-02-01:** CRITICAL advisory published

---

## Security Update Guidelines

### Reporting Vulnerabilities
- Email: security@shadowcypher.site
- Include: affected versions, reproduction steps, impact assessment
- Allow 90 days for patching before public disclosure

### Update Frequency
- Critical: Deploy within 24 hours
- High: Deploy within 1 week
- Medium: Deploy within 2 weeks
- Low: Deploy with next scheduled release

### Verification
Use `bulletin-check.sh` to verify your installation is not affected:
```bash
./bulletin-check.sh --advisory-check
./bulletin-check.sh --deep-scan
```
