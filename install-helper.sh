#!/usr/bin/env bash
################################################################################
# SHADOWCYPHER // INSTALLATION HELPER
# OS detection, dependency installation, and guided setup
################################################################################

set -e

# Colors for output
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
BLUE='\033[1;34m'
NC='\033[0m'

# Logging functions
log_banner() {
    echo -e "\n${BLUE}=================================================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${BLUE}=================================================================================${NC}\n"
}

log_step() {
    echo -e "${CYAN}[→]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Check if running with required privileges for system package installation
check_sudo_if_needed() {
    if [[ "$INSTALL_SYSTEM_DEPS" == "true" && "$EUID" -ne 0 && ! -w /usr/bin ]]; then
        log_warn "System package installation requires sudo. You may be prompted for your password."
    fi
}

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS="$ID"
        OS_VERSION="$VERSION_ID"
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        OS_VERSION=$(lsb_release -sr)
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        OS=$(echo $DISTRIB_ID | tr '[:upper:]' '[:lower:]')
        OS_VERSION="$DISTRIB_RELEASE"
    else
        OS="unknown"
        OS_VERSION="unknown"
    fi

    log_info "Detected OS: ${CYAN}$OS $OS_VERSION${NC}"
}

# Detect available package manager
detect_package_manager() {
    if command -v apt-get &>/dev/null; then
        PKG_MANAGER="apt"
        PKG_UPDATE="apt-get update"
        PKG_INSTALL="apt-get install -y"
    elif command -v dnf &>/dev/null; then
        PKG_MANAGER="dnf"
        PKG_UPDATE="dnf check-update"
        PKG_INSTALL="dnf install -y"
    elif command -v yum &>/dev/null; then
        PKG_MANAGER="yum"
        PKG_UPDATE="yum check-update"
        PKG_INSTALL="yum install -y"
    elif command -v pacman &>/dev/null; then
        PKG_MANAGER="pacman"
        PKG_UPDATE="pacman -Sy"
        PKG_INSTALL="pacman -S --noconfirm"
    elif command -v zypper &>/dev/null; then
        PKG_MANAGER="zypper"
        PKG_UPDATE="zypper refresh"
        PKG_INSTALL="zypper install -y"
    else
        PKG_MANAGER="none"
    fi

    if [ "$PKG_MANAGER" != "none" ]; then
        log_success "Package manager detected: ${CYAN}$PKG_MANAGER${NC}"
    else
        log_warn "No compatible package manager found. You may need to install dependencies manually."
    fi
}

# Install system dependencies based on package manager
install_system_deps() {
    log_step "Installing system dependencies..."

    case "$PKG_MANAGER" in
        apt)
            log_info "Using apt-get for Debian/Ubuntu/Linux Mint..."
            sudo apt-get update -qq || true
            sudo apt-get install -y \
                python3 python3-dev python3-pip python3-venv \
                libgtk-3-0 libgtk-3-dev \
                libgirepository1.0-dev \
                libcairo2-dev \
                pkg-config \
                build-essential \
                curl wget git \
                gir1.2-gtk-3.0 \
                python3-gi python3-gi-cairo || log_warn "Some packages failed to install"
            ;;
        dnf)
            log_info "Using dnf for Fedora/RHEL/CentOS..."
            sudo dnf install -y \
                python3 python3-devel \
                gtk3 gtk3-devel \
                gobject-introspection-devel \
                cairo-devel \
                pkgconfig \
                gcc gcc-c++ \
                curl wget git \
                python3-gobject || log_warn "Some packages failed to install"
            ;;
        yum)
            log_info "Using yum for older RHEL/CentOS..."
            sudo yum install -y \
                python3 python3-devel \
                gtk3 gtk3-devel \
                gobject-introspection-devel \
                cairo-devel \
                pkgconfig \
                gcc gcc-c++ \
                curl wget git || log_warn "Some packages failed to install"
            ;;
        pacman)
            log_info "Using pacman for Arch Linux..."
            sudo pacman -Sy --noconfirm \
                python python-pip \
                gtk3 \
                gobject-introspection \
                cairo \
                base-devel \
                curl wget git || log_warn "Some packages failed to install"
            ;;
        zypper)
            log_info "Using zypper for openSUSE..."
            sudo zypper install -y \
                python3 python3-devel \
                gtk3 gtk3-devel \
                gobject-introspection-devel \
                cairo-devel \
                pkg-config \
                gcc gcc-c++ \
                curl wget git || log_warn "Some packages failed to install"
            ;;
        *)
            log_error "Unsupported package manager or unable to install system dependencies automatically."
            log_info "Please manually install the following:"
            cat << 'EOF'
    - Python 3.10+
    - GTK-3 development files
    - GObject Introspection
    - Cairo development files
    - Build tools (gcc, make)
    - curl, wget, git
