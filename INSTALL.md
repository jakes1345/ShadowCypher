# ShadowCypher Installation Guide

ShadowCypher is an enterprise-grade offensive security platform that runs entirely on your machine. This guide covers system requirements, installation steps, and troubleshooting.

## System Requirements

### Minimum Requirements
- **OS:** Linux (Ubuntu 18.04+, Debian 10+, Fedora 30+, or equivalent)
- **Python:** 3.10 or higher
- **RAM:** 8 GB minimum (16 GB recommended)
- **Disk Space:** 20 GB (for base install + dependencies)
- **GPU:** Optional but highly recommended for AI inference

### Recommended Setup
- **OS:** Ubuntu 20.04 LTS or Ubuntu 22.04 LTS (actively tested)
- **Python:** 3.12
- **RAM:** 16 GB or more
- **Disk Space:** 50 GB (includes AI models and wordlists)
- **GPU:** NVIDIA with CUDA support (8GB+ VRAM) or AMD with ROCm

### Required System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    python3 python3-dev python3-pip python3-venv \
    libgtk-3-0 libgtk-3-dev \
    libgirepository1.0-dev \
    libcairo2-dev \
    pkg-config \
    build-essential \
    curl wget git
```

**Fedora/RHEL:**
```bash
sudo dnf install -y \
    python3 python3-devel \
    gtk3 gtk3-devel \
    gobject-introspection-devel \
    cairo-devel \
    pkgconfig \
    gcc gcc-c++ \
    curl wget git
```

**Arch Linux:**
```bash
sudo pacman -S \
    python python-pip \
    gtk3 \
    gobject-introspection \
    cairo \
    base-devel \
    curl wget git
```

### GPU Support (Optional)

For GPU-accelerated AI inference with Ollama:

**NVIDIA (CUDA):**
```bash
# Install NVIDIA Driver
sudo apt-get install -y nvidia-driver-XXX nvidia-utils

# Install CUDA Toolkit (if not already installed)
# Visit: https://developer.nvidia.com/cuda-downloads
```

**AMD (ROCm):**
```bash
# Install ROCm
wget -qO - https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -
echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/debian focal main' | sudo tee /etc/apt/sources.list.d/rocm.list
sudo apt-get update
sudo apt-get install -y rocm-dkms
```

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/jakes1345/ShadowCypher.git
cd ShadowCypher
```

### 2. Automated Installation (Recommended)

The included `install.sh` script automates the entire setup process:

```bash
./install.sh
```

This script will:
- Create a Python virtual environment
- Install all Python dependencies
- Run system stability audit
- Generate local executable wrapper
- Register desktop integration
- Detect GPU and configure AI models

**Installation modes:**
```bash
./install.sh              # Local dev install (uses venv, no root)
./install.sh --apt-source # Add apt repository (requires sudo)
./install.sh --deb        # Install from .deb package via apt
```

### 3. Manual Installation

If you prefer manual setup:

#### Step 3.1: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Step 3.2: Install Python Dependencies
```bash
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
pip install -e .
```

#### Step 3.3: Install Optional Dependencies

For full functionality with all AI and security modules:
```bash
pip install -e ".[full]"  # All features
pip install -e ".[ai]"    # AI orchestration only
pip install -e ".[dev]"   # Development and testing
```

#### Step 3.4: Create Directories
```bash
mkdir -p wordlists findings reports logs tools data
```

#### Step 3.5: Desktop Integration
```bash
# Create .local/bin directory
mkdir -p ~/.local/bin

# Create launcher script
cat > ~/.local/bin/shadowcypher << 'EOF'
#!/usr/bin/env bash
export PATH="$PATH:$HOME/.local/bin:$PWD/tools"
cd "$(dirname "$0")/../.."
source venv/bin/activate
exec python3 -m shadowcypher.app "$@"
EOF
chmod +x ~/.local/bin/shadowcypher
```

### 4. Configure AI Engine (Ollama)

#### Install Ollama
```bash
curl https://ollama.com/install.sh | sh
```

Or download from: https://ollama.com/download

#### Start Ollama Service
```bash
# In a separate terminal:
ollama serve

# Or as a systemd service:
sudo systemctl start ollama
sudo systemctl enable ollama
```

#### Pull AI Models

ShadowCypher can use any Ollama-compatible model. Recommended models based on GPU VRAM:

**22GB+ VRAM (Elite):**
```bash
ollama pull dolphin-mixtral:8x7b
```

**12-22GB VRAM (Pro):**
```bash
ollama pull dolphin-llama3.1:8b-q8_0
```

**7-12GB VRAM (Standard):**
```bash
ollama pull dolphin-llama3:8b
```

**Under 7GB VRAM (Lite):**
```bash
ollama pull dolphin-mistral:7b
```

The install.sh script will automatically detect your GPU VRAM and pull the appropriate model.

### 5. Configuration

#### Environment Variables
Create a `.env` file in the project root:

```bash
# AI Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=dolphin-mistral:7b

# Optional: API Keys for external threat intel
# OTX_API_KEY=your_key_here
# ABUSEIPDB_API_KEY=your_key_here

# Logging
LOG_LEVEL=INFO

# GUI Display (for headless systems)
# DISPLAY=:0
# GDK_BACKEND=x11  # or: wayland
```

