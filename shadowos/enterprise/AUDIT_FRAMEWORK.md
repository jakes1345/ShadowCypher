# ShadowCypher Centralized Audit Framework

## Overview

The ShadowCypher Centralized Audit Framework provides enterprise-grade audit logging, event correlation, and incident investigation capabilities for comprehensive security monitoring and compliance.

This framework enables organizations to:
- Collect and normalize events from multiple sources in real-time
- Correlate related events for incident investigation
- Generate alerts based on configurable rules
- Export audit logs to SIEM platforms (Splunk, ELK)
- Maintain long-term audit trails for forensics and compliance
- Integrate with Guardian vault operations for credential audit

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Event Sources (Input Layer)              │
├─────────────────────────────────────────────────────────────┤
│ Auditd │ Syslog │ Application Logs │ Guardian Vault │ Auth  │
└────────┬────────┬──────────────────┬────────────────┬──────┘
         │        │                  │                │
         └────────┴──────────────────┴────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │Log Normalization│ (Convert to unified schema)
         └────────┬───────┘
                  │
                  ▼
         ┌──────────────────────┐
         │Event Enrichment &     │
         │Correlation Engine    │
         └────────┬─────────────┘
                  │
                  ▼
         ┌──────────────────────────────┐
         │Alert Rule Engine              │
         │(Threat Detection & Analysis) │
         └────────┬─────────────────────┘
                  │
         ┌────────┴────────┬──────────────┐
         │                 │              │
         ▼                 ▼              ▼
    ┌──────────┐  ┌─────────────┐  ┌──────────┐
    │ Logging  │  │Notification │  │Escalation│
    │ & Storage│  │  System     │  │ Handler  │
    └──────────┘  └─────────────┘  └──────────┘
         │                               │
         └───────────────┬───────────────┘
                         │
                 ┌───────┴────────┬──────────┐
                 │                │          │
                 ▼                ▼          ▼
            ┌─────────┐  ┌──────────────┐  ┌────────────┐
            │Database │  │ SIEM Export  │  │Compliance  │
            │(Long-   │  │(Splunk, ELK) │  │ Reports    │
            │term)    │  └──────────────┘  └────────────┘
            └─────────┘
```

### Component Details

#### 1. Log Collection Layer

**Supported Sources:**
- **Auditd**: Linux kernel audit framework events
- **Syslog**: System-wide syslog messages (RFC 3164/5424)
- **Application Logs**: Custom application event logs
- **Guardian Vault**: Credential access and key operations
- **Auth Service**: Authentication and authorization events
- **Network**: Connection and firewall events

**Collection Methods:**
- Real-time socket-based collection (UDP/TCP)
- File tail with position tracking
- System integration hooks
- REST API consumption

#### 2. Event Normalization

All events are normalized to the unified audit schema:

```json
{
  "event_id": "UUID",
  "timestamp": "RFC3339",
  "source": {"type", "name", "component"},
  "user": {"id", "name", "privileged"},
  "action": "enum",
  "result": {"status", "error_code", "error_message"},
  "category": "enum",
  "severity": "critical|high|medium|low|informational",
  "resource": {"type", "identifier"},
  "correlation_id": "UUID",
  "metadata": {}
}
```

#### 3. Event Enrichment & Correlation

**Enrichment Operations:**
- User context lookup and privilege level detection
- Resource ownership and access control resolution
- Threat intelligence lookup
- Anomaly scoring

**Correlation Engine:**
- Temporal correlation (events within time windows)
- User activity chains (related actions by same user)
- Resource-based correlation (events affecting same resource)
- Cross-source correlation (related events from different sources)

#### 4. Alert Rule Engine

Alert rules trigger on event patterns and conditions:

```python
AlertRule(
    rule_id="rule:privilege_escalation",
    name="Privilege Escalation Detected",
    conditions=[
        lambda e: e.action == "privilege_escalation",
        lambda e: e.result_status == "success"
    ],
    severity=EventSeverity.CRITICAL,
    actions=["alert", "notification", "escalate"]
)
```

**Built-in Alert Rules:**
- Privilege escalation attempts (successful/failed)
- Unauthorized data access
- Credential vault access
- Configuration changes
- Policy violations
- Anomalous authentication patterns
- Mass data deletion

#### 5. Notification & Response

**Notification Channels:**
- Syslog/UDP to security operations center
- Email to security team
- HTTPS webhook to incident response systems
- SMS for critical alerts

**Automatic Responses:**
- Event logging and archival
- Alert escalation to team
- Incident ticket creation
- Automatic investigation triggers

## Guardian Vault Audit Integration

### Vault Access Audit

Every access to the Guardian vault is logged with full context:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-05T14:30:22Z",
  "action": "vault_access",
  "category": "vault_operation",
  "severity": "high",
  "resource": {
    "type": "vault",
    "identifier": "credentials:github"
  },
  "user": {
    "id": "user:jack",
    "privileged": true
  },
  "metadata": {
    "vault_operation": "decrypt",
    "credential_type": "api_key",
    "access_duration_ms": 245
  }
}
```

