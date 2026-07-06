# ShadowCypher Troubleshooting Guide

A comprehensive guide to diagnosing and fixing common ShadowCypher issues.

## Quick Diagnostics

Run the interactive diagnostic script:
```bash
chmod +x troubleshoot.sh
./troubleshoot.sh
```

This will check your environment, dependencies, and system health, then suggest fixes.

---

## Table of Contents

- [Installation & Dependencies](#installation--dependencies)
- [Application Launch Issues](#application-launch-issues)
- [Ollama & AI Features](#ollama--ai-features)
- [GTK & UI Issues](#gtk--ui-issues)
- [Network & Relay](#network--relay)
- [Scanning & Performance](#scanning--performance)
- [Encryption & Security](#encryption--security)
- [Log Interpretation](#log-interpretation)
- [Platform-Specific](#platform-specific)
- [When to Seek Help](#when-to-seek-help)

---

## Installation & Dependencies

### Python version mismatch

**Symptoms**: `ModuleNotFoundError`, `SyntaxError: invalid syntax`, or "not compatible with Python X.X"

**Diagnosis**:
```bash
python3 --version
```

**Solution**: ShadowCypher requires Python 3.12 or higher.

```bash
# Check if python3.12+ is installed
which python3.12

# If not, install it
# Ubuntu/Debian
sudo apt update && sudo apt install python3.12 python3.12-venv python3.12-dev

# macOS
brew install python@3.12

# Then update your shell
python3 -m venv venv
source venv/bin/activate
```

### Missing GTK libraries

**Symptoms**: `ImportError: cannot import name '_gi'` or "Gtk cannot be initialized"

**Diagnosis**:
```bash
python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk"
```

**Solution**:

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-3.0 libgtk-3-0 libcairo2
```

**macOS**:
```bash
brew install gtk+3
pip install pycairo pygobject
```

**Fedora/RHEL**:
```bash
sudo dnf install python3-gi gtk3 cairo
```

**Windows/WSL2**:
```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-3.0 xwayland
```

### Missing Python dependencies

**Symptoms**: `ModuleNotFoundError: No module named 'X'`

**Diagnosis**:
```bash
pip list | grep -E 'aiohttp|pydantic|cryptography|treequest'
```

**Solution**:
```bash
cd /home/jack/ShadowCypher
pip install -r requirements.txt --upgrade

# If that fails, try:
pip install --no-cache-dir -r requirements.txt
```

### Go compilation fails

**Symptoms**: "Failed to compile native relay" or "go: command not found"

**Diagnosis**:
```bash
go version
ls -la shadowcypher/native/relay/
```

**Solution**: Install Go 1.24+

```bash
# Linux
wget https://go.dev/dl/go1.24.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.24.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin

# macOS
brew install golang

# Verify
go version
```

If the relay binary exists but won't run:
```bash
# Remove stale binary (will auto-recompile)
rm -f shadowcypher/native/relay/relay
python3 -m shadowcypher.app
```

---

## Application Launch Issues

### "Address already in use" error

**Symptoms**: `OSError: [Errno 48] Address already in use` or "port 8888 is already in use"

**Diagnosis**:
```bash
lsof -i :8888
# Or on some systems:
netstat -tln | grep 8888
```

**Solution**: Either kill the existing process or use a different port:

```bash
# Kill the existing ShadowCypher instance
pkill -f "shadowcypher"
sleep 2
python3 -m shadowcypher.app

# Or use a different port
export SHADOW_PORT=9999
python3 -m shadowcypher.app
```

### Application crashes immediately after launch

**Symptoms**: App launches then exits without UI

**Diagnosis**: Check the log file:
```bash
tail -100 ~/.shadowcypher/logs/shadowcypher.jsonl | jq '.'
```

**Common causes & solutions**:

1. **Ollama not running**:
   ```bash
   # Check if Ollama is running
   curl -s http://localhost:11434/api/tags
   
   # If not, start it
   ollama serve
   
   # If not installed, install Ollama from https://ollama.ai
   ```

2. **Configuration error**:
   ```bash
   # Check for syntax errors in config.json
   python3 -m json.tool config.json
   
   # If corrupted, remove it (will regenerate on next launch)
   rm config.json
   ```

3. **Permission denied on log directory**:
   ```bash
   # Check directory permissions
   ls -la ~/.shadowcypher/logs/
   
   # Fix ownership
   sudo chown -R $USER:$USER ~/.shadowcypher/
   ```

4. **Stale Python cache**:
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
   find . -name "*.pyc" -delete
   python3 -m shadowcypher.app
   ```

### Window doesn't display or rendering issues

**Symptoms**: Window appears blank, buttons don't respond, or display glitches

**Diagnosis**:
```bash
export GTK_DEBUG=interactive
python3 -m shadowcypher.app
```

**Solution**:

**For Wayland systems**:
```bash
# Force X11
export GDK_BACKEND=x11
python3 -m shadowcypher.app
```

**For performance/rendering issues**:
```bash
# Disable hardware acceleration
export GDK_SCALE=1
export GDK_DPI_SCALE=1
python3 -m shadowcypher.app
```

**On WSL2**: Install an X11 server (VcXsrv, Xming) and set:
```bash
export DISPLAY=:0
python3 -m shadowcypher.app
```

---

## Ollama & AI Features

### Ollama connection refused

**Symptoms**: "Failed to connect to Ollama at http://localhost:11434"

**Diagnosis**:
```bash
# Check if Ollama is running
ps aux | grep ollama

# Try to reach it
curl -s http://localhost:11434/api/tags
```

**Solution**:

1. **Start Ollama**:
   ```bash
   ollama serve
   ```
   This will keep it running in the foreground. Optionally, install as a system service.

2. **If Ollama is not installed**:
   - Visit https://ollama.ai
   - Download and install for your platform
   - Start it

3. **If the API endpoint is different**:
   ```bash
   export OLLAMA_BASE_URL=http://your-ollama-host:11434
   python3 -m shadowcypher.app
   ```

### "Model not found" or "No models available"

**Symptoms**: Ollama is running but says "No models installed"

**Diagnosis**:
```bash
ollama list
```

**Solution**: Pull a model:
```bash
# Recommended models
ollama pull llama2       # 7B, ~4GB
ollama pull gemma        # 7B, ~5GB
ollama pull mistral      # 7B, ~5GB
ollama pull phi          # 2.7B, ~2GB (smallest)

# Verify
ollama list
```

The Ollama UI will update automatically once a model is available.

### AI inference is very slow

**Symptoms**: Responses take 30+ seconds or timeout

**Causes**:
- Using a large model (70B) without GPU support
- Insufficient VRAM
- CPU-only inference

**Solution**:

1. **Check if GPU is being used**:
   ```bash
   # NVIDIA
   nvidia-smi
   
   # AMD
   rocm-smi
   ```

2. **Use a smaller model**:
   ```bash
   ollama pull phi          # 2.7B (fastest)
   ollama pull gemma:7b     # 7B (good balance)
   ```

3. **Enable GPU in Ollama** (if you have NVIDIA/AMD GPU):
   ```bash
   # The installer should auto-detect, but verify:
   ollama show llama2 | grep gpu
   ```

4. **Reduce token limits in config.json**:
   ```json
   {
     "ai": {
       "max_tokens": 512,
       "temperature": 0.5
     }
   }
   ```

### Token limit exceeded errors

**Symptoms**: "Input tokens exceed maximum context length" or "truncated response"

**Solution**: 

1. **Increase token limit if your model supports it**:
   ```json
   {
     "ai": {
       "max_tokens": 4096,
       "max_context": 8192
     }
   }
   ```

2. **Or use a smaller context window**:
   ```json
   {
     "ai": {
       "max_tokens": 1024
     }
   }
   ```

3. **Or use a larger model** that supports more context (e.g., Llama 3 70B)

---

## GTK & UI Issues

### "Cannot register existing type 'GdkPixbuf'" on launch

**Symptoms**: Crash during GTK initialization

**Diagnosis**: This is usually a GTK versioning issue.

**Solution**:
```bash
# Reinstall GTK cleanly
sudo apt remove python3-gi gir1.2-gtk-3.0 --auto-remove
sudo apt update
sudo apt install python3-gi gir1.2-gtk-3.0

# On macOS:
brew uninstall --force gtk+3
brew install gtk+3
pip install --force-reinstall pycairo pygobject
```

### Buttons/text are too small or too large

**Symptoms**: UI scaling is off, text is hard to read

**Solution**:
```bash
# Adjust UI scale
export GDK_SCALE=2         # Make everything 2x larger
export GDK_DPI_SCALE=1.5   # Adjust DPI scaling

python3 -m shadowcypher.app
```

Or set in config.json:
```json
{
  "ui": {
    "dpi_scale": 1.5,
    "font_size": 12
  }
}
```

### App is very responsive but uses high CPU

**Symptoms**: Fan running, high CPU usage even when idle

**Solution**:

1. **Check what's consuming CPU**:
   ```bash
   top -p $(pgrep -f "shadowcypher.app")
   ```

2. **Common culprits**:
   - Ollama running in background → reduce inference frequency
   - Sisyphus (file integrity checker) running too frequently
   - AutoScan still running → stop it in the UI

3. **Reduce scan refresh rate**:
   ```json
   {
     "ui": {
       "refresh_interval_ms": 3000
     }
   }
   ```

---

## Network & Relay

### Go relay won't start or crashes

**Symptoms**: "Failed to start relay" or "Connection refused"

**Diagnosis**:
```bash
# Check if relay is running
ps aux | grep relay

# Check relay logs
tail -f ~/.shadowcypher/logs/relay.log

# Try starting manually
cd shadowcypher/native/relay && go run main.go
```

**Solution**:

1. **Recompile the relay**:
   ```bash
   cd shadowcypher/native/relay
   go build -o relay main.go
   cd ../../..
   ```

2. **Check for port conflicts**:
   ```bash
   lsof -i :9999  # Default relay port
   ```

3. **Verify Go installation**:
   ```bash
   go version
   go env GOPATH
   ```

### WebSocket connection drops frequently

**Symptoms**: "WebSocket connection lost" warnings, intermittent disconnects

**Diagnosis**:
```bash
# Check network connectivity
ping -c 5 127.0.0.1

# Check for firewall rules
sudo iptables -L -n | grep 999
```

**Solution**:

1. **Increase WebSocket timeout** in config.json:
   ```json
   {
     "relay": {
       "ws_timeout_seconds": 30,
       "reconnect_interval_ms": 1000
     }
   }
   ```

2. **Check firewall**:
   ```bash
   # Ubuntu/Debian
   sudo ufw status
   sudo ufw allow 9999/tcp
   ```

3. **Restart the relay**:
   ```bash
   pkill -f relay
   sleep 2
   python3 -m shadowcypher.app
   ```

### Sovereign Chat won't connect

**Symptoms**: "Failed to connect to chat server" or "Authentication failed"

**Diagnosis**:
```bash
# Check if chat service is running
curl -s http://localhost:8888/api/chat/status

# Check chat logs
tail -f ~/.shadowcypher/logs/sovereign_chat.log
```

**Solution**:

1. **Verify config**:
   ```bash
   # Check config.json has correct chat settings
   cat config.json | jq '.chat'
   ```

2. **Generate new authentication keys**:
   ```bash
   python3 -c "from shadowcypher.core.sovereign_chat import generate_keys; generate_keys()"
   ```

3. **Reset chat database** (data will be lost):
   ```bash
   rm ~/.shadowcypher/sovereign_chat.db
   python3 -m shadowcypher.app
   ```

---

## Scanning & Performance

### Nmap not found or scan fails

**Symptoms**: "nmap: command not found" or "Nmap scan failed"

**Diagnosis**:
```bash
which nmap
nmap --version
```

**Solution**:

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install nmap

# macOS
brew install nmap

# Fedora/RHEL
sudo dnf install nmap

# Verify
nmap --version
```

If nmap is installed but not found, check config.json:
```json
{
  "tools": {
    "nmap_path": "/usr/bin/nmap"
  }
}
```

### Nuclei templates not updating

**Symptoms**: "Nuclei template cache outdated" or very slow template loading

**Solution**:

```bash
# Force update templates
nuclei -update-templates

# Or manually:
rm -rf ~/.nuclei-cache/
nuclei -list-templates

# If nuclei not installed:
GO111MODULE=on go get -u -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei
```

### SQLmap hangs or times out

**Symptoms**: SQLmap scan never completes or hangs indefinitely

**Solution**:

1. **Set a timeout**:
   ```json
   {
     "tools": {
       "sqlmap": {
         "timeout_seconds": 60
       }
     }
   }
   ```

2. **Use less aggressive payloads**:
   ```json
   {
     "tools": {
       "sqlmap": {
         "risk": 1,
         "level": 1
       }
     }
   }
   ```

3. **Or abort the current scan** in the UI and try a different target

### AutoScan is extremely slow

**Symptoms**: AutoScan takes 20+ minutes for a simple target

**Diagnosis**:
```bash
# Check what's running
ps aux | grep -E 'nmap|nuclei|sqlmap|nikto'

# Check CPU/disk usage
top
iostat -x 1
```

**Solution**:

1. **Use quick-scan instead**:
   ```bash
   shadow-cli -p "quick scan 192.168.1.1"
   ```

2. **Limit scope**:
   ```bash
   shadow-cli -p "scan 192.168.1.100 --ports 22,80,443"
   ```

3. **Skip expensive scans**:
   ```json
   {
     "scanning": {
       "skip_sqlmap": true,
       "skip_web_scanning": false,
       "nuclei_timeout": 30
     }
   }
   ```

4. **Increase disk I/O if bottlenecked**:
   - Move temp directory to SSD
   - Check for other high-I/O processes

### "Permission denied" during scan

**Symptoms**: "Port scanning requires elevated privileges" or "Operation not permitted"

**Diagnosis**:
```bash
whoami
id -u
```

**Solution**:

Some scans (raw socket operations, low-level port scans) require root:

```bash
# Run with sudo
sudo python3 -m shadowcypher.app

# Or use passwordless sudo for specific tools
sudo visudo
# Add: your_user ALL=(ALL) NOPASSWD: /usr/bin/nmap, /usr/bin/nuclei
```

---

## Encryption & Security

### Citadel vault won't unlock

**Symptoms**: "Incorrect passphrase" or "Decryption failed"

**Solution**:

1. **Verify the passphrase**:
   - Check for extra spaces, capitalization, non-ASCII characters
   - Try a backup passphrase if you have one

2. **If you forgot the passphrase**:
   ```bash
   # The vault is encrypted with PBKDF2 + AES-256-GCM
   # There is no recovery method — you will lose access to the vault
   
   # Option: Reset it (data will be lost)
   rm ~/.shadowcypher/citadel.vault
   python3 -m shadowcypher.app
   ```

### Sovereign Chat messages won't decrypt

**Symptoms**: "Failed to decrypt message" or garbled output

**Cause**: Session key corruption or key mismatch

**Solution**:

1. **Restart the chat service**:
   ```bash
   python3 -m shadowcypher.app
   # Then reconnect in the UI
   ```

2. **If that doesn't work, reset the chat database**:
   ```bash
   rm ~/.shadowcypher/sovereign_chat.db
   python3 -m shadowcypher.app
   ```
   (Messages will be lost.)

### Hardware fingerprint binding errors

**Symptoms**: "Hardware fingerprint mismatch" or "Citadel locked to different hardware"

**Cause**: You've moved the installation to a different machine or changed hardware

**Solution**:

1. **Re-bind to current hardware**:
   ```bash
   python3 -c "from shadowcypher.core.citadel import rebind_hardware_fingerprint; rebind_hardware_fingerprint()"
   ```

2. **Or disable hardware binding** (less secure):
   ```json
   {
     "citadel": {
       "require_hardware_fingerprint": false
     }
   }
   ```

---

## Log Interpretation

### Where are logs stored?

```bash
~/.shadowcypher/logs/
├── shadowcypher.jsonl     # Main application log
├── relay.log              # Go relay logs
├── threat_intel.log       # Threat intelligence module
├── scans/                 # Individual scan logs
│   ├── nmap_*.log
│   ├── nuclei_*.log
│   └── sqlmap_*.log
```

### How to read the main log

```bash
# View recent errors
cat ~/.shadowcypher/logs/shadowcypher.jsonl | jq 'select(.level=="ERROR")' -c

# View specific module logs
cat ~/.shadowcypher/logs/shadowcypher.jsonl | jq 'select(.module=="auto_scan")' -c

# Filter by timestamp
cat ~/.shadowcypher/logs/shadowcypher.jsonl | jq 'select(.timestamp > "2024-01-15T10:00:00")' -c

# Pretty-print last 20 lines
tail -20 ~/.shadowcypher/logs/shadowcypher.jsonl | jq '.'
```

### Common error messages

| Message | Cause | Fix |
|---|---|---|
| `module_not_found: 'ollama'` | Ollama not running | Start Ollama with `ollama serve` |
| `permission_denied: nmap` | Insufficient privileges | Run with `sudo` or set passwordless sudo |
| `connection_refused: relay` | Go relay crashed | `pkill -f relay && python3 -m shadowcypher.app` |
| `timeout: threat_intel` | Network/API timeout | Check network, retry later, or increase timeout in config |
| `invalid_configuration: missing X` | Config error | Check `config.json` syntax with `python3 -m json.tool config.json` |

---

## Platform-Specific

### Linux (Ubuntu/Debian)

**Issue: Missing GTK dependencies after install**

```bash
sudo apt install libgtk-3-dev libgirepository1.0-dev libcairo2-dev
pip install pycairo pygobject
```

**Issue: Systemd permission denied**

```bash
# If you see "Failed to execute: /usr/bin/systemctl"
# Just use the GUI instead, or run with sudo
```

### macOS

**Issue: M1/M2 compatibility**

```bash
# Ensure you're using the arm64 Python
python3 -c "import platform; print(platform.machine())"

# If x86_64, install arm64 Python from https://www.python.org or brew
```

**Issue: "Gdk-Message: 18:00:00.000: Error initializing Cairo"**

```bash
# Reinstall with Homebrew's tools
brew install cairo
pip install --force-reinstall pycairo pygobject gtk-osxapplication
```

### Windows/WSL2

**Issue: Display server not available**

```bash
# Install VcXsrv (https://sourceforge.net/projects/vcxsrv/) or Xming
# Start it, then in WSL:
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
python3 -m shadowcypher.app
```

**Issue: Very slow performance on WSL2**

```bash
# Use WSL2 with GPU passthrough (if you have NVIDIA)
# Or use the native Linux environment if possible

# Increase WSL2 memory allocation in .wslconfig
# [wsl2]
# memory=8GB
# processors=4
```

---

## When to Seek Help

### Diagnostic checklist before contacting support

1. Run the diagnostic script:
   ```bash
   ./troubleshoot.sh | tee diagnostic_report.txt
   ```

2. Collect logs:
   ```bash
   tar -czf shadowcypher_logs.tar.gz ~/.shadowcypher/logs/
   ```

3. Check system info:
   ```bash
   uname -a
   python3 --version
   go version
   lsb_release -a  # Linux only
   ```

### How to report a bug

1. **Title**: Concise description (e.g., "AutoScan crashes with SQLite error")
2. **Environment**:
   - OS and version
   - Python version
   - ShadowCypher version
   - Go version
3. **Steps to reproduce**: Exact steps that trigger the issue
4. **Expected behavior**: What should happen
5. **Actual behavior**: What actually happens
6. **Logs**: Output of `./troubleshoot.sh` and relevant log excerpts
7. **Screenshots**: If UI-related

### Where to get help

- **GitHub Issues**: https://github.com/jakes1345/ShadowCypher/issues
- **GitHub Discussions**: https://github.com/jakes1345/ShadowCypher/discussions
- **Email**: support@shadowcypher.site
- **Security issues**: security@shadowcypher.site (do not file as public issues)

### Response time

- **Critical bugs** (crashes, data loss): 24–48 hours
- **High priority** (features broken): 3–5 days
- **Normal**: 1–2 weeks
- **Documentation/enhancements**: As time permits

---

**Last updated**: January 2025
