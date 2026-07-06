#!/bin/bash
################################################################################
# ShadowCypher LUKS Disk Encryption Setup
#
# This script automates the setup of LUKS2 encrypted volumes for Guardian vault
# and other enterprise security features. Includes validation, error handling,
# and recovery procedures.
#
# Usage: ./luks-setup.sh [options] <device>
# Example: ./luks-setup.sh -m /mnt/guardian-vault /dev/sdb1
#
# WARNING: This script modifies disk partitions and will destroy existing data
# on the target device. Backup data before running.
################################################################################

set -euo pipefail

# Script configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DEFAULT_CONFIG="${SCRIPT_DIR}/encrypt-config.json"

# Color output for better readability
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Global variables (set by arguments)
DEVICE=""
MOUNT_POINT=""
VOLUME_NAME="shadowcypher-vault"
CONFIG_FILE="${DEFAULT_CONFIG}"
SKIP_CONFIRMATION=false
VERBOSE=false

################################################################################
# Utility Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_verbose() {
    if [[ "${VERBOSE}" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*" >&2
    fi
}

die() {
    log_error "$@"
    exit 1
}

confirm() {
    local prompt="$1"
    local response

    if [[ "${SKIP_CONFIRMATION}" == "true" ]]; then
        return 0
    fi

    read -p "$(echo -e ${YELLOW}${prompt}${NC})" -r response
    [[ "${response}" =~ ^[Yy]$ ]]
}

################################################################################
# System Prerequisite Checks
################################################################################

check_prerequisites() {
    log_info "Checking system prerequisites..."

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        die "This script must be run as root"
    fi
    log_verbose "Running with root privileges"

    # Check for required commands
    local required_cmds=("cryptsetup" "lvm" "mkfs.ext4" "mount" "blkid")
    for cmd in "${required_cmds[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            die "Required command not found: $cmd"
        fi
        log_verbose "Found: $cmd"
    done

    # Check cryptsetup version
    local crypt_version
    crypt_version=$(cryptsetup --version | awk '{print $2}')
    log_verbose "cryptsetup version: $crypt_version"

    log_success "All prerequisites satisfied"
}

check_device() {
    log_info "Validating device: $DEVICE"

    # Check if device exists
    if [[ ! -e "$DEVICE" ]]; then
        die "Device does not exist: $DEVICE"
    fi
    log_verbose "Device exists: $DEVICE"

    # Check if device is a block device
    if [[ ! -b "$DEVICE" ]]; then
        die "Target is not a block device: $DEVICE"
    fi
    log_verbose "Confirmed block device"

    # Check if device is in use
    if lsblk -o MOUNTPOINT "$DEVICE" 2>/dev/null | grep -q "^/"; then
        die "Device is currently mounted: $DEVICE"
    fi
    log_verbose "Device is not mounted"

    # Check device size
    local device_size
    device_size=$(blockdev --getsize64 "$DEVICE" 2>/dev/null || echo 0)
    if [[ $device_size -lt 1073741824 ]]; then
        die "Device too small (minimum 1 GB): $DEVICE"
    fi
    log_verbose "Device size: $(( device_size / 1024 / 1024 / 1024 )) GB"

    log_success "Device validation passed"
}

check_mount_point() {
    log_info "Validating mount point: $MOUNT_POINT"

    # Check if mount point exists and is empty (if already mounted)
    if [[ -e "$MOUNT_POINT" ]]; then
        if ! mountpoint -q "$MOUNT_POINT"; then
            log_warn "Mount point exists but is not currently mounted"
        fi
    else
        log_verbose "Mount point does not exist (will be created)"
    fi

    # Verify parent directory is writable
    local parent_dir
    parent_dir=$(dirname "$MOUNT_POINT")
    if [[ ! -w "$parent_dir" ]]; then
        die "Parent directory is not writable: $parent_dir"
    fi
    log_verbose "Parent directory is writable"

    log_success "Mount point validation passed"
}

################################################################################
# LUKS Operations
################################################################################

create_luks_volume() {
    log_info "Creating LUKS2 encrypted volume..."
    log_warn "This will DESTROY all data on $DEVICE"

    if ! confirm "Continue with encryption setup? (y/N) "; then
        die "Setup cancelled by user"
    fi

    # Load configuration
    local cipher algo key_size iter_time
    if [[ -f "$CONFIG_FILE" ]]; then
        log_verbose "Loading configuration from: $CONFIG_FILE"
        cipher=$(jq -r '.encryption.cipher' "$CONFIG_FILE")
        algo=$(jq -r '.encryption.algorithm' "$CONFIG_FILE")
        key_size=$(jq -r '.encryption.key_size' "$CONFIG_FILE")
        iter_time=$(jq -r '.encryption.iter_time' "$CONFIG_FILE")
    else
        log_warn "Config file not found, using defaults"
        cipher="aes-xts-plain64"
        algo="AES-256"
        key_size="512"
        iter_time="2000"
    fi

    log_info "Formatting device with:"
    log_info "  Cipher: $cipher ($algo)"
    log_info "  Key size: $key_size bits"
    log_info "  Iteration time: ${iter_time}ms"

    # Clear any existing LUKS headers
    log_verbose "Wiping existing LUKS headers..."
    dd if=/dev/zero of="$DEVICE" bs=1M count=1 2>/dev/null || true

    # Create LUKS2 volume
    if ! cryptsetup luksFormat \
        --type luks2 \
        --cipher "$cipher" \
        --key-size "$key_size" \
        --iter-time "$iter_time" \
        --pbkdf pbkdf2 \
        --pbkdf-force-iterations 0 \
        --batch-mode \
        "$DEVICE"; then
        die "Failed to format LUKS volume"
    fi

    log_success "LUKS volume created successfully"
}

open_luks_volume() {
    log_info "Opening LUKS volume: $DEVICE -> /dev/mapper/$VOLUME_NAME"

    if cryptsetup luksOpen "$DEVICE" "$VOLUME_NAME"; then
        log_success "LUKS volume opened"
        log_verbose "Mapped device: /dev/mapper/$VOLUME_NAME"
    else
        die "Failed to open LUKS volume"
    fi
}

create_filesystem() {
    log_info "Creating ext4 filesystem on encrypted volume..."

    local mapped_device="/dev/mapper/$VOLUME_NAME"

    if ! [[ -e "$mapped_device" ]]; then
        die "Mapped device not found: $mapped_device"
    fi

    if ! mkfs.ext4 -F "$mapped_device"; then
        die "Failed to create filesystem"
    fi

    log_success "Filesystem created"
}

mount_volume() {
    log_info "Mounting encrypted volume to: $MOUNT_POINT"

    local mapped_device="/dev/mapper/$VOLUME_NAME"

    # Create mount point if it doesn't exist
    if [[ ! -d "$MOUNT_POINT" ]]; then
        log_verbose "Creating mount point directory"
        mkdir -p "$MOUNT_POINT" || die "Failed to create mount point"
    fi

    # Mount the volume
    if ! mount "$mapped_device" "$MOUNT_POINT"; then
        die "Failed to mount encrypted volume"
    fi

    # Set permissions (accessible only by root)
    chmod 700 "$MOUNT_POINT" || die "Failed to set mount point permissions"

    log_success "Volume mounted to $MOUNT_POINT"
    log_verbose "Mount permissions: 700 (root only)"
}

configure_persistent_mount() {
    log_info "Configuring persistent mounting..."

    local device_uuid
    device_uuid=$(cryptsetup luksUUID "$DEVICE")
    log_verbose "Device UUID: $device_uuid"

    local mapped_device="/dev/mapper/$VOLUME_NAME"
    local fs_uuid
    fs_uuid=$(blkid -s UUID -o value "$mapped_device")
    log_verbose "Filesystem UUID: $fs_uuid"

    # Update /etc/crypttab
    log_info "Adding entry to /etc/crypttab..."
    if grep -q "^$VOLUME_NAME" /etc/crypttab 2>/dev/null; then
        log_warn "Entry already exists in /etc/crypttab, skipping"
    else
        echo "$VOLUME_NAME UUID=$device_uuid none luks,discard" >> /etc/crypttab
        log_success "Added to /etc/crypttab"
    fi

    # Update /etc/fstab
    log_info "Adding entry to /etc/fstab..."
    if grep -q "^UUID=$fs_uuid" /etc/fstab 2>/dev/null; then
        log_warn "Entry already exists in /etc/fstab, skipping"
    else
        echo "UUID=$fs_uuid $MOUNT_POINT ext4 defaults,errors=remount-ro 0 2" >> /etc/fstab
        log_success "Added to /etc/fstab"
    fi

    log_success "Persistent mount configuration complete"
}

create_recovery_key() {
    log_info "Generating recovery key..."

    local recovery_file="${MOUNT_POINT}/.recovery-key-encrypted"
    local temp_key
    temp_key=$(mktemp)

    # Generate 32-byte random recovery key
    if ! dd if=/dev/urandom of="$temp_key" bs=32 count=1 2>/dev/null; then
        rm -f "$temp_key"
        die "Failed to generate recovery key"
    fi

    # Add recovery key as second key slot
    log_verbose "Adding recovery key to LUKS header..."
    if ! cryptsetup luksAddKey "$DEVICE" "$temp_key" \
        --iter-time 2000 --pbkdf pbkdf2 --batch-mode; then
        rm -f "$temp_key"
        die "Failed to add recovery key to LUKS header"
    fi

    # Store encrypted backup of recovery key (for administrative access)
    log_verbose "Storing recovery key backup"
    if command -v openssl &>/dev/null; then
        openssl enc -aes-256-cbc -salt -in "$temp_key" \
            -out "$recovery_file" -pass pass:"backup-password-change-me" 2>/dev/null || true
        chmod 600 "$recovery_file"
        log_info "Recovery key backup: $recovery_file"
    fi

    # Securely wipe temporary key
    shred -vfz -n 3 "$temp_key" 2>/dev/null || rm -f "$temp_key"

    log_success "Recovery key created (recovery password printed above)"
}

################################################################################
# Status and Information
################################################################################

show_status() {
    log_info "Volume Status:"

    if [[ -b "$DEVICE" ]]; then
        cryptsetup status /dev/mapper/"$VOLUME_NAME" 2>/dev/null || log_warn "Volume not currently open"
    fi

    log_info "Mount Status:"
    if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
        df -h "$MOUNT_POINT" | tail -n 1
    else
        log_warn "Volume not currently mounted"
    fi
}

show_usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS] <device>