### Key Operation Audit

Encryption key operations trigger high-severity events:

```
encryption_key_generation  → High severity
encryption_key_rotation    → High severity
encryption_key_operation   → Medium severity
decryption                 → High severity (unusual patterns)
```

### Compliance Audit Trail

Maintains immutable audit trail for:
- Who accessed credentials and when
- What operations were performed
- Duration and outcome of operations
- Success/failure details and error codes

## Event Correlation and Forensics

### Forensic Query Interface

Retrieve related event chains for incident investigation:

```python
daemon = AuditDaemon()

# Query by correlation ID
events = daemon.get_forensic_query({
    "correlation_id": "chain:12345"
})

# Each chain contains chronologically ordered events
# showing related activities and context
for event in events:
    print(f"{event.timestamp}: {event.action} by {event.user_id}")
```

### Incident Investigation Workflow

1. **Alert Triggered**: System detects suspicious pattern
2. **Event Isolation**: Extract correlation chain for event
3. **Context Analysis**: Review related events and metadata
4. **Impact Assessment**: Identify affected resources
5. **Root Cause Analysis**: Trace actions back to origin
6. **Remediation**: Execute automated or manual response

## SIEM Integration

### Splunk Integration

**HEC (HTTP Event Collector) Integration:**

```python
# Events automatically exported to Splunk in HEC format
{
    "time": 1625270240.123,
    "source": "vault-01",
    "sourcetype": "shadowcypher:guardian_vault",
    "host": "shadowcypher-prod-01",
    "event": {
        "event_id": "...",
        "action": "vault_access",
        ...
    }
}
```

**Splunk Queries:**

```spl
sourcetype="shadowcypher:*"
| search action=vault_access
| stats count by user_id
| where count > 10
```

### ELK Stack Integration

**Elasticsearch Integration:**

```json
PUT /shadowcypher-audit/_doc
{
  "timestamp": "2026-07-05T14:30:22Z",
  "source_type": "guardian_vault",
  "action": "vault_access",
  "user_id": "user:jack",
  ...
}
```

**Kibana Dashboards:**
- Real-time event stream
- Alert timeline and metrics
- User activity heatmap
- Vault access patterns
- Privilege escalation attempts

## Compliance and Retention

### Log Retention Policies

```json
{
  "policy_id": "default_retention",
  "retention_days": 90,
  "archive_strategy": "compress",
  "compression": true,
  "encryption": true
}
```

**Retention Tiers:**
- Hot (0-30 days): Searchable in database
- Warm (30-90 days): Compressed, searchable via index
- Cold (90+ days): Immutable archive storage
- Deleted after configured retention period

### Compliance Support

**Standards Supported:**
- SOC 2 Type II
- ISO 27001
- GDPR (data retention, user rights)
- HIPAA (audit trails)
- PCI DSS (access logging)

**Export Formats:**
- JSON (API consumption)
- CSV (spreadsheet analysis)
- Syslog (RFC 3164/5424)
- CEF (Common Event Format)
- SIEM native formats

## High-Availability Architecture

### Distributed Audit Collection

```
┌────────────┐  ┌────────────┐  ┌────────────┐
│ Collector 1│  │ Collector 2│  │ Collector 3│
│ (Active)   │  │ (Standby)  │  │ (Standby)  │
└─────┬──────┘  └─────┬──────┘  └─────┬──────┘
      │               │               │
      └───────────────┴───────────────┘
              │
              ▼
      ┌──────────────────┐
      │Event Aggregator  │
      │(Load Balancer)   │
      └────────┬─────────┘
               │
      ┌────────┴─────────┐
      │                  │
      ▼                  ▼
┌─────────────┐  ┌─────────────┐
│Database     │  │Database     │
│Primary      │  │Replica      │
└─────────────┘  └─────────────┘
```

### Circuit Breaker Pattern

Handles failures in external integrations gracefully:

```python
breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)

# Fails open (stops sending) after 5 failures
# Attempts recovery after 60 seconds
success, result = breaker.call(send_to_splunk, event)
if not success:
    # Log locally, don't lose data
    save_to_local_queue(event)
```

### Queue Management

