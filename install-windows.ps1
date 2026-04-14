# ShadowCypher — Windows installer (PowerShell)
# Run from elevated PowerShell: .\install-windows.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> ShadowCypher Windows bootstrap" -ForegroundColor Cyan

# Require Python 3.12+
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python 3.12+ required. Install from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# GTK3 for Windows: easiest path is MSYS2 OR the PyGObject wheels from tschoonj
Write-Host "==> Installing PyGObject + pycairo wheels" -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: pycairo PyGObject

Write-Host "==> Installing ShadowCypher Python requirements" -ForegroundColor Cyan
python -m pip install -r requirements.txt

Write-Host ""
Write-Host "NOTE: Most offensive modules (nmap, aircrack, iptables) require" -ForegroundColor Yellow
Write-Host "      WSL2 + Kali for full functionality on Windows." -ForegroundColor Yellow
Write-Host ""
Write-Host "==> First-run will prompt for your handle on launch." -ForegroundColor Green
Write-Host "    Run: python -m shadowcypher.app" -ForegroundColor Green
