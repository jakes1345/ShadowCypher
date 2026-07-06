#!/bin/bash

# hardware-report.sh
# Detect hardware specifications and check compatibility with ShadowCypher
# Supports both human-readable and JSON output formats

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_FILE="${SCRIPT_DIR}/hardware-db.json"
OUTPUT_FORMAT="human"  # human | json
VERBOSE=false
CHECK_DATABASE=false

# Colors for output (disabled for JSON)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2

    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        return
    fi

    case "$status" in
        ok)
            echo -e "${GREEN}✓${NC} $message"
            ;;
        warn)
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        error)
            echo -e "${RED}✗${NC} $message"
            ;;
        info)
            echo "ℹ $message"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Detect CPU information
detect_cpu() {
    local cpu_model=""
    local cpu_cores=0
    local cpu_threads=0
    local cpu_arch=""

    # Detect architecture
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        cpu_model=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Unknown")
        cpu_cores=$(sysctl -n hw.physical_cpus 2>/dev/null || echo "0")
        cpu_threads=$(sysctl -n hw.logical_cpus 2>/dev/null || echo "0")
        cpu_arch=$(uname -m)
    else
        # Linux
        if [[ -f /proc/cpuinfo ]]; then
            cpu_model=$(grep "^model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
            cpu_cores=$(grep -c "^processor" /proc/cpuinfo)
            cpu_threads=$(grep "^siblings" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
            [[ -z "$cpu_threads" ]] && cpu_threads=$cpu_cores
        fi
        cpu_arch=$(uname -m)
    fi

    # Validate values
    [[ -z "$cpu_model" ]] && cpu_model="Unknown"
    [[ -z "$cpu_cores" ]] && cpu_cores="Unknown"
    [[ -z "$cpu_threads" ]] && cpu_threads="Unknown"

    echo "$cpu_model|$cpu_cores|$cpu_threads|$cpu_arch"
}

# Detect RAM information
detect_ram() {
    local ram_total=0
    local ram_available=0

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        ram_total=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
        ram_available=$(vm_stat 2>/dev/null | grep "Pages free" | awk '{print $3}' | tr -d '.' || echo "0")
        ram_available=$((ram_available * 4096 / 1024 / 1024 / 1024))
    else
        # Linux
        if [[ -f /proc/meminfo ]]; then
            ram_total=$(grep "^MemTotal:" /proc/meminfo | awk '{print $2}')
            ram_available=$(grep "^MemAvailable:" /proc/meminfo | awk '{print $2}')
            ram_total=$((ram_total / 1024 / 1024))
            ram_available=$((ram_available / 1024 / 1024))
        fi
    fi

    # Convert to GB if needed
    if [[ $ram_total -gt 0 ]]; then
        ram_total=$((ram_total / 1024))
    fi
    if [[ $ram_available -gt 0 ]]; then
        ram_available=$((ram_available / 1024))
    fi

    [[ -z "$ram_total" ]] && ram_total="Unknown"
    [[ -z "$ram_available" ]] && ram_available="Unknown"

    echo "$ram_total|$ram_available"
}

# Detect storage information
detect_storage() {
    local storage_total=0
    local storage_used=0
    local storage_available=0

    if [[ "$OSTYPE" == "darwin"* ]]; then
        local disk=$(df -h / | tail -1)
        storage_total=$(echo "$disk" | awk '{print $2}' | sed 's/Gi//')
        storage_available=$(echo "$disk" | awk '{print $4}' | sed 's/Gi//')
        storage_used=$(echo "$disk" | awk '{print $3}' | sed 's/Gi//')
    else
        if command -v df &> /dev/null; then
            local disk=$(df -B1 / | tail -1)
            storage_total=$(echo "$disk" | awk '{print $2}')
            storage_available=$(echo "$disk" | awk '{print $4}')
            storage_used=$(echo "$disk" | awk '{print $3}')

            storage_total=$((storage_total / 1024 / 1024 / 1024))
            storage_available=$((storage_available / 1024 / 1024 / 1024))
            storage_used=$((storage_used / 1024 / 1024 / 1024))
        fi
    fi

    [[ -z "$storage_total" ]] && storage_total="Unknown"
    [[ -z "$storage_available" ]] && storage_available="Unknown"
    [[ -z "$storage_used" ]] && storage_used="Unknown"

    echo "$storage_total|$storage_used|$storage_available"
}

# Detect GPU information
detect_gpu() {
    local gpu_info="None"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS GPU detection
        gpu_info=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chipset Model:" | head -1 | awk -F': ' '{print $2}' || echo "Integrated")
    else
        # Linux GPU detection
        if command -v lspci &> /dev/null; then
            gpu_info=$(lspci | grep -i "VGA\|3D\|Display" | cut -d: -f3 | head -1 | xargs || echo "Integrated")
            [[ -z "$gpu_info" ]] && gpu_info="Integrated"
        fi
    fi

    [[ -z "$gpu_info" ]] && gpu_info="Unknown"
    echo "$gpu_info"
}

# Detect OS information
detect_os() {
    local os_name=""
    local os_version=""

    if [[ "$OSTYPE" == "darwin"* ]]; then
        os_name="macOS"
        os_version=$(sw_vers -productVersion)
    else
        if [[ -f /etc/os-release ]]; then
            os_name=$(grep "^NAME=" /etc/os-release | cut -d= -f2 | tr -d '"')
            os_version=$(grep "^VERSION=" /etc/os-release | cut -d= -f2 | tr -d '"')
        fi
    fi

    [[ -z "$os_name" ]] && os_name="Unknown"
    [[ -z "$os_version" ]] && os_version="Unknown"

    echo "$os_name|$os_version"
}

# Assess hardware compatibility
assess_compatibility() {
    local cpu_cores=$1
    local ram_gb=$2
    local storage_gb=$3
    local cpu_arch=$4

    local compatibility="supported"
    local score=100
    local issues=()

    # Check CPU cores
    if [[ "$cpu_cores" -lt 2 ]]; then
        compatibility="degraded"
        ((score -= 20))
        issues+=("Insufficient CPU cores (minimum recommended: 2, detected: $cpu_cores)")
    elif [[ "$cpu_cores" -lt 4 ]]; then
        ((score -= 10))
        issues+=("Limited CPU cores for optimal performance (recommended: 4+, detected: $cpu_cores)")
    fi

    # Check RAM
    if [[ "$ram_gb" -lt 4 ]]; then
        compatibility="degraded"
        ((score -= 30))
        issues+=("Insufficient RAM (minimum: 4GB, detected: ${ram_gb}GB)")
    elif [[ "$ram_gb" -lt 8 ]]; then
        ((score -= 15))
        issues+=("Limited RAM for optimal performance (recommended: 8GB+, detected: ${ram_gb}GB)")
    elif [[ "$ram_gb" -lt 16 ]]; then
        ((score -= 5))
        issues+=("Good RAM but 16GB+ recommended for heavy workloads (detected: ${ram_gb}GB)")
    fi

    # Check storage
    if [[ "$storage_gb" -lt 10 ]]; then
        compatibility="degraded"
        ((score -= 20))
        issues+=("Insufficient storage space (minimum: 10GB, detected: ${storage_gb}GB)")
    elif [[ "$storage_gb" -lt 50 ]]; then
        ((score -= 10))
        issues+=("Limited storage for optimal experience (recommended: 50GB+, detected: ${storage_gb}GB)")
    fi

    # Ensure score doesn't go below 0
    [[ $score -lt 0 ]] && score=0

    # Unsupported architectures
    if [[ ! "$cpu_arch" =~ ^(x86_64|arm64|aarch64)$ ]]; then
        compatibility="unsupported"
        issues+=("Unsupported CPU architecture: $cpu_arch")
    fi

    echo "$compatibility|$score|${issues[*]}"
}

# Check against hardware database
check_database() {
    if [[ ! -f "$DB_FILE" ]]; then
        print_status error "Hardware database not found at $DB_FILE"
        return 1
    fi

    print_status info "Checking against hardware database..."

    # Extract CPU model from detection
    local cpu_model=$(echo "$CPU_INFO" | cut -d'|' -f1)

    # Count matching entries
    if command -v jq &> /dev/null; then
        local match_count=$(jq "[.[] | select(.cpu | test(\"$cpu_model\"; \"i\"))] | length" "$DB_FILE" 2>/dev/null || echo "0")
        if [[ "$match_count" -gt 0 ]]; then
            print_status ok "Found $match_count similar hardware configurations in database"
        else
            print_status warn "No exact CPU match in database, but general compatibility should be similar"
        fi
    fi
}

# Output in JSON format
output_json() {
    local cpu_model=$(echo "$CPU_INFO" | cut -d'|' -f1)
    local cpu_cores=$(echo "$CPU_INFO" | cut -d'|' -f2)
    local cpu_threads=$(echo "$CPU_INFO" | cut -d'|' -f3)
    local cpu_arch=$(echo "$CPU_INFO" | cut -d'|' -f4)

    local ram_total=$(echo "$RAM_INFO" | cut -d'|' -f1)
    local ram_available=$(echo "$RAM_INFO" | cut -d'|' -f2)

    local storage_total=$(echo "$STORAGE_INFO" | cut -d'|' -f1)
    local storage_used=$(echo "$STORAGE_INFO" | cut -d'|' -f2)
    local storage_available=$(echo "$STORAGE_INFO" | cut -d'|' -f3)

    local os_name=$(echo "$OS_INFO" | cut -d'|' -f1)
    local os_version=$(echo "$OS_INFO" | cut -d'|' -f2)

    local compatibility=$(echo "$COMPATIBILITY" | cut -d'|' -f1)
    local score=$(echo "$COMPATIBILITY" | cut -d'|' -f2)

    # Build JSON
    cat <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "hardware": {
    "cpu": {
      "model": "$cpu_model",
      "cores": $cpu_cores,
      "threads": $cpu_threads,
      "architecture": "$cpu_arch"
    },
    "memory": {
      "total_gb": $ram_total,
      "available_gb": $ram_available
    },
    "storage": {
      "total_gb": $storage_total,
      "used_gb": $storage_used,
      "available_gb": $storage_available
    },
    "gpu": "$GPU_INFO"
  },
  "system": {
    "os": "$os_name",
    "version": "$os_version",
    "kernel": "$(uname -r)"
  },
  "compatibility": {
    "status": "$compatibility",
    "score": $score
  }
}
EOF
}

# Output in human-readable format
output_human() {
    local cpu_model=$(echo "$CPU_INFO" | cut -d'|' -f1)
    local cpu_cores=$(echo "$CPU_INFO" | cut -d'|' -f2)
    local cpu_threads=$(echo "$CPU_INFO" | cut -d'|' -f3)
    local cpu_arch=$(echo "$CPU_INFO" | cut -d'|' -f4)

    local ram_total=$(echo "$RAM_INFO" | cut -d'|' -f1)
    local ram_available=$(echo "$RAM_INFO" | cut -d'|' -f2)

    local storage_total=$(echo "$STORAGE_INFO" | cut -d'|' -f1)
    local storage_used=$(echo "$STORAGE_INFO" | cut -d'|' -f2)
    local storage_available=$(echo "$STORAGE_INFO" | cut -d'|' -f3)

    local os_name=$(echo "$OS_INFO" | cut -d'|' -f1)
    local os_version=$(echo "$OS_INFO" | cut -d'|' -f2)

    local compatibility=$(echo "$COMPATIBILITY" | cut -d'|' -f1)
    local score=$(echo "$COMPATIBILITY" | cut -d'|' -f2)
    local issues=$(echo "$COMPATIBILITY" | cut -d'|' -f3-)

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "          ShadowCypher Hardware Compatibility Report"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    echo "SYSTEM INFORMATION"
    echo "───────────────────────────────────────────────────────────────"
    echo "OS:                  $os_name"
    echo "Version:             $os_version"
    echo "Kernel:              $(uname -r)"
    echo "Architecture:        $(uname -m)"
    echo ""

    echo "CPU INFORMATION"
    echo "───────────────────────────────────────────────────────────────"
    echo "Model:               $cpu_model"
    echo "Cores:               $cpu_cores"
    echo "Threads:             $cpu_threads"
    echo "Architecture:        $cpu_arch"
    echo ""

    echo "MEMORY"
    echo "───────────────────────────────────────────────────────────────"
    echo "Total:               ${ram_total}GB"
    echo "Available:           ${ram_available}GB"
    echo ""

    echo "STORAGE"
    echo "───────────────────────────────────────────────────────────────"
    echo "Total:               ${storage_total}GB"
    echo "Used:                ${storage_used}GB"
    echo "Available:           ${storage_available}GB"
    echo ""

    echo "GPU"
    echo "───────────────────────────────────────────────────────────────"
    echo "Device:              $GPU_INFO"
    echo ""

    echo "COMPATIBILITY ASSESSMENT"
    echo "───────────────────────────────────────────────────────────────"

    case "$compatibility" in
        supported)
            print_status ok "Status: SUPPORTED"
            ;;
        degraded)
            print_status warn "Status: DEGRADED (Limited functionality)"
            ;;
        unsupported)
            print_status error "Status: UNSUPPORTED"
            ;;
    esac

    echo "Compatibility Score: $score/100"
    echo ""

    if [[ -n "$issues" ]] && [[ "$issues" != " " ]]; then
        echo "RECOMMENDATIONS"
        echo "───────────────────────────────────────────────────────────────"
        IFS=' ' read -ra ISSUE_ARRAY <<< "$issues"
        for issue in "${ISSUE_ARRAY[@]}"; do
            print_status warn "$issue"
        done
        echo ""
    fi

    echo "═══════════════════════════════════════════════════════════════"
    echo "Report generated: $(date)"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
}

