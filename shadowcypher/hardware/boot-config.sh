#!/bin/bash

################################################################################
# ShadowCypher Boot Configuration Manager
# Manages UEFI/BIOS boot profiles, Secure Boot, TPM, and firmware settings
################################################################################

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILES_FILE="${SCRIPT_DIR}/boot-profiles.json"
CONFIG_CACHE_DIR="/var/cache/shadowcypher/boot"
LOG_FILE="/var/log/shadowcypher/boot-config.log"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# Utility Functions
################################################################################

log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" >> "${LOG_FILE}"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $*"
    log "INFO" "$*"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
    log "SUCCESS" "$*"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
    log "WARN" "$*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*"
    log "ERROR" "$*"
}

require_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This operation requires root privileges"
        exit 1
    fi
}

require_jq() {
    if ! command -v jq &> /dev/null; then
        error "jq is required but not installed"
        exit 1
    fi
}

require_efibootmgr() {
    if ! command -v efibootmgr &> /dev/null; then
        error "efibootmgr is required but not installed"
        exit 1
    fi
}

################################################################################
# UEFI Detection and Validation
################################################################################

is_uefi_system() {
    if [ -d /sys/firmware/efi ]; then
        return 0
    else
        return 1
    fi
}

check_efi_vars_accessible() {
    if [ -d /sys/firmware/efi/efivars ] || [ -d /sys/firmware/efi/fw_platform_size ]; then
        return 0
    else
        return 1
    fi
}

get_secure_boot_status() {
    if command -v efibootmgr &> /dev/null; then
        efibootmgr -p 2>/dev/null | grep -q "Secure Boot: enabled" && echo "enabled" || echo "disabled"
    else
        echo "unknown"
    fi
}

get_setup_mode_status() {
    local setup_mode_path="/sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c"
    if [ -f "${setup_mode_path}" ]; then
        hexdump -C "${setup_mode_path}" | grep -oE '[0-9a-f]{2}$' | tail -1 | tr -d ' '
    else
        echo "unknown"
    fi
}

check_tpm_present() {
    if [ -c /dev/tpm0 ] || [ -c /dev/tpmrm0 ]; then
        return 0
    else
        return 1
    fi
}

get_tpm_version() {
    if command -v tpm2_getcap &> /dev/null; then
        tpm2_getcap properties-fixed 2>/dev/null | grep -i "TPM2_PT_FIRMWARE_VERSION" | head -1 || echo "2.0"
    elif [ -f /proc/driver/tpm/version ]; then
        cat /proc/driver/tpm/version
    else
        echo "unknown"
    fi
}

check_nx_bit_enabled() {
    if grep -q " nx " /proc/cpuinfo; then
        return 0
    else
        return 1
    fi
}

check_vt_d_enabled() {
    dmesg 2>/dev/null | grep -iq "IOMMU enabled" && return 0 || return 1
}

################################################################################
# Profile Management
################################################################################

validate_profiles_file() {
    if [ ! -f "${PROFILES_FILE}" ]; then
        error "Boot profiles file not found: ${PROFILES_FILE}"
        return 1
    fi

    if ! jq empty "${PROFILES_FILE}" 2>/dev/null; then
        error "Boot profiles file is not valid JSON"
        return 1
    fi

    return 0
}

list_profiles() {
    require_jq

    if ! validate_profiles_file; then
        return 1
    fi

    info "Available boot profiles:"
    jq -r '.profiles | keys[]' "${PROFILES_FILE}" | while read -r profile; do
        local name=$(jq -r ".profiles[\"${profile}\"].name" "${PROFILES_FILE}")
        local description=$(jq -r ".profiles[\"${profile}\"].description" "${PROFILES_FILE}")
        local security_level=$(jq -r ".profiles[\"${profile}\"].security_level" "${PROFILES_FILE}")
        printf "  %-20s %s (Security Level: %d)\n" "${profile}" "${name}" "${security_level}"
        printf "    %s\n" "${description}"
    done
}

get_profile() {
    local profile_name="$1"
    require_jq

    if ! validate_profiles_file; then
        return 1
    fi

    if ! jq -e ".profiles[\"${profile_name}\"]" "${PROFILES_FILE}" > /dev/null 2>&1; then
        error "Profile not found: ${profile_name}"
        return 1
    fi

    jq ".profiles[\"${profile_name}\"]" "${PROFILES_FILE}"
}

################################################################################
# Boot Variable Management
################################################################################

get_boot_order() {
    if command -v efibootmgr &> /dev/null; then
        efibootmgr -p 2>/dev/null | grep "BootOrder" | awk '{print $NF}' || echo ""
    else
        echo ""
    fi
}

show_boot_entries() {
    if command -v efibootmgr &> /dev/null; then
        info "Current boot entries:"
        efibootmgr -v | grep "^Boot"
    else
        error "efibootmgr not available"
        return 1
    fi
}

