# CVSS Scoring Reference

## CVSS v3.1 Overview

Common Vulnerability Scoring System v3.1 — industry standard for rating vulnerability severity.
Score range: 0.0–10.0

## Severity Ratings

| Score | Severity |
|-------|----------|
| 0.0 | None |
| 0.1–3.9 | Low |
| 4.0–6.9 | Medium |
| 7.0–8.9 | High |
| 9.0–10.0 | Critical |

## Base Score Metrics

### Attack Vector (AV)
- **Network (N)**: Remotely exploitable over internet — highest severity weight
- **Adjacent (A)**: Requires same network/Bluetooth/WiFi
- **Local (L)**: Requires local access (logged-in user, physical)
- **Physical (P)**: Requires physical device access

### Attack Complexity (AC)
- **Low (L)**: No special conditions; attacker can exploit at will
- **High (H)**: Race conditions, specific configurations required

### Privileges Required (PR)
- **None (N)**: No authentication needed
- **Low (L)**: Standard user account
- **High (H)**: Admin/root required

### User Interaction (UI)
- **None (N)**: No user action required (wormable)
- **Required (R)**: Victim must click/open/visit

### Scope (S)
- **Unchanged (U)**: Impact stays within vulnerable component
- **Changed (C)**: Attacker can impact resources beyond the vulnerable component

### CIA Impact (C/I/A)
- **High (H)**: Complete loss of confidentiality/integrity/availability
- **Low (L)**: Partial/limited impact
- **None (N)**: No impact

## Common Score Examples

| CVE | Score | Why |
|-----|-------|-----|
| Log4Shell (CVE-2021-44228) | 10.0 | AV:N, AC:L, PR:N, UI:N, S:C, C:H, I:H, A:H |
| EternalBlue (MS17-010) | 9.8 | AV:N, AC:L, PR:N, UI:N, S:U, C:H, I:H, A:H |
| Heartbleed (CVE-2014-0160) | 7.5 | AV:N, AC:L, PR:N, UI:N, S:U, C:H, I:N, A:N |
| Shellshock (CVE-2014-6271) | 9.8 | AV:N, AC:L, PR:N, UI:N, S:U, C:H, I:H, A:H |
| PrintNightmare (CVE-2021-34527) | 8.8 | AV:N, AC:L, PR:L, UI:N, S:U, C:H, I:H, A:H |
| Dirty COW (CVE-2016-5195) | 7.0 | AV:L, AC:H, PR:L, UI:N, S:U, C:H, I:H, A:H |
| BlueKeep (CVE-2019-0708) | 9.8 | AV:N, AC:L, PR:N, UI:N, S:U, C:H, I:H, A:H |

## Temporal Metrics (adjust base score)

- **Exploit Code Maturity (E)**: Unproven / Proof-of-Concept / Functional / High
- **Remediation Level (RL)**: Official Fix / Temporary / Workaround / Unavailable
- **Report Confidence (RC)**: Unknown / Reasonable / Confirmed

## Environmental Metrics

Adjust for your specific environment:
- **Modified Attack Metrics**: Override base metrics for your context
- **CIA Requirements**: How critical is C/I/A for this asset?
  - CR/IR/AR: Not Defined / Low / Medium / High

## CVSS v4.0 (2023)

New features in CVSS 4.0:
- Finer granularity: new metrics like Attack Requirements (AT), Recovery (RE), Value Density (VC/VI/VA)
- Renamed severity naming: Base → Base+Threat+Environmental
- Supplemental metrics (non-scoring): Safety, Automatable, Provider Urgency

## Prioritization Framework (SSVC)

CISA uses SSVC (Stakeholder-Specific Vulnerability Categorization):
- Factors: Exploitation status, Automatable, Technical Impact, Mission Impact
- Outcomes: Track / Track* / Attend / Act
- CISA KEV list = vulnerabilities known to be actively exploited → Act immediately

## Quick Triage Rules

1. CVSS ≥ 9.0 + on CISA KEV = patch within 24 hours
2. CVSS ≥ 7.0 + internet-facing = patch within 7 days
3. CVSS ≥ 4.0 + internal network = patch within 30 days
4. CVSS < 4.0 = patch next maintenance window
5. No CVE score but PoC public = treat as High