# Print usage
usage() {
    cat <<EOF
Usage: hardware-report.sh [OPTIONS]

Generate a hardware compatibility report for ShadowCypher.

OPTIONS:
    -h, --help              Show this help message
    -j, --json              Output in JSON format (default: human-readable)
    -d, --check-db          Check against hardware database
    -v, --verbose           Enable verbose output
    -q, --quick             Quick check without database verification

EXAMPLES:
    ./hardware-report.sh                  # Human-readable report
    ./hardware-report.sh --json           # JSON output
    ./hardware-report.sh --check-db       # Check against database
    ./hardware-report.sh -j -d            # JSON output with database check

EOF
}

# Main execution
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -j|--json)
                OUTPUT_FORMAT="json"
                shift
                ;;
            -d|--check-db)
                CHECK_DATABASE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quick)
                CHECK_DATABASE=false
                shift
                ;;
            *)
                echo "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Collect hardware information
    CPU_INFO=$(detect_cpu)
    RAM_INFO=$(detect_ram)
    STORAGE_INFO=$(detect_storage)
    GPU_INFO=$(detect_gpu)
    OS_INFO=$(detect_os)

    # Assess compatibility
    local cpu_cores=$(echo "$CPU_INFO" | cut -d'|' -f2)
    local ram_gb=$(echo "$RAM_INFO" | cut -d'|' -f1)
    local storage_gb=$(echo "$STORAGE_INFO" | cut -d'|' -f1)
    local cpu_arch=$(echo "$CPU_INFO" | cut -d'|' -f4)

    COMPATIBILITY=$(assess_compatibility "$cpu_cores" "$ram_gb" "$storage_gb" "$cpu_arch")

    # Output report
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        output_json
    else
        output_human

        # Check database if requested
        if [[ "$CHECK_DATABASE" == "true" ]]; then
            check_database
        fi
    fi
}

# Run main function
main "$@"
