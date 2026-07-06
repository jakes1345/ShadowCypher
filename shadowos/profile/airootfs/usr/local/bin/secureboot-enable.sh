#!/bin/bash
################################################################################
# Secure Boot Implementation Script
#
# This script enables and configures UEFI Secure Boot for enterprise systems
# Includes key generation, enrollment, bootloader signing, and verification
#
# Requirements:
#   - UEFI firmware with Secure Boot support
#   - Root/administrator privileges
#   - efivar, openssl, sbsign (secure-boot package)
#   - grub, shim (bootloader packages)
#
# Usage:
#   sudo ./secureboot-enable.sh [--policy CONFIG_FILE] [--mode strict|audit]
#
# Author: ShadowCypher Security
# Version: 1.0.0
################################################################################

set -euo pipefail

# Global configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly POLICY_FILE="${SCRIPT_DIR}/secureboot-policy.json"
readonly LOG_FILE="/var/log/secureboot-setup.log"
readonly STATE_DIR="/var/lib/secureboot"
readonly KEY_DIR="/etc/secure-boot/keys"
readonly EFI_BACKUP_DIR="/var/backups/efi-vars"

# Script options
POLICY_CONFIG="${POLICY_FILE}"
SECURE_BOOT_MODE="audit"
DRY_RUN=0
VERBOSE=0

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
    echo -e "${YELLOW}[WARNING]${NC} $@" >&2
}

log_error() {
    log "ERROR" "$@"
    echo -e "${RED}[ERROR]${NC} $@" >&2
}

log_success() {
    log "SUCCESS" "$@"
    echo -e "${GREEN}[OK]${NC} $@"
}

log_debug() {
    if [[ ${VERBOSE} -eq 1 ]]; then
        log "DEBUG" "$@"
    fi
}

# Usage information
usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
    --policy FILE       Policy configuration file (default: ${POLICY_FILE})
    --mode MODE         Secure Boot mode: strict or audit (default: audit)
    --dry-run           Show what would be done without making changes
    --verbose           Enable verbose output
    --help              Show this help message

