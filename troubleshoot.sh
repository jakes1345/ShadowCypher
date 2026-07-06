#!/bin/bash

#############################################################################
# ShadowCypher Troubleshooting & Diagnostics Script
#
# Usage:
#   ./troubleshoot.sh              # Interactive diagnostics
#   ./troubleshoot.sh --quick      # Quick diagnosis (5 minutes)
#   ./troubleshoot.sh --full       # Full diagnosis (15 minutes)
#   ./troubleshoot.sh --export     # Export diagnostic report
#
# This script:
# 1. Checks system requirements
# 2. Verifies dependencies
# 3. Tests key services (Ollama, relay, chat)
# 4. Diagnoses common issues
# 5. Suggests fixes
# 6. Generates a diagnostic report
#############################################################################

set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diagnostic counters
ERRORS=0
WARNINGS=0
INFO_COUNT=0

# Report file
REPORT_FILE="/tmp/shadowcypher_diagnostic_$(date +%Y%m%d_%H%M%S).txt"

#############################################################################
# Utility Functions
#############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[INFO] $1" >> "$REPORT_FILE"
    ((INFO_COUNT++))
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    echo "[PASS] $1" >> "$REPORT_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[WARN] $1" >> "$REPORT_FILE"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo "[FAIL] $1" >> "$REPORT_FILE"
    ((ERRORS++))
}

header() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
    echo "=== $1 ===" >> "$REPORT_FILE"
}

