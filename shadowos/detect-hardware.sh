#!/bin/bash
##########################################################################
# ShadowOS Hardware Detection Script
# Detects system boot mode, CPU, GPU, TPM, and Secure Boot configuration
#
# Usage: ./detect-hardware.sh [--json] [--verbose]
#
# Output: Hardware profile for boot configuration selection
##########################################################################

set -o pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VERBOSE=false
JSON_OUTPUT=false

##########################################################################
# Utility Functions
##########################################################################

log_info() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${BLUE}[INFO]${NC} $1" >&2
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_success() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${GREEN}[OK]${NC} $1" >&2
    fi
}

##########################################################################
# Boot Mode Detection
##########################################################################

detect_boot_mode() {
    local boot_mode="unknown"

    log_info "Detecting boot mode..."

    # Check for EFI System Table
    if [[ -d /sys/firmware/efi ]]; then
        boot_mode="uefi"
        log_success "Detected UEFI boot"
    elif [[ -d /sys/firmware/efi/efivars ]]; then
        boot_mode="uefi"
        log_success "Detected UEFI boot (efivars present)"
    elif [[ -e /proc/cmdline ]] && grep -q "efi=" /proc/cmdline; then
        boot_mode="uefi"
        log_success "Detected UEFI boot (efi cmdline)"
    else
        boot_mode="bios"
        log_success "Detected legacy BIOS boot"
    fi

    echo "$boot_mode"
}

##########################################################################
# Secure Boot Detection
##########################################################################

detect_secure_boot() {
    local secure_boot="disabled"
    local secure_boot_setup="unknown"

    log_info "Detecting Secure Boot status..."

    if [[ ! -d /sys/firmware/efi ]]; then
        log_warn "Not an EFI system, Secure Boot not available"
        echo "disabled:not_efi"
        return
    fi

    # Check Secure Boot status via efivarfs
    if [[ -e /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c ]]; then
        local sb_var=$(cat /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c 2>/dev/null | od -An -tx1 | tail -c 3 | tr -d ' ')
        if [[ "$sb_var" == "01" ]]; then
            secure_boot="enabled"
            log_success "Secure Boot is enabled"
        else
            secure_boot="disabled"
            log_info "Secure Boot is disabled"
        fi
    fi

    # Check Setup Mode
    if [[ -e /sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c ]]; then
        local setup_var=$(cat /sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c 2>/dev/null | od -An -tx1 | tail -c 3 | tr -d ' ')
        if [[ "$setup_var" == "01" ]]; then
            secure_boot_setup="setup"
            log_info "Secure Boot is in Setup Mode (keys can be enrolled)"
        else
            secure_boot_setup="user"
            log_info "Secure Boot is in User Mode"
        fi
    fi

    echo "${secure_boot}:${secure_boot_setup}"
}

##########################################################################
# CPU Detection
##########################################################################

detect_cpu() {
    local cpu_vendor="unknown"
    local cpu_model="unknown"
    local cpu_count=0
    local cpu_cores=0

    log_info "Detecting CPU information..."

    # Get CPU count and cores
    cpu_count=$(nproc 2>/dev/null || echo "1")
    cpu_cores=$(lscpu 2>/dev/null | grep "^Core(s) per socket:" | awk '{print $4}' || echo "$cpu_count")

    # Detect CPU vendor
    if [[ -f /proc/cpuinfo ]]; then
        if grep -qi "GenuineIntel" /proc/cpuinfo; then
            cpu_vendor="intel"
            cpu_model=$(grep -m1 "model name" /proc/cpuinfo | sed 's/.*: //')
            log_success "Detected Intel CPU: $cpu_model"
        elif grep -qi "AuthenticAMD" /proc/cpuinfo; then
            cpu_vendor="amd"
            cpu_model=$(grep -m1 "model name" /proc/cpuinfo | sed 's/.*: //')
            log_success "Detected AMD CPU: $cpu_model"
        elif grep -qi "ARM" /proc/cpuinfo; then
            cpu_vendor="arm"
            cpu_model=$(grep -m1 "model name" /proc/cpuinfo | sed 's/.*: //' || echo "ARM Processor")
            log_success "Detected ARM CPU: $cpu_model"
        fi
    fi

    echo "${cpu_vendor}:${cpu_model}:${cpu_count}:${cpu_cores}"
}

##########################################################################
# GPU Detection
##########################################################################

