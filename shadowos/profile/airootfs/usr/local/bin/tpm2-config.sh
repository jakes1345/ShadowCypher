#!/bin/bash
###############################################################################
# TPM 2.0 Sealing Configuration Script for ShadowCypher
#
# Purpose: Initialize TPM 2.0, create sealing policies, seal/unseal keys
# Usage: ./tpm2-config.sh <command> [options]
# Version: 1.0
###############################################################################

set -euo pipefail

# Configuration
readonly TPM_DEVICE="/dev/tpm0"
readonly TPM_CONFIG_DIR="/var/lib/shadowcypher"
readonly TPM_SEALED_BLOB="${TPM_CONFIG_DIR}/tpm-sealed.blob"
readonly TPM_PUBLIC_KEY="${TPM_CONFIG_DIR}/tpm-public.pem"
readonly TPM_AUDIT_LOG="/var/log/shadowcypher-tpm.log"
readonly CONFIG_FILE="/etc/tpm2-sealing.json"

# Script directories
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

###############################################################################
# Logging Functions
###############################################################################

log_info() {
    local msg="$1"
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $msg"
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $msg" >> "${TPM_AUDIT_LOG}"
}

log_success() {
    local msg="$1"
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $msg"
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') - $msg" >> "${TPM_AUDIT_LOG}"
}

log_warning() {
    local msg="$1"
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $msg" >&2
    echo "[WARNING] $(date '+%Y-%m-%d %H:%M:%S') - $msg" >> "${TPM_AUDIT_LOG}"
}

log_error() {
    local msg="$1"
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $msg" >&2
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $msg" >> "${TPM_AUDIT_LOG}"
}

###############################################################################
# Prerequisites & Validation
###############################################################################

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        return 1
    fi
}

check_dependencies() {
    local deps=("tpm2_getcap" "tpm2_createprimary" "tpm2_create" "tpm2_unseal" \
                "tpm2_pcrread" "tpm2_quote" "jq" "openssl" "cryptsetup")

    local missing=()
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing+=("$cmd")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing[*]}"
        log_info "Install tpm2-tools: apt-get install tpm2-tools"
        return 1
    fi

    log_success "All dependencies found"
    return 0
}

create_audit_log() {
    if [[ ! -f "${TPM_AUDIT_LOG}" ]]; then
        mkdir -p "$(dirname "${TPM_AUDIT_LOG}")"
        touch "${TPM_AUDIT_LOG}"
        chmod 600 "${TPM_AUDIT_LOG}"
        log_info "Created audit log: ${TPM_AUDIT_LOG}"
    fi
}

###############################################################################
# TPM 2.0 Detection & Initialization
###############################################################################

check_tpm() {
    log_info "Checking TPM 2.0 availability..."

    if [[ ! -e "${TPM_DEVICE}" ]]; then
        log_error "TPM device not found: ${TPM_DEVICE}"
        return 1
    fi

    if ! tpm2_getcap handles-persistent 2>/dev/null | grep -q "0x"; then
        log_error "TPM 2.0 not accessible or not responding"
        return 1
    fi

    log_success "TPM 2.0 detected and accessible"
    return 0
}

init_tpm_environment() {
    log_info "Initializing TPM 2.0 environment..."

    # Create necessary directories
    mkdir -p "${TPM_CONFIG_DIR}"
    mkdir -p "$(dirname "${TPM_AUDIT_LOG}")"

    chmod 700 "${TPM_CONFIG_DIR}"
    chmod 600 "${TPM_AUDIT_LOG}"

    # Clear TPM hierarchy authorization (password)
    log_info "Clearing TPM hierarchies..."
    tpm2_changeauth -c o "" 2>/dev/null || true
    tpm2_changeauth -c p "" 2>/dev/null || true
    tpm2_changeauth -c e "" 2>/dev/null || true

    # Clear existing persistent objects (safe for new initialization)
    tpm2_evictcontrol -C o 0x81000001 2>/dev/null || true

    log_success "TPM 2.0 environment initialized"
    return 0
}

###############################################################################
# TPM Primary Key & Sealing
###############################################################################

create_primary_key() {
    log_info "Creating TPM primary key..."

    # Create primary key in owner hierarchy
    tpm2_createprimary -C o -g sha256 -G rsa -c "${TPM_CONFIG_DIR}/primary.ctx" \
        -L "sha256:0,1,7" 2>/dev/null

    log_success "Primary key created"
}

