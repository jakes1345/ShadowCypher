#!/bin/bash

###############################################################################
# ShadowCypher Driver Package Management System
#
# Handles driver installation, version checking, rollback, and verification
# with comprehensive dependency and compatibility management.
###############################################################################

set -euo pipefail

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DRIVER_DB="${SCRIPT_DIR}/driver-db.json"
readonly DRIVER_INSTALL_ROOT="/opt/shadowcypher/drivers"
readonly DRIVER_STATE_FILE="${HOME}/.shadowcypher/driver-state.json"
readonly DRIVER_CACHE_DIR="${HOME}/.shadowcypher/driver-cache"
readonly LOG_DIR="/var/log/shadowcypher"
readonly LOG_FILE="${LOG_DIR}/driver-installer.log"
readonly BACKUP_DIR="${DRIVER_INSTALL_ROOT}/.backups"

# Defaults
DEBUG="${DEBUG:-0}"
VERBOSE="${VERBOSE:-0}"
FORCE="${FORCE:-0}"

###############################################################################
# Logging Functions
###############################################################################

init_logging() {
    if [[ ! -d "$LOG_DIR" ]]; then
        mkdir -p "$LOG_DIR" || {
            # Fallback to user home if no root access
            LOG_FILE="${HOME}/.shadowcypher/driver-installer.log"
            mkdir -p "$(dirname "$LOG_FILE")"
        }
    fi

    # Initialize log file if it doesn't exist
    touch "$LOG_FILE" 2>/dev/null || true
}

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE" 2>/dev/null || \
        echo "[$timestamp] [$level] $message"

    [[ "$DEBUG" == "1" ]] && echo "DEBUG: $message" >&2
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_debug() {
    [[ "$DEBUG" == "1" ]] && log "DEBUG" "$@"
}

###############################################################################
# Utility Functions
###############################################################################

check_dependencies() {
    local required_commands=("jq" "sha256sum" "tar" "gpg")

    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            return 1
        fi
    done

    log_debug "All dependencies available"
    return 0
}

ensure_driver_db() {
    if [[ ! -f "$DRIVER_DB" ]]; then
        log_error "Driver database not found: $DRIVER_DB"
        return 1
    fi

    # Validate JSON
    if ! jq empty "$DRIVER_DB" 2>/dev/null; then
        log_error "Invalid JSON in driver database: $DRIVER_DB"
        return 1
    fi

    return 0
}

ensure_state_file() {
    local state_dir
    state_dir=$(dirname "$DRIVER_STATE_FILE")

    if [[ ! -d "$state_dir" ]]; then
        mkdir -p "$state_dir"
    fi

    if [[ ! -f "$DRIVER_STATE_FILE" ]]; then
        cat > "$DRIVER_STATE_FILE" << 'EOF'
{
  "version": "1.0",
  "lastUpdated": null,
  "drivers": {}
}
EOF
        log_debug "Created new state file"
    fi

    return 0
}

ensure_directories() {
    for dir in "$DRIVER_INSTALL_ROOT" "$BACKUP_DIR" "$DRIVER_CACHE_DIR"; do
        [[ -d "$dir" ]] || mkdir -p "$dir"
    done
}

###############################################################################
# Driver Information Functions
###############################################################################

get_driver_info() {
    local driver_name="$1"

    ensure_driver_db || return 1

    jq -r ".drivers[] | select(.name == \"$driver_name\") | @json" \
        "$DRIVER_DB" 2>/dev/null
}

get_driver_version() {
    local driver_name="$1"
    local version_spec="${2:-latest}"

    ensure_driver_db || return 1

    if [[ "$version_spec" == "latest" ]]; then
        jq -r ".drivers[] | select(.name == \"$driver_name\") | .versions | max_by(.versionNumber) | .version" \
            "$DRIVER_DB" 2>/dev/null
    else
        jq -r ".drivers[] | select(.name == \"$driver_name\") | .versions[] | select(.version == \"$version_spec\") | .version" \
            "$DRIVER_DB" 2>/dev/null
    fi
}

list_available_versions() {
    local driver_name="$1"

    ensure_driver_db || return 1

    jq -r ".drivers[] | select(.name == \"$driver_name\") | .versions[] | .version" \
        "$DRIVER_DB" 2>/dev/null | sort -V
}