detect_gpu() {
    local gpu_vendor="none"
    local gpu_count=0

    log_info "Detecting GPU information..."

    # Check for NVIDIA GPUs
    if lspci 2>/dev/null | grep -qi "nvidia"; then
        gpu_vendor="nvidia"
        gpu_count=$(lspci 2>/dev/null | grep -c -i "nvidia")
        log_success "Detected $gpu_count NVIDIA GPU(s)"
    # Check for AMD GPUs
    elif lspci 2>/dev/null | grep -qi "AMD.*Radeon\|ATI"; then
        gpu_vendor="amd"
        gpu_count=$(lspci 2>/dev/null | grep -c -i "AMD.*Radeon\|ATI")
        log_success "Detected $gpu_count AMD GPU(s)"
    # Check for Intel GPUs
    elif lspci 2>/dev/null | grep -qi "Intel.*Graphics"; then
        gpu_vendor="intel"
        gpu_count=$(lspci 2>/dev/null | grep -c -i "Intel.*Graphics")
        log_success "Detected $gpu_count Intel GPU(s)"
    else
        log_info "No discrete GPU detected"
    fi

    echo "${gpu_vendor}:${gpu_count}"
}

##########################################################################
# TPM Detection
##########################################################################

detect_tpm() {
    local tpm_version="none"
    local tpm_present=false

    log_info "Detecting TPM information..."

    # Check for TPM 2.0
    if [[ -c /dev/tpm0 ]]; then
        # Try to get TPM version from sysfs
        if [[ -f /sys/class/tpm/tpm0/tpm_version_major ]]; then
            local major=$(cat /sys/class/tpm/tpm0/tpm_version_major 2>/dev/null)
            if [[ "$major" == "2" ]]; then
                tpm_version="2.0"
                tpm_present=true
                log_success "Detected TPM 2.0"
            elif [[ "$major" == "1" ]]; then
                tpm_version="1.2"
                tpm_present=true
                log_success "Detected TPM 1.2"
            fi
        fi

        # Fallback: check device node
        if [[ "$tpm_version" == "none" ]]; then
            # Try to detect via tpm2_getcap if available
            if command -v tpm2_getcap &>/dev/null; then
                if tpm2_getcap properties-fixed 2>/dev/null | grep -q "TPM2_PT_FIRMWARE_VERSION"; then
                    tpm_version="2.0"
                    tpm_present=true
                    log_success "Detected TPM 2.0 (via tpm2_getcap)"
                fi
            else
                # Assume TPM 2.0 if /dev/tpm0 exists and we're on modern system
                tpm_version="2.0"
                tpm_present=true
                log_success "Detected TPM (assumed 2.0)"
            fi
        fi
    else
        log_info "No TPM device detected"
    fi

    echo "${tpm_version}"
}

##########################################################################
# RAM Detection
##########################################################################

detect_ram() {
    local ram_mb=0

    log_info "Detecting RAM information..."

    if [[ -f /proc/meminfo ]]; then
        ram_mb=$(grep "^MemTotal:" /proc/meminfo | awk '{print $2/1024}' | cut -d'.' -f1)
        log_success "Detected ${ram_mb}MB RAM"
    fi

    echo "$ram_mb"
}

##########################################################################
# Storage Detection
##########################################################################

detect_storage() {
    local disk_count=0
    local disk_total_gb=0

    log_info "Detecting storage information..."

    if command -v lsblk &>/dev/null; then
        disk_count=$(lsblk -d -n -o NAME | wc -l)
        disk_total_gb=$(lsblk -d -n -o SIZE | sed 's/G.*//' | awk '{sum+=$1} END {print sum}')
        log_success "Detected $disk_count disk(s), ${disk_total_gb}GB total"
    fi

    echo "${disk_count}:${disk_total_gb}"
}

##########################################################################
# Generate Boot Configuration Recommendation
##########################################################################

recommend_boot_config() {
    local boot_mode="$1"
    local secure_boot="$2"
    local tpm="$3"
    local recommendation=""

    log_info "Generating boot configuration recommendation..."

    if [[ "$boot_mode" == "uefi" ]]; then
        if [[ "$tpm" != "none" ]]; then
            if [[ "$secure_boot" == "enabled" ]]; then
                recommendation="secure-boot-tpm"
            else
                recommendation="tpm"
            fi
        elif [[ "$secure_boot" == "enabled" ]]; then
            recommendation="secure-boot"
        else
            recommendation="uefi"
        fi
    else
        recommendation="legacy-bios"
    fi

    log_success "Recommended configuration: $recommendation"
    echo "$recommendation"
}

##########################################################################
# JSON Output
##########################################################################