separator() {
    echo -e "${BLUE}---${NC}"
    echo "---" >> "$REPORT_FILE"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

#############################################################################
# System Information
#############################################################################

check_system_info() {
    header "System Information"

    log_info "Collecting system information..."

    # OS
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        log_info "OS: $PRETTY_NAME"
        log_info "Kernel: $(uname -r)"
    else
        log_warning "Could not determine OS (not Linux?)"
    fi

    # Architecture
    log_info "Architecture: $(uname -m)"

    # CPU
    local cpu_count=$(nproc)
    log_info "CPU cores: $cpu_count"

    # Memory
    local mem_total=$(free -h | grep Mem | awk '{print $2}')
    local mem_available=$(free -h | grep Mem | awk '{print $7}')
    log_info "Memory: $mem_total (available: $mem_available)"

    # Disk
    local root_usage=$(df -h / | tail -1 | awk '{print $5}')
    local root_free=$(df -h / | tail -1 | awk '{print $4}')
    log_info "Root filesystem: $root_usage used, $root_free free"

    # Home directory
    if [[ -d "$HOME" ]]; then
        local home_usage=$(du -sh "$HOME" 2>/dev/null | awk '{print $1}')
        log_info "Home directory size: $home_usage"
    fi
}

#############################################################################
# Dependency Checks
#############################################################################

check_python() {
    header "Python Environment"

    if ! command_exists python3; then
        log_error "python3 not found in PATH"
        return 1
    fi

    local py_version=$(python3 --version 2>&1 | awk '{print $2}')
    log_info "Python version: $py_version"

    # Check if >= 3.12
    local major=$(echo "$py_version" | cut -d. -f1)
    local minor=$(echo "$py_version" | cut -d. -f2)

    if (( major > 3 )) || (( major == 3 && minor >= 12 )); then
        log_success "Python 3.12+ requirement met"
    else
        log_error "Python 3.12+ required (you have $py_version)"
        return 1
    fi

    # Check Python path
    log_info "Python executable: $(which python3)"

    # Check venv
    if [[ -d "venv" ]]; then
        log_success "Virtual environment exists"
        if [[ -f "venv/bin/activate" ]]; then
            log_info "venv is properly configured"
        fi
    else
        log_warning "No virtual environment found (consider: python3 -m venv venv)"
    fi

    return 0
}

check_python_modules() {
    header "Python Module Dependencies"

    # Critical modules
    local critical_modules=("gi" "aiohttp" "pydantic" "cryptography" "treequest" "psutil")

    for module in "${critical_modules[@]}"; do
        if python3 -c "import $module" 2>/dev/null; then
            log_success "Module '$module' found"
        else
            log_error "Module '$module' NOT found"
            log_info "Fix: pip install -r requirements.txt --upgrade"
        fi
    done

    # Check specific versions
    local pydantic_version=$(python3 -c "import pydantic; print(pydantic.__version__)" 2>/dev/null)
    if [[ -n "$pydantic_version" ]]; then
        log_info "pydantic version: $pydantic_version"
    fi

    return 0
}

check_gtk() {
    header "GTK Dependencies"

    # Check GTK Python bindings
    if python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" 2>/dev/null; then
        log_success "GTK 3.0 Python bindings available"
    else
        log_error "GTK 3.0 Python bindings NOT available"
        if grep -qi ubuntu /etc/os-release 2>/dev/null; then
            log_info "Fix: sudo apt install python3-gi gir1.2-gtk-3.0 libgtk-3-0"
        elif grep -qi fedora /etc/os-release 2>/dev/null; then
            log_info "Fix: sudo dnf install python3-gi gtk3 cairo"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            log_info "Fix: brew install gtk+3 && pip install pycairo pygobject"
        fi
        return 1
    fi

    # Check Cairo
    if python3 -c "import cairo" 2>/dev/null; then
        log_success "Cairo graphics library available"
    else
        log_warning "Cairo not found (UI rendering may not work)"
    fi

    return 0
}

check_go() {
    header "Go Environment"

    if ! command_exists go; then
        log_error "Go not found in PATH"
        log_info "Fix: Install Go 1.24+ from https://go.dev/dl"
        return 1
    fi

    local go_version=$(go version | awk '{print $3}')
    log_info "Go version: $go_version"

    # Try to compile the relay
    if [[ -d "shadowcypher/native/relay" ]]; then
        log_info "Attempting to compile Go relay..."
        if (cd shadowcypher/native/relay && go build -o relay main.go 2>/dev/null); then
            log_success "Go relay compiles successfully"
        else
            log_error "Failed to compile Go relay"
            log_info "Check: shadowcypher/native/relay/main.go for syntax errors"
        fi
    fi

    return 0
}

check_external_tools() {
    header "External Security Tools"

    local tools=("nmap" "nuclei" "nikto" "sqlmap" "hydra" "john" "hashcat")
    local found=0
    local missing=0

    for tool in "${tools[@]}"; do
        if command_exists "$tool"; then
            log_success "$tool is installed"
            ((found++))
        else
            log_warning "$tool is NOT installed (optional)"
            ((missing++))
        fi
    done

    log_info "Found $found/$((found + missing)) optional security tools"

    if (( missing > 0 )); then
        log_warning "Some optional tools are missing. ShadowCypher will work without them."
    fi

    return 0
}

#############################################################################
# Service Checks
#############################################################################

check_ollama() {
    header "Ollama AI Service"

    if ! command_exists ollama; then
        log_error "Ollama not installed"
        log_info "Install from: https://ollama.ai"
        return 1
    fi

    log_info "Ollama found: $(which ollama)"

    # Check if Ollama service is running
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        log_success "Ollama service is running on localhost:11434"

        # List models
        local models=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*' | cut -d'"' -f4)
        if [[ -n "$models" ]]; then
            log_success "Available models:"
            echo "$models" | while read -r model; do
                log_info "  - $model"
            done
        else
            log_warning "No models installed. Run: ollama pull llama2"
        fi
    else
        log_error "Ollama service is NOT running"
        log_info "Start it: ollama serve &"
        return 1
    fi

    # Check OLLAMA_BASE_URL env var
    if [[ -n "$OLLAMA_BASE_URL" ]]; then
        log_info "Custom Ollama endpoint: $OLLAMA_BASE_URL"
    fi

    return 0
}

check_relay() {
    header "Go Relay Service"

    local relay_path="shadowcypher/native/relay/relay"

    # Check if relay binary exists
    if [[ -f "$relay_path" ]]; then
        log_success "Relay binary exists: $relay_path"
    else
        log_warning "Relay binary not yet compiled"
        log_info "Will be auto-compiled on first launch"
    fi

    # Check if relay is running
    if lsof -i :9999 >/dev/null 2>&1; then
        log_success "Relay is running on port 9999"
    else
        log_warning "Relay is not currently running (normal if app not launched)"
    fi

    # Check port availability
    if lsof -i :9999 >/dev/null 2>&1; then
        local relay_pid=$(lsof -i :9999 | tail -1 | awk '{print $2}')
        log_info "Process on port 9999: PID $relay_pid"
    fi

    return 0
}

check_shadowcypher_app() {
    header "ShadowCypher Application"

    # Check if app is running
    if pgrep -f "shadowcypher.app" >/dev/null; then
        log_success "ShadowCypher application is running"
        local pids=$(pgrep -f "shadowcypher.app")
        log_info "Process IDs: $pids"
    else
        log_warning "ShadowCypher application is not running (normal if not launched)"
    fi

    # Check configuration
    if [[ -f "config.json" ]]; then
        log_success "config.json exists"
        if python3 -m json.tool config.json >/dev/null 2>&1; then
            log_success "config.json is valid JSON"
        else
            log_error "config.json has invalid JSON syntax"
        fi
    else
        log_warning "config.json not found (will be created on first launch)"
    fi

    return 0
}

check_ports() {
    header "Network Ports"

    local shadow_port="${SHADOW_PORT:-8888}"
    log_info "Checking critical ports..."

    # Check main app port
    if lsof -i ":$shadow_port" >/dev/null 2>&1; then
        log_warning "Port $shadow_port is in use"
        local proc=$(lsof -i ":$shadow_port" | tail -1 | awk '{print $1}')
        log_info "Process: $proc"
    else
        log_success "Port $shadow_port is available"
    fi

    # Check relay port
    if lsof -i :9999 >/dev/null 2>&1; then
        log_success "Relay port 9999 is available/in use by relay"
    else
        log_success "Relay port 9999 is available"
    fi

    # Check Ollama port
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        log_success "Ollama port 11434 is accessible"
    else
        log_warning "Ollama port 11434 is not accessible"
    fi

    return 0
}

#############################################################################
# File System Checks
#############################################################################

check_filesystem() {
    header "File System"

    # ShadowCypher directory
    if [[ -d "shadowcypher" ]]; then
        log_success "ShadowCypher source directory exists"
    else
        log_error "ShadowCypher source directory NOT found"
        log_info "Run this script from the ShadowCypher root directory"
        return 1
    fi

    # Home directory
    if [[ -d "$HOME/.shadowcypher" ]]; then
        log_success "~/.shadowcypher config directory exists"

        local config_size=$(du -sh "$HOME/.shadowcypher" 2>/dev/null | awk '{print $1}')
        log_info "Size: $config_size"
    else
        log_info "~/.shadowcypher will be created on first launch"
    fi

    # Logs
    if [[ -d "$HOME/.shadowcypher/logs" ]]; then
        log_success "Log directory exists"
        local log_count=$(find "$HOME/.shadowcypher/logs" -type f 2>/dev/null | wc -l)
        log_info "Log files: $log_count"
    fi

    # Check permissions
    if [[ -w "$HOME" ]]; then
        log_success "Write permission to home directory"
    else
        log_error "No write permission to home directory"
        return 1
    fi

    # Disk space check
    local free_space=$(df -BG "$HOME" | tail -1 | awk '{print $4}' | sed 's/G//')
    if (( free_space > 5 )); then
        log_success "Sufficient disk space: ${free_space}GB free"
    else
        log_warning "Low disk space: ${free_space}GB free (recommended: 5GB+)"
    fi

    return 0
}

#############################################################################
# Advanced Diagnostics
#############################################################################

check_logs() {
    header "Recent Log Analysis"

    local log_file="$HOME/.shadowcypher/logs/shadowcypher.jsonl"

    if [[ -f "$log_file" ]]; then
        log_success "Log file exists"

        # Count errors in last 100 lines
        local recent_errors=$(tail -100 "$log_file" 2>/dev/null | grep -c '"level":"ERROR"' || echo 0)

        if (( recent_errors > 0 )); then
            log_warning "Recent errors detected: $recent_errors in last 100 log lines"
            log_info "Last error:"
            tail -100 "$log_file" | grep '"level":"ERROR"' | tail -1 | jq '.message' 2>/dev/null || echo "  (could not parse)"
        else
            log_success "No recent errors in logs"
        fi
    else
        log_info "No logs yet (app hasn't been launched)"
    fi
}

check_network() {
    header "Network Connectivity"

    # DNS resolution
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_success "Internet connectivity OK (can reach 8.8.8.8)"
    else
        log_warning "Cannot reach external IP (8.8.8.8)"
    fi

    # DNS resolution
    if ping -c 1 google.com >/dev/null 2>&1; then
        log_success "DNS resolution OK"
    else
        log_warning "DNS resolution failed"
    fi

    # Localhost
    if ping -c 1 127.0.0.1 >/dev/null 2>&1; then
        log_success "Localhost loopback OK"
    else
        log_error "Localhost loopback FAILED"
    fi

    return 0
}

#############################################################################
# Test Runs
#############################################################################

test_python_import() {
    header "Python Import Test"

    log_info "Testing core ShadowCypher imports..."

    # Test basic imports
    if python3 -c "import sys; sys.path.insert(0, '.'); from shadowcypher.core.assessor import SecurityAssessor" 2>/dev/null; then
        log_success "Core module imports work"
    else
        log_error "Core module imports failed"
        log_info "Try: pip install -r requirements.txt"
        return 1
    fi

    return 0
}

#############################################################################
# Summary Report
#############################################################################

generate_summary() {
    header "Diagnostic Summary"

    echo ""
    echo -e "${BLUE}=== RESULTS ===${NC}"
    echo "=== RESULTS ===" >> "$REPORT_FILE"

    echo -e "${GREEN}✓ Passed: $INFO_COUNT${NC}"
    echo "✓ Passed: $INFO_COUNT" >> "$REPORT_FILE"

    if (( WARNINGS > 0 )); then
        echo -e "${YELLOW}⚠ Warnings: $WARNINGS${NC}"
        echo "⚠ Warnings: $WARNINGS" >> "$REPORT_FILE"
    fi

    if (( ERRORS > 0 )); then
        echo -e "${RED}✗ Errors: $ERRORS${NC}"
        echo "✗ Errors: $ERRORS" >> "$REPORT_FILE"
    fi

    echo ""
    echo "Full report saved to: $REPORT_FILE"

    if (( ERRORS == 0 )); then
        echo -e "${GREEN}System looks good! Ready to launch ShadowCypher.${NC}"
        echo "System looks good! Ready to launch ShadowCypher." >> "$REPORT_FILE"
        return 0
    else
        echo -e "${RED}There are issues that need fixing before launching.${NC}"
        echo "There are issues that need fixing before launching." >> "$REPORT_FILE"
        return 1
    fi
}

#############################################################################
# Main Execution
#############################################################################

main() {
    # Initialize report
    {
        echo "ShadowCypher Diagnostic Report"
        echo "Generated: $(date)"
        echo "Hostname: $(hostname)"
        echo "User: $(whoami)"
        echo "Working Directory: $(pwd)"
        echo ""
    } > "$REPORT_FILE"

    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║   ShadowCypher Diagnostic & Troubleshooting Tool         ║"
    echo "║   Version 1.0 (January 2025)                            ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # Run diagnostics based on mode
    case "${1:-normal}" in
        --quick)
            log_info "Running quick diagnostics (5 minutes)..."
            check_system_info
            check_python
            check_gtk
            check_ollama
            check_shadowcypher_app
            ;;
        --full)
            log_info "Running full diagnostics (15 minutes)..."
            check_system_info
            check_python
            check_python_modules
            check_gtk
            check_go
            check_external_tools
            check_ollama
            check_relay
            check_shadowcypher_app
            check_ports
            check_filesystem
            check_logs
            check_network
            test_python_import
            ;;
        --export)
            log_info "Exporting diagnostic report..."
            check_system_info
            check_python
            check_python_modules
            check_gtk
            check_go
            check_external_tools
            check_ollama
            check_relay
            check_shadowcypher_app
            check_ports
            check_filesystem
            check_logs
            check_network
            ;;
        *)
            log_info "Running standard diagnostics (10 minutes)..."
            check_system_info
            check_python
            check_python_modules
            check_gtk
            check_go
            check_external_tools
            check_ollama
            check_relay
            check_shadowcypher_app
            check_ports
            check_filesystem
            check_logs
            ;;
    esac

    # Generate summary
    generate_summary

    # Save report path to file for reference
    echo "$REPORT_FILE" > /tmp/shadowcypher_latest_report.txt

    # Optional: cat the report
    separator
    echo ""
    log_info "Full diagnostic report:"
    cat "$REPORT_FILE"
}

# Ensure bash syntax is correct
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
