#!/bin/bash

###############################################################################
# ShadowCypher Device Checker
#
# Performs device identification, registry lookup, and compliance validation
# against the Certified Devices Registry.
#
# Usage:
#   device-checker.sh --check-device [device-model]
#   device-checker.sh --lookup-id VENDOR-MODEL-VARIANT
#   device-checker.sh --lookup-manufacturer "manufacturer"
#   device-checker.sh --lookup-model "model-pattern"
#   device-checker.sh --check-compliance DEVICE-ID
#   device-checker.sh --list-all
#   device-checker.sh --validate-registry
###############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REGISTRY_FILE="${PROJECT_ROOT}/data/security/device-registry.json"
LOG_DIR="${PROJECT_ROOT}/logs"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

###############################################################################
# Utility Functions
###############################################################################

log_info() {
    echo "[INFO] $*" | tee -a "${LOG_DIR}/device-checker.log"
}

log_error() {
    echo "[ERROR] $*" >&2 | tee -a "${LOG_DIR}/device-checker.log"
}

log_success() {
    echo "[SUCCESS] $*" | tee -a "${LOG_DIR}/device-checker.log"
}

log_warning() {
    echo "[WARNING] $*" | tee -a "${LOG_DIR}/device-checker.log"
}

# Check if required tools are available
check_dependencies() {
    local required_tools=("jq" "date")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool '$tool' not found. Please install it."
            exit 1
        fi
    done
}

# Validate registry file exists and is readable
validate_registry_file() {
    if [[ ! -f "${REGISTRY_FILE}" ]]; then
        log_error "Registry file not found: ${REGISTRY_FILE}"
        exit 1
    fi

    if [[ ! -r "${REGISTRY_FILE}" ]]; then
        log_error "Registry file not readable: ${REGISTRY_FILE}"
        exit 1
    fi
}

# Validate JSON format of registry
validate_json_format() {
    if ! jq empty "${REGISTRY_FILE}" 2>/dev/null; then
        log_error "Registry file contains invalid JSON"
        return 1
    fi
    return 0
}

###############################################################################
# Device Detection Functions
###############################################################################

# Detect current device information from system
detect_current_device() {
    local os_type="unknown"
    local device_model="unknown"

    # Detect OS type
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        os_type="linux"
        # Try to get device model
        if [[ -f /sys/devices/virtual/dmi/id/product_name ]]; then
            device_model=$(cat /sys/devices/virtual/dmi/id/product_name)
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        os_type="macos"
        device_model=$(system_profiler SPHardwareDataType | grep "Model Name" | awk -F': ' '{print $2}')
    fi

    echo "OS: ${os_type}, Device: ${device_model}"
}

###############################################################################
# Registry Query Functions
###############################################################################

# Lookup device by ID
lookup_by_id() {
    local device_id="$1"

    validate_registry_file
    validate_json_format

    log_info "Looking up device by ID: ${device_id}"

    local result
    result=$(jq --arg id "$device_id" '.devices[] | select(.id == $id)' "${REGISTRY_FILE}" 2>/dev/null)

    if [[ -z "$result" ]] || [[ "$result" == "null" ]]; then
        log_warning "Device not found in registry: ${device_id}"
        return 1
    fi

    echo "$result"
    return 0
}

# Lookup devices by manufacturer
lookup_by_manufacturer() {
    local manufacturer="$1"

    validate_registry_file
    validate_json_format

    log_info "Looking up devices by manufacturer: ${manufacturer}"

    local result
    result=$(jq --arg mfg "$manufacturer" '.devices[] | select(.manufacturer == $mfg)' "${REGISTRY_FILE}" 2>/dev/null)

    if [[ -z "$result" ]] || [[ "$result" == "null" ]]; then
        log_warning "No devices found for manufacturer: ${manufacturer}"
        return 1
    fi

    echo "$result"
    return 0
}

# Lookup devices by model pattern (supports wildcards)
lookup_by_model() {
    local model_pattern="$1"
    # Convert wildcard pattern to regex
    local regex_pattern="${model_pattern//\*/.*}"

    validate_registry_file
    validate_json_format

    log_info "Looking up devices by model pattern: ${model_pattern}"

    local result
    result=$(jq --arg pattern "$regex_pattern" '.devices[] | select(.model | test($pattern))' "${REGISTRY_FILE}" 2>/dev/null)

    if [[ -z "$result" ]] || [[ "$result" == "null" ]]; then
        log_warning "No devices found matching pattern: ${model_pattern}"
        return 1
    fi

    echo "$result"
    return 0
}

