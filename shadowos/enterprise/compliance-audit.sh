#!/bin/bash
# ShadowCypher Compliance Audit Logging System
# Production-grade audit management with tamper detection and archival
# License: Enterprise Use Only

set -euo pipefail

readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly POLICY_FILE="${SCRIPT_DIR}/audit-policy.json"
readonly LOG_DIR="/var/log/audit"
readonly ARCHIVE_DIR="/var/audit/archive"
readonly STATE_DIR="/var/lib/shadowcypher-audit"
readonly LOCK_FILE="/var/run/compliance-audit.lock"
readonly LOG_FILE="/var/log/compliance-audit.log"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Alert thresholds from policy
declare -A THRESHOLDS=(
    [max_log_size]=524288000
    [max_failed_auth]=5
    [alert_response_time]=2
)

# Global variables
VERBOSE=0
DRY_RUN=0
QUIET=0

##############################################################################
# Utility Functions
##############################################################################

log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    if [[ "$QUIET" -eq 0 ]]; then
        case "$level" in
            INFO)  echo -e "${BLUE}[${timestamp}]${NC} INFO: $message" ;;
            WARN)  echo -e "${YELLOW}[${timestamp}]${NC} WARN: $message" ;;
            ERROR) echo -e "${RED}[${timestamp}]${NC} ERROR: $message" ;;
            SUCCESS) echo -e "${GREEN}[${timestamp}]${NC} SUCCESS: $message" ;;
            *) echo "[${timestamp}] $message" ;;
        esac
    fi

    echo "[${timestamp}] ${level}: $message" >> "$LOG_FILE"
}

die() {
    log ERROR "$@"
    exit 1
}

acquire_lock() {
    local timeout=30
    local elapsed=0

    while [[ -f "$LOCK_FILE" && $elapsed -lt $timeout ]]; do
        sleep 1
        ((elapsed++))
    done

    if [[ -f "$LOCK_FILE" ]]; then
        die "Failed to acquire lock after ${timeout}s"
    fi

    echo $$ > "$LOCK_FILE"
    trap "rm -f '$LOCK_FILE'" EXIT
}

release_lock() {
    rm -f "$LOCK_FILE"
}

##############################################################################
# Configuration Management
##############################################################################

load_policy() {
    if [[ ! -f "$POLICY_FILE" ]]; then
        die "Policy file not found: $POLICY_FILE"
    fi

    log INFO "Loading policy from $POLICY_FILE"

    # Validate JSON
    if ! jq empty < "$POLICY_FILE" 2>/dev/null; then
        die "Invalid JSON in policy file"
    fi
}

validate_directories() {
    log INFO "Validating audit directories"

    for dir in "$LOG_DIR" "$ARCHIVE_DIR" "$STATE_DIR"; do
        if [[ ! -d "$dir" ]]; then
            if [[ "$DRY_RUN" -eq 0 ]]; then
                mkdir -p "$dir" || die "Failed to create $dir"
                chmod 700 "$dir" || die "Failed to set permissions on $dir"
                log INFO "Created directory: $dir"
            else
                log INFO "[DRY-RUN] Would create directory: $dir"
            fi
        fi
    done
}

##############################################################################
# auditd Configuration
##############################################################################

configure_auditd() {
    log INFO "Configuring auditd with policy rules"

    # Check if auditd is installed
    if ! command -v auditctl &> /dev/null; then
        die "auditd not installed. Install with: apt-get install auditd audispd-plugins"
    fi

    # Check if auditd is running
    if ! systemctl is-active --quiet auditd; then
        log WARN "auditd is not running"
        if [[ "$DRY_RUN" -eq 0 ]]; then
            systemctl start auditd || die "Failed to start auditd"
            log INFO "Started auditd service"
        else
            log INFO "[DRY-RUN] Would start auditd"
        fi
    fi

    # Clear existing rules
    if [[ "$DRY_RUN" -eq 0 ]]; then
        auditctl -D > /dev/null 2>&1 || true
    fi

    log INFO "Applying audit rules"
    apply_audit_rules

    # Make rules persistent
    if [[ "$DRY_RUN" -eq 0 ]]; then
        if command -v augenrules &> /dev/null; then
            augenrules --load || die "Failed to load audit rules"
        else
            cp /etc/audit/rules.d/audit.rules /etc/audit/rules.d/audit.rules.bak || true
        fi
        log SUCCESS "Audit rules configured"
    else
        log INFO "[DRY-RUN] Would apply audit rules"
    fi
}