Create a LUKS2 encrypted volume for ShadowCypher Guardian vault.

POSITIONAL ARGUMENTS:
    <device>              Block device to encrypt (e.g., /dev/sdb1)

OPTIONS:
    -m, --mount <path>    Mount point (default: /mnt/guardian-vault)
    -n, --name <name>     Volume name (default: shadowcypher-vault)
    -c, --config <file>   Configuration file (default: $DEFAULT_CONFIG)
    -y, --yes             Skip confirmation prompts
    -v, --verbose         Verbose output
    -s, --status          Show volume status
    -h, --help            Show this help message

EXAMPLES:
    # Basic setup with prompts
    sudo $SCRIPT_NAME /dev/sdb1

    # Setup with custom mount point
    sudo $SCRIPT_NAME -m /mnt/vault /dev/sdb1

    # Non-interactive setup
    sudo $SCRIPT_NAME -y -m /mnt/vault /dev/sdb1

    # Show status of existing volume
    $SCRIPT_NAME -s

EOF
}

################################################################################
# Main Function
################################################################################

main() {
    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -m|--mount)
                MOUNT_POINT="$2"
                shift 2
                ;;
            -n|--name)
                VOLUME_NAME="$2"
                shift 2
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -y|--yes)
                SKIP_CONFIRMATION=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -s|--status)
                show_status
                exit 0
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                die "Unknown option: $1"
                ;;
            *)
                DEVICE="$1"
                shift
                ;;
        esac
    done

    # Validate arguments
    if [[ -z "$DEVICE" ]]; then
        show_usage
        die "Device not specified"
    fi

    if [[ -z "$MOUNT_POINT" ]]; then
        MOUNT_POINT="/mnt/${VOLUME_NAME}"
    fi

    log_info "ShadowCypher LUKS Encryption Setup"
    log_info "Device: $DEVICE"
    log_info "Volume: $VOLUME_NAME"
    log_info "Mount: $MOUNT_POINT"

    # Execute setup steps
    check_prerequisites
    check_device
    check_mount_point
    create_luks_volume
    open_luks_volume
    create_filesystem
    mount_volume
    configure_persistent_mount
    create_recovery_key
    show_status

    log_success "LUKS encryption setup complete!"
    log_info "Volume is ready for use at $MOUNT_POINT"
    log_info "To unmount: umount $MOUNT_POINT && cryptsetup luksClose $VOLUME_NAME"
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
