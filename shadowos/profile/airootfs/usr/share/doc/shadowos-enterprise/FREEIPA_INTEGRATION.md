# FreeIPA Integration for ShadowCypher Enterprise

## Overview

FreeIPA is a centralized identity management and privilege access management (PAM) solution that integrates LDAP, Kerberos, DNS, and certificate authority (CA) services. This document describes how ShadowCypher leverages FreeIPA for enterprise identity management, particularly for Guardian vault integration and privilege escalation control.

## Architecture

### Core Components

1. **FreeIPA Server Cluster**
   - Replicated LDAP directory (389 Directory Server)
   - Kerberos KDC (Key Distribution Center) for authentication
   - Integrated DNS for service discovery
   - Red Hat Certificate System (RHCS) for certificate authority
   - Web UI and XML-RPC API for automation

2. **Identity Federation**
   - User provisioning from Guardian vault
   - Group management by security roles
   - Automatic sync on vault changes
   - External identity provider bridge (optional)

3. **Privilege Management**
   - Sudo rule deployment via FreeIPA
   - Role-based access control (RBAC)
   - Audit logging for all privilege grants
   - Automated revocation on role change

## User and Group Management

### User Provisioning

Users are provisioned from ShadowCypher's Guardian vault into FreeIPA with the following attributes:

```
- uid: Generated from vault user ID
- cn: Full name from vault profile
- mail: Email address from vault
- telephoneNumber: Phone from vault (optional)
- description: Role and clearance level
- userPassword: Kerberos principal password (generated)
```

### Group Mapping

Security roles in Guardian vault map to FreeIPA groups:

- `shadow-admins`: Guardian vault administrators
- `shadow-auditors`: Security auditors with read-only access
- `shadow-analysts`: Threat analysts with operational access
- `shadow-soc`: Security operations center staff
- `shadow-incident-response`: IR team with elevated privileges
- `shadow-compliance`: Compliance and risk management

### Group Rules

Automatic group membership rules based on vault attributes:

```
Rule: "incident-response-active"
  Condition: role == "incident-response" AND status == "active"
  Action: Add to shadow-incident-response
  
Rule: "auditor-read-only"
  Condition: role == "auditor"
  Action: Add to shadow-auditors, remove from other operational groups
```

## LDAP Integration

### Connection Parameters

```
Protocol: LDAPv3
Port: 389 (unencrypted), 636 (LDAPS)
Base DN: dc=shadowcypher,dc=site
Bind DN: uid=admin,cn=users,cn=accounts,dc=shadowcypher,dc=site
RootDSE: Automatic discovery
```

### Client Configuration

LDAP clients (application servers, workstations) are configured with:

1. **Server discovery** via DNS SRV records
2. **TLS certificate validation** against FreeIPA CA
3. **Authentication fallback** (primary/secondary servers)
4. **Connection pooling** and timeout settings
5. **Group nesting resolution** for privilege evaluation

### Sync Mechanism

One-way sync from Guardian vault to FreeIPA:

1. Query Guardian vault for user/role changes
2. Transform vault data to LDAP schema
3. Perform bulk LDAP modify operations (atomic batches)
4. Log all changes to audit trail
5. Trigger automatic client refresh via SSSD

## Kerberos Integration

### Realm Configuration

```
Realm: SHADOWCYPHER.SITE
KDC: freeipa-1.shadowcypher.site
KDC: freeipa-2.shadowcypher.site (replica)
Admin Server: freeipa-1.shadowcypher.site
Default Domain: shadowcypher.site
```

### Principal Formats

User principals follow the pattern:

```
username@SHADOWCYPHER.SITE
incident-response/admin@SHADOWCYPHER.SITE (service principal)
host/freeipa-1.shadowcypher.site@SHADOWCYPHER.SITE (host principal)
```

### Ticket Lifetime Policies

```
Default TGT lifetime: 24 hours
Service ticket lifetime: 1 hour
Renewable TGT: Up to 7 days
```

## Sudo Rule Deployment

### Rule Structure

Sudo rules define privilege escalation paths:

```
Rule Name: incident-response-sudo-all
Description: IR team sudo access to all commands
Users: %shadow-incident-response
Hosts: +shadowcypher-servers
Commands: ALL
Options: !authenticate, log_output
Runasuser: ALL
Runasgroup: ALL
```