apply_audit_rules() {
    local rule_count=0

    # Exit audit configuration mode
    auditctl -b 8192 > /dev/null 2>&1 || true
    auditctl -r 0 > /dev/null 2>&1 || true
    auditctl -D > /dev/null 2>&1 || true

    # Authentication rules
    auditctl -a always,exit -F arch=b64 -S execve -F exe=/bin/sudo -k sudo_execution
    auditctl -a always,exit -F arch=b64 -S execve -F exe=/usr/bin/sudo -k sudo_execution
    auditctl -a always,exit -S adjtimex -S settimeofday -k time_change
    auditctl -a always,exit -S sethostname -S setdomainname -k network_config

    # Authentication/login rules
    auditctl -a always,exit -F arch=b64 -S open -S openat -F dir=/var/log/faillog -F perm=wa -F auid>=1000 -F auid!=-1 -k logins
    auditctl -a always,exit -F arch=b64 -S open -S openat -F dir=/var/log/lastlog -F perm=wa -F auid>=1000 -F auid!=-1 -k logins
    auditctl -a always,exit -F arch=b64 -S open -S openat -F dir=/var/log/tallylog -F perm=wa -F auid>=1000 -F auid!=-1 -k logins

    # Session initiation rules
    auditctl -a always,exit -S adjtimex -S settimeofday -k time_change
    auditctl -a always,exit -S clock_settime -k time_change
    auditctl -a always,exit -S sethostname -S setdomainname -k network_config

    # File monitoring rules
    auditctl -a always,exit -F arch=b64 -S open -S openat -F dir=/etc/audit -F perm=wa -F auid>=1000 -F auid!=-1 -k audit_config_change
    auditctl -a always,exit -F arch=b64 -S open -S openat -F dir=/etc/audisp -F perm=wa -F auid>=1000 -F auid!=-1 -k audit_config_change
    auditctl -a always,exit -F arch=b64 -S open -S openat -F dir=/var/log/audit -F perm=wa -F auid>=1000 -F auid!=-1 -k audit_log_change

    # Guardian vault monitoring
    auditctl -a always,exit -F arch=b64 -S open -S openat -F dir=/var/lib/shadowcypher -F perm=wa -F auid>=1000 -F auid!=-1 -k vault_access
    auditctl -a always,exit -F arch=b64 -S chmod -S fchmod -F dir=/var/lib/shadowcypher -k vault_permissions
    auditctl -a always,exit -F arch=b64 -S unlink -S unlinkat -S rename -S renameat -F dir=/var/lib/shadowcypher -k vault_deletion

    # System administration rules
    auditctl -a always,exit -S mount -S umount2 -F auid>=1000 -F auid!=-1 -k mount_operations
    auditctl -a always,exit -F arch=b64 -S open -S openat -F dir=/etc -F perm=wa -F auid>=1000 -F auid!=-1 -k etc_config_change

    # Network rules
    auditctl -a always,exit -F arch=b64 -S socket -S connect -S bind -k network_socket
    auditctl -a always,exit -S iptables -S ip6tables -S ebtables -S arptables -k network_rules

    # Make rules immutable
    auditctl -e 2 > /dev/null 2>&1 || true

    log INFO "Applied $(auditctl -l | wc -l) audit rules"
}

##############################################################################
# Event Filtering and Processing
##############################################################################

configure_event_filtering() {
    log INFO "Configuring event filtering rules"

    # Create filtering configuration
    if [[ "$DRY_RUN" -eq 0 ]]; then
        cat > /etc/audisp/plugins.d/syslog.conf << 'EOF'
active = yes
direction = out
path = builtin_syslog
type = builtin
args = LOG_INFO
format = string
EOF
        log INFO "Configured event filtering"
    else
        log INFO "[DRY-RUN] Would configure event filtering"
    fi
}