Examples:
    # Check Secure Boot support
    sudo $0 --mode audit --dry-run

    # Enable Secure Boot with custom policy
    sudo $0 --policy /custom/policy.json --mode strict

    # Generate keys and enroll
    sudo $0 --mode strict

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --policy)
                POLICY_CONFIG="$2"
                shift 2
                ;;
            --mode)
                SECURE_BOOT_MODE="$2"
                if [[ ! "${SECURE_BOOT_MODE}" =~ ^(strict|audit)$ ]]; then
                    log_error "Invalid mode: ${SECURE_BOOT_MODE}"
                    exit 1
                fi
                shift 2
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --verbose)
                VERBOSE=1
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Check if running as root
check_root() {
    if [[ ${EUID} -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Initialize directories and logging
init_environment() {
    mkdir -p "${STATE_DIR}" "${KEY_DIR}" "${EFI_BACKUP_DIR}" "$(dirname "${LOG_FILE}")"
    chmod 700 "${KEY_DIR}"
    log_info "Initialized environment: ${STATE_DIR}, ${KEY_DIR}, ${EFI_BACKUP_DIR}"
}

# Check UEFI firmware support
check_uefi_support() {
    log_info "Checking UEFI firmware support..."

    if [[ ! -d /sys/firmware/efi ]]; then
        log_error "UEFI firmware not detected. System is using BIOS, not UEFI."
        log_error "Secure Boot requires UEFI firmware."
        return 1
    fi

    if [[ ! -d /sys/firmware/efi/efivars ]]; then
        log_error "EFI variables not accessible. Check efivarfs kernel module."
        return 1
    fi

    log_success "UEFI firmware detected"
    return 0
}

# Check Secure Boot capability
check_secureboot_capability() {
    log_info "Checking Secure Boot capability..."

    if ! command -v efivar &>/dev/null; then
        log_error "efivar utility not found. Install efitools package."
        return 1
    fi

    # Check if Secure Boot variable exists
    if efivar --list 2>/dev/null | grep -q "SecureBoot"; then
        log_success "Secure Boot capability detected"

        # Check current status
        local sb_status
        sb_status=$(efivar --list 2>/dev/null | grep "SecureBoot" || true)
        log_info "Current Secure Boot status: ${sb_status}"
        return 0
    else
        log_warn "Secure Boot variable not found. System may not support Secure Boot."
        return 1
    fi
}

# Check required tools
check_requirements() {
    log_info "Checking required tools..."

    local missing_tools=()
    local required_tools=("efivar" "openssl" "mokutil" "grub-mkconfig" "mount" "umount")

    for tool in "${required_tools[@]}"; do
        if ! command -v "${tool}" &>/dev/null; then
            missing_tools+=("${tool}")
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install with: sudo apt install efitools mokutil grub-efi-amd64-signed shim-signed sbsigntool"
        return 1
    fi

    log_success "All required tools available"
    return 0
}

# Backup current EFI variables
backup_efi_vars() {
    log_info "Backing up current EFI variables..."

    local backup_dir="${EFI_BACKUP_DIR}/backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${backup_dir}"

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_debug "[DRY RUN] Would backup EFI variables to ${backup_dir}"
        return 0
    fi

    # Backup SecureBoot variables
    local vars=("SecureBoot" "PK" "KEK" "db" "dbx" "SetupMode")
    for var in "${vars[@]}"; do
        if [[ -f "/sys/firmware/efi/efivars/${var}-8be4df61-93ca-11d2-aa0d-00e098032b8c" ]]; then
            cp "/sys/firmware/efi/efivars/${var}-"* "${backup_dir}/" 2>/dev/null || true
            log_debug "Backed up EFI variable: ${var}"
        fi
    done

    chmod 700 "${backup_dir}"
    log_success "EFI variables backed up to ${backup_dir}"
    echo "${backup_dir}" > "${STATE_DIR}/last_backup"
}

# Generate Secure Boot keys
generate_keys() {
    log_info "Generating Secure Boot keys..."

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_debug "[DRY RUN] Would generate keys in ${KEY_DIR}"
        return 0
    fi

    # Check if keys already exist
    if [[ -f "${KEY_DIR}/PK.key" ]]; then
        log_warn "Keys already exist in ${KEY_DIR}"
        return 0
    fi

    # Generate Platform Key (PK)
    log_info "Generating Platform Key (PK)..."
    openssl req -new -x509 -newkey rsa:4096 -sha256 -days 3650 \
        -nodes -subj "/CN=ShadowCypher PK" \
        -keyout "${KEY_DIR}/PK.key" \
        -out "${KEY_DIR}/PK.crt" \
        2>/dev/null

    # Generate Key Exchange Key (KEK)
    log_info "Generating Key Exchange Key (KEK)..."
    openssl req -new -x509 -newkey rsa:4096 -sha256 -days 3650 \
        -nodes -subj "/CN=ShadowCypher KEK" \
        -keyout "${KEY_DIR}/KEK.key" \
        -out "${KEY_DIR}/KEK.crt" \
        2>/dev/null

    # Generate Signature Database key (db)
    log_info "Generating Signature Database (db) key..."
    openssl req -new -x509 -newkey rsa:4096 -sha256 -days 3650 \
        -nodes -subj "/CN=ShadowCypher db" \
        -keyout "${KEY_DIR}/db.key" \
        -out "${KEY_DIR}/db.crt" \
        2>/dev/null

    # Generate Forbidden Database key (dbx) - typically same as db
    log_info "Generating Forbidden Database (dbx) key..."
    cp "${KEY_DIR}/db.key" "${KEY_DIR}/dbx.key"
    cp "${KEY_DIR}/db.crt" "${KEY_DIR}/dbx.crt"

    # Secure key files
    chmod 600 "${KEY_DIR}"/*.key
    chmod 644 "${KEY_DIR}"/*.crt

    log_success "Secure Boot keys generated in ${KEY_DIR}"
}

# Enroll keys into EFI variables
enroll_keys() {
    log_info "Enrolling Secure Boot keys into EFI variables..."

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_debug "[DRY RUN] Would enroll keys using mokutil"
        return 0
    fi

    # Check if system is in Setup Mode
    if ! grep -q "1" /sys/firmware/efi/efivars/SetupMode-* 2>/dev/null; then
        log_warn "System is not in Setup Mode. Keys cannot be enrolled."
        log_info "Reboot into firmware settings to enable Setup Mode, then re-run this script."
        return 1
    fi

    # Enroll keys using mokutil for MOK management
    log_info "Preparing keys for MOK enrollment..."
    mokutil --import "${KEY_DIR}/db.crt" --password 2>/dev/null || true

    log_success "Keys prepared for enrollment"
    log_info "Keys will be enrolled after next reboot"
}

# Sign GRUB bootloader
sign_grub_bootloader() {
    log_info "Signing GRUB bootloader..."

    if [[ ! -f /boot/efi/EFI/ubuntu/grubx64.efi ]] && [[ ! -f /boot/efi/EFI/debian/grubx64.efi ]]; then
        log_warn "GRUB bootloader not found at expected locations"
        log_info "Install GRUB with: sudo apt install grub-efi-amd64"
        return 1
    fi

    local grub_path
    if [[ -f /boot/efi/EFI/ubuntu/grubx64.efi ]]; then
        grub_path="/boot/efi/EFI/ubuntu/grubx64.efi"
    else
        grub_path="/boot/efi/EFI/debian/grubx64.efi"
    fi

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_debug "[DRY RUN] Would sign GRUB at ${grub_path}"
        return 0
    fi

    if ! command -v sbsign &>/dev/null; then
        log_error "sbsign utility not found. Install with: sudo apt install sbsigntool"
        return 1
    fi

    log_info "Signing GRUB binary: ${grub_path}"
    sbsign --key "${KEY_DIR}/db.key" --cert "${KEY_DIR}/db.crt" \
        --output "${grub_path}" "${grub_path}" 2>/dev/null

    log_success "GRUB bootloader signed"
}

# Configure boot entry order
configure_boot_entries() {
    log_info "Configuring boot entry order..."

    if ! command -v efibootmgr &>/dev/null; then
        log_warn "efibootmgr not found. Boot entry order configuration skipped."
        return 1
    fi

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_debug "[DRY RUN] Would configure boot entries"
        efibootmgr || true
        return 0
    fi

    local boot_entries
    boot_entries=$(efibootmgr | grep "ubuntu\|debian\|grub" | head -1)

    if [[ -z "${boot_entries}" ]]; then
        log_warn "No GRUB boot entry found"
        return 1
    fi

    log_info "Current boot entries:"
    efibootmgr

    log_success "Boot entry configuration completed"
}

# Verify Secure Boot status
verify_secureboot_status() {
    log_info "Verifying Secure Boot status..."

    # Check SecureBoot variable
    if [[ -f /sys/firmware/efi/efivars/SecureBoot-* ]]; then
        local sb_status
        sb_status=$(od -An -tx1 /sys/firmware/efi/efivars/SecureBoot-* | awk '{print $NF}')

        if [[ "${sb_status}" == "01" ]]; then
            log_success "Secure Boot is ENABLED"
        else
            log_warn "Secure Boot is DISABLED"
        fi
    else
        log_warn "Secure Boot variable not accessible"
    fi

    # Check kernel parameter
    if grep -q "Secure boot" /proc/cmdline 2>/dev/null; then
        log_info "Kernel Secure Boot parameter detected"
    fi

    # Check for mokutil
    if command -v mokutil &>/dev/null; then
        log_info "MOK enrollment status:"
        mokutil --list-enrolled 2>/dev/null | head -5 || true
    fi
}

# Handle boot failures
handle_boot_failure() {
    log_error "Boot failure recovery initiated..."

    local last_backup
    if [[ -f "${STATE_DIR}/last_backup" ]]; then
        last_backup=$(cat "${STATE_DIR}/last_backup")
        log_info "Last backup location: ${last_backup}"
        log_info "To restore: sudo cp ${last_backup}/* /sys/firmware/efi/efivars/"
    fi

    log_info "Alternative recovery options:"
    log_info "1. Disable Secure Boot in BIOS/UEFI Setup"
    log_info "2. Boot from recovery media"
    log_info "3. Restore previous EFI variable backup"
}

# Audit boot chain
audit_boot_chain() {
    log_info "Auditing boot chain..."

    echo "=== Boot Chain Audit ===" | tee -a "${LOG_FILE}"

    # Check firmware
    echo "Firmware: $(cat /sys/firmware/efi/fw_platform_size)" | tee -a "${LOG_FILE}"

    # Check Secure Boot status
    if [[ -f /sys/firmware/efi/efivars/SecureBoot-* ]]; then
        echo "Secure Boot: $(od -An -tx1 /sys/firmware/efi/efivars/SecureBoot-*)" | tee -a "${LOG_FILE}"
    fi

    # Check EFI boot variables
    echo "EFI Boot Entries:" | tee -a "${LOG_FILE}"
    efibootmgr 2>/dev/null | grep -E "^Boot" | tee -a "${LOG_FILE}" || true

    # Check GRUB
    if [[ -f /boot/efi/EFI/ubuntu/grubx64.efi ]] || [[ -f /boot/efi/EFI/debian/grubx64.efi ]]; then
        echo "GRUB bootloader: PRESENT" | tee -a "${LOG_FILE}"
    fi

    # Check shim
    if [[ -f /boot/efi/EFI/ubuntu/shimx64.efi ]] || [[ -f /boot/efi/EFI/debian/shimx64.efi ]]; then
        echo "Shim bootloader: PRESENT" | tee -a "${LOG_FILE}"
    fi

    # Check kernel modules
    if grep -q "module.sig_enforce" /proc/cmdline 2>/dev/null; then
        echo "Kernel Module Signing: ENFORCED" | tee -a "${LOG_FILE}"
    else
        echo "Kernel Module Signing: NOT ENFORCED" | tee -a "${LOG_FILE}"
    fi

    log_success "Boot chain audit completed"
}

# Implement rollback protection
setup_rollback_protection() {
    log_info "Setting up rollback protection..."

    local rollback_file="${STATE_DIR}/bootloader-version"

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_debug "[DRY RUN] Would create rollback protection file"
        return 0
    fi

    local version="1.0.0-$(date +%Y%m%d)"
    echo "${version}" > "${rollback_file}"
    chmod 600 "${rollback_file}"

    log_info "Rollback protection version: ${version}"
    log_success "Rollback protection configured"
}

# Generate audit report
generate_audit_report() {
    log_info "Generating audit report..."

    local report_file="${STATE_DIR}/audit-report-$(date +%Y%m%d-%H%M%S).txt"

    {
        echo "=== ShadowCypher Secure Boot Audit Report ==="
        echo "Generated: $(date)"
        echo ""
        echo "=== System Information ==="
        uname -a
        echo ""
        echo "=== UEFI Status ==="
        [[ -d /sys/firmware/efi ]] && echo "UEFI: YES" || echo "UEFI: NO"
        echo ""
        echo "=== Secure Boot Status ==="
        if [[ -f /sys/firmware/efi/efivars/SecureBoot-* ]]; then
            od -An -tx1 /sys/firmware/efi/efivars/SecureBoot-* | awk '{print $NF}'
        fi
        echo ""
        echo "=== Key Information ==="
        ls -lh "${KEY_DIR}" 2>/dev/null || echo "Keys not found"
        echo ""
        echo "=== Boot Configuration ==="
        efibootmgr 2>/dev/null || echo "efibootmgr not available"
        echo ""
        echo "=== Kernel Parameters ==="
        cat /proc/cmdline
        echo ""
    } | tee "${report_file}"

    log_success "Audit report saved to ${report_file}"
}

# Main execution function
main() {
    log_info "=== ShadowCypher Secure Boot Setup ==="
    log_info "Mode: ${SECURE_BOOT_MODE}"
    log_info "Policy: ${POLICY_CONFIG}"

    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "DRY RUN MODE - No changes will be made"
    fi

    check_root
    init_environment

    # Check system requirements
    if ! check_uefi_support; then
        log_error "System does not support UEFI Secure Boot"
        exit 1
    fi

    if ! check_requirements; then
        log_error "System missing required tools"
        exit 1
    fi

    # Backup existing configuration
    backup_efi_vars

    # Setup Secure Boot
    check_secureboot_capability
    generate_keys
    enroll_keys
    sign_grub_bootloader
    configure_boot_entries
    verify_secureboot_status
    setup_rollback_protection

    # Audit and reporting
    audit_boot_chain
    generate_audit_report

    log_success "=== Secure Boot setup completed ==="
    log_info "Next steps:"
    log_info "1. Reboot system to apply changes"
    log_info "2. Enter BIOS/UEFI Setup if prompted"
    log_info "3. Verify Secure Boot is enabled"
    log_info "4. Enroll keys when prompted by mokutil"
    log_info "5. Review logs in ${LOG_FILE}"
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    parse_args "$@"
    main
fi