#### Configuration File
Edit `~/.config/shadowcypher/config.yml` (created on first run):

```yaml
ai:
  model: "dolphin-mistral:7b"
  temperature: 0.7
  max_tokens: 2048

security:
  scan_timeout: 300
  max_parallel_tasks: 4

logging:
  level: "INFO"
  format: "json"
```

## Verification & Testing

### 1. Check Installation
```bash
# Verify Python packages
python3 -c "import shadowcypher; print(shadowcypher.__version__)"

# List available GTK libraries
python3 -c "import gi; gi.require_version('Gtk', '3.0'); print('GTK-3.0 OK')"
```

### 2. Verify Ollama
```bash
# Check Ollama service
curl http://localhost:11434/api/tags

# List available models
ollama list
```

### 3. Run Tests
```bash
# Run full test suite
pytest tests/ -v

# Run specific test module
pytest tests/test_config.py -v

# With coverage
pytest tests/ --cov=shadowcypher --cov-report=html
```

### 4. Start ShadowCypher
```bash
# Via alias (if installed)
shadowcypher

# Or directly
python3 -m shadowcypher.app

# Or via launcher
~/.local/bin/shadowcypher
```

## Post-Installation Configuration

### Desktop Shortcut
After running `install.sh`, ShadowCypher will appear in your application menu. To manually create a desktop shortcut:

```bash
cat > ~/.local/share/applications/shadowcypher.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=ShadowCypher
GenericName=Tactical Security Suite
Comment=Enterprise-grade offensive security and intelligence platform
Exec=$HOME/.local/bin/shadowcypher
Icon=shadowcypher
Terminal=false
Categories=System;Security;
Keywords=security;pentest;offensive;
StartupNotify=true
EOF
```

### Path Configuration
Ensure these are in your `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'gi'"

**Solution:** Install GTK bindings
```bash
# Ubuntu/Debian
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Fedora
sudo dnf install python3-gobject gtk3

# Arch
sudo pacman -S python-gobject gtk3
```

### Issue: "No module named 'shadowcypher'"

**Solution:** Install in development mode
```bash
cd /path/to/ShadowCypher
source venv/bin/activate
pip install -e .
```

### Issue: "Cannot connect to Ollama"

**Solution:** Verify Ollama is running
```bash
# Start Ollama if not running
ollama serve

# Check connection
curl http://localhost:11434/api/tags

# Verify OLLAMA_HOST environment variable
echo $OLLAMA_HOST  # Should output: http://localhost:11434
```

### Issue: GTK display errors on headless/SSH systems

**Solution:** Configure display settings
```bash
# For Wayland
export GDK_BACKEND=wayland

# For X11
export DISPLAY=:0
export GDK_BACKEND=x11
```

### Issue: Permission denied on ~/.local/bin/shadowcypher

**Solution:** Ensure script is executable
```bash
chmod +x ~/.local/bin/shadowcypher
```

### Issue: Out of memory during AI model loading

**Solution:** Check available VRAM and model size
```bash
# Check GPU VRAM
nvidia-smi  # NVIDIA
rocm-smi    # AMD

# Use a smaller model
ollama pull mistral:7b
```

### Issue: High CPU usage during scans

**Solution:** Limit parallel tasks in config
```yaml
security:
  max_parallel_tasks: 2  # Reduce from default
  scan_timeout: 180      # Timeout in seconds
```

## Development Installation

For contributing to ShadowCypher, install with dev dependencies:

```bash
cd ShadowCypher
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

Run code quality checks:
```bash
# Linting
ruff check shadowcypher/

# Type checking
mypy shadowcypher/

# Security scan
bandit -r shadowcypher/

# Tests
pytest tests/ -v --cov
```

## Uninstallation

### Complete Uninstall
```bash
# Remove application launcher
rm ~/.local/bin/shadowcypher

# Remove desktop shortcut
rm ~/.local/share/applications/shadowcypher.desktop

# Remove configuration (optional)
rm -rf ~/.config/shadowcypher

# Remove virtual environment (if using venv)
rm -rf /path/to/ShadowCypher/venv

# Remove repository (optional)
rm -rf /path/to/ShadowCypher
```

### Keep Configuration
If reinstalling and want to preserve settings:
```bash
# Backup config
cp -r ~/.config/shadowcypher ~/.config/shadowcypher.backup

# After reinstall
cp -r ~/.config/shadowcypher.backup/* ~/.config/shadowcypher/
```

## Getting Help

- **Issues:** https://github.com/jakes1345/ShadowCypher/issues
- **Documentation:** See `docs/` directory
- **Security Reports:** Use the in-app Secure Comm-Link (Support & Ticketing tab)
- **Email:** security@shadowcypher.site

## Version Information

Check your installed version:
```bash
python3 -c "import shadowcypher; print(f'ShadowCypher {shadowcypher.__version__}')"
```

Required Python version:
```bash
python3 --version  # Should be 3.10+
```

---

**Last Updated:** July 2026  
**Tested on:** Ubuntu 20.04 LTS, Ubuntu 22.04 LTS, Debian 11+