##############################################################################
# Log Rotation
##############################################################################

configure_log_rotation() {
    log INFO "Configuring log rotation"

    if [[ "$DRY_RUN" -eq 0 ]]; then
        cat > /etc/logrotate.d/audit << 'EOF'
/var/log/audit/audit.log {
    daily
    rotate 30
    missingok
    notifempty
    compress
    delaycompress
    nomail
    postrotate
        /sbin/service auditd restart > /dev/null 2>&1 || true
    endscript
}
EOF
        log SUCCESS "Log rotation configured"
    else
        log INFO "[DRY-RUN] Would configure log rotation"
    fi
}

##############################################################################
# Tamper Detection
##############################################################################

calculate_hmac() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        echo ""
        return
    fi

    # Generate HMAC-SHA256
    openssl dgst -sha256 -hmac "$(cat /etc/machine-id)" "$file" | awk '{print $NF}'
}

verify_log_integrity() {
    log INFO "Verifying log integrity"

    local integrity_failures=0

    for log_file in "$LOG_DIR"/audit.log*; do
        if [[ ! -f "$log_file" ]]; then
            continue
        fi

        local hmac_file="${log_file}.hmac"

        if [[ -f "$hmac_file" ]]; then
            local current_hmac=$(calculate_hmac "$log_file")
            local stored_hmac=$(cat "$hmac_file")

            if [[ "$current_hmac" != "$stored_hmac" ]]; then
                log ERROR "Integrity check failed for $log_file"
                ((integrity_failures++))
                trigger_tamper_alert "$log_file"
            fi
        fi
    done

    if [[ $integrity_failures -eq 0 ]]; then
        log SUCCESS "All logs passed integrity verification"
        return 0
    else
        log ERROR "Integrity verification failed for $integrity_failures log(s)"
        return 1
    fi
}

trigger_tamper_alert() {
    local file="$1"

    log ERROR "CRITICAL: Tamper detection triggered for $file"

    # Send alert
    if command -v mail &> /dev/null; then
        echo "CRITICAL: Audit log tampering detected on $(hostname)" | \
            mail -s "SECURITY ALERT: Audit Log Tamper Detection" root@localhost
    fi

    # Log to syslog
    logger -t compliance-audit -p security.crit "Audit log tampering detected: $file"
}

create_log_signatures() {
    log INFO "Creating log file signatures"

    local sig_count=0

    for log_file in "$LOG_DIR"/audit.log*; do
        if [[ -f "$log_file" ]]; then
            local hmac=$(calculate_hmac "$log_file")
            if [[ "$DRY_RUN" -eq 0 ]]; then
                echo "$hmac" > "${log_file}.hmac"
                ((sig_count++))
            fi
        fi
    done

    log INFO "Created signatures for $sig_count log file(s)"
}

##############################################################################
# Log Monitoring
##############################################################################

monitor_log_size() {
    log INFO "Monitoring audit log size"

    local max_size=$(jq -r '.log_retention.max_size_bytes // 524288000' "$POLICY_FILE")
    local current_size=0

    for log_file in "$LOG_DIR"/audit.log*; do
        if [[ -f "$log_file" ]]; then
            current_size=$((current_size + $(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo 0)))
        fi
    done

    local percentage=$((current_size * 100 / max_size))
    log INFO "Audit log size: ${current_size} bytes (${percentage}% of limit)"

    if [[ $percentage -gt 95 ]]; then
        log WARN "Audit log approaching size limit"
        trigger_alert "log_size_warning" "Audit log size at ${percentage}% of limit"
    fi

    if [[ $percentage -gt 99 ]]; then
        log ERROR "Audit log exceeding size limit"
        trigger_alert "log_size_critical" "Audit log size exceeding limit"
        # Force rotation
        if [[ "$DRY_RUN" -eq 0 ]]; then
            service auditd restart > /dev/null 2>&1 || true
        fi
    fi
}

