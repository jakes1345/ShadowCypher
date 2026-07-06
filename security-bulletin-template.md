# Security Bulletin Template

This is the standard template for creating new ShadowCypher security bulletins and vulnerability announcements. Use this template for all official security advisories.

---

## Template: Security Advisory

```markdown
# [Bulletin Title]

**Severity:** [Critical | High | Medium | Low]  
**CVE ID:** [CVE-YYYY-NNNN]  
**Affected Versions:** [Module/Component] <= [version]  
**Published:** [YYYY-MM-DD]  
**Fixed In:** [Module/Component] [version]  

## Vulnerability Description

[2-3 sentences describing the technical nature of the vulnerability. Include the root cause and how it can be exploited. Be specific about the affected code/component.]

## Impact

[Bulleted list of impacts, organized by severity level:]
- [Highest impact first - e.g., "Remote code execution"]
- [Second-order impacts - e.g., "Data compromise"]
- [Third-order impacts - e.g., "Service disruption"]

## Affected Versions

- [Component] versions <= [version number]
- [Component] versions [version] through [version] (if multiple ranges)

## Proof of Concept (if applicable)

[Optional: Include a minimal PoC that demonstrates the vulnerability without enabling actual attacks]

```python
# Example: Do NOT include actual working exploits
# This is for internal understanding only
```

## Remediation Steps

1. [Immediate action - typically upgrade]
2. [Verification/audit step]
3. [Configuration change if needed]
4. [Monitoring/alerting setup]
5. [Optional: Long-term hardening measure]

## Detection

[Instructions for detecting if the system is vulnerable]

```bash
# Example: Check if vulnerable version is installed
./bulletin-check.sh --check-cve CVE-YYYY-NNNN
```

## Timeline

- **[YYYY-MM-DD]:** Vulnerability reported / discovered
- **[YYYY-MM-DD]:** Root cause identified and investigation began
- **[YYYY-MM-DD]:** Patch developed and tested
- **[YYYY-MM-DD]:** CVE assigned (if applicable)
- **[YYYY-MM-DD]:** Fixed version released
- **[YYYY-MM-DD]:** Advisory published

## References

- [Link to patch/commit]
- [Link to related documentation]
- [CVSS Score: https://www.first.org/cvss/calculator/3.1]

## Contact

For questions about this advisory:
- Email: security@shadowcypher.site
- GitHub Security Advisory: [link]
```

---

## Creating a New Bulletin: Step-by-Step Guide

