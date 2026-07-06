#!/bin/bash

# ShadowOS Driver Package Management Installer
# Handles NVIDIA, AMD, Intel, wireless, and storage drivers

set -euo pipefail

LOG_FILE="/var/log/shadowos-drivers.log"
DRIVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/drivers" && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[${timestamp}]${NC} ${level}: ${msg}" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}SUCCESS${NC}" "$@"
}

log_error() {
    log "${RED}ERROR${NC}" "$@"
}

log_info() {
    log "${BLUE}INFO${NC}" "$@"
}

log_warning() {
    log "${YELLOW}WARNING${NC}" "$@"
}

error_exit() {
    log_error "$@"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "This script must be run as root (use sudo)"
    fi
}

detect_hardware() {
    log_info "Detecting hardware..."

    # Check for NVIDIA
    if lspci | grep -q NVIDIA; then
        log_info "NVIDIA GPU detected"
        NVIDIA_DETECTED=1
    fi

    # Check for AMD
    if lspci | grep -q "AMD\|Advanced Micro Devices"; then
        log_info "AMD GPU/APU detected"
        AMD_DETECTED=1
    fi

    # Check for Intel
    if lspci | grep -q Intel; then
        log_info "Intel GPU/CPU detected"
        INTEL_DETECTED=1
    fi

    # Check for wireless
    if ip link show | grep -q "wlan\|wlp"; then
        log_info "Wireless device detected"
        WIRELESS_DETECTED=1
    fi

    # Check for NVMe
    if lsblk | grep -q nvme; then
        log_info "NVMe storage detected"
        NVME_DETECTED=1
    fi
}

install_nvidia() {
    log_info "Installing NVIDIA drivers..."

    # Check if NVIDIA GPU is present
    if ! lspci | grep -q NVIDIA; then
        log_warning "No NVIDIA GPU detected, skipping NVIDIA installation"
        return 0
    fi

    # Update package database
    pacman -Sy --noconfirm >> "$LOG_FILE" 2>&1 || log_warning "Failed to sync package database"

    # Install NVIDIA proprietary driver
    log_info "Installing nvidia package..."
    if pacman -S --noconfirm nvidia nvidia-utils lib32-nvidia-utils >> "$LOG_FILE" 2>&1; then
        log_success "NVIDIA drivers installed successfully"
    else
        log_warning "NVIDIA proprietary driver installation failed, attempting nouveau fallback..."
        if pacman -S --noconfirm xf86-video-nouveau >> "$LOG_FILE" 2>&1; then
            log_success "Fallback to Nouveau open-source driver installed"
        else
            log_error "Both NVIDIA and Nouveau installation failed"
            return 1
        fi
    fi

    # Install development headers if kernel-devel is available
    if pacman -Ss linux-headers | grep -q linux-headers; then
        log_info "Installing linux-headers for NVIDIA module compilation..."
        pacman -S --noconfirm linux-headers >> "$LOG_FILE" 2>&1 || log_warning "linux-headers installation failed"
    fi

    # Verify installation
    if command -v nvidia-smi &> /dev/null; then
        log_success "NVIDIA drivers verified: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader)"
    else
        log_warning "nvidia-smi not found; driver may require reboot"
    fi
}

install_amd() {
    log_info "Installing AMD drivers..."

    # Check if AMD GPU/APU is present
    if ! lspci | grep -q "AMD\|Advanced Micro Devices"; then
        log_warning "No AMD GPU/APU detected, skipping AMD installation"
        return 0
    fi

    # Update package database
    pacman -Sy --noconfirm >> "$LOG_FILE" 2>&1 || log_warning "Failed to sync package database"

    # Install AMDGPU stack
    log_info "Installing AMDGPU drivers..."
    if pacman -S --noconfirm xf86-video-amdgpu mesa lib32-mesa >> "$LOG_FILE" 2>&1; then
        log_success "AMD AMDGPU drivers installed successfully"
    else
        log_error "AMDGPU installation failed, attempting ATI fallback..."
        if pacman -S --noconfirm xf86-video-ati >> "$LOG_FILE" 2>&1; then
            log_success "Fallback to ATI driver installed"
        else
            log_error "Both AMDGPU and ATI installation failed"
            return 1
        fi
    fi

    # Install Vulkan support
    log_info "Installing Vulkan support..."
    pacman -S --noconfirm vulkan-radeon lib32-vulkan-radeon >> "$LOG_FILE" 2>&1 || log_warning "Vulkan installation failed"

    # Verify installation
    if glxinfo | grep -q "AMD\|AMDGPU"; then
        log_success "AMD GPU detected in glxinfo"
    else
        log_warning "AMD GPU not verified in glxinfo; may require reboot"
    fi
}

install_intel() {
    log_info "Installing Intel drivers..."

    # Check if Intel GPU is present
    if ! lspci | grep -q Intel | grep -q VGA; then
        log_warning "No Intel GPU detected, skipping Intel installation"
        return 0
    fi

    # Update package database
    pacman -Sy --noconfirm >> "$LOG_FILE" 2>&1 || log_warning "Failed to sync package database"

    # Install Intel GPU drivers (i915)
    log_info "Installing Intel GPU drivers..."
    if pacman -S --noconfirm xf86-video-intel mesa lib32-mesa >> "$LOG_FILE" 2>&1; then
        log_success "Intel GPU drivers installed successfully"
    else
        log_error "Intel GPU driver installation failed"
        return 1
    fi

    # Install Vulkan support for Intel Arc
    log_info "Installing Intel Vulkan support..."
    pacman -S --noconfirm vulkan-intel lib32-vulkan-intel >> "$LOG_FILE" 2>&1 || log_warning "Intel Vulkan installation failed"

    # Install Intel microcode
    log_info "Installing Intel microcode..."
    pacman -S --noconfirm intel-ucode >> "$LOG_FILE" 2>&1 || log_warning "Intel microcode installation failed"

    # Verify installation
    if lspci | grep -i "intel.*graphics" > /dev/null; then
        log_success "Intel GPU drivers verified"
    else
        log_warning "Intel GPU not verified; may require reboot"
    fi
}