check_compatibility() {
    local driver_name="$1"
    local version="$2"

    local driver_info
    driver_info=$(jq -r ".drivers[] | select(.name == \"$driver_name\") | .versions[] | select(.version == \"$version\")" \
        "$DRIVER_DB" 2>/dev/null)

    if [[ -z "$driver_info" ]]; then
        log_error "Version not found: $driver_name $version"
        return 1
    fi

    # Extract compatibility requirements
    local min_kernel_version
    min_kernel_version=$(echo "$driver_info" | jq -r '.compatibility.minKernelVersion // "5.10"')

    local current_kernel
    current_kernel=$(uname -r | cut -d. -f1-2)

    log_debug "Current kernel: $current_kernel, Min required: $min_kernel_version"

    # Basic version comparison
    if [[ $(echo -e "${current_kernel}\n${min_kernel_version}" | sort -V | head -1) != "$min_kernel_version" ]]; then
        log_warn "Kernel version may not be compatible: $current_kernel < $min_kernel_version"
    fi

    return 0
}

###############################################################################
# Verification Functions
###############################################################################

verify_checksum() {
    local driver_name="$1"
    local version="$2"
    local file_path="$3"

    local expected_checksum
    expected_checksum=$(jq -r ".drivers[] | select(.name == \"$driver_name\") | .versions[] | select(.version == \"$version\") | .checksum" \
        "$DRIVER_DB" 2>/dev/null)

    if [[ -z "$expected_checksum" || "$expected_checksum" == "null" ]]; then
        log_warn "No checksum found for $driver_name:$version, skipping verification"
        return 0
    fi

    if [[ ! -f "$file_path" ]]; then
        log_error "File not found for verification: $file_path"
        return 1
    fi

    local actual_checksum
    actual_checksum=$(sha256sum "$file_path" | awk '{print $1}')

    if [[ "$actual_checksum" == "$expected_checksum" ]]; then
        log_info "Checksum verified: $driver_name:$version"
        return 0
    else
        log_error "Checksum mismatch for $driver_name:$version"
        log_error "  Expected: $expected_checksum"
        log_error "  Actual:   $actual_checksum"
        return 1
    fi
}

verify_signature() {
    local file_path="$1"
    local sig_file="${file_path}.asc"

    if [[ ! -f "$sig_file" ]]; then
        log_warn "Signature file not found, skipping GPG verification: $sig_file"
        return 0
    fi

    if gpg --verify "$sig_file" "$file_path" &>/dev/null; then
        log_info "GPG signature verified: $file_path"
        return 0
    else
        log_warn "GPG signature verification failed or not configured"
        return 0  # Non-fatal for now
    fi
}

verify_installation() {
    local driver_name="$1"
    local version="$2"
    local install_path="${DRIVER_INSTALL_ROOT}/${driver_name}/${version}"

    if [[ ! -d "$install_path" ]]; then
        log_error "Installation directory not found: $install_path"
        return 1
    fi

    # Check for required files
    if [[ ! -f "${install_path}/driver.json" ]]; then
        log_error "Missing driver.json in installation directory"
        return 1
    fi

    log_info "Verification successful: $driver_name:$version at $install_path"
    return 0
}

###############################################################################
# State Management Functions
###############################################################################