### Role-Based Rules

1. **SOC Operators**
   - Can restart services (systemctl restart)
   - Can view logs (tail, journalctl)
   - Cannot modify system configuration

2. **Incident Response**
   - Full sudo access to investigation tools
   - Can access kernel crash dumps
   - Can suspend/kill processes
   - Cannot modify firewall rules

3. **System Administrators**
   - Full unrestricted sudo access
   - Can modify security policies
   - Can enroll/unenroll hosts

### Rule Deployment

Rules are deployed via:

1. `ipa sudorule-add` (create rule)
2. `ipa sudorule-add-user` (add user/group)
3. `ipa sudorule-add-host` (add target hosts)
4. `ipa sudorule-add-allow-command` (add allowed commands)

Changes are immediately effective on clients running SSSD with sudo provider enabled.

## Certificate Authority Integration

### CA Hierarchy

```
Root CA: ShadowCypher Root (self-signed)
↳ Intermediate CA: FreeIPA CA (enterprise signing)
  ↳ Server certificates (TLS for services)
  ↳ Client certificates (user authentication)
  ↳ Host certificates (machine identity)
```

### Certificate Issuance

FreeIPA issues certificates for:

1. **Service Certificates**
   - LDAP/TLS server certificates
   - Web UI HTTPS certificate
   - Kerberos KDC certificates

2. **User Certificates**
   - S/MIME email certificates (optional)
   - VPN client certificates
   - Smart card certificates

3. **Host Certificates**
   - Machine identity for mutual TLS
   - SSH host key backup
   - Automatic renewal prior to expiry

### Renewal Policy

```
- Certificate lifetime: 3 years
- Renewal: 60 days before expiry
- Automatic renewal: Enabled for hosts
- Manual renewal: User-initiated via web UI or CLI
```

## High-Availability Setup

### Replication Topology

Recommended production topology for HA:

```
            DNS (master)
                 |
         +-------+-------+
         |       |       |
      LDAP   LDAP    LDAP
       KDC    KDC     KDC
       CA1    CA2     CA3
```

3+ FreeIPA replicas in active-active configuration with:

- **Automatic replication** of LDAP changes
- **Kerberos KDC sync** via MIT Kerberos replication protocol
- **CA replication** via certmonger
- **DNS multi-master** for service discovery
- **Load balancing** via round-robin DNS or HAProxy

### Health Checks

Monitoring endpoints:

```
LDAP: ldapsearch -H ldaps://freeipa-1.shadowcypher.site
Kerberos: kinit -n
HTTP API: GET https://freeipa-1.shadowcypher.site/api/v2/status
DNS: dig @freeipa-1.shadowcypher.site _kerberos._tcp.shadowcypher.site SRV
```

### Failover Procedure

Automatic client failover via:

1. SSSD (System Security Services Daemon) service discovery
2. DNS SRV record lookups for _ldap._tcp, _kerberos._tcp
3. Manual failover: Update DNS or modify /etc/krb5.conf on clients

## Guardian Vault User Sync

### Sync Process

Bidirectional synchronization between Guardian vault and FreeIPA:

```
Guardian Vault (source of truth)
    ↓
    Change Detection (Vault audit log)
    ↓
    FreeIPA API Client
    ↓
    User/Group Create/Modify/Delete
    ↓
    LDAP Replication
    ↓
    Client SSSD Cache Update
```

### Vault Attributes → LDAP Mapping

| Guardian Vault | FreeIPA LDAP |
|---|---|
| user_id | uid |
| full_name | cn, displayName |
| email | mail |
| role | description, memberOf (groups) |
| clearance_level | clearanceLevel (custom) |
| active_status | nsAccountLock (boolean) |
| mfa_enabled | userCertificate (optional) |

### Sync Intervals

- User creation/deletion: Real-time (< 5 seconds)
- Role changes: Near real-time (< 30 seconds)
- Batch updates: Hourly reconciliation
- Failed operations: Queued for retry (exponential backoff)

### Conflict Resolution

1. Vault is source of truth for user attributes
2. FreeIPA is source of truth for Kerberos passwords
3. Manual override possible via LDAP but triggers vault reconciliation
4. Audit log tracks all conflicts and resolutions