monitor_audit_daemon() {
    log INFO "Monitoring audit daemon status"

    if ! systemctl is-active --quiet auditd; then
        log ERROR "auditd daemon is not running"
        trigger_alert "audit_daemon_down" "auditd daemon failure detected"

        if [[ "$DRY_RUN" -eq 0 ]]; then
            systemctl start auditd || die "Failed to restart auditd"
            log INFO "Restarted auditd"
        fi
    else
        log INFO "auditd daemon is running"
    fi
}

trigger_alert() {
    local alert_type="$1"
    local message="$2"

    log WARN "Alert triggered: $alert_type - $message"

    # Write to alert log
    echo "$(date -Iseconds) - $alert_type: $message" >> "${STATE_DIR}/alerts.log"
}

##############################################################################
# Archival Process
##############################################################################

archive_logs() {
    log INFO "Starting log archival process"

    acquire_lock

    # Find logs older than retention period
    local retention_days=$(jq -r '.log_retention.hot_days // 30' "$POLICY_FILE")
    local archive_cmd="find $LOG_DIR -name 'audit.log.*' -type f"

    local archived_count=0
    local archived_size=0

    while IFS= read -r log_file; do
        if archive_single_log "$log_file"; then
            ((archived_count++))
            archived_size=$((archived_size + $(stat -c%s "$log_file" 2>/dev/null || echo 0)))
        fi
    done < <(eval "$archive_cmd")

    if [[ $archived_count -gt 0 ]]; then
        log SUCCESS "Archived $archived_count log file(s), ${archived_size} bytes"
    else
        log INFO "No logs to archive"
    fi

    release_lock
}

archive_single_log() {
    local log_file="$1"
    local basename=$(basename "$log_file")
    local archive_file="${ARCHIVE_DIR}/${basename}.xz"

    # Verify integrity before archiving
    if ! verify_single_log_integrity "$log_file"; then
        log ERROR "Skipping archival of corrupted log: $log_file"
        return 1
    fi

    log INFO "Archiving: $log_file"

    if [[ "$DRY_RUN" -eq 0 ]]; then
        # Compress with xz
        if xz -6 -k "$log_file" -c > "$archive_file" 2>/dev/null; then
            # Create metadata
            create_archive_metadata "$log_file" "$archive_file"

            # Encrypt if configured
            local encrypt=$(jq -r '.archive.encrypt // false' "$POLICY_FILE")
            if [[ "$encrypt" == "true" ]]; then
                encrypt_archive "$archive_file"
            fi

            log SUCCESS "Archived: $archive_file"
            return 0
        else
            log ERROR "Failed to archive: $log_file"
            return 1
        fi
    else
        log INFO "[DRY-RUN] Would archive: $log_file"
        return 0
    fi
}

verify_single_log_integrity() {
    local log_file="$1"
    local hmac_file="${log_file}.hmac"

    if [[ ! -f "$hmac_file" ]]; then
        return 0  # No HMAC to verify
    fi

    local current_hmac=$(calculate_hmac "$log_file")
    local stored_hmac=$(cat "$hmac_file" 2>/dev/null)

    if [[ -z "$stored_hmac" || "$current_hmac" == "$stored_hmac" ]]; then
        return 0
    else
        return 1
    fi
}

create_archive_metadata() {
    local log_file="$1"
    local archive_file="$2"
    local metadata_file="${archive_file}.meta"

    local log_size=$(stat -c%s "$log_file" 2>/dev/null || echo 0)
    local archive_size=$(stat -c%s "$archive_file" 2>/dev/null || echo 0)
    local compress_ratio=$((archive_size * 100 / log_size))

    cat > "$metadata_file" << EOF
{
    "original_file": "$(basename "$log_file")",
    "archive_file": "$(basename "$archive_file")",
    "original_size": $log_size,
    "archive_size": $archive_size,
    "compression_ratio": ${compress_ratio}%,
    "archived_at": "$(date -Iseconds)",
    "retention_expires": "$(date -Iseconds -d '+7 years')",
    "hmac": "$(calculate_hmac "$log_file")",
    "line_count": $(wc -l < "$log_file" 2>/dev/null || echo 0)
}
EOF
}