EOF
            exit 1
            ;;
    esac

    log_success "System dependencies installed."
}

# Check Python version
check_python() {
    log_step "Checking Python version..."

    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 is not installed or not in PATH."
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python version: ${CYAN}$PYTHON_VERSION${NC}"

    # Check if version is 3.10 or higher
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        log_error "Python 3.10 or higher is required (found $PYTHON_VERSION)."
        exit 1
    fi

    log_success "Python version requirement met."
}

# Create virtual environment
setup_venv() {
    local VENV_PATH="${1:-.}/venv"

    log_step "Setting up Python virtual environment..."

    if [ -d "$VENV_PATH" ]; then
        log_warn "Virtual environment already exists at $VENV_PATH"
        read -p "Remove and recreate? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_PATH"
        else
            log_info "Using existing virtual environment."
            return 0
        fi
    fi

    python3 -m venv "$VENV_PATH" || {
        log_error "Failed to create virtual environment."
        exit 1
    }

    log_success "Virtual environment created at ${CYAN}$VENV_PATH${NC}"
}

# Activate virtual environment
activate_venv() {
    local VENV_PATH="${1:-.}/venv"

    if [ -f "$VENV_PATH/bin/activate" ]; then
        source "$VENV_PATH/bin/activate"
        log_success "Virtual environment activated."
    else
        log_error "Virtual environment activation script not found."
        exit 1
    fi
}

# Install Python packages
install_python_deps() {
    local INSTALL_TYPE="${1:-base}"

    log_step "Installing Python dependencies..."

    # Upgrade pip
    log_info "Upgrading pip, setuptools, and wheel..."
    pip install --upgrade pip setuptools wheel -q || {
        log_error "Failed to upgrade pip."
        exit 1
    }

    # Install base requirements
    if [ -f "requirements.txt" ]; then
        log_info "Installing requirements from requirements.txt..."
        pip install -r requirements.txt -q || {
            log_error "Failed to install requirements."
            exit 1
        }
    else
        log_warn "requirements.txt not found in current directory."
    fi

    # Install package in development mode
    log_info "Installing shadowcypher package in development mode..."
    pip install -e . -q || {
        log_error "Failed to install package."
        exit 1
    }

    # Install optional dependencies
    case "$INSTALL_TYPE" in
        full)
            log_info "Installing full dependencies (all features)..."
            pip install -e ".[full]" -q || log_warn "Some optional dependencies failed to install"
            ;;
        ai)
            log_info "Installing AI dependencies..."
            pip install -e ".[ai]" -q || log_warn "Some AI dependencies failed to install"
            ;;
        dev)
            log_info "Installing development dependencies..."
            pip install -e ".[dev]" -q || log_warn "Some dev dependencies failed to install"
            ;;
        *)
            log_info "Using base installation."
            ;;
    esac

    log_success "Python dependencies installed."
}

# Create required directories
create_directories() {
    log_step "Creating required directories..."

    local APP_DIR="${1:-.}"

    mkdir -p "$APP_DIR/wordlists"
    mkdir -p "$APP_DIR/findings"
    mkdir -p "$APP_DIR/reports"
    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/tools"
    mkdir -p "$APP_DIR/data"

    log_success "Directories created."
}

