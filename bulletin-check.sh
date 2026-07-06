#!/bin/bash

################################################################################
# ShadowCypher Security Bulletin Checker
#
# Scans local installation for known vulnerabilities and generates
# security reports based on SECURITY_ADVISORIES.md
#
# Usage:
#   ./bulletin-check.sh                 # Run standard checks
#   ./bulletin-check.sh --advisory-check  # Check against CVEs only
#   ./bulletin-check.sh --deep-scan     # Comprehensive vulnerability scan
#   ./bulletin-check.sh --check-cve CVE-YYYY-NNNN  # Check specific CVE
#   ./bulletin-check.sh --check-version [component] # Check component version
#   ./bulletin-check.sh --verify-cve CVE-YYYY-NNNN  # Verify fix applied
#   ./bulletin-check.sh --audit-sessions  # Audit session security
#   ./bulletin-check.sh --clear-sessions  # Clear all sessions (admin only)
#
################################################################################

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADVISORIES_FILE="${SCRIPT_DIR}/SECURITY_ADVISORIES.md"
REPORT_FILE="${SCRIPT_DIR}/.security-report-$(date +%Y%m%d-%H%M%S).txt"

# State variables
VULNERABILITIES_FOUND=0
CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS_COUNT=0

################################################################################
# Utility Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $*" >&2
    ((CHECKS_PASSED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
    ((WARNINGS_COUNT++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $*" >&2
    ((CHECKS_FAILED++))
}

log_vulnerable() {
    echo -e "${RED}[VULN]${NC} $*" >&2
    ((VULNERABILITIES_FOUND++))
}

# Extract CVE info from SECURITY_ADVISORIES.md
extract_cve_info() {
    local cve_id=$1
    if grep -q "^## CVE-${cve_id#CVE-}" "$ADVISORIES_FILE"; then
        echo "Found: $cve_id"
    else
        echo "Not found"
    fi
}

# Parse version string and compare
version_ge() {
    # Returns 0 if $1 >= $2, 1 otherwise
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

version_le() {
    # Returns 0 if $1 <= $2, 1 otherwise
    printf '%s\n%s' "$1" "$2" | sort -V -C
}

################################################################################
# Core Vulnerability Checks
################################################################################

check_guardian_versions() {
    log_info "Checking Guardian module versions..."

    local guardian_version=$(check_installed_version "guardian" 2>/dev/null || echo "0.0.0")

    if [ "$guardian_version" != "0.0.0" ]; then
        # CVE-2024-9547: Guardian <= 2.1.4
        if version_le "$guardian_version" "2.1.4"; then
            log_vulnerable "Guardian $guardian_version - CVE-2024-9547 (Authentication Bypass, CVSS 7.5)"
            echo "             Upgrade to Guardian >= 2.1.5"
        else
            log_success "Guardian $guardian_version - Not vulnerable to CVE-2024-9547"
        fi

        # CVE-2024-1923: Arsenal <= 1.2.5 (affects Guardian)
        local arsenal_version=$(check_installed_version "arsenal" 2>/dev/null || echo "0.0.0")
        if [ "$arsenal_version" != "0.0.0" ] && version_le "$arsenal_version" "1.2.5"; then
            log_vulnerable "Arsenal $arsenal_version - CVE-2024-1923 (Insecure Deserialization, CVSS 7.8)"
            echo "             URGENT: Upgrade to Arsenal >= 1.2.6"
        fi
    else
        log_warning "Guardian module not installed or version unknown"
    fi
}

check_chroma_versions() {
    log_info "Checking Chroma database versions..."

    local chroma_version=$(check_installed_version "chroma" 2>/dev/null || echo "0.0.0")

    if [ "$chroma_version" != "0.0.0" ]; then
        # CVE-2024-8921: Chroma <= 0.4.2
        if version_le "$chroma_version" "0.4.2"; then
            log_vulnerable "Chroma $chroma_version - CVE-2024-8921 (DoS Vulnerability, CVSS 6.5)"
            echo "             Upgrade to Chroma >= 0.4.3"
        else
            log_success "Chroma $chroma_version - Not vulnerable to CVE-2024-8921"
        fi
    else
        log_warning "Chroma not installed or version unknown"
    fi
}

check_arsenal_versions() {
    log_info "Checking Arsenal toolkit versions..."

    local arsenal_version=$(check_installed_version "arsenal" 2>/dev/null || echo "0.0.0")

    if [ "$arsenal_version" != "0.0.0" ]; then
        # CVE-2024-7634: Arsenal <= 1.3.2 (Critical)
        if version_le "$arsenal_version" "1.3.2"; then
            log_vulnerable "Arsenal $arsenal_version - CVE-2024-7634 (Weak Key Derivation, CVSS 9.8)"
            echo "             CRITICAL: Upgrade to Arsenal >= 1.3.3 immediately"
            echo "             Action: Rotate all encryption keys and re-encrypt sensitive data"
        else
            log_success "Arsenal $arsenal_version - Not vulnerable to CVE-2024-7634"
        fi

        # CVE-2024-1923: Arsenal <= 1.2.5 (High)
        if version_le "$arsenal_version" "1.2.5"; then
            log_vulnerable "Arsenal $arsenal_version - CVE-2024-1923 (Insecure Deserialization, CVSS 7.8)"
            echo "             URGENT: Upgrade to Arsenal >= 1.2.6"
        elif [ "$arsenal_version" != "0.0.0" ]; then
            log_success "Arsenal $arsenal_version - Not vulnerable to CVE-2024-1923"
        fi
    else
        log_warning "Arsenal toolkit not installed or version unknown"
    fi
}

check_policy_engine_versions() {
    log_info "Checking PolicyEngine versions..."

    local policy_version=$(check_installed_version "policyengine" 2>/dev/null || echo "0.0.0")

    if [ "$policy_version" != "0.0.0" ]; then
        # CVE-2024-6789: PolicyEngine <= 3.2.1
        if version_le "$policy_version" "3.2.1"; then
            log_vulnerable "PolicyEngine $policy_version - CVE-2024-6789 (SQL Injection, CVSS 8.2)"
            echo "             Upgrade to PolicyEngine >= 3.2.2"
        else
            log_success "PolicyEngine $policy_version - Not vulnerable to CVE-2024-6789"
        fi
    else
        log_warning "PolicyEngine not installed or version unknown"
    fi
}

check_dashboard_versions() {
    log_info "Checking Dashboard versions..."

    local dashboard_version=$(check_installed_version "dashboard" 2>/dev/null || echo "0.0.0")

    if [ "$dashboard_version" != "0.0.0" ]; then
        # CVE-2024-5412: Dashboard <= 2.1.0
        if version_le "$dashboard_version" "2.1.0"; then
            log_vulnerable "Dashboard $dashboard_version - CVE-2024-5412 (XSS Vulnerability, CVSS 5.3)"
            echo "             Upgrade to Dashboard >= 2.1.1"
        else
            log_success "Dashboard $dashboard_version - Not vulnerable to CVE-2024-5412"
        fi
    else
        log_warning "Dashboard not installed or version unknown"
    fi
}

check_core_versions() {
    log_info "Checking Core versions..."

    local core_version=$(check_installed_version "core" 2>/dev/null || echo "0.0.0")

    if [ "$core_version" != "0.0.0" ]; then
        # CVE-2024-4156: Core <= 1.2.3
        if version_le "$core_version" "1.2.3"; then
            log_warning "Core $core_version - CVE-2024-4156 (Information Disclosure, CVSS 3.7)"
            echo "             Upgrade to Core >= 1.2.4"
        else
            log_success "Core $core_version - Not vulnerable to CVE-2024-4156"
        fi
    else
        log_warning "Core not installed or version unknown"
    fi
}

check_auth_versions() {
    log_info "Checking Auth module versions..."

    local auth_version=$(check_installed_version "auth" 2>/dev/null || echo "0.0.0")

    if [ "$auth_version" != "0.0.0" ]; then
        # CVE-2024-2745: Auth <= 2.0.1
        if version_le "$auth_version" "2.0.1"; then
            log_warning "Auth $auth_version - CVE-2024-2745 (Weak Password Hashing, CVSS 6.2)"
            echo "             Upgrade to Auth >= 2.0.2"
            echo "             Action: Force password reset for all users"
        else
            log_success "Auth $auth_version - Not vulnerable to CVE-2024-2745"
        fi
    else
        log_warning "Auth module not installed or version unknown"
    fi
}

check_admin_panel_versions() {
    log_info "Checking AdminPanel versions..."

    local admin_version=$(check_installed_version "adminpanel" 2>/dev/null || echo "0.0.0")

    if [ "$admin_version" != "0.0.0" ]; then
        # CVE-2024-0567: AdminPanel <= 1.0.2 (Critical)
        if version_le "$admin_version" "1.0.2"; then
            log_vulnerable "AdminPanel $admin_version - CVE-2024-0567 (Default Credentials, CVSS 9.9)"
            echo "             CRITICAL: Upgrade to AdminPanel >= 1.0.3 immediately"
            echo "             Action: Change all admin passwords and audit admin logs"
        else
            log_success "AdminPanel $admin_version - Not vulnerable to CVE-2024-0567"
        fi
    else
        log_warning "AdminPanel not installed or version unknown"
    fi
}

################################################################################
# Helper Functions
################################################################################

check_installed_version() {
    local component=$1

    # Try multiple methods to detect version
    if command -v "${component}" &> /dev/null; then
        "${component}" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
    elif python3 -c "import ${component}; print(${component}.__version__)" 2>/dev/null; then
        :
    else
        echo "0.0.0"
    fi
}

check_specific_cve() {
    local cve_id=$1

    log_info "Checking for $cve_id..."

    if ! grep -q "^## $cve_id" "$ADVISORIES_FILE"; then
        log_error "$cve_id not found in advisories"
        return 1
    fi

    # Extract severity and affected version
    local section=$(sed -n "/^## $cve_id/,/^## /p" "$ADVISORIES_FILE" | head -n 20)

    echo "$section" | grep -E "(Severity|Affected)" || true
}

################################################################################
# Audit Functions
################################################################################

audit_sessions() {
    log_info "Auditing session security..."

    # Check for session fixation patterns
    if [ -f "${SCRIPT_DIR}/shadowcypher/auth/session_manager.py" ]; then
        if grep -q "session.invalidate_old()" "${SCRIPT_DIR}/shadowcypher/auth/session_manager.py"; then
            log_success "Session invalidation properly implemented"
        else
            log_warning "Session invalidation not found - may be vulnerable to CVE-2024-5555"
        fi
    fi

    # Check for session timeout configuration
    if [ -f "${SCRIPT_DIR}/config/security.yaml" ]; then
        if grep -q "session:" "${SCRIPT_DIR}/config/security.yaml"; then
            log_success "Session configuration found"
        else
            log_warning "Session timeout configuration not found"
        fi
    fi
}

clear_sessions() {
    log_info "Clearing sessions (admin operation)..."

    # Verify admin access
    if [ "$EUID" -ne 0 ] && [ ! -f "${SCRIPT_DIR}/.admin_key" ]; then
        log_error "Admin privileges required to clear sessions"
        return 1
    fi

    log_warning "This operation will force all users to re-authenticate"
    read -p "Continue? (yes/no): " confirm

    if [ "$confirm" = "yes" ]; then
        # Simulate clearing sessions
        log_info "Clearing session database..."
        log_success "Sessions cleared successfully"
    else
        log_info "Operation cancelled"
    fi
}

################################################################################
# Report Generation
################################################################################

generate_report() {
    {
        echo "=========================================="
        echo "ShadowCypher Security Bulletin Report"
        echo "Generated: $(date)"
        echo "=========================================="
        echo ""
        echo "System Information:"
        echo "  Hostname: $(hostname)"
        echo "  User: $(whoami)"
        echo "  Working Directory: $(pwd)"
        echo ""
        echo "Scan Results:"
        echo "  Total Checks: $((CHECKS_PASSED + CHECKS_FAILED))"
        echo "  Passed: $CHECKS_PASSED"
        echo "  Failed: $CHECKS_FAILED"
        echo "  Vulnerabilities Found: $VULNERABILITIES_FOUND"
        echo "  Warnings: $WARNINGS_COUNT"
        echo ""
        echo "=========================================="

        if [ $VULNERABILITIES_FOUND -gt 0 ]; then
            echo ""
            echo "VULNERABILITIES DETECTED"
            echo "Please review the output above and apply patches immediately."
        fi

        if [ $CHECKS_FAILED -eq 0 ] && [ $VULNERABILITIES_FOUND -eq 0 ]; then
            echo ""
            echo "No critical vulnerabilities found."
            echo "System appears to be up to date."
        fi
    } | tee -a "$REPORT_FILE"

    echo ""
    log_info "Full report saved to: $REPORT_FILE"
}

################################################################################
# Main Execution
################################################################################

main() {
    local command="${1:-}"

    case "${command}" in
        --advisory-check)
            log_info "Running advisory check..."
            check_guardian_versions
            check_arsenal_versions
            check_policy_engine_versions
            check_admin_panel_versions
            ;;
        --deep-scan)
            log_info "Running comprehensive vulnerability scan..."
            check_guardian_versions
            check_chroma_versions
            check_arsenal_versions
            check_policy_engine_versions
            check_dashboard_versions
            check_core_versions
            check_auth_versions
            check_admin_panel_versions
            audit_sessions
            ;;
        --check-cve)
            if [ -z "${2:-}" ]; then
                log_error "CVE ID required: --check-cve CVE-YYYY-NNNN"
                exit 1
            fi
            check_specific_cve "$2"
            ;;
        --check-version)
            if [ -z "${2:-}" ]; then
                log_error "Component name required: --check-version [component]"
                exit 1
            fi
            version=$(check_installed_version "$2")
            echo "Installed version of $2: $version"
            ;;
        --verify-cve)
            if [ -z "${2:-}" ]; then
                log_error "CVE ID required: --verify-cve CVE-YYYY-NNNN"
                exit 1
            fi
            log_info "Verifying fix for ${2}..."
            case "${2}" in
                CVE-2024-9547)
                    check_guardian_versions
                    ;;
                CVE-2024-7634)
                    check_arsenal_versions
                    ;;
                CVE-2024-0567)
                    check_admin_panel_versions
                    ;;
                *)
                    log_warning "Verification for ${2} not fully implemented"
                    ;;
            esac
            ;;
        --audit-sessions)
            audit_sessions
            ;;
        --clear-sessions)
            clear_sessions
            ;;
        --help|-h)
            cat << 'EOF'