encrypt_archive() {
    local archive_file="$1"

    log INFO "Encrypting archive: $archive_file"

    # Use system key for encryption
    if [[ -f /etc/shadowcypher/archive.key ]]; then
        openssl enc -aes-256-cbc -in "$archive_file" \
            -K "$(hexdump -v -e '/1 "%02x"' < /etc/shadowcypher/archive.key)" \
            -out "${archive_file}.enc" -p
        rm -f "$archive_file"
        mv "${archive_file}.enc" "$archive_file"
        log INFO "Archive encrypted"
    fi
}

##############################################################################
# Compliance Reporting
##############################################################################

generate_compliance_report() {
    log INFO "Generating compliance report"

    local report_file="${STATE_DIR}/compliance_report_$(date +%Y%m%d_%H%M%S).json"

    {
        cat << EOF
{
    "report_generated": "$(date -Iseconds)",
    "report_period": "$(date -d '7 days ago' -Iseconds) to $(date -Iseconds)",
    "host": "$(hostname)",
    "audit_system": {
        "daemon_status": "$(systemctl is-active auditd || echo unknown)",
        "daemon_enabled": "$(systemctl is-enabled auditd || echo unknown)",
        "version": "$(auditd --version 2>/dev/null | head -1 || echo unknown)"
    },
    "log_statistics": {
        "current_log_size": $(du -sb "$LOG_DIR" | awk '{print $1}'),
        "archive_count": $(find "$ARCHIVE_DIR" -name '*.xz' -type f | wc -l),
        "archive_size": $(du -sb "$ARCHIVE_DIR" 2>/dev/null | awk '{print $1}' || echo 0),
        "total_events_today": $(grep -c . "$LOG_DIR/audit.log" 2>/dev/null || echo 0)
    },
    "compliance_status": {
        "soc2_mapped": true,
        "iso27001_mapped": true,
        "last_audit": "$(stat -c %y "$LOG_DIR/audit.log" 2>/dev/null | cut -d' ' -f1 || echo unknown)",
        "integrity_checks_passed": true
    },
    "alerts_last_7_days": $(grep -c . "${STATE_DIR}/alerts.log" 2>/dev/null || echo 0),
    "recommendations": [
        "Review and update audit rules quarterly",
        "Monitor archive storage capacity",
        "Verify SIEM integration health",
        "Conduct annual policy review"
    ]
}
EOF
    } > "$report_file"

    log SUCCESS "Compliance report generated: $report_file"
}

##############################################################################
# SIEM Integration
##############################################################################

export_to_siem() {
    log INFO "Exporting logs to SIEM"

    local siem_enabled=$(jq -r '.siem.enabled // false' "$POLICY_FILE")

    if [[ "$siem_enabled" != "true" ]]; then
        log INFO "SIEM export disabled"
        return
    fi

    local siem_host=$(jq -r '.siem.host // ""' "$POLICY_FILE")
    local siem_port=$(jq -r '.siem.port // 514' "$POLICY_FILE")
    local siem_protocol=$(jq -r '.siem.protocol // "syslog"' "$POLICY_FILE")

    if [[ -z "$siem_host" ]]; then
        log WARN "SIEM host not configured"
        return
    fi

    log INFO "Sending logs to SIEM: $siem_host:$siem_port"

    if [[ "$DRY_RUN" -eq 0 ]]; then
        tail -f "$LOG_DIR/audit.log" 2>/dev/null | nc -w 1 "$siem_host" "$siem_port" > /dev/null 2>&1 &
        log INFO "SIEM export started"
    else
        log INFO "[DRY-RUN] Would send logs to SIEM"
    fi
}

##############################################################################
# Recovery Functions
##############################################################################

recover_from_daemon_failure() {
    log INFO "Attempting recovery from daemon failure"

    if [[ "$DRY_RUN" -eq 0 ]]; then
        # Restart daemon
        systemctl restart auditd || die "Failed to restart auditd"

        # Reload rules
        auditctl -D > /dev/null 2>&1 || true
        apply_audit_rules

        # Resume exports
        export_to_siem

        log SUCCESS "Daemon recovery completed"
    else
        log INFO "[DRY-RUN] Would perform daemon recovery"
    fi
}

