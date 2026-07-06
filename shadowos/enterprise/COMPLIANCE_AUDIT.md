# ShadowCypher Compliance Audit Logging

## Overview

Compliance audit logging is the foundation of ShadowCypher's enterprise security posture. This system provides comprehensive logging, monitoring, and reporting for all security-relevant events across the platform, ensuring adherence to SOC2, ISO/IEC 27001, and other regulatory frameworks.

## Architecture

### Core Components

1. **auditd Integration**: Kernel-level system call auditing via Linux auditd
2. **Event Filtering Engine**: Application-level event categorization and enrichment
3. **Log Aggregation**: Centralized storage with rotation and archival
4. **Tamper Detection**: Cryptographic verification and integrity checking
5. **Alert System**: Real-time notifications for suspicious activities
6. **Reporting Engine**: Automated compliance report generation
7. **Archive System**: Long-term retention with encryption and indexing

### Data Flow

```
System Events → auditd → Event Filter → Log Aggregation → Archive/Alert
                  ↓          ↓              ↓
            Kernel Calls  Rules Engine  Rotation
                                        Archival
```

## Event Types and Logging Rules

### System-Level Events

**Authentication & Access Control**
- User login/logout attempts (successful and failed)
- sudo/privilege escalation attempts
- SSH key changes
- User account creation/modification/deletion
- Group membership changes
- SELinux policy violations

**File & Directory Operations**
- Sensitive file modifications (Guardian vault, configs, keys)
- Permission changes on audit logs
- File deletion attempts
- Unauthorized read access to protected files
- Symbolic link modifications

**Process Monitoring**
- Execution of sensitive binaries (crypto tools, system utilities)
- Child process spawning from network daemons
- Core dump generation
- Signal handling (SIGKILL, SIGSTOP)

**Network Activity**
- Inbound connection attempts
- Raw socket creation
- iptables/firewall rule modifications
- Network namespace changes
- DNS query logging (for threat detection)

### Application-Level Events

**Vault Operations**
- Unlock/lock events with user and timestamp
- Key derivation operations
- Decryption/encryption operations
- Recovery code usage
- Master password changes

**Guardian Security Events**
- Module configuration changes
- Policy enforcement actions
- Incident response execution
- Threat detection triggers
- Audit agent status changes

**Administrative Actions**
- Configuration file modifications
- Encryption key material handling
- License/subscription changes
- User permission modifications
- API key rotation

### Audit Rules Configuration

The system implements comprehensive rules across multiple categories:

- **Executable Tracking**: Monitor execution of cryptographic tools
- **Sensitive Data Access**: Track access to Guardian vault storage
- **Configuration Changes**: Log all configuration file modifications
- **Deletion Monitoring**: Prevent unlogged deletion of critical files
- **Network Monitoring**: Track unusual network behavior
- **System Call Filtering**: Application-specific system call monitoring

## Tamper Detection and Protection

### Cryptographic Verification

1. **Audit Log Signatures**
   - Each log entry is signed with HMAC-SHA256
   - Key derivation from system-provided entropy
   - Signatures verified during archival process
   - Failed verification triggers immediate alerts

2. **Log Chain Integrity**
   - Sequential checksums linking log entries
   - Hash chain prevents insertion/deletion of entries
   - Root hash stored in secure location
   - Periodic verification of chain integrity

3. **Timestamp Verification**
   - NTP-synchronized timestamps with leap second handling
   - Detection of clock skew/manipulation attempts
   - Correlation with system journal timestamps
   - Timezone-aware processing

### Access Controls

- Audit logs readable only by root and designated audit users
- Write permission restricted to audit daemon only
- Immutable attribute set on rotated/archived logs
- Regular permission verification

### Anomaly Detection

- Baseline establishment for normal activity patterns
- Detection of unusual access patterns
- Alert on multiple failed authentication attempts
- Monitor for audit log size anomalies
- Track daemon restart/failure events

## Log Retention and Archival

### Retention Policy

**Hot Storage** (Active Logs)
- Retained for 30 days in `/var/log/audit`
- Size limit: 500MB per file
- Rotation occurs daily or at size limit
- Real-time alerting enabled

**Warm Storage** (Recent Logs)
- Retained for 90 days in `/var/audit/archive`
- Compressed with xz (compression level 6)
- Checksummed for integrity verification
- Accessible for investigation and analysis

**Cold Storage** (Long-term Retention)
- Retained for 2555 days (7 years) for compliance
- Stored in encrypted, write-protected format
- Indexed by date and audit rule category
- Requires explicit authorization for access
- Stored off-site with regular verification

### Archival Process

1. **Trigger Events**
   - Daily at 01:00 UTC
   - When log file reaches 100MB
   - Manual trigger via compliance-audit.sh archive
   - Triggered by backup/snapshot procedures