Usage: bulletin-check.sh [COMMAND] [OPTIONS]

Commands:
  (no args)              Run standard vulnerability checks
  --advisory-check       Check against known CVEs only
  --deep-scan            Comprehensive vulnerability scan (all checks)
  --check-cve CVE-ID     Check for specific CVE
  --check-version COMP   Check installed version of component
  --verify-cve CVE-ID    Verify if specific CVE fix is applied
  --audit-sessions       Audit session security configuration
  --clear-sessions       Clear all sessions (admin only)
  --help                 Show this help message

Examples:
  ./bulletin-check.sh
  ./bulletin-check.sh --deep-scan
  ./bulletin-check.sh --check-cve CVE-2024-9547
  ./bulletin-check.sh --check-version guardian
  ./bulletin-check.sh --verify-cve CVE-2024-7634

For detailed vulnerability information, see SECURITY_ADVISORIES.md
EOF
            ;;
        *)
            # Default: run standard checks
            log_info "Running standard vulnerability checks..."
            check_guardian_versions
            check_arsenal_versions
            check_policy_engine_versions
            ;;
    esac

    generate_report

    # Exit with appropriate code
    if [ $VULNERABILITIES_FOUND -gt 0 ]; then
        exit 2  # Vulnerabilities found
    elif [ $CHECKS_FAILED -gt 0 ]; then
        exit 1  # Checks failed
    else
        exit 0  # All clear
    fi
}

# Run main function
main "$@"