create_sealing_policy() {
    log_info "Creating sealing policy based on PCR configuration..."

    local config_file="${1:-${CONFIG_FILE}}"

    if [[ ! -f "${config_file}" ]]; then
        log_error "Configuration file not found: ${config_file}"
        return 1
    fi

    # Extract PCR indices from config
    local pcr_spec=$(jq -r '.sealing_policy.pcr_selection | join(",")' "${config_file}")
    local pcr_array=($(echo "$pcr_spec" | tr ',' ' '))

    log_info "PCR selection: ${pcr_array[*]}"

    # Read current PCR values
    log_info "Reading current PCR values..."
    tpm2_pcrread -o "${TPM_CONFIG_DIR}/pcr.dat" \
        "${pcr_array[@]}" 2>/dev/null

    # Create sealing policy: PCR values must match
    tpm2_createpolicy --policy-pcr -l "${pcr_spec}" \
        -f "${TPM_CONFIG_DIR}/pcr.dat" \
        -L "${TPM_CONFIG_DIR}/seal-policy.dat" 2>/dev/null

    log_success "Sealing policy created for PCRs: ${pcr_array[*]}"
    return 0
}

seal_key() {
    local key_material="$1"

    log_info "Sealing key material to TPM..."

    if [[ -z "${key_material}" ]]; then
        log_error "Key material not provided"
        return 1
    fi

    # Create sealing object under primary key
    echo -n "${key_material}" | tpm2_create -C "${TPM_CONFIG_DIR}/primary.ctx" \
        -g sha256 -G keyedhash \
        -r "${TPM_CONFIG_DIR}/seal.priv" \
        -u "${TPM_CONFIG_DIR}/seal.pub" \
        -L "${TPM_CONFIG_DIR}/seal-policy.dat" \
        -i- 2>/dev/null

    # Load sealed object and save context
    tpm2_load -C "${TPM_CONFIG_DIR}/primary.ctx" \
        -r "${TPM_CONFIG_DIR}/seal.priv" \
        -u "${TPM_CONFIG_DIR}/seal.pub" \
        -c "${TPM_CONFIG_DIR}/seal.ctx" 2>/dev/null

    # Serialize sealed blob for storage
    {
        cat "${TPM_CONFIG_DIR}/seal.pub"
        cat "${TPM_CONFIG_DIR}/seal.priv"
    } > "${TPM_SEALED_BLOB}"

    chmod 600 "${TPM_SEALED_BLOB}"

    log_success "Key sealed and stored at: ${TPM_SEALED_BLOB}"
    return 0
}

unseal_key() {
    log_info "Unsealing key from TPM..."

    if [[ ! -f "${TPM_SEALED_BLOB}" ]]; then
        log_error "Sealed blob not found: ${TPM_SEALED_BLOB}"
        return 1
    fi

    # Verify PCRs match before unsealing
    if ! verify_pcrs; then
        log_error "PCR verification failed - unsealing denied"
        return 1
    fi

    # Extract blob components
    local pub_size=312  # Standard RSA public key size

    dd if="${TPM_SEALED_BLOB}" of="${TPM_CONFIG_DIR}/seal.pub" \
        bs=1 count=${pub_size} 2>/dev/null

    dd if="${TPM_SEALED_BLOB}" of="${TPM_CONFIG_DIR}/seal.priv" \
        bs=1 skip=${pub_size} 2>/dev/null

    # Load sealed object
    tpm2_load -C "${TPM_CONFIG_DIR}/primary.ctx" \
        -r "${TPM_CONFIG_DIR}/seal.priv" \
        -u "${TPM_CONFIG_DIR}/seal.pub" \
        -c "${TPM_CONFIG_DIR}/seal.ctx" 2>/dev/null

    # Unseal and output key
    local unsealed_key
    unsealed_key=$(tpm2_unseal -c "${TPM_CONFIG_DIR}/seal.ctx" 2>/dev/null)

    if [[ -z "${unsealed_key}" ]]; then
        log_error "Unsealing failed"
        return 1
    fi

    log_success "Key unsealed successfully"
    echo "${unsealed_key}"

    return 0
}

###############################################################################
# PCR Management
###############################################################################