# Setup executable launcher
setup_launcher() {
    local APP_DIR="${1:-.}"
    local LOCAL_BIN="${2:-$HOME/.local/bin}"

    log_step "Setting up executable launcher..."

    mkdir -p "$LOCAL_BIN"

    # Create the launcher script
    cat > "$APP_DIR/shadowcypher_launch" << EOF
#!/usr/bin/env bash
# ShadowCypher Local Launcher - Generated by install-helper.sh
export PATH="\$PATH:$LOCAL_BIN:$APP_DIR/tools"
cd "$APP_DIR"

# Display backend detection
if [ -n "\$WAYLAND_DISPLAY" ]; then
    export GDK_BACKEND=wayland
elif [ -z "\$DISPLAY" ]; then
    export DISPLAY=:0
fi

source "$APP_DIR/venv/bin/activate"
exec python3 -m shadowcypher.app "\$@"
EOF

    chmod +x "$APP_DIR/shadowcypher_launch"

    # Create symlink
    ln -sf "$APP_DIR/shadowcypher_launch" "$LOCAL_BIN/shadowcypher"

    log_success "Launcher created at ${CYAN}$LOCAL_BIN/shadowcypher${NC}"
}

# Check and configure Ollama
setup_ollama() {
    log_step "Checking Ollama installation..."

    if ! command -v ollama &>/dev/null; then
        log_warn "Ollama is not installed."
        read -p "Install Ollama now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Visiting https://ollama.com/download in browser..."
            if command -v xdg-open &>/dev/null; then
                xdg-open "https://ollama.com/download"
            elif command -v open &>/dev/null; then
                open "https://ollama.com/download"
            else
                log_info "Please visit: https://ollama.com/download"
            fi
            log_info "After installation, run: ollama serve"
            return 0
        else
            log_warn "Ollama skipped. AI features will not be available."
            return 0
        fi
    fi

    log_success "Ollama is installed."

    # Check if Ollama service is running
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        log_success "Ollama service is running."

        # List available models
        log_info "Available models:"
        ollama list 2>/dev/null | tail -n +2 | while read line; do
            echo "    $line"
        done
    else
        log_warn "Ollama service is not running. Start with: ollama serve"
        log_info "Recommended models:"
        log_info "  Elite (22GB+ VRAM):    ollama pull dolphin-mixtral:8x7b"
        log_info "  Pro (12GB+ VRAM):      ollama pull dolphin-llama3.1:8b-q8_0"
        log_info "  Standard (7GB+ VRAM):  ollama pull dolphin-llama3:8b"
        log_info "  Lite (under 7GB VRAM): ollama pull dolphin-mistral:7b"
    fi
}

# Run verification tests
run_verification() {
    log_step "Running verification tests..."

    local TESTS_PASSED=0
    local TESTS_FAILED=0

    # Test 1: Python imports
    log_info "Checking Python dependencies..."
    if python3 -c "import shadowcypher; print('OK')" 2>/dev/null | grep -q OK; then
        log_success "✓ ShadowCypher imports correctly"
        ((TESTS_PASSED++))
    else
        log_error "✗ Failed to import shadowcypher"
        ((TESTS_FAILED++))
    fi

    # Test 2: GTK
    log_info "Checking GTK-3.0..."
    if python3 -c "import gi; gi.require_version('Gtk', '3.0'); print('OK')" 2>/dev/null | grep -q OK; then
        log_success "✓ GTK-3.0 is available"
        ((TESTS_PASSED++))
    else
        log_error "✗ GTK-3.0 is not available"
        ((TESTS_FAILED++))
    fi

    # Test 3: Ollama (if available)
    if command -v ollama &>/dev/null; then
        log_info "Checking Ollama..."
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            log_success "✓ Ollama service is available"
            ((TESTS_PASSED++))
        else
            log_warn "⚠ Ollama service is not running"
        fi
    fi

    echo ""
    echo -e "${CYAN}Test Results:${NC}"
    echo -e "  ${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "  ${RED}Failed:${NC} $TESTS_FAILED"

    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "All verification tests passed!"
    else
        log_warn "Some tests failed. Check the output above."
    fi
}