set_boot_timeout() {
    local timeout="$1"
    require_root
    require_efibootmgr

    info "Setting boot timeout to ${timeout} seconds"
    if efibootmgr -t "${timeout}" 2>/dev/null; then
        success "Boot timeout set to ${timeout} seconds"
        return 0
    else
        error "Failed to set boot timeout"
        return 1
    fi
}

################################################################################
# Validation Functions
################################################################################

validate_system() {
    local profile_name="$1"
    require_root

    info "Validating system configuration for profile: ${profile_name}"

    local profile
    profile=$(get_profile "${profile_name}") || return 1

    local passed=0
    local failed=0
    local warnings=0

    # Check UEFI system
    if is_uefi_system; then
        success "UEFI firmware detected"
        ((passed++))
    else
        error "UEFI firmware not detected (system may be BIOS-based)"
        ((failed++))
    fi

    # Check EFI vars accessible
    if check_efi_vars_accessible; then
        success "EFI variables are accessible"
        ((passed++))
    else
        error "EFI variables are not accessible"
        ((failed++))
    fi

    # Check Secure Boot
    local secure_boot_required=$(echo "${profile}" | jq -r '.uefi.secure_boot.enabled')
    local secure_boot_status=$(get_secure_boot_status)
    if [ "${secure_boot_required}" = "true" ]; then
        if [ "${secure_boot_status}" = "enabled" ]; then
            success "Secure Boot is enabled (required)"
            ((passed++))
        else
            error "Secure Boot is not enabled (required for this profile)"
            ((failed++))
        fi
    else
        info "Secure Boot not required for this profile (current: ${secure_boot_status})"
    fi

    # Check TPM
    local tpm_required=$(echo "${profile}" | jq -r '.uefi.tpm.enabled')
    if [ "${tpm_required}" = "true" ]; then
        if check_tpm_present; then
            success "TPM device detected"
            ((passed++))
        else
            error "TPM device not detected (required for this profile)"
            ((failed++))
        fi
    else
        info "TPM not required for this profile"
    fi

    # Check NX bit
    local nx_required=$(echo "${profile}" | jq -r '.uefi.memory_protection.nx_bit_enabled')
    if [ "${nx_required}" = "true" ]; then
        if check_nx_bit_enabled; then
            success "NX bit is enabled"
            ((passed++))
        else
            error "NX bit is not enabled (required for this profile)"
            ((failed++))
        fi
    fi

    # Check VT-d/IOMMU
    local iommu_required=$(echo "${profile}" | jq -r '.uefi.iommu.enabled')
    if [ "${iommu_required}" = "true" ]; then
        if check_vt_d_enabled; then
            success "VT-d/IOMMU is enabled"
            ((passed++))
        else
            warn "VT-d/IOMMU not detected in dmesg (may be disabled in BIOS)"
            ((warnings++))
        fi
    fi

    # Summary
    echo ""
    info "Validation Summary:"
    printf "  Passed:   %d\n" "${passed}"
    printf "  Failed:   %d\n" "${failed}"
    printf "  Warnings: %d\n" "${warnings}"

    if [ "${failed}" -gt 0 ]; then
        error "Validation failed for profile: ${profile_name}"
        return 1
    else
        success "Validation passed for profile: ${profile_name}"
        return 0
    fi
}

################################################################################
# Configuration Application
################################################################################

apply_profile() {
    local profile_name="$1"
    require_root

    info "Applying boot profile: ${profile_name}"

    local profile
    profile=$(get_profile "${profile_name}") || return 1

    # Set boot timeout
    local boot_timeout=$(echo "${profile}" | jq -r '.uefi.boot_timeout_seconds')
    if command -v efibootmgr &> /dev/null; then
        info "Setting boot timeout to ${boot_timeout} seconds"
        efibootmgr -t "${boot_timeout}" 2>/dev/null || warn "Could not set boot timeout"
    fi

    # Cache profile for reference
    mkdir -p "${CONFIG_CACHE_DIR}"
    echo "${profile}" > "${CONFIG_CACHE_DIR}/active-profile.json"
    echo "${profile_name}" > "${CONFIG_CACHE_DIR}/active-profile-name.txt"

    success "Boot profile applied: ${profile_name}"
    info "Note: Some UEFI settings (Secure Boot, TPM, VT-d) must be configured in BIOS/UEFI firmware menu"

    return 0
}

################################################################################
# System Information and Reporting
################################################################################

get_system_info() {
    info "System Boot Configuration Information:"
    echo ""

    # UEFI/BIOS info
    if is_uefi_system; then
        echo "Firmware Type:        UEFI"
    else
        echo "Firmware Type:        BIOS (legacy)"
    fi

    # Secure Boot
    echo "Secure Boot:          $(get_secure_boot_status)"
    echo "Setup Mode:           $(get_setup_mode_status)"

    # TPM
    if check_tpm_present; then
        echo "TPM Present:          Yes"
        echo "TPM Version:          $(get_tpm_version)"
    else
        echo "TPM Present:          No"
    fi

    # CPU features
    if check_nx_bit_enabled; then
        echo "NX Bit:               Enabled"
    else
        echo "NX Bit:               Disabled"
    fi

    if check_vt_d_enabled; then
        echo "VT-d/IOMMU:           Enabled"
    else
        echo "VT-d/IOMMU:           Not detected"
    fi

    echo ""
}