2. **Processing Steps**
   - Verify log integrity (HMAC check)
   - Generate summary statistics
   - Compress with xz compression
   - Create indexed metadata file
   - Encrypt with system key (AES-256-GCM)
   - Generate retention manifest
   - Transmit to archive destination
   - Delete source after confirmation

3. **Archive Metadata**
   - Date range covered
   - Event count by category
   - Checksum of compressed data
   - Encryption key reference
   - Retention expiration date

### Storage Locations

- **Active**: `/var/log/audit/audit.log*`
- **Archive**: `/var/audit/archive/`
- **Remote**: Configured in audit-policy.json
- **Backup**: Cross-replicated to secondary site

## Integration with SOC/SIEM Systems

### Export Formats

**CEF (Common Event Format)**
- Standard format for security monitoring
- Support for real-time streaming
- Field mapping for Guardian events
- Severity classification aligned with incident response

**Syslog (RFC 3164 & RFC 5424)**
- Standard UDP/TLS transport
- Facility code: LOCAL2 (144)
- Structured data support for extended fields
- Rate limiting to prevent SIEM flooding

**JSON Lines**
- One JSON object per line
- Suitable for log aggregation platforms
- Includes all audit context
- Compatible with Splunk, ELK, DataDog, Sumo Logic

### SIEM Integration

**Real-time Stream**
- TLS connection to SIEM collector
- Mutual authentication with certificates
- Compression enabled for bandwidth optimization
- Automatic reconnection on failure

**Batch Export**
- Daily export of previous day's logs
- Scheduled at 02:00 UTC
- Includes summary statistics
- Supports multiple SIEM platforms simultaneously

**Alert Forwarding**
- High-severity events forwarded immediately
- Alert correlation with SIEM rules
- Custom alert rules defined in audit-policy.json
- Integration with incident response workflows

## Compliance Standards

### SOC2 Type II

**Trust Service Criteria Addressed**
- CC6.1: Logical Access Controls - comprehensive audit trail
- CC7.1: System Monitoring - real-time monitoring and alerting
- CC7.2: Monitoring Tools - audit logging for security analysis
- A1.2: Availability - audit system redundancy and recovery

**Audit Evidence**
- Logs demonstrate access controls enforcement
- Tamper detection shows log integrity
- Retention policy ensures historical data availability
- Alert logs show timely detection of anomalies

### ISO/IEC 27001

**Controls Mapping**
- A.12.4.1: Recording user activities (audit logging)
- A.12.4.3: Administrator and operator logs
- A.12.4.4: Synchronization of system clocks
- A.14.2.1: Change log maintenance
- A.13.1.3: Logging of information security events

**Documentation Requirements**
- Audit policy and procedures documented
- Log retention schedule formalized
- Access controls to audit logs defined
- Regular review procedures established

### PCI DSS (if applicable)

**Requirements**
- 10.1: All access to audit trails
- 10.2: Implementation of user identification
- 10.3: Restrict access to audit trail history
- 10.7: Retain audit trail for at least one year

### HIPAA (if applicable)

**Security Rule**
- Audit Control (164.312(b))
- Implement recording and examination of access to ePHI
- 6-year minimum retention
- Automatic audit controls

## Incident Response Workflows

### Detection Phase

1. **Alert Generation**
   - Real-time evaluation against anomaly rules
   - Correlation with previous events
   - Context enrichment with system information
   - Severity classification (Critical/High/Medium/Low)

2. **Alert Routing**
   - Critical: Immediate email + Slack + PagerDuty
   - High: Queued for immediate investigation
   - Medium: Daily digest
   - Low: Archive for trend analysis

### Investigation Phase

1. **Log Retrieval**
   - Query by time range, user, system, event type
   - Cross-reference with SIEM data
   - Timeline reconstruction
   - Related event correlation

2. **Context Analysis**
   - Before/after snapshots of affected systems
   - System state at time of incident
   - Network connectivity analysis
   - Process memory/file access patterns

### Response Phase

1. **Remediation Actions**
   - Documented in incident response logs
   - Each action includes authorization
   - Change management integration
   - Automatic verification of remediation

2. **Containment**
   - Network isolation if necessary
   - Account lockdown procedures
   - Key rotation if compromise suspected
   - Automated rollback capabilities

### Post-Incident

1. **Analysis**
   - Root cause determination
   - Timeline reconstruction
   - Impact assessment
   - Preventive measures identified

2. **Documentation**
   - Incident report generation
   - Audit log export for investigation
   - Lessons learned documentation
   - Policy update requirements

## Guardian Vault Audit Trail

### Vault Operation Events

**Unlock Operations**
```
Event: vault.unlock
Fields:
  - user_id: authenticated user identifier
  - timestamp: UTC timestamp
  - duration: unlock period (seconds)
  - ip_address: source IP
  - mfa_used: boolean
  - unlock_method: password|recovery_code|biometric
```