### 1. Gather Information
- [ ] Get exact CVE ID from mitre.org or NIST
- [ ] Document affected versions (check git history for version tags)
- [ ] Identify root cause with code references
- [ ] Calculate CVSS score (use https://www.first.org/cvss/calculator/)
- [ ] Determine patch status and release timeline

### 2. Choose Severity Level

**Critical (CVSS 9.0-10.0)**
- Remote code execution
- Complete system compromise
- Default credentials allowing admin access
- Cryptographic bypass affecting all data
- **Action:** Release hotfix, notify users immediately

**High (CVSS 7.0-8.9)**
- Authentication/authorization bypass
- Significant information disclosure
- Denial of service with impact
- Vulnerability affecting core security functions
- **Action:** Release patch within 1 week, notification recommended

**Medium (CVSS 4.0-6.9)**
- Limited impact DoS
- XSS/CSRF in non-admin areas
- Information disclosure of non-sensitive data
- Logic errors affecting specific workflows
- **Action:** Schedule patch, include in next release

**Low (CVSS 0.1-3.9)**
- Information disclosure (non-sensitive)
- Minor logic flaws
- Hardening recommendations
- **Action:** Include in next scheduled release

### 3. Write Clear, Precise Descriptions

**DO:**
- Be specific: "The Token validation function uses loose comparison (==) instead of strict (===) causing type coercion issues"
- Include affected code paths: "Guardian/auth/token_validator.py:145-156"
- Explain the exploitation scenario clearly
- Use technical but accessible language

**DON'T:**
- Be vague: "There's a security issue in the system"
- Exaggerate impact: "Affects all users" when it's limited to specific configs
- Include working exploits or attack code
- Use alarmist language without justification

### 4. Provide Actionable Remediation

**Structure each step as executable:**
- ✗ "Fix the vulnerability"
- ✓ "Update [component] to version 1.2.3: `pip install --upgrade shadowcypher-component==1.2.3`"

**Include verification:**
```bash
# Verify the fix is in place
./bulletin-check.sh --verify-cve CVE-YYYY-NNNN
```

### 5. Add Timeline for Transparency

Show the investigation and development process:
```
2024-01-15 → 2024-01-20 = Diagnosis phase
2024-01-20 → 2024-02-01 = Fix development and testing
2024-02-01 → [today] = Public disclosure delay (responsible disclosure)
```

### 6. Review Before Publishing

**Checklist:**
- [ ] All version numbers verified against git tags
- [ ] CVSS score calculated and documented
- [ ] Remediation steps tested by at least 2 team members
- [ ] Grammar and clarity reviewed
- [ ] No unintended information disclosure in the advisory itself
- [ ] Timeline is accurate and complete
- [ ] Affected versions list is exhaustive
- [ ] No working exploit code included

---

## Example Bulletin (Realistic, Fictional)

### CVE-2024-5555 - Session Fixation in Guardian Module

**Severity:** High (CVSS 7.9)  
**CVE ID:** CVE-2024-5555  
**Affected Versions:** Guardian <= 2.0.3  
**Published:** 2024-05-15  
**Fixed In:** Guardian 2.0.4  

### Vulnerability Description

A session fixation vulnerability exists in the Guardian module's session initialization routine. When a user logs in, the existing session ID is not invalidated, allowing an attacker to craft a session ID before authentication and have the user's authenticated session bound to that ID. The vulnerability exists in `guardian/auth/session_manager.py` lines 67-81, where `session.regenerate()` is called after authentication but the old session is not explicitly destroyed.

### Impact

- Session hijacking: An attacker can predict or set a session ID and force a user to use it
- Account takeover after login
- Potential access to assessments and audit logs
- Risk of privilege escalation if admin session is fixed

### Affected Versions

- Guardian <= 2.0.3 (all configurations)
- Guardian 2.1.0-beta through 2.1.2 (beta release track)

### Remediation Steps

1. **Upgrade immediately:** `pip install --upgrade shadowcypher-guardian==2.0.4`
2. **Invalidate all sessions:**
   ```bash
   ./bulletin-check.sh --clear-sessions
   # Or manually: DELETE FROM sessions WHERE created_at < NOW();
   ```
3. **Force re-authentication:** Users must log in again
4. **Monitor for suspicious activity:**
   ```bash
   ./bulletin-check.sh --audit-sessions --time-range "7 days"
   ```
5. **Enable session binding:** Ensure IP-based session binding is enabled in config:
   ```yaml
   session:
     bind_to_ip: true
     timeout: 3600
   ```

### Detection

Check if you're running a vulnerable version:
```bash
./bulletin-check.sh --check-version guardian
# Output: guardian version 2.0.3 - VULNERABLE to CVE-2024-5555
```

### Timeline

- **2024-04-10:** Session fixation discovered by security researcher via email
- **2024-04-15:** Root cause identified: missing session invalidation
- **2024-04-28:** Patch developed and validated in test environment
- **2024-05-05:** QA testing completed, patch approved for release
- **2024-05-15:** Guardian 2.0.4 released with fix
- **2024-05-15:** Security advisory published

### Technical Details

**Root Cause:** The session initialization code creates a new session but does not invalidate the previous one:

```python
# guardian/auth/session_manager.py (VULNERABLE)
def authenticate_user(user_id):
    # ... authentication check ...
    session.user_id = user_id  # Assigns to existing session ID
    session.regenerate()        # Creates new session but old one persists
    # Missing: session.invalidate_old()
```

**Fix:**
```python
def authenticate_user(user_id):
    old_session_id = session.id
    session.user_id = user_id
    session.regenerate()
    session.invalidate(old_session_id)  # Explicitly destroy old session
```

---

## Common Mistakes to Avoid

1. **Vague timelines** - Always be specific with dates (YYYY-MM-DD)
2. **Missing version ranges** - List all affected versions, not just the latest
3. **Incomplete remediation** - Include verification steps, not just "upgrade"
4. **Exaggerated CVSS** - Calculate accurately; don't round up for impact
5. **Working exploits** - Never include proof-of-concept that actually works
6. **Delayed disclosure** - Follow responsible disclosure (90-day window)
7. **Unclear impact** - Describe specific systems and data affected
8. **No timeline** - Always show investigation and development time

---

## Publishing Checklist

Before posting the advisory to SECURITY_ADVISORIES.md:

- [ ] Patch released to all supported versions
- [ ] Advisory reviewed by 2+ security team members
- [ ] CVSS score validated
- [ ] All remediation steps tested
- [ ] Version numbers match actual releases
- [ ] Timeline is complete and accurate
- [ ] No sensitive information disclosed
- [ ] User notification email drafted (if severity >= High)
- [ ] Advisory added to SECURITY_ADVISORIES.md
- [ ] GitHub security advisory created (if applicable)
- [ ] Blog post planned (for critical/high severity)

---

## Filing a Security Report

If you discover a vulnerability in ShadowCypher:

1. **Do NOT** open a public GitHub issue
2. **Do** email: security@shadowcypher.site
3. Include:
   - Affected component and versions
   - Description of vulnerability
   - Steps to reproduce (if safe)
   - Estimated impact
   - Any suggested fixes
4. Allow 90 days for patch before public disclosure
5. Acknowledge reporter in advisory (if requested)

---

## Reference: CVSS 3.1 Scoring

| Score Range | Severity | Response Time |
|---|---|---|
| 9.0-10.0 | Critical | Immediate (24h) |
| 7.0-8.9 | High | 1 week |
| 4.0-6.9 | Medium | 2 weeks |
| 0.1-3.9 | Low | Next release |

**Calculate CVSS:** https://www.first.org/cvss/calculator/3.1

Consider:
- Attack Vector (Network vs Local)
- Attack Complexity (Low vs High)
- Privileges Required (None vs Low vs High)
- User Interaction (None vs Required)
- Scope (Unchanged vs Changed)
- Confidentiality Impact (High vs Low vs None)
- Integrity Impact (High vs Low vs None)
- Availability Impact (High vs Low vs None)