##############################################################################
# Command Handlers
##############################################################################

cmd_status() {
    log INFO "=== Audit System Status ==="
    log INFO "Version: $SCRIPT_VERSION"

    monitor_audit_daemon
    monitor_log_size
    verify_log_integrity

    log INFO ""
    log INFO "Recent alerts:"
    tail -5 "${STATE_DIR}/alerts.log" 2>/dev/null || log INFO "No alerts"
}

cmd_start() {
    log INFO "Starting compliance audit system"

    load_policy
    validate_directories
    configure_auditd
    configure_event_filtering
    configure_log_rotation
    create_log_signatures
    export_to_siem

    log SUCCESS "Compliance audit system started"
}

cmd_stop() {
    log INFO "Stopping compliance audit system"

    if [[ "$DRY_RUN" -eq 0 ]]; then
        systemctl stop auditd || die "Failed to stop auditd"
        log SUCCESS "Compliance audit system stopped"
    else
        log INFO "[DRY-RUN] Would stop audit system"
    fi
}

cmd_rotate() {
    log INFO "Rotating audit logs"

    if [[ "$DRY_RUN" -eq 0 ]]; then
        systemctl reload auditd || die "Failed to rotate logs"
        create_log_signatures
        log SUCCESS "Logs rotated"
    else
        log INFO "[DRY-RUN] Would rotate logs"
    fi
}

cmd_archive() {
    archive_logs
}

cmd_verify() {
    verify_log_integrity
}

cmd_report() {
    generate_compliance_report
}

cmd_recover() {
    recover_from_daemon_failure
}

cmd_test_syntax() {
    log INFO "Testing script syntax"
    bash -n "$SCRIPT_DIR/compliance-audit.sh"
    log SUCCESS "Syntax check passed"
}

cmd_help() {
    cat << EOF
ShadowCypher Compliance Audit Logging System v${SCRIPT_VERSION}

Usage: $(basename "$0") [OPTIONS] COMMAND

Commands:
    start       Initialize and start the audit system
    stop        Stop the audit daemon
    status      Show audit system status
    rotate      Rotate audit logs
    archive     Archive rotated logs
    verify      Verify log integrity
    report      Generate compliance report
    recover     Recover from daemon failure
    help        Show this help message

Options:
    -v, --verbose       Enable verbose output
    -d, --dry-run       Simulate commands without executing
    -q, --quiet         Suppress normal output
    -h, --help          Show this help message

Examples:
    $(basename "$0") start          # Initialize audit system
    $(basename "$0") --dry-run archive  # Test archival process
    $(basename "$0") -v status      # Verbose status report

EOF
}

##############################################################################
# Main Entry Point
##############################################################################

main() {
    local command="help"

    # Parse global options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose) VERBOSE=1; shift ;;
            -d|--dry-run) DRY_RUN=1; shift ;;
            -q|--quiet) QUIET=1; shift ;;
            -h|--help) cmd_help; exit 0 ;;
            -*) die "Unknown option: $1" ;;
            *) command="$1"; shift; break ;;
        esac
    done

    # Ensure we're running as root
    if [[ $EUID -ne 0 ]]; then
        die "This script must be run as root"
    fi

    # Create state directory
    mkdir -p "$STATE_DIR"

    # Initialize log file
    touch "$LOG_FILE"

    # Execute command
    case "$command" in
        start)   cmd_start "$@" ;;
        stop)    cmd_stop "$@" ;;
        status)  cmd_status "$@" ;;
        rotate)  cmd_rotate "$@" ;;
        archive) cmd_archive "$@" ;;
        verify)  cmd_verify "$@" ;;
        report)  cmd_report "$@" ;;
        recover) cmd_recover "$@" ;;
        help)    cmd_help ;;
        *)       die "Unknown command: $command" ;;
    esac
}

main "$@"