# List all devices in registry
list_all_devices() {
    validate_registry_file
    validate_json_format

    log_info "Listing all certified devices"

    jq '.devices[] | "\(.id): \(.manufacturer) \(.model) - \(.certification.level | ascii_upcase) (\(.certification.expiration_date))"' \
        "${REGISTRY_FILE}" 2>/dev/null
}

###############################################################################
# Compliance Check Functions
###############################################################################

# Check if device certification is current
check_certification_validity() {
    local device_id="$1"
    local expiration_date="$2"
    local today
    today=$(date +%Y-%m-%d)

    if [[ "$today" > "$expiration_date" ]]; then
        log_warning "Certification expired for ${device_id} (expired: ${expiration_date})"
        return 1
    fi

    return 0
}

# Perform full compliance check on device
check_device_compliance() {
    local device_id="$1"
    local device_data

    log_info "Checking compliance for device: ${device_id}"

    device_data=$(lookup_by_id "$device_id") || return 1

    local cert_level
    local expiration_date
    local compliance_standards
    local issues_found
    local last_verified

    cert_level=$(echo "$device_data" | jq -r '.certification.level')
    expiration_date=$(echo "$device_data" | jq -r '.certification.expiration_date')
    compliance_standards=$(echo "$device_data" | jq -r '.certification.compliance_standards[]' | tr '\n' ', ')
    issues_found=$(echo "$device_data" | jq -r '.audit_trail.issues_found')
    last_verified=$(echo "$device_data" | jq -r '.audit_trail.last_verified')

    echo ""
    echo "=========================================="
    echo "Device Compliance Report"
    echo "=========================================="
    echo "Device ID: ${device_id}"
    echo "Certification Level: $(echo "$cert_level" | tr '[:lower:]' '[:upper:]')"
    echo "Expiration Date: ${expiration_date}"
    echo "Last Verified: ${last_verified}"
    echo "Issues Found: ${issues_found}"
    echo "Compliance Standards: ${compliance_standards%,*}"
    echo ""

    # Check validity
    if check_certification_validity "$device_id" "$expiration_date"; then
        log_success "Device certification is VALID"
        echo "Status: COMPLIANT"
    else
        log_warning "Device certification is EXPIRED"
        echo "Status: NON-COMPLIANT (Certification Expired)"
    fi

    # Check issues
    if [[ "$issues_found" -gt 0 ]]; then
        log_warning "Device has ${issues_found} compliance issue(s)"
        echo "Recommendation: Schedule audit and remediation"
    else
        log_success "No compliance issues found"
        echo "Recommendation: No action required"
    fi

    echo "=========================================="
    echo ""
}

###############################################################################
# Validation Functions
###############################################################################