## Password Policy Enforcement

### Password Requirements

```
Minimum length: 12 characters
Password history: 24 previous passwords remembered
Password expiry: 90 days
Warn before expiry: 14 days
Lockout after failed attempts: 6 attempts
Lockout duration: 30 minutes
Allow self-service password reset: Yes (via vault)
```

### Kerberos Key Rotation

```
- Automatic key rotation: Monthly
- Master key backup: Encrypted in vault
- Key versioning: Tracked for client compatibility
- Emergency key reset: Admin initiated, logged
```

### MFA Integration

Optional MFA in addition to password:

1. **TOTP (Time-based One-Time Password)**
   - Generated via FreeIPA TOTP plugin
   - Enrolled during user provisioning
   - Synced with Guardian vault

2. **Hardware Tokens**
   - Smart card support via PKCS#11
   - PIV (Personal Identity Verification) cards
   - Automatic certificate issuance

## Threat Model

### Security Considerations

1. **Centralized Authentication**
   - **Risk**: Single point of failure for authentication
   - **Mitigation**: Multi-replica HA setup, offline Kerberos support
   - **Monitoring**: Real-time replication lag detection

2. **LDAP Directory Exposure**
   - **Risk**: Directory contents reveal user list, group membership
   - **Mitigation**: TLS encryption mandatory, ACL-restricted reads, anonymous bind disabled
   - **Monitoring**: LDAP query audit logging

3. **Kerberos Key Compromise**
   - **Risk**: All authentication compromised if krb5.keytab leaked
   - **Mitigation**: Host keytabs protected with 0600 permissions, file integrity monitoring
   - **Monitoring**: Failed Kerberos auth attempts, key access audits

4. **Sudo Privilege Escalation**
   - **Risk**: Privilege grant misconfigurations allow unintended access
   - **Mitigation**: Principle of least privilege, command restrictions, command auditing
   - **Monitoring**: Sudo rule audit logs, failed sudo attempts

5. **Certificate Authority Compromise**
   - **Risk**: Ability to issue fraudulent certificates
   - **Mitigation**: CA access restricted to FreeIPA admins, certificate transparency logging
   - **Monitoring**: Certificate issuance audit logs, validity period enforcement

6. **Vault-FreeIPA Sync Inconsistency**
   - **Risk**: User access incorrectly provisioned or removed
   - **Mitigation**: Atomic operations, rollback on failure, periodic reconciliation
   - **Monitoring**: Sync error rates, user access mismatch alerts

### Audit Logging

All security-relevant operations are logged:

```
- User creation/modification/deletion
- Group membership changes
- Sudo rule modifications
- Certificate issuance/revocation
- Password resets
- Failed authentication attempts
- Privilege escalation (sudo usage)
- FreeIPA server administration
```

Logs are:

1. Stored in FreeIPA audit trail (kept for 90 days)
2. Exported to SIEM (Splunk, ELK) for long-term retention
3. Protected against tampering with digital signatures
4. Analyzed for anomalies (unusual sudo usage, group membership churn)

## Deployment Checklist

- [ ] Install FreeIPA server with HA replicas (3+ servers recommended)
- [ ] Configure DNS zones and service discovery records
- [ ] Enroll initial administrative users
- [ ] Create security groups matching Guardian vault roles
- [ ] Deploy SSSD clients on all servers
- [ ] Configure sudo providers on SSSD
- [ ] Create and test sudo rules
- [ ] Set up certificate authority and issue certificates
- [ ] Configure password policies
- [ ] Enroll Guardian vault users via API
- [ ] Set up replication monitoring and alerting
- [ ] Enable audit logging to SIEM
- [ ] Test failover scenarios
- [ ] Document emergency procedures

## References

- [FreeIPA Official Documentation](https://www.freeipa.org/page/Documentation)
- [MIT Kerberos Administrator Guide](https://web.mit.edu/kerberos/krb5-1.21/doc/)
- [LDAP RFC 4511](https://tools.ietf.org/html/rfc4511)
- [Sudo Defaults](https://www.sudo.ws/)
- [SSSD Configuration](https://sssd.io/)
