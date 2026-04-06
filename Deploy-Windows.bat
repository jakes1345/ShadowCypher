@echo off
TITLE ShadowCypher OMNI-Build Deployment Engine
color 0B

echo ===================================================
echo    S H A D O W C Y P H E R   [ W S L 2   P U L S E ]
echo ===================================================
echo [+] Initializing Windows-to-Linux deployment vector...
echo.

:: Check if WSL is present
wsl --status >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [!] ERROR: Windows Subsystem for Linux (WSL) is not enabled.
    echo [*] Attempting to install WSL (Ubuntu)...
    echo [*] Please accept any Administrator prompts.
    wsl --install -d Ubuntu
    echo.
    echo [!] SYSTEM REBOOT REQUIRED.
    echo [!] After reboot, allow Ubuntu to set up its username/password, 
    echo [!] then run this script again.
    pause
    exit
)

echo [+] Deep-Linking into Linux Subsystem...
echo [+] Synchronizing Cyber-Arsenal dependencies (This may take a moment)...
echo.

:: Launch WSL, install prerequisites, clone/update repo, and launch the GTK UI
wsl -d Ubuntu -e bash -c "echo '[SYSTEM] Updating Linux Subsystem...'; sudo apt-get update; echo '[SYSTEM] Installing Base GTK and Penetration Tools...'; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-pip nmap tshark tcpdump aircrack-ng john hydra binwalk exiftool python3-venv; echo '[SYSTEM] Verifying ShadowCypher Repository...'; if [ ! -d ~/ShadowCypher ]; then git clone https://github.com/jakes1345/ShadowCypher.git ~/ShadowCypher; fi; cd ~/ShadowCypher && git config pull.rebase false && git pull; echo '[SYSTEM] Engaging Python Virtual Environment...'; python3 -m venv venv; source venv/bin/activate; pip install -r requirements.txt; echo '[SYSTEM] LAUNCHING OBSIDIAN HUD...'; python3 -m shadowcypher.app"

echo.
echo [SYSTEM] Operation Concluded. See you in the void.
pause