**Decryption Events**
```
Event: vault.decrypt
Fields:
  - user_id: authenticated user
  - timestamp: UTC timestamp
  - key_type: stored_password|identity|totp|note
  - key_id: unique key identifier
  - action: read|export|modify
  - purpose: user_provided|system_generated
```

**Key Management Events**
```
Event: vault.key_operation
Fields:
  - user_id: authenticated user
  - timestamp: UTC timestamp
  - operation: generate|import|rotate|delete|backup
  - key_type: master_key|individual_entry_key
  - status: success|failure
  - error_message: if applicable
```

**Recovery Events**
```
Event: vault.recovery
Fields:
  - user_id: authenticated user
  - timestamp: UTC timestamp
  - recovery_type: password_reset|account_recovery|key_restore
  - recovery_code_used: boolean
  - authorization: self_service|admin_assisted
  - status: success|failure
```

### Access Pattern Analysis

- Frequency of vault access per user
- Unusual access times or patterns
- Access from new devices/locations
- Concurrent access attempts
- Bulk export operations

### Integrity Monitoring

- Vault database size monitoring
- Hash verification of vault contents
- Detection of unauthorized modifications
- Encryption integrity checks
- Backup consistency verification

## Monitoring and Alerting

### Key Metrics

**Availability**
- Audit daemon uptime percentage (target: 99.99%)
- Log rotation success rate (target: 100%)
- Archive completion rate (target: 100%)
- Alert delivery success rate (target: 99.95%)

**Performance**
- Average log write latency (<50ms)
- Archive processing time (<1 hour for daily logs)
- SIEM export latency (<5 minutes)
- Alert generation latency (<2 seconds)

**Security**
- Failed authentication attempts
- Tamper detection triggers
- Unauthorized access attempts
- Compliance violation detections

### Alert Thresholds

- More than 5 failed login attempts in 1 minute: High
- Modification of audit rules: Critical
- Audit daemon restart: High
- Archive failure: Critical
- Log file size exceeding 95% of quota: Medium
- HMAC verification failure: Critical

## Maintenance and Monitoring

### Regular Reviews

**Daily**
- Audit daemon status verification
- Critical alert review
- Archive completion confirmation

**Weekly**
- Log volume trending
- Performance metric review
- SIEM integration validation
- Archive integrity spot checks

**Monthly**
- Compliance report generation
- Policy effectiveness review
- Retention schedule verification
- System capacity planning

**Quarterly**
- Formal audit of audit system
- Disaster recovery testing
- Alert rule effectiveness analysis
- Compliance standard verification

### Disaster Recovery

**Audit Daemon Failure**
- Automatic detection and restart
- Alert on repeated failures
- Fallback to syslog mode
- Manual intervention procedures

**Log Storage Failure**
- Failover to secondary storage
- Data loss window minimization
- Automatic resynchronization
- Archive integrity verification

**Archive Corruption**
- Detection during integrity checks
- Restoration from secondary copy
- Investigation of cause
- Root cause remediation

## Compliance Reporting

### Automated Reports

**Daily Summary**
- Total events logged
- Critical events summary
- System health status
- Archive completion status

**Weekly Digest**
- Top users by activity
- High-risk event summary
- Compliance violations
- System performance metrics

**Monthly Report**
- Comprehensive event analysis
- Compliance control assessment
- User access patterns
- Policy violation summary

**Annual Audit Report**
- Year-over-year trends
- Incident summary
- Compliance certifications
- Policy recommendations

### Evidence Collection

Reports include:
- Sample audit entries (with sensitive data redacted)
- Verification of tamper detection functionality
- Archive integrity proof
- SIEM integration logs
- Alert system operational logs

## Security Best Practices

1. **Segregation of Duties**: Separate audit review from system administration
2. **Independent Verification**: Regular third-party audit of audit system
3. **Least Privilege**: Users have minimum necessary permissions
4. **Defense in Depth**: Multiple layers of protection for audit logs
5. **Documentation**: All procedures and changes documented
6. **Testing**: Regular drills and simulations
7. **Training**: Staff educated on audit procedures
8. **Automation**: Minimize manual intervention where possible

## Implementation Checklist

- [ ] auditd installed and configured
- [ ] Audit rules loaded from audit-policy.json
- [ ] Log rotation configured
- [ ] Archive process automated
- [ ] Tamper detection enabled
- [ ] SIEM integration configured
- [ ] Alert system functional
- [ ] Monitoring dashboard active
- [ ] Retention policy validated
- [ ] Backup procedures tested
- [ ] Incident response procedures documented
- [ ] Staff training completed
- [ ] Compliance assessment completed
- [ ] Third-party audit scheduled

## References

- Linux auditd Documentation: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/security_guide/chap-system_auditing
- SOC2 Requirements: https://www.aicpa.org/soc2
- ISO/IEC 27001:2022
- NIST SP 800-53: Audit and Accountability (AU) Controls
- CEF Standard: https://www.arista.com/en/cef
- Syslog Protocol: RFC 3164, RFC 5424