verify_pcrs() {
    log_info "Verifying PCR values..."

    local config_file="${CONFIG_FILE}"

    if [[ ! -f "${config_file}" ]]; then
        log_warning "Configuration file not found, skipping PCR verification"
        return 0
    fi

    # Get expected PCR selection from config
    local pcr_spec=$(jq -r '.sealing_policy.pcr_selection | join(",")' "${config_file}" 2>/dev/null || echo "")

    if [[ -z "${pcr_spec}" ]]; then
        log_warning "No PCR selection in config, skipping verification"
        return 0
    fi

    local pcr_array=($(echo "$pcr_spec" | tr ',' ' '))

    # Read current PCR values
    log_info "Reading current PCR values..."
    local current_pcrs
    current_pcrs=$(tpm2_pcrread -o /tmp/current-pcr.dat "${pcr_array[@]}" 2>/dev/null)

    # Compare with sealing policy PCR values
    if [[ -f "${TPM_CONFIG_DIR}/pcr.dat" ]]; then
        if cmp -s /tmp/current-pcr.dat "${TPM_CONFIG_DIR}/pcr.dat"; then
            log_success "PCR values match sealing policy"
            rm -f /tmp/current-pcr.dat
            return 0
        else
            log_error "PCR values do not match sealing policy"
            log_info "PCR mismatch indicates platform state change (firmware, hardware, or secure boot)"
            return 1
        fi
    fi

    return 0
}

read_pcrs() {
    log_info "Reading current PCR values..."

    tpm2_pcrread -o /tmp/pcr.dat \
        sha256:0,1,2,3,4,5,6,7 2>/dev/null

    echo "Current PCR values:"
    tpm2_pcrread sha256:0,1,2,3,4,5,6,7 2>/dev/null

    return 0
}

###############################################################################
# Attestation
###############################################################################

create_attestation() {
    log_info "Creating attestation quote..."

    # Generate random nonce
    local nonce
    nonce=$(openssl rand -hex 32)

    # Create quote using primary key
    tpm2_quote -c "${TPM_CONFIG_DIR}/primary.ctx" \
        -l sha256:0,1,7 \
        -g sha256 \
        -o "${TPM_CONFIG_DIR}/quote.out" \
        -m "${TPM_CONFIG_DIR}/quote.msg" \
        -n "$nonce" 2>/dev/null

    # Get TPM public key for signature verification
    tpm2_readpublic -c "${TPM_CONFIG_DIR}/primary.ctx" \
        -o "${TPM_PUBLIC_KEY}" 2>/dev/null

    # Verify quote signature
    openssl dgst -sha256 \
        -verify "${TPM_PUBLIC_KEY}" \
        -signature "${TPM_CONFIG_DIR}/quote.out" \
        "${TPM_CONFIG_DIR}/quote.msg" 2>/dev/null

    if [[ $? -eq 0 ]]; then
        log_success "Attestation quote valid and verified"
        log_audit_event "attestation" "success" "$(cat ${TPM_CONFIG_DIR}/quote.msg | base64 -w0)"
        return 0
    else
        log_error "Attestation quote signature verification failed"
        log_audit_event "attestation" "failure" "signature_verification_failed"
        return 1
    fi
}

###############################################################################
# Audit & Logging
###############################################################################

log_audit_event() {
    local event_type="$1"
    local result="$2"
    local details="$3"

    local timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

    local audit_json
    audit_json=$(jq -n \
        --arg ts "$timestamp" \
        --arg et "$event_type" \
        --arg res "$result" \
        --arg det "$details" \
        '{timestamp: $ts, event_type: $et, result: $res, details: $det}')

    echo "$audit_json" >> "${TPM_AUDIT_LOG}"
}

show_audit_log() {
    log_info "Recent TPM audit events:"

    if [[ ! -f "${TPM_AUDIT_LOG}" ]]; then
        log_warning "Audit log not found"
        return 1
    fi

    tail -20 "${TPM_AUDIT_LOG}"
    return 0
}

###############################################################################
# Backup & Recovery
###############################################################################

generate_backup_key() {
    log_info "Generating backup unsealing key..."

    # Generate random 32-byte key (256-bit)
    local backup_key
    backup_key=$(openssl rand -hex 32)

    local backup_file="${TPM_CONFIG_DIR}/backup-unseal.key"

    echo "$backup_key" > "$backup_file"
    chmod 600 "$backup_file"

    log_success "Backup key generated: $backup_file"
    log_warning "SECURE THIS KEY SEPARATELY! It is independent of TPM."

    echo "$backup_key"
    return 0
}

recovery_unlock() {
    log_info "Starting recovery unlock procedure..."

    local backup_key_path="$1"

    if [[ ! -f "${backup_key_path}" ]]; then
        log_error "Backup key file not found: ${backup_key_path}"
        return 1
    fi

    local backup_key
    backup_key=$(cat "${backup_key_path}")

    log_success "Recovery key loaded"
    echo "$backup_key"

    return 0
}