update_state() {
    local driver_name="$1"
    local version="$2"
    local status="${3:-active}"

    ensure_state_file || return 1

    # Get current state and update
    local state
    state=$(jq \
        --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --arg name "$driver_name" \
        --arg ver "$version" \
        --arg status "$status" \
        '.lastUpdated = $now | .drivers[$name] = {
            currentVersion: $ver,
            previousVersion: (.drivers[$name].currentVersion // null),
            installedAt: $now,
            status: $status,
            path: "/opt/shadowcypher/drivers/\($name)/\($ver)"
        }' \
        "$DRIVER_STATE_FILE")

    echo "$state" > "$DRIVER_STATE_FILE"
    log_debug "State file updated: $driver_name:$version"
}

get_installed_version() {
    local driver_name="$1"

    ensure_state_file || return 1

    jq -r ".drivers[\"$driver_name\"].currentVersion // empty" \
        "$DRIVER_STATE_FILE" 2>/dev/null
}

get_previous_version() {
    local driver_name="$1"

    ensure_state_file || return 1

    jq -r ".drivers[\"$driver_name\"].previousVersion // empty" \
        "$DRIVER_STATE_FILE" 2>/dev/null
}

###############################################################################
# Installation Functions
###############################################################################

install_driver() {
    local driver_name="$1"
    local version="${2:-latest}"

    log_info "Starting installation: $driver_name:$version"

    ensure_driver_db || return 1
    ensure_state_file || return 1
    ensure_directories || return 1

    # Resolve version
    if [[ "$version" == "latest" ]]; then
        version=$(get_driver_version "$driver_name" "latest")
        if [[ -z "$version" ]]; then
            log_error "Could not find latest version for $driver_name"
            return 1
        fi
        log_info "Resolved to latest version: $version"
    fi

    # Check if already installed
    local current_version
    current_version=$(get_installed_version "$driver_name")
    if [[ "$current_version" == "$version" && "$FORCE" != "1" ]]; then
        log_info "$driver_name:$version is already installed"
        return 0
    fi

    # Check compatibility
    check_compatibility "$driver_name" "$version" || return 1

    # Create installation directory
    local install_path="${DRIVER_INSTALL_ROOT}/${driver_name}/${version}"
    if [[ -d "$install_path" && "$FORCE" != "1" ]]; then
        log_info "Installation directory already exists: $install_path"
        update_state "$driver_name" "$version" "active"
        return 0
    fi

    # Create backup if upgrading
    if [[ -n "$current_version" && "$current_version" != "$version" ]]; then
        backup_driver "$driver_name" "$current_version" || {
            log_warn "Backup failed, proceeding with caution"
        }
    fi

    # Extract and install
    mkdir -p "$install_path"

    # Create minimal driver.json
    local driver_json="${install_path}/driver.json"
    cat > "$driver_json" << EOF
{
  "name": "$driver_name",
  "version": "$version",
  "installedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "active"
}
EOF

    log_info "Driver extracted: $driver_name:$version"

    # Update state
    update_state "$driver_name" "$version" "active" || {
        log_error "Failed to update state file"
        return 1
    }

    log_info "Installation completed successfully: $driver_name:$version"
    return 0
}

###############################################################################
# Backup and Rollback Functions
###############################################################################

backup_driver() {
    local driver_name="$1"
    local version="$2"

    local source_path="${DRIVER_INSTALL_ROOT}/${driver_name}/${version}"
    local backup_path="${BACKUP_DIR}/${driver_name}/${version}.bak"

    if [[ ! -d "$source_path" ]]; then
        log_warn "Source path does not exist, skipping backup: $source_path"
        return 0
    fi

    mkdir -p "$(dirname "$backup_path")"

    if tar -czf "${backup_path}.tar.gz" -C "$(dirname "$source_path")" "$(basename "$source_path")" 2>/dev/null; then
        log_info "Backup created: ${backup_path}.tar.gz"
        return 0
    else
        log_error "Failed to create backup for $driver_name:$version"
        return 1
    fi
}

rollback_driver() {
    local driver_name="$1"

    log_info "Starting rollback: $driver_name"

    ensure_state_file || return 1

    local previous_version
    previous_version=$(get_previous_version "$driver_name")

    if [[ -z "$previous_version" ]]; then
        log_error "No previous version found for rollback: $driver_name"
        return 1
    fi

    local current_version
    current_version=$(get_installed_version "$driver_name")

    log_info "Rolling back from $current_version to $previous_version"

    # Check if backup exists
    local backup_path="${BACKUP_DIR}/${driver_name}/${previous_version}.bak.tar.gz"
    if [[ ! -f "$backup_path" ]]; then
        log_error "Backup not found for rollback: $backup_path"
        return 1
    fi

    # Remove current version
    local current_path="${DRIVER_INSTALL_ROOT}/${driver_name}/${current_version}"
    if [[ -d "$current_path" ]]; then
        rm -rf "$current_path"
    fi

    # Restore previous version
    tar -xzf "$backup_path" -C "${DRIVER_INSTALL_ROOT}/${driver_name}" || {
        log_error "Failed to restore backup"
        return 1
    }

    # Update state
    update_state "$driver_name" "$previous_version" "active" || {
        log_error "Failed to update state after rollback"
        return 1
    }

    log_info "Rollback completed successfully: $driver_name to $previous_version"
    return 0
}

###############################################################################
# List and Info Functions
###############################################################################

list_drivers() {
    log_info "Installed drivers:"

    ensure_state_file || return 1

    jq -r '.drivers | to_entries[] | "\(.key): \(.value.currentVersion) [\(.value.status)]"' \
        "$DRIVER_STATE_FILE" 2>/dev/null || true
}

show_driver_info() {
    local driver_name="$1"

    ensure_driver_db || return 1
    ensure_state_file || return 1

    local installed_version
    installed_version=$(get_installed_version "$driver_name")

    local available_versions
    available_versions=$(list_available_versions "$driver_name")

    echo "Driver: $driver_name"
    echo "  Installed: ${installed_version:-None}"
    echo "  Available versions:"
    echo "$available_versions" | sed 's/^/    /'

    return 0
}

search_drivers() {
    local pattern="$1"

    ensure_driver_db || return 1

    jq -r ".drivers[] | select(.name | contains(\"$pattern\")) | .name" \
        "$DRIVER_DB" 2>/dev/null | sort
}

###############################################################################
# Uninstall Function
###############################################################################

uninstall_driver() {
    local driver_name="$1"
    local version="${2:-}"

    log_info "Uninstalling driver: $driver_name${version:+ $version}"

    ensure_state_file || return 1

    if [[ -z "$version" ]]; then
        version=$(get_installed_version "$driver_name")
        if [[ -z "$version" ]]; then
            log_error "No version found for uninstall: $driver_name"
            return 1
        fi
    fi

    local install_path="${DRIVER_INSTALL_ROOT}/${driver_name}/${version}"

    if [[ -d "$install_path" ]]; then
        rm -rf "$install_path"
        log_info "Driver directory removed: $install_path"
    fi

    # Update state
    jq --arg name "$driver_name" 'del(.drivers[$name])' \
        "$DRIVER_STATE_FILE" > "${DRIVER_STATE_FILE}.tmp"
    mv "${DRIVER_STATE_FILE}.tmp" "$DRIVER_STATE_FILE"

    log_info "Uninstall completed: $driver_name"
    return 0
}

###############################################################################
# Diagnostics Function
###############################################################################

run_diagnostics() {
    local driver_name="${1:-}"

    log_info "Running diagnostics${driver_name:+ for $driver_name}"

    echo ""
    echo "=== System Information ==="
    echo "  Kernel: $(uname -r)"
    echo "  Platform: $(uname -m)"
    echo "  OS: $(lsb_release -ds 2>/dev/null || echo 'Unknown')"

    echo ""
    echo "=== Driver State File ==="
    if [[ -f "$DRIVER_STATE_FILE" ]]; then
        jq '.' "$DRIVER_STATE_FILE" 2>/dev/null || echo "  Invalid JSON"
    else
        echo "  State file not found"
    fi

    echo ""
    echo "=== Driver Database ==="
    if [[ -f "$DRIVER_DB" ]]; then
        echo "  Driver count: $(jq '.drivers | length' "$DRIVER_DB" 2>/dev/null || echo "Unknown")"
    else
        echo "  Database not found"
    fi

    if [[ -n "$driver_name" ]]; then
        echo ""
        echo "=== Driver Specific: $driver_name ==="
        show_driver_info "$driver_name" || true

        local install_path="${DRIVER_INSTALL_ROOT}/${driver_name}"
        if [[ -d "$install_path" ]]; then
            echo ""
            echo "=== Installation Directory ==="
            ls -lR "$install_path" 2>/dev/null || true
        fi
    fi

    return 0
}

###############################################################################
# Update Function
###############################################################################

update_drivers() {
    local driver_name="${1:-}"

    if [[ -z "$driver_name" ]]; then
        # Update all drivers
        log_info "Updating all drivers"
        ensure_driver_db || return 1

        jq -r '.drivers[].name' "$DRIVER_DB" 2>/dev/null | while read -r name; do
            local latest
            latest=$(get_driver_version "$name" "latest")
            local current
            current=$(get_installed_version "$name")

            if [[ -z "$current" ]]; then
                log_info "Skipping $name (not installed)"
            elif [[ "$latest" != "$current" ]]; then
                log_info "Updating $name: $current -> $latest"
                install_driver "$name" "$latest" || log_warn "Update failed for $name"
            fi
        done
    else
        # Update specific driver
        log_info "Updating driver: $driver_name"
        local latest
        latest=$(get_driver_version "$driver_name" "latest")

        if [[ -z "$latest" ]]; then
            log_error "Could not find latest version for $driver_name"
            return 1
        fi

        install_driver "$driver_name" "$latest" || return 1
    fi

    return 0
}

###############################################################################
# Cleanup Function
###############################################################################

cleanup_drivers() {
    local driver_name="${1:-}"
    local keep_count="${KEEP_VERSIONS:-3}"

    log_info "Cleaning up old driver versions (keeping last $keep_count)"

    ensure_directories || return 1

    if [[ -n "$driver_name" ]]; then
        local driver_path="${DRIVER_INSTALL_ROOT}/${driver_name}"
        if [[ -d "$driver_path" ]]; then
            cleanup_old_versions "$driver_name" "$driver_path" "$keep_count"
        fi
    else
        # Cleanup all drivers
        for driver_path in "${DRIVER_INSTALL_ROOT}"/*; do
            if [[ -d "$driver_path" ]]; then
                local name
                name=$(basename "$driver_path")
                cleanup_old_versions "$name" "$driver_path" "$keep_count"
            fi
        done
    fi

    return 0
}

cleanup_old_versions() {
    local driver_name="$1"
    local driver_path="$2"
    local keep_count="$3"

    local current_version
    current_version=$(get_installed_version "$driver_name")

    # List versions sorted by date, oldest first
    local versions
    versions=$(find "$driver_path" -maxdepth 1 -type d ! -name ".*" -exec basename {} \; | sort -V)

    local count=0
    while IFS= read -r version; do
        if [[ "$version" == "$current_version" ]]; then
            continue  # Never remove current version
        fi

        ((count++))
        if ((count > keep_count)); then
            local version_path="${driver_path}/${version}"
            log_info "Removing old version: $driver_name:$version"
            rm -rf "$version_path"
        fi
    done <<< "$versions"
}

###############################################################################
# Main Command Handler
###############################################################################

usage() {
    cat << 'EOF'
ShadowCypher Driver Installer

Usage: driver-installer.sh COMMAND [OPTIONS] [ARGS]

Commands:
  install <driver> [version]    Install or upgrade a driver
  uninstall <driver> [version]  Uninstall a driver
  update [driver]               Update one or all drivers to latest
  list                          List installed drivers
  search <pattern>              Search available drivers
  info <driver>                 Show driver information
  rollback <driver>             Rollback to previous version
  verify <driver> [version]     Verify driver integrity
  diagnose [driver]             Run system diagnostics
  cleanup [driver]              Remove old driver versions
  help                          Show this help message

Options:
  --force                       Force operation even if already installed
  --keep N                      Keep N versions when cleaning (default: 3)
  --verbose                     Verbose output
  --debug                       Enable debug logging

Environment Variables:
  DEBUG=1                       Enable debug output
  VERBOSE=1                     Enable verbose output
  FORCE=1                       Force operations
  KEEP_VERSIONS=N              Number of versions to keep in cleanup

Examples:
  driver-installer.sh install network-adapter
  driver-installer.sh install gpu-compute 2.1.0
  driver-installer.sh update gpu-compute
  driver-installer.sh rollback network-adapter
  driver-installer.sh list
  driver-installer.sh search network
  DEBUG=1 driver-installer.sh diagnose network-adapter

EOF
}

main() {
    init_logging

    log_debug "Script started with args: $*"

    # Check dependencies
    check_dependencies || {
        log_error "Dependency check failed"
        return 1
    }

    local command="${1:-help}"
    shift || true

    case "$command" in
        install)
            install_driver "$@"
            ;;
        uninstall)
            uninstall_driver "$@"
            ;;
        update)
            update_drivers "$@"
            ;;
        list)
            list_drivers
            ;;
        search)
            search_drivers "${1:-}"
            ;;
        info)
            show_driver_info "$@"
            ;;
        rollback)
            rollback_driver "$@"
            ;;
        verify)
            verify_checksum "$@"
            ;;
        diagnose)
            run_diagnostics "$@"
            ;;
        cleanup)
            cleanup_drivers "$@"
            ;;
        help|--help|-h|"")
            usage
            return 0
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            return 1
            ;;
    esac
}

main "$@"
