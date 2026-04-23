# ==============================================================================
# SHADOWCYPHER // WINDOWS SETUP ORCHESTRATOR (PowerShell)
# ==============================================================================
# Automates the deployment and cryptographic arming of the ShadowCypher suite
# for Windows-based tactical workstations.

Write-Host "[*] Initializing ShadowCypher Deployment for Windows..." -ForegroundColor Cyan

# 1. Directory Hardening
$Dirs = @("logs", "findings", "payloads\ghost", "reports")
foreach ($Dir in $Dirs) {
    if (!(Test-Path $Dir)) {
        New-Item -ItemType Directory -Path $Dir | Out-Null
        Write-Host "[OK] Created directory: $Dir" -ForegroundColor Green
    }
}

# 2. Cryptographic Arming
$KeyDir = "C:\ProgramData\ShadowCypher"
$KeyFile = "$KeyDir\master.key"

if (!(Test-Path $KeyFile)) {
    Write-Host "[*] Generating Master Cryptographic Key..." -ForegroundColor Yellow
    if (!(Test-Path $KeyDir)) {
        New-Item -ItemType Directory -Path $KeyDir | Out-Null
    }
    
    $Bytes = New-Object Byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($Bytes)
    [System.IO.File]::WriteAllBytes($KeyFile, $Bytes)
    
    Write-Host "[OK] Master Key Forge: SUCCESS ($KeyFile)" -ForegroundColor Green
} else {
    Write-Host "[OK] Master Key detected: NOMINAL" -ForegroundColor Green
}

# 3. Environment Check
Write-Host "[*] Checking Python and Go environment..." -ForegroundColor Cyan
python --version
go version

Write-Host "`n[!] SHADOWCYPHER IS ARMED AND READY FOR WINDOWS OPERATION." -ForegroundColor Green
Write-Host "[*] Run 'python -m shadowcypher.app' to ignite the Citadel."