###############################################################################
# Testing & Validation
###############################################################################

test_seal_unseal() {
    log_info "Running seal/unseal test..."

    local test_key="test-key-$(openssl rand -hex 16)"

    # Create temporary sealing policy
    local temp_dir=$(mktemp -d)
    tpm2_pcrread -o "${temp_dir}/pcr.dat" sha256:0,1,7 2>/dev/null
    tpm2_createpolicy --policy-pcr -l "sha256:0,1,7" \
        -f "${temp_dir}/pcr.dat" \
        -L "${temp_dir}/seal-policy.dat" 2>/dev/null

    # Seal test key
    echo -n "$test_key" | tpm2_create -C "${TPM_CONFIG_DIR}/primary.ctx" \
        -g sha256 -G keyedhash \
        -r "${temp_dir}/seal.priv" \
        -u "${temp_dir}/seal.pub" \
        -L "${temp_dir}/seal-policy.dat" \
        -i- 2>/dev/null

    # Load and unseal
    tpm2_load -C "${TPM_CONFIG_DIR}/primary.ctx" \
        -r "${temp_dir}/seal.priv" \
        -u "${temp_dir}/seal.pub" \
        -c "${temp_dir}/seal.ctx" 2>/dev/null

    local unsealed
    unsealed=$(tpm2_unseal -c "${temp_dir}/seal.ctx" 2>/dev/null)

    # Verify
    if [[ "${unsealed}" == "${test_key}" ]]; then
        log_success "Seal/unseal test PASSED"
        rm -rf "${temp_dir}"
        return 0
    else
        log_error "Seal/unseal test FAILED"
        rm -rf "${temp_dir}"
        return 1
    fi
}

###############################################################################
# Command Dispatcher
###############################################################################

usage() {
    cat << 'EOF'
TPM 2.0 Sealing Configuration for ShadowCypher

Usage: tpm2-config.sh <command> [options]

Commands:
  check                 - Check TPM 2.0 availability
  init                  - Initialize TPM 2.0 environment
  seal-create          - Create sealing policy from current PCRs
  seal-key             - Seal encryption key to TPM
  unseal-key           - Unseal encryption key from TPM
  unseal-test          - Test unsealing (verify it works)
  read-pcrs            - Display current PCR values
  verify-pcrs          - Verify PCR values match sealing policy
  attestation          - Create and verify attestation quote
  audit-log            - Display TPM audit log
  backup-key-generate  - Generate backup unsealing key
  recovery-unlock      - Recover access with backup key
  help                 - Show this help message

Examples:
  ./tpm2-config.sh check
  ./tpm2-config.sh init
  ./tpm2-config.sh seal-create
  ./tpm2-config.sh seal-key
  ./tpm2-config.sh unseal-key
  ./tpm2-config.sh backup-key-generate
  ./tpm2-config.sh recovery-unlock /path/to/backup.key

Configuration File:
  /etc/tpm2-sealing.json - PCR selection, sealing policies

Audit Log:
  /var/log/shadowcypher-tpm.log

EOF
}

main() {
    local command="${1:-help}"

    # Initialize audit log
    create_audit_log

    case "${command}" in
        check)
            check_root
            check_tpm
            ;;
        init)
            check_root
            check_dependencies
            check_tpm
            init_tpm_environment
            create_primary_key
            ;;
        seal-create)
            check_root
            check_dependencies
            create_sealing_policy "${2:-${CONFIG_FILE}}"
            ;;
        seal-key)
            check_root
            check_dependencies

            if [[ $# -lt 2 ]]; then
                log_error "Usage: $0 seal-key <key-material>"
                return 1
            fi

            seal_key "$2"
            ;;
        unseal-key)
            check_root
            check_dependencies
            unseal_key
            ;;
        unseal-test)
            check_root
            check_dependencies
            test_seal_unseal
            ;;
        read-pcrs)
            read_pcrs
            ;;
        verify-pcrs)
            verify_pcrs
            ;;
        attestation)
            check_root
            check_dependencies
            create_attestation
            ;;
        audit-log)
            show_audit_log
            ;;
        backup-key-generate)
            check_root
            generate_backup_key
            ;;
        recovery-unlock)
            if [[ $# -lt 2 ]]; then
                log_error "Usage: $0 recovery-unlock <backup-key-path>"
                return 1
            fi
            recovery_unlock "$2"
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log_error "Unknown command: ${command}"
            usage
            return 1
            ;;
    esac
}

main "$@"