output_json() {
    local boot_mode="$1"
    local sb_status="$2"
    local cpu_info="$3"
    local gpu_info="$4"
    local tpm_version="$5"
    local ram_mb="$6"
    local storage_info="$7"
    local recommendation="$8"

    IFS=':' read -r sb_enabled sb_setup <<<"$sb_status"
    IFS=':' read -r cpu_vendor cpu_model cpu_count cpu_cores <<<"$cpu_info"
    IFS=':' read -r gpu_vendor gpu_count <<<"$gpu_info"
    IFS=':' read -r disk_count disk_total <<<"$storage_info"

    cat <<EOF
{
  "hardware": {
    "boot_mode": "$boot_mode",
    "cpu": {
      "vendor": "$cpu_vendor",
      "model": "$cpu_model",
      "count": $cpu_count,
      "cores": $cpu_cores
    },
    "gpu": {
      "vendor": "$gpu_vendor",
      "count": $gpu_count
    },
    "ram_mb": $ram_mb,
    "storage": {
      "disk_count": $disk_count,
      "total_gb": $disk_total
    },
    "tpm": {
      "version": "$tpm_version"
    },
    "secure_boot": {
      "enabled": "$sb_enabled",
      "mode": "$sb_setup"
    }
  },
  "recommendation": "$recommendation"
}
EOF
}

##########################################################################
# Text Output
##########################################################################

output_text() {
    local boot_mode="$1"
    local sb_status="$2"
    local cpu_info="$3"
    local gpu_info="$4"
    local tpm_version="$5"
    local ram_mb="$6"
    local storage_info="$7"
    local recommendation="$8"

    IFS=':' read -r sb_enabled sb_setup <<<"$sb_status"
    IFS=':' read -r cpu_vendor cpu_model cpu_count cpu_cores <<<"$cpu_info"
    IFS=':' read -r gpu_vendor gpu_count <<<"$gpu_info"
    IFS=':' read -r disk_count disk_total <<<"$storage_info"

    cat <<EOF

${BLUE}=== ShadowOS Hardware Profile ===${NC}

Boot Configuration:
  Boot Mode:           $boot_mode
  Secure Boot:         $sb_enabled ($sb_setup)
  Recommended Config:  ${GREEN}$recommendation${NC}

Processor:
  Vendor:              $cpu_vendor
  Model:               $cpu_model
  Logical CPUs:        $cpu_count
  Cores per socket:    $cpu_cores

Graphics:
  GPU Vendor:          $gpu_vendor
  GPU Count:           $gpu_count

Memory:
  RAM:                 ${ram_mb}MB

Storage:
  Disks:               $disk_count
  Total Capacity:      ${disk_total}GB

Security:
  TPM Version:         $tpm_version

EOF
}

##########################################################################
# Main Function
##########################################################################

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    log_info "Starting hardware detection..."

    # Detect all hardware components
    local boot_mode=$(detect_boot_mode)
    local sb_status=$(detect_secure_boot)
    local cpu_info=$(detect_cpu)
    local gpu_info=$(detect_gpu)
    local tpm_version=$(detect_tpm)
    local ram_mb=$(detect_ram)
    local storage_info=$(detect_storage)

    # Generate recommendation
    IFS=':' read -r sb_enabled sb_setup <<<"$sb_status"
    local recommendation=$(recommend_boot_config "$boot_mode" "$sb_enabled" "$tpm_version")

    # Output results
    if [[ "$JSON_OUTPUT" == true ]]; then
        output_json "$boot_mode" "$sb_status" "$cpu_info" "$gpu_info" "$tpm_version" "$ram_mb" "$storage_info" "$recommendation"
    else
        output_text "$boot_mode" "$sb_status" "$cpu_info" "$gpu_info" "$tpm_version" "$ram_mb" "$storage_info" "$recommendation"
    fi

    log_info "Hardware detection complete"
}

show_help() {
    cat <<EOF
ShadowOS Hardware Detection Script

Usage: $0 [OPTIONS]

Options:
  --json              Output results in JSON format
  --verbose           Show detailed detection progress
  --help              Show this help message

Examples:
  # Basic detection with text output
  $0

  # Verbose detection with JSON output
  $0 --json --verbose

  # Parse JSON output
  $0 --json | jq '.hardware.cpu'

Output:
  Detects and reports:
  - Boot mode (UEFI or Legacy BIOS)
  - CPU vendor, model, and count
  - GPU vendor and count
  - TPM version (if present)
  - RAM amount
  - Storage configuration
  - Secure Boot status
  - Recommended boot configuration

Exit Codes:
  0   Successful detection
  1   Error during detection

EOF
}

# Run main function
main "$@"
