# ShadowCypher Guardian Agent — Windows installer
# Usage (run in PowerShell as your normal user, no admin required for user-scope install):
#   iwr https://shadowcypher.site/agent/install.ps1 | iex
# Or save locally and run:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\install.ps1
#Requires -Version 5.1

$ErrorActionPreference = "Stop"

$CYAN  = [char]27 + "[96m"
$BOLD  = [char]27 + "[1m"
$DIM   = [char]27 + "[2m"
$RESET = [char]27 + "[0m"

$INSTALL_DIR      = Join-Path $env:LOCALAPPDATA "shadowcypher-agent"
$GITHUB_REPO      = "jakes1345/ShadowCypher"
$AGENT_FALLBACK   = "https://shadowcypher.site/agent/shadowcypher_agent.py"

Write-Host ""
Write-Host "${CYAN}${BOLD}ShadowCypher Guardian Agent${RESET}"
Write-Host "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
Write-Host ""

# ── 1. Python check ───────────────────────────────────────────────────────────
$python = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]; $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 9) { $python = $candidate; break }
        }
    } catch {}
}

if (-not $python) {
    Write-Host "[!] Python 3.9+ not found."
    Write-Host "    Download from https://python.org/downloads/"
    Write-Host "    Make sure to tick 'Add Python to PATH' during install."
    Write-Host ""
    Write-Host "    Or install via winget:"
    Write-Host "      winget install Python.Python.3.12"
    exit 1
}
Write-Host "  Python:  $(& $python --version)"

# ── 2. Download agent ─────────────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null

$agentUrl = $null
Write-Host "[*] Looking up latest release..."
try {
    $releases = Invoke-RestMethod "https://api.github.com/repos/$GITHUB_REPO/releases" `
        -Headers @{ Accept = "application/vnd.github+json" } -TimeoutSec 10
    foreach ($r in $releases) {
        if ($r.tag_name -like "agent-v*" -and -not $r.prerelease -and -not $r.draft) {
            foreach ($a in $r.assets) {
                if ($a.name -eq "shadowcypher_agent.py") {
                    $agentUrl = $a.browser_download_url
                    break
                }
            }
            if ($agentUrl) { break }
        }
    }
} catch {
    Write-Host "[*] GitHub lookup failed — using fallback"
}

if (-not $agentUrl) {
    Write-Host "[*] No release found — downloading from shadowcypher.site"
    $agentUrl = $AGENT_FALLBACK
} else {
    Write-Host "[*] Found release: $agentUrl"
}

$agentFile = Join-Path $INSTALL_DIR "shadowcypher_agent.py"
Write-Host "[*] Downloading agent to $agentFile..."
Invoke-WebRequest $agentUrl -OutFile $agentFile

# ── 3. Create venv and install deps ──────────────────────────────────────────
Write-Host "[*] Setting up Python environment..."
& $python -m venv (Join-Path $INSTALL_DIR ".venv")
$pip = Join-Path $INSTALL_DIR ".venv\Scripts\pip.exe"
& $pip install --quiet --upgrade pip
& $pip install --quiet requests

# ── 4. Write wrapper batch file ───────────────────────────────────────────────
$venvPython = Join-Path $INSTALL_DIR ".venv\Scripts\python.exe"
$wrapperBat = Join-Path $INSTALL_DIR "shadow-agent.cmd"
Set-Content $wrapperBat "@echo off`r`n`"$venvPython`" `"$agentFile`" %*"

# Add install dir to user PATH if needed
$userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$INSTALL_DIR*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "$INSTALL_DIR;$userPath", "User")
    Write-Host "[*] Added $INSTALL_DIR to your user PATH (restart terminal to take effect)"
}

# ── 5. Configure ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "${CYAN}${BOLD}Configuration${RESET}"
Write-Host "${DIM}Get your API key at: https://shadowcypher.site → Account → API Key${RESET}"
Write-Host ""
& $venvPython $agentFile init

# ── 6. Install scheduled task (persistent daemon) ────────────────────────────
Write-Host ""
Write-Host "[*] Installing Guardian as a Windows Scheduled Task..."
& $venvPython $agentFile install-service

# ── 7. Done ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "${CYAN}${BOLD}Guardian Agent installed${RESET}"
Write-Host ""
Write-Host "  Commands (restart terminal first so PATH is live):"
Write-Host "    shadow-agent status            # check daemon status"
Write-Host "    shadow-agent update            # check for and apply updates"
Write-Host "    shadow-agent once              # run a single scan"
Write-Host "    shadow-agent uninstall-service # remove scheduled task"
Write-Host ""
Write-Host "${DIM}  Agent files: $INSTALL_DIR${RESET}"
Write-Host ""