# Validate entire registry integrity
validate_registry_integrity() {
    log_info "Validating registry integrity"

    validate_registry_file || return 1
    validate_json_format || return 1

    local device_count
    device_count=$(jq '.devices | length' "${REGISTRY_FILE}")

    log_info "Registry contains ${device_count} certified devices"

    # Check for duplicate IDs
    local duplicate_ids
    duplicate_ids=$(jq '.devices[].id' "${REGISTRY_FILE}" | sort | uniq -d)

    if [[ -n "$duplicate_ids" ]]; then
        log_error "Duplicate device IDs found: ${duplicate_ids}"
        return 1
    fi

    # Validate each device record
    local valid_count=0
    local invalid_count=0

    while IFS= read -r device; do
        local device_id
        device_id=$(echo "$device" | jq -r '.id')

        # Check required fields
        local required_fields=("id" "manufacturer" "model" "specifications" "certification" "audit_trail")
        local missing_fields=()

        for field in "${required_fields[@]}"; do
            if [[ $(echo "$device" | jq "has(\"$field\")") != "true" ]]; then
                missing_fields+=("$field")
            fi
        done

        if [[ ${#missing_fields[@]} -gt 0 ]]; then
            log_warning "Device ${device_id} missing fields: ${missing_fields[*]}"
            ((invalid_count++))
        else
            ((valid_count++))
        fi
    done < <(jq -c '.devices[]' "${REGISTRY_FILE}")

    log_success "Registry validation complete: ${valid_count} valid, ${invalid_count} invalid"

    if [[ $invalid_count -gt 0 ]]; then
        return 1
    fi

    return 0
}

###############################################################################
# Report Generation
###############################################################################

# Generate compliance report
generate_report() {
    local report_file="${LOG_DIR}/device-compliance-report-${TIMESTAMP// /_}.txt"

    {
        echo "ShadowCypher Device Compliance Report"
        echo "Generated: ${TIMESTAMP}"
        echo "Registry: ${REGISTRY_FILE}"
        echo ""
        echo "=========================================="
        echo "Registry Summary"
        echo "=========================================="

        local total_devices
        local gold_count
        local silver_count
        local bronze_count

        total_devices=$(jq '.devices | length' "${REGISTRY_FILE}")
        gold_count=$(jq '[.devices[] | select(.certification.level == "gold")] | length' "${REGISTRY_FILE}")
        silver_count=$(jq '[.devices[] | select(.certification.level == "silver")] | length' "${REGISTRY_FILE}")
        bronze_count=$(jq '[.devices[] | select(.certification.level == "bronze")] | length' "${REGISTRY_FILE}")

        echo "Total Certified Devices: ${total_devices}"
        echo "Gold Level: ${gold_count}"
        echo "Silver Level: ${silver_count}"
        echo "Bronze Level: ${bronze_count}"
        echo ""

        echo "=========================================="
        echo "Expiration Status"
        echo "=========================================="

        local today
        today=$(date +%Y-%m-%d)

        local expired_count
        expired_count=$(jq --arg today "$today" '[.devices[] | select(.certification.expiration_date < $today)] | length' "${REGISTRY_FILE}")

        echo "Expired Certifications: ${expired_count}"

        if [[ $expired_count -gt 0 ]]; then
            echo ""
            echo "Expired Devices:"
            jq --arg today "$today" '.devices[] | select(.certification.expiration_date < $today) | "\(.id) - Expired: \(.certification.expiration_date)"' "${REGISTRY_FILE}"
        fi

    } | tee "$report_file"

    log_success "Report generated: ${report_file}"
}

###############################################################################
# Main Help/Usage
###############################################################################

show_usage() {
    cat << EOF
ShadowCypher Device Checker - Device Certification and Compliance Tool

USAGE:
    device-checker.sh [COMMAND] [OPTIONS]

COMMANDS:
    --check-device [model]      Check current device against registry (optional: specify device model)
    --lookup-id ID              Lookup device by certification ID
    --lookup-manufacturer NAME  List all devices from manufacturer
    --lookup-model PATTERN      List devices matching model pattern (supports *)
    --check-compliance ID       Perform full compliance check on device
    --list-all                  List all certified devices in registry
    --validate-registry         Validate registry integrity and format
    --generate-report           Generate compliance summary report
    --help                      Display this help message
    --version                   Show version information

EXAMPLES:
    # Check current device
    device-checker.sh --check-device

    # Lookup specific device
    device-checker.sh --lookup-id APPLE-IPHONE-15-PRO

    # Find all Apple devices
    device-checker.sh --lookup-manufacturer "Apple"

    # Find iPhones (any model)
    device-checker.sh --lookup-model "iPhone*"

    # Check compliance for a device
    device-checker.sh --check-compliance APPLE-IPHONE-15-PRO

    # Validate the registry
    device-checker.sh --validate-registry

REGISTRY LOCATION:
    ${REGISTRY_FILE}

LOG FILES:
    ${LOG_DIR}/device-checker.log

EOF
}

show_version() {
    echo "ShadowCypher Device Checker v1.0.0"
    echo "Registry Version: $(jq -r '.registry_version' "${REGISTRY_FILE}" 2>/dev/null || echo 'unknown')"
}

###############################################################################
# Main Entry Point
###############################################################################

main() {
    # Check dependencies
    check_dependencies

    # Parse arguments
    local command="${1:-}"

    case "$command" in
        --check-device)
            detect_current_device
            ;;
        --lookup-id)
            if [[ -z "${2:-}" ]]; then
                log_error "Device ID required for --lookup-id"
                exit 1
            fi
            lookup_by_id "$2" | jq '.' || exit 1
            ;;
        --lookup-manufacturer)
            if [[ -z "${2:-}" ]]; then
                log_error "Manufacturer name required for --lookup-manufacturer"
                exit 1
            fi
            lookup_by_manufacturer "$2" | jq '.' || exit 1
            ;;
        --lookup-model)
            if [[ -z "${2:-}" ]]; then
                log_error "Model pattern required for --lookup-model"
                exit 1
            fi
            lookup_by_model "$2" | jq '.' || exit 1
            ;;
        --check-compliance)
            if [[ -z "${2:-}" ]]; then
                log_error "Device ID required for --check-compliance"
                exit 1
            fi
            check_device_compliance "$2"
            ;;
        --list-all)
            list_all_devices
            ;;
        --validate-registry)
            validate_registry_integrity
            ;;
        --generate-report)
            generate_report
            ;;
        --help)
            show_usage
            ;;
        --version)
            show_version
            ;;
        *)
            log_error "Unknown command: ${command}"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
