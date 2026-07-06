# ShadowCypher Quick Start Guide

Get ShadowCypher up and running in 5 minutes.

## Prerequisites

- **Linux system** (Ubuntu 20.04 LTS recommended)
- **Python 3.10+**
- **8GB RAM minimum**
- **20GB disk space**

## Quick Install (One Command)

```bash
git clone https://github.com/jakes1345/ShadowCypher.git
cd ShadowCypher
./install.sh
```

The `install.sh` script will automatically:
- Detect your OS and install system dependencies
- Create a Python virtual environment
- Install all required packages
- Configure desktop integration
- Detect your GPU and set up appropriate AI models

**Installation takes 5-10 minutes depending on internet speed and GPU support.**

## Alternative: Using the Install Helper

For more control over installation options:

```bash
./install-helper.sh
```

Useful options:
```bash
./install-helper.sh --system      # System deps only
./install-helper.sh --full        # Include all optional modules
./install-helper.sh --dev         # Include development tools
./install-helper.sh --help        # Show all options
```

## Step 2: Set Up AI Models

Open a new terminal and start the Ollama service:

```bash
ollama serve
```

In another terminal, pull a model based on your GPU VRAM:

```bash
# For 22GB+ VRAM (Elite performance)
ollama pull dolphin-mixtral:8x7b

# For 12GB+ VRAM (Pro performance)
ollama pull dolphin-llama3.1:8b-q8_0

# For 7GB+ VRAM (Standard performance)
ollama pull dolphin-llama3:8b

# For under 7GB VRAM (Lite performance)
ollama pull dolphin-mistral:7b
```

To check available models:
```bash
ollama list
```

## Step 3: Launch ShadowCypher

```bash
shadowcypher
```

Or find it in your application menu under Security/System.

If the command doesn't work, try:
```bash
~/.local/bin/shadowcypher
```

Or launch directly:
```bash
cd /path/to/ShadowCypher
source venv/bin/activate
python3 -m shadowcypher.app
```

## First Steps

Once ShadowCypher opens:

1. **Command HUD** - See system status (CPU, RAM, Disk usage)
2. **Shadow Synthesizer** - Chat with local AI for security analysis
3. **Signal Analysis** - Run network reconnaissance on targets
4. **Spectral Intelligence** - OSINT (DNS, WHOIS, username search)
5. **Support & Ticketing** - Configure API keys and settings

## Common Commands

### Verify Installation
```bash
# Check Python packages
python3 -c "import shadowcypher; print('OK')"

# Check GTK (for GUI)
python3 -c "import gi; gi.require_version('Gtk', '3.0'); print('OK')"

# Check Ollama
curl http://localhost:11434/api/tags
```

### Run Tests
```bash
cd /path/to/ShadowCypher
source venv/bin/activate
pytest tests/ -v
```

### Check Logs
```bash
tail -f ~/.config/shadowcypher/logs/app.log
```

## Troubleshooting

### "command not found: shadowcypher"
```bash
# Add to your PATH
export PATH="$HOME/.local/bin:$PATH"

# Or add permanently to ~/.bashrc or ~/.zshrc:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### "ModuleNotFoundError: No module named 'gi'"
```bash
# Ubuntu/Debian
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Fedora
sudo dnf install python3-gobject gtk3
```

### "Cannot connect to Ollama"
```bash
# Make sure Ollama is running:
ollama serve

# Test connection:
curl http://localhost:11434/api/tags
```

### GUI doesn't display
```bash
# For Wayland:
export GDK_BACKEND=wayland
shadowcypher

# For X11:
export DISPLAY=:0
export GDK_BACKEND=x11
shadowcypher
```

### Out of memory
```bash
# Use a smaller AI model:
ollama pull mistral:7b

# Or configure in ~/.config/shadowcypher/config.yml:
ai:
  model: "mistral:7b"
  temperature: 0.5
  max_tokens: 1024
```

## Configuration

Edit configuration file (created on first run):
```bash
~/.config/shadowcypher/config.yml
```

Example:
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
```

## Environment Variables

Optional, set in `~/.bashrc` or create `.env` file:

```bash
# Ollama configuration
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=dolphin-mistral:7b

# Logging
export LOG_LEVEL=INFO
```

## Next Steps

- **Full Documentation:** See `INSTALL.md` for comprehensive setup
- **Developer Guide:** See `docs/` directory
- **API Documentation:** Check `docs/api/`
- **Agents & Modules:** See `AGENTS.md`

## Running Specific Modules

### Just the CLI (no GUI)
```bash
python3 shadow_cli.py
```

### Run tests
```bash
pytest tests/test_config.py -v
pytest tests/ --cov=shadowcypher
```

### Development mode
```bash
pip install -e ".[dev]"
ruff check shadowcypher/
mypy shadowcypher/
```

## Performance Tips

### For Slower Systems
1. Use a smaller AI model: `ollama pull mistral:7b`
2. Reduce parallel scan tasks in config
3. Disable non-essential modules
4. Run with: `python3 -m shadowcypher.app --minimal`

### For GPU Systems
1. Install GPU drivers for your hardware
2. Pull larger models for better AI quality
3. Enable GPU acceleration in Ollama
4. Monitor VRAM: `nvidia-smi` or `rocm-smi`

### Disk Space Optimization
- Remove downloaded models you don't use: `ollama rm modelname`
- Clean up old logs: `rm ~/.config/shadowcypher/logs/*.log`
- Archive old reports: `cd findings && tar czf archive-$(date +%Y%m%d).tar.gz *.json`

## Getting Help

- **Issues:** https://github.com/jakes1345/ShadowCypher/issues
- **Documentation:** In `docs/` directory
- **Security Reports:** In-app Support & Ticketing tab
- **Email:** security@shadowcypher.site

## Uninstall

```bash
# Remove launcher
rm ~/.local/bin/shadowcypher

# Remove desktop shortcut
rm ~/.local/share/applications/shadowcypher.desktop

# Remove the repo (optional)
rm -rf /path/to/ShadowCypher
```

---

**Ready to explore?** Launch ShadowCypher and start with the **Command HUD** for system overview or **Shadow Synthesizer** to chat with local AI about security topics.

**Pro tip:** Use the built-in **Shadow Synthesizer** to ask questions like "What are the top CVEs affecting Linux 6.x?" or "Explain what a DNS amplification attack is." All analysis stays on your machine.
