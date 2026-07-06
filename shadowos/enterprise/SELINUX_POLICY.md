# SELinux Policy Framework for ShadowCypher Enterprise

## Overview

This document outlines the SELinux (Security Enhanced Linux) policy framework for ShadowCypher enterprise features, specifically designed to protect the Guardian vault and associated security infrastructure through mandatory access control (MAC).

## SELinux Fundamentals

### DAC vs MAC

**Discretionary Access Control (DAC)**
- Traditional UNIX/Linux permission model (rwx bits, ownership)
- Access decisions made by file owners
- Users can modify permissions on their own files
- Subject to privilege escalation through setuid/setgid exploits

**Mandatory Access Control (MAC)**
- Enforced by policy, not by user
- Access decisions based on security labels, not ownership
- Users cannot modify labels
- Provides fine-grained control independent of DAC

SELinux implements MAC through three subsystems: Type Enforcement (TE), Role-Based Access Control (RBAC), and Multi-Level Security (MLS).

## Type Enforcement (TE)

Type Enforcement is the primary mechanism in SELinux. Every object (file, process, socket) is labeled with a **type**, and access rules define what types can access what.

### Core Concepts

**Types**: Security identifiers assigned to subjects and objects
- Process types (domains): `guardian_vault_t`, `shadowcypher_agent_t`
- File types: `guardian_data_t`, `guardian_key_t`, `encrypted_storage_t`

**Domains**: Type labels for processes; represent a process context
- Only processes running in a domain can be labeled with that domain type
- Domain transitions occur when a process spawns another

**Attributes**: Collections of types grouped for policy convenience
- `guardian_domain`: All Guardian service domains
- `encrypted_data`: All encrypted file types
- `network_capable`: Types allowed network access

**Allow Rules**: Grant access
```
allow source_type target_type : object_class permission;
```

**Deny Rules**: Explicitly deny access (used rarely, usually for audit)

## Role-Based Access Control (RBAC)

RBAC adds a second layer of access control using roles and users.

### Components

**SELinux Users**: Associated with Linux users; define the set of roles available
- `guardian_u`: Guardian vault admin user
- `system_u`: System services
- `user_u`: Standard user (optional, for userspace processes)

**Roles**: Intermediate labels linking users to types
- `guardian_r`: Guardian vault administration role
- `system_r`: System services role

**User Rules**: Map SELinux users to roles
```
user guardian_u roles { guardian_r };
user system_u roles { system_r };
```

**Role Allow Rules**: Permit role transitions
```
allow guardian_r guardian_domain;
```

## Multi-Level Security (MLS)

MLS provides confidentiality and integrity labels using sensitivity levels and categories.

### MLS Components

**Sensitivities**: Linear classification levels
- `s0`: Unclassified (default)
- `s1`: Sensitive
- `s2`: Confidential

**Categories**: Compartments for fine-grained separation
- `c0-c31`: Available categories
- Example: `c0=vault`, `c1=keys`, `c2=audit_logs`

**MLS Levels**: Sensitivity + category combinations
- `s0`: Unclassified, no categories
- `s1:c0,c1`: Sensitive, vault and keys
- `s2:c0.c31`: Confidential, all compartments

**MLS Rules**: Control information flow
- **Read Down**: A process at level X can read level Y if Y dominates X
- **Write Up**: A process at level X can write level Y if X dominates Y
- These prevent information leakage between levels

## Policy Development Workflow

### 1. Define Security Goals

Before writing policy:
- Identify critical assets (Guardian vault, encryption keys)
- List threat scenarios (privilege escalation, lateral movement, data exfiltration)
- Define trust boundaries
- Set enforcement level (permissive for testing, enforcing for production)

### 2. Audit Baseline

Run system in permissive mode to identify required permissions:
```bash
semanage permissive -a guardian_vault_t
auditd logs policy violations without enforcing them
tail -f /var/log/audit/audit.log | grep AVC
```

### 3. Policy Development

Build policy incrementally:
1. Define types and domains
2. Create allow rules based on audit data
3. Compile and test in permissive mode
4. Switch to enforcing mode
5. Monitor audit logs for denials

### 4. Testing & Iteration

- Run functional tests in permissive mode
- Review AVC denials in logs
- Add allow rules for legitimate access
- Repeat until clean audit log
- Transition to enforcing for production

### 5. Deployment & Monitoring

- Load policy module into running kernel
- Monitor `/var/log/audit/audit.log` for violations
- Create alerts for critical denials
- Maintain audit trail for compliance

## Custom Domain and Type Definitions

### Guardian Vault Types

```
type guardian_vault_t;
type guardian_vault_exec_t;
type guardian_vault_tmp_t;
type guardian_vault_var_run_t;

type guardian_key_t;
type guardian_encrypted_data_t;
type guardian_audit_log_t;
```

### Attribute Definitions

Attributes group related types for concise policy rules:

```
attribute guardian_domain;
attribute guardian_tmpfs_type;
attribute encrypted_file_type;
attribute audit_readable_type;

typeattribute guardian_vault_t guardian_domain;
typeattribute guardian_vault_tmp_t guardian_tmpfs_type;
typeattribute guardian_encrypted_data_t encrypted_file_type;
```

### Domain Transitions

Process spawning is controlled via domain transitions:

```
type guardian_service_exec_t;
allow guardian_t guardian_service_exec_t : file execute_no_trans;
allow guardian_t guardian_service_t : process transition;
```

The `domain_auto_trans()` macro simplifies this:
```
domain_auto_trans(guardian_t, guardian_service_exec_t, guardian_service_t)
```

## File Transitions and Object Contexts

### Initial Contexts

Files are created with parent directory context by default. Use file transition rules to override:

```
type guardian_vault_data_t;
type guardian_vault_tmp_t;

# When guardian_vault_t creates files in /var/tmp, they get guardian_vault_tmp_t
filetrans_pattern(guardian_vault_t, var_t, guardian_vault_tmp_t, file)

# When guardian_vault_t creates directories in /var/lib/shadowcypher, they get guardian_vault_data_t
filetrans_pattern(guardian_vault_t, var_lib_t, guardian_vault_data_t, dir)
```

### Relabel and Restore Context

Set initial contexts in file_contexts:
```
/var/lib/shadowcypher/vault(/.*)?        -- system_u:object_r:guardian_vault_data_t:s0
/var/lib/shadowcypher/keys(/.*)?         -- system_u:object_r:guardian_key_t:s0
/usr/bin/guardian-vault                     system_u:object_r:guardian_vault_exec_t:s0
```

Restore contexts with:
```bash
restorecon -Rv /var/lib/shadowcypher
```

## Guardian Vault SELinux Integration

### Vault Process Context

The Guardian vault daemon runs with a dedicated domain:

```
type guardian_vault_t;
type guardian_vault_exec_t;

init_daemon_domain(guardian_vault_t, guardian_vault_exec_t)
```

### Encrypted Data Protection

- All vault data stored in `guardian_encrypted_data_t` type
- Only guardian_vault_t and authorized admin processes can read encrypted data
- Audit logs track all access attempts

### Key Material Access

```
type guardian_key_t;

# Only the vault can access key files
allow guardian_vault_t guardian_key_t : file { read };
deny ~guardian_vault_t guardian_key_t : file { read };
```

### Temporary File Handling

```
type guardian_vault_tmp_t;

# Vault can create and manage temp files
allow guardian_vault_t guardian_vault_tmp_t : file { create read write unlink };

# Temp files are automatically cleaned by cron jobs
allow initrc_t guardian_vault_tmp_t : dir { search };
allow initrc_t guardian_vault_tmp_t : file { delete };
```

### IPC and Signals

```
# Control signals between vault processes
allow guardian_vault_t guardian_vault_t : process { signal signull };

# DBus communication (if applicable)
allow guardian_vault_t system_dbus_t : unix_stream_socket connectto;
```

## Threat Model: Privilege Escalation Prevention

### Attack Scenario 1: Exploited Daemon

**Threat**: Attacker exploits vulnerability in guardian-vault service to gain code execution

**Mitigation**:
- Service runs in restricted domain (guardian_vault_t)
- Cannot access unrelated files (/etc, /home, etc.)
- Cannot change SELinux context
- Cannot execute arbitrary binaries
- Cannot access kernel memory

**Example Denial**:
```
AVC avc:  denied  { execute } for  pid=1234 comm="guardian-vault"
  name="bash" dev="dm-0" ino=12345 scontext=system_u:system_r:guardian_vault_t:s0
  tcontext=system_u:object_r:shell_exec_t:s0 tclass=file
```

### Attack Scenario 2: Lateral Movement

**Threat**: Compromised service attempts to access other daemon data

**Mitigation**:
- Each daemon has separate type (sshd_t, httpd_t, etc.)
- Allow rules specify exact access permissions
- Encrypted data types accessible only to vault

**Example Policy**:
```
# Deny by default
deny guardian_vault_t httpd_var_t : dir { search };
deny guardian_vault_t sshd_var_t : file { read };
```

### Attack Scenario 3: Unauthorized Key Access

**Threat**: Unprivileged user or service attempts to read encryption keys

**Mitigation**:
- Key files labeled guardian_key_t
- Only guardian_vault_t can read keys
- MLS context prevents read-down violations

**Example Rule**:
```
type guardian_key_t;
allow guardian_vault_t guardian_key_t : file { read };
neverallow ~guardian_vault_t guardian_key_t : file { read write };
```

### Attack Scenario 4: Audit Log Tampering

**Threat**: Attacker attempts to cover tracks by modifying audit logs

**Mitigation**:
- Audit logs in guardian_audit_log_t
- Write-protected; only audit daemon can write
- Read restricted to admin processes

**Example Rule**:
```
type guardian_audit_log_t;
allow auditd_t guardian_audit_log_t : file { write append };
neverallow ~auditd_t guardian_audit_log_t : file { write append };
```

## Policy Compilation and Loading

### Compile Policy Module

```bash
checkmodule -M -m -o selinux-policy.mod selinux-policy.te
semodule_package -o selinux-policy.pp -m selinux-policy.mod
```

### Load Into Kernel

```bash
semodule -i selinux-policy.pp
```

### Verify Loaded Policy

```bash
semodule -l | grep guardian
semanage fcontext -l | grep guardian
```

## Enforcement Modes

### Permissive Mode
- Policy violations logged but not enforced
- Use during development and testing
- Check audit.log for required rules

### Enforcing Mode
- All access must be explicitly allowed
- Violations blocked and logged
- Production deployment

### Disabled Mode
- SELinux entirely disabled
- Only use for debugging
- Requires reboot to enable

## Audit and Compliance

### AVC Denial Analysis

```bash
# Extract unique denials
grep "AVC avc: denied" /var/log/audit/audit.log | cut -d' ' -f9- | sort -u

# Convert to policy rules
ausearch -m AVC --ts recent | audit2allow -a -M guardian_allow
```

### Compliance Logging

- All access to encrypted data logged
- Guardian vault start/stop logged
- Key access attempts logged with timestamp and user
- Failed access attempts trigger alerts

## References

- SELinux Project: https://selinuxproject.org/
- Fedora SELinux Guide: https://docs.fedoraproject.org/en-US/selinux-user-guide/
- Red Hat SELinux Policy Guide: https://access.redhat.com/documentation/
- audit2allow Manual: man audit2allow