install_wireless() {
    log_info "Installing wireless drivers and firmware..."

    # Update package database
    pacman -Sy --noconfirm >> "$LOG_FILE" 2>&1 || log_warning "Failed to sync package database"

    # Install wireless base packages
    log_info "Installing wireless base packages..."
    pacman -S --noconfirm wireless_tools wpa_supplicant dialog >> "$LOG_FILE" 2>&1 || log_warning "Wireless base packages installation failed"

    # Install Intel wireless firmware
    log_info "Installing Intel wireless firmware..."
    pacman -S --noconfirm intel-wireless-fw >> "$LOG_FILE" 2>&1 || log_warning "Intel wireless firmware installation failed"

    # Install Realtek wireless drivers
    log_info "Installing Realtek wireless drivers..."
    pacman -S --noconfirm rtl88xxau-airmon-git >> "$LOG_FILE" 2>&1 || log_warning "Realtek wireless driver installation failed (may require AUR)"

    # Install Qualcomm Atheros drivers
    log_info "Installing Atheros wireless firmware..."
    pacman -S --noconfirm ath10k-firmware ath11k-firmware >> "$LOG_FILE" 2>&1 || log_warning "Atheros firmware installation failed"

    # Install Broadcom wireless drivers (if available)
    log_info "Installing Broadcom wireless drivers..."
    pacman -S --noconfirm broadcom-wl >> "$LOG_FILE" 2>&1 || log_warning "Broadcom wireless driver installation failed (may be in AUR)"

    # Verify wireless devices
    log_info "Verifying wireless devices..."
    if ip link show | grep -q "wlan\|wlp"; then
        log_success "Wireless device(s) detected: $(ip link show | grep -E 'wlan|wlp' | awk '{print $2}')"
    else
        log_warning "No wireless devices detected"
    fi
}

install_storage() {
    log_info "Installing storage drivers and firmware..."

    # Update package database
    pacman -Sy --noconfirm >> "$LOG_FILE" 2>&1 || log_warning "Failed to sync package database"

    # Install NVMe utilities
    log_info "Installing NVMe utilities..."
    pacman -S --noconfirm nvme-cli >> "$LOG_FILE" 2>&1 || log_warning "NVMe utilities installation failed"

    # Install SATA utilities
    log_info "Installing SATA utilities..."
    pacman -S --noconfirm hdparm sdparm >> "$LOG_FILE" 2>&1 || log_warning "SATA utilities installation failed"

    # Install RAID utilities
    log_info "Installing RAID utilities..."
    pacman -S --noconfirm mdadm >> "$LOG_FILE" 2>&1 || log_warning "RAID utilities installation failed"

    # Install ATA firmware
    log_info "Installing ATA firmware..."
    pacman -S --noconfirm linux-firmware >> "$LOG_FILE" 2>&1 || log_warning "Linux firmware installation failed"

    # Verify storage devices
    log_info "Verifying storage devices..."
    local storage_devices=$(lsblk -nd -o NAME,TYPE | awk '{print $1}')
    if [[ -n "$storage_devices" ]]; then
        log_success "Storage device(s) detected: $storage_devices"
    else
        log_warning "No storage devices detected"
    fi
}

show_usage() {
    cat << EOF
Usage: $0 <driver-type>

driver-type options:
  nvidia    - Install NVIDIA GPU drivers
  amd       - Install AMD GPU/APU drivers
  intel     - Install Intel GPU drivers
  wireless  - Install wireless drivers and firmware
  storage   - Install storage drivers and firmware
  all       - Install all driver categories
  help      - Show this help message

Examples:
  sudo $0 nvidia
  sudo $0 amd
  sudo $0 all

Installation log: $LOG_FILE
Driver directory: $DRIVER_DIR
EOF
}

main() {
    check_root

    # Initialize log file
    {
        echo "=== ShadowOS Driver Installation ==="
        echo "Started: $(date)"
        echo "User: $(whoami)"
    } >> "$LOG_FILE"

    log_info "ShadowOS Driver Installation Script"

    if [[ $# -eq 0 ]]; then
        log_error "No driver type specified"
        show_usage
        exit 1
    fi

    local driver_type="$1"

    case "$driver_type" in
        nvidia)
            install_nvidia
            ;;
        amd)
            install_amd
            ;;
        intel)
            install_intel
            ;;
        wireless)
            install_wireless
            ;;
        storage)
            install_storage
            ;;
        all)
            log_info "Installing all drivers..."
            install_nvidia
            install_amd
            install_intel
            install_wireless
            install_storage
            log_success "All driver installations completed"
            ;;
        help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown driver type: $driver_type"
            show_usage
            exit 1
            ;;
    esac

    {
        echo "Completed: $(date)"
        echo "Exit code: $?"
    } >> "$LOG_FILE"

    log_success "Driver installation process completed"
}

main "$@"