# Print usage instructions
print_usage() {
    cat << 'EOF'

Usage: ./install-helper.sh [OPTIONS]

Options:
    --help              Show this help message
    --system            Install system dependencies only
    --python            Install Python dependencies only
    --full              Install all optional dependencies (AI, security modules)
    --ai                Install AI modules only
    --dev               Install development dependencies (testing, linting)
    --no-ollama         Skip Ollama configuration
    --no-verify         Skip verification tests
    -y, --yes           Accept all prompts automatically

Examples:
    # Full installation with all dependencies
    ./install-helper.sh

    # Install system deps only (for manual Python setup)
    ./install-helper.sh --system

    # Full install with AI modules
    ./install-helper.sh --full

    # Development setup
    ./install-helper.sh --dev

EOF
}

# Main installation flow
main() {
    log_banner "ShadowCypher Installation Helper"

    # Parse arguments
    INSTALL_SYSTEM_DEPS=true
    INSTALL_PYTHON_DEPS=true
    PYTHON_INSTALL_TYPE="base"
    SETUP_OLLAMA=true
    RUN_VERIFICATION=true
    AUTO_YES=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                print_usage
                exit 0
                ;;
            --system)
                INSTALL_PYTHON_DEPS=false
                SETUP_OLLAMA=false
                RUN_VERIFICATION=false
                ;;
            --python)
                INSTALL_SYSTEM_DEPS=false
                SETUP_OLLAMA=false
                ;;
            --full)
                PYTHON_INSTALL_TYPE="full"
                ;;
            --ai)
                PYTHON_INSTALL_TYPE="ai"
                ;;
            --dev)
                PYTHON_INSTALL_TYPE="dev"
                ;;
            --no-ollama)
                SETUP_OLLAMA=false
                ;;
            --no-verify)
                RUN_VERIFICATION=false
                ;;
            -y|--yes)
                AUTO_YES=true
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
        shift
    done

    # Get application directory
    APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$APP_DIR"

    # Detection phase
    detect_distro
    detect_package_manager
    check_python

    # Installation phase
    if [ "$INSTALL_SYSTEM_DEPS" = true ]; then
        if [ "$PKG_MANAGER" != "none" ]; then
            check_sudo_if_needed
            install_system_deps
        else
            log_warn "Skipping system dependencies (no compatible package manager found)."
        fi
    fi

    if [ "$INSTALL_PYTHON_DEPS" = true ]; then
        setup_venv "$APP_DIR"
        activate_venv "$APP_DIR"
        install_python_deps "$PYTHON_INSTALL_TYPE"
    fi

    # Setup phase
    create_directories "$APP_DIR"
    setup_launcher "$APP_DIR"

    if [ "$SETUP_OLLAMA" = true ]; then
        setup_ollama
    fi

    # Verification phase
    if [ "$RUN_VERIFICATION" = true ]; then
        echo ""
        run_verification
    fi

    # Completion
    log_banner "Installation Complete"

    echo -e "${GREEN}ShadowCypher has been installed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start Ollama (if not already running):"
    echo -e "     ${CYAN}ollama serve${NC}"
    echo ""
    echo "  2. Pull an AI model (in another terminal):"
    echo -e "     ${CYAN}ollama pull dolphin-mistral:7b${NC}"
    echo ""
    echo "  3. Launch ShadowCypher:"
    echo -e "     ${CYAN}shadowcypher${NC}"
    echo "     or"
    echo -e "     ${CYAN}$APP_DIR/shadowcypher_launch${NC}"
    echo ""
    echo "  4. Access from application menu or launcher"
    echo ""
    echo "For help: ./install-helper.sh --help"
}

# Run main function
main "$@"