- In-memory event queue with overflow handling
- Persistent queue for failed exports
- Configurable queue size (default 10,000 events)
- Graceful shutdown with queue draining

## Performance Optimization

### Event Processing

- **Parallel Processing**: Multi-threaded event queue processing
- **Async I/O**: Non-blocking socket and file operations
- **Batch Export**: Batched SIEM exports (100 events/batch)
- **Memory Pooling**: Reusable event structures

### Tuning Parameters

```json
{
  "event_queue_size": 10000,
  "batch_export_size": 100,
  "correlation_window_seconds": 300,
  "worker_threads": 4,
  "log_rotation_size_mb": 1000,
  "index_refresh_interval": "30s"
}
```

### Benchmarks

On standard hardware (4 CPU, 8GB RAM):
- Event Collection: 10,000 events/sec
- Event Processing: 5,000 events/sec
- External Export: 2,000 events/sec (batched)
- Correlation Query: <100ms for typical chain

## Configuration

### Environment Variables

```bash
AUDIT_LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
AUDIT_CONFIG=/etc/shadowcypher/audit.json
VAULT_AUDIT_LOG=/var/log/guardian/vault.log
SIEM_ENDPOINT=https://splunk.example.com:8088
SIEM_HEC_TOKEN=abcd1234efgh5678
```

### Configuration File

```json
{
  "log_level": "INFO",
  "event_queue_size": 10000,
  "correlation_window": 300,
  "retention_days": 90,
  "enable_syslog": true,
  "syslog_port": 514,
  "enable_vault_audit": true,
  "alert_rules": [
    {
      "rule_id": "privilege_escalation",
      "name": "Privilege Escalation",
      "enabled": true,
      "severity": "critical"
    }
  ]
}
```

## Error Handling and Resilience

### Failure Scenarios

| Scenario | Handling |
|----------|----------|
| Source unavailable | Skip source, continue collection from others |
| Event queue full | Drop events, log warning (prevents memory exhaustion) |
| SIEM down | Queue locally, retry with circuit breaker |
| Correlation error | Process event without correlation chain |
| Alert rule error | Log error, continue processing |
| Daemon crash | Systemd auto-restart, drain queued events on startup |

### Logging Strategy

- **Debug**: Event normalization details
- **Info**: Source initialization, rule matches
- **Warning**: Queue full, connection failures
- **Error**: Exception stack traces, data loss scenarios

## Deployment

### Systemd Service

```ini
[Unit]
Description=ShadowCypher Audit Daemon
After=network.target

[Service]
Type=simple
User=audit-daemon
ExecStart=/usr/local/bin/audit-daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
FROM python:3.11-slim
RUN pip install shadowcypher-audit
CMD ["python3", "-m", "shadowcypher.audit.daemon"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: audit-daemon
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: audit-daemon
        image: shadowcypher/audit-daemon:latest
        env:
        - name: AUDIT_LOG_LEVEL
          value: INFO
        - name: SIEM_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: siem-config
              key: endpoint
```

## Security Considerations

### Data Protection

- Events encrypted in transit (TLS 1.3 for SIEM export)
- At-rest encryption for archived logs
- RBAC for audit log access
- Immutable archive format (WORM: Write Once Read Many)

### Integrity

- Event ID uniqueness (UUID v4)
- Cryptographic signatures on exported batches
- Audit log checksums
- Chain of custody for forensic evidence

### Access Control

- Only privileged users can query audit logs
- Guardian vault requires decryption to view sensitive fields
- Role-based access to SIEM dashboards
- Audit of audit log access itself (meta-auditing)

## Troubleshooting

### Common Issues

**High CPU Usage:**
- Check alert rule complexity
- Reduce correlation window
- Increase worker threads

**Events Not Appearing:**
- Verify source connectivity
- Check log rotation permissions
- Review event queue size

**SIEM Connection Failures:**
- Check network connectivity and firewall
- Verify HEC token and endpoint
- Review circuit breaker logs

**Correlation Chains Empty:**
- Adjust correlation window (default 300s)
- Check user activity patterns
- Verify source time synchronization

## Future Enhancements

- Machine learning-based anomaly detection
- Advanced event correlation rules (behavioral baselining)
- Real-time threat intelligence integration
- Automated incident response playbooks
- Guardian vault backup audit trail
- Distributed tracing across microservices
- Event deduplication and compression

## References

- [Audit Framework Schema](audit-schema.json)
- [Daemon Implementation](audit-daemon.py)
- [NIST SP 800-53: Audit and Accountability](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5)
- [CEF (Common Event Format) Specification](https://www.arcmailing.com/cef)