generate_report() {
    local output_file="${1:-boot-config-report.txt}"

    info "Generating boot configuration report..."

    {
        echo "================================================================================"
        echo "ShadowCypher Boot Configuration Report"
        echo "Generated: $(date)"
        echo "================================================================================"
        echo ""

        # System information
        get_system_info

        # Current active profile
        if [ -f "${CONFIG_CACHE_DIR}/active-profile-name.txt" ]; then
            echo "Active Profile:       $(cat ${CONFIG_CACHE_DIR}/active-profile-name.txt)"
        else
            echo "Active Profile:       None (use 'apply' command to apply a profile)"
        fi
        echo ""

        # Boot entries
        if command -v efibootmgr &> /dev/null; then
            echo "Current Boot Order:   $(get_boot_order)"
            echo ""
            echo "Boot Entries:"
            efibootmgr -v | grep "^Boot" | sed 's/^/  /'
        fi
        echo ""

        # Available profiles
        echo "Available Profiles:"
        jq -r '.profiles | keys[]' "${PROFILES_FILE}" | while read -r profile; do
            local name=$(jq -r ".profiles[\"${profile}\"].name" "${PROFILES_FILE}")
            printf "  - %s (%s)\n" "${profile}" "${name}"
        done
        echo ""

        echo "================================================================================"
    } | tee "${output_file}"

    success "Report generated: ${output_file}"
}

################################################################################
# Help and Usage
################################################################################

print_help() {
    cat << 'EOF'
ShadowCypher Boot Configuration Manager

USAGE:
    boot-config.sh [COMMAND] [OPTIONS]

COMMANDS:
    list                List all available boot profiles
    show-profile        Show details for a specific profile
                        USAGE: boot-config.sh show-profile <profile-name>

    apply               Apply a boot profile to the system
                        USAGE: boot-config.sh apply <profile-name>
                        REQUIRES: root privileges

    validate            Validate current system against a profile
                        USAGE: boot-config.sh validate <profile-name>
                        REQUIRES: root privileges

    status              Show current boot configuration status
                        USAGE: boot-config.sh status
                        REQUIRES: root privileges

    boot-info           Display current boot entries and order
                        USAGE: boot-config.sh boot-info
                        REQUIRES: root privileges

    report              Generate a detailed boot configuration report
                        USAGE: boot-config.sh report [OUTPUT_FILE]
                        REQUIRES: root privileges

    help                Show this help message

    version             Show version information

PROFILES:
    enterprise-server   High-security datacenter deployments
    workstation         Secure development workstations
    edge-device         Embedded and edge computing
    legacy-hardware     Older systems with minimal security support
    air-gapped          Isolated systems with manual verification

EXAMPLES:
    # List available profiles
    sudo ./boot-config.sh list

    # Apply enterprise server profile
    sudo ./boot-config.sh apply enterprise-server

    # Validate system against workstation profile
    sudo ./boot-config.sh validate workstation

    # Generate configuration report
    sudo ./boot-config.sh report boot-report.txt

    # Show current status
    sudo ./boot-config.sh status

NOTES:
    - Root privileges are required for most operations
    - UEFI firmware is required for full functionality
    - Some settings (Secure Boot, TPM, VT-d) must be configured in BIOS/UEFI
    - Configuration is logged to /var/log/shadowcypher/boot-config.log
    - Active profile is cached in /var/cache/shadowcypher/boot/

EOF
}

print_version() {
    echo "ShadowCypher Boot Configuration Manager v1.0"
}

################################################################################
# Main Command Handler
################################################################################

main() {
    # Ensure log directory exists
    mkdir -p "$(dirname "${LOG_FILE}")"
    mkdir -p "${CONFIG_CACHE_DIR}"

    if [ $# -eq 0 ]; then
        print_help
        exit 0
    fi

    local command="$1"
    shift

    case "${command}" in
        list)
            list_profiles
            ;;
        show-profile)
            if [ $# -lt 1 ]; then
                error "Profile name required"
                exit 1
            fi
            get_profile "$1" | jq . || exit 1
            ;;
        apply)
            if [ $# -lt 1 ]; then
                error "Profile name required"
                exit 1
            fi
            apply_profile "$1"
            ;;
        validate)
            if [ $# -lt 1 ]; then
                error "Profile name required"
                exit 1
            fi
            validate_system "$1"
            ;;
        status)
            get_system_info
            ;;
        boot-info)
            require_root
            show_boot_entries
            ;;
        report)
            require_root
            generate_report "${1:-boot-config-report.txt}"
            ;;
        help)
            print_help
            ;;
        version)
            print_version
            ;;
        *)
            error "Unknown command: ${command}"
            print_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
