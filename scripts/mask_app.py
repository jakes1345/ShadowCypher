import os
import subprocess
import sys

# --- CONFIGURATION ---
APP_NAME = "ShadowCypher"
COMPANY_NAME = "Shadow Security Operations"
DESCRIPTION = "Tactical Security & OSINT Suite"
VERSION = "3.0.0"
ICON_PATH = "assets/dist/shadowcypher.ico"
ENTRY_POINT = "shadowcypher/app.py"

def create_windows_version_info():
    """Generates a version info file for PyInstaller to mask the executable."""
    content = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(3, 0, 0, 0),
    prodvers=(3, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', '{COMPANY_NAME}'),
        StringStruct('FileDescription', '{DESCRIPTION}'),
        StringStruct('FileVersion', '{VERSION}'),
        StringStruct('InternalName', '{APP_NAME}'),
        StringStruct('LegalCopyright', '© 2026 {COMPANY_NAME}. All rights reserved.'),
        StringStruct('OriginalFilename', '{APP_NAME}.exe'),
        StringStruct('ProductName', '{APP_NAME}'),
        StringStruct('ProductVersion', '{VERSION}')])
      ]), 
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    with open("assets/dist/version_info.txt", "w") as f:
        f.write(content.strip())
    print("[+] Created Windows Version Info for masking.")

def print_instructions():
    print("\n" + "="*60)
    print(" SHADOWCYPHER MASKING & BUNDLING ENGINE")
    print("="*60)
    print(f"\n[!] To mask the application and avoid basic AV flags, follow these steps:")
    print("\n1. ON WINDOWS (Native, not WSL):")
    print("   pip install pyinstaller")
    print(f"   pyinstaller --noconfirm --onefile --windowed --icon=\"{ICON_PATH}\" \\")
    print(f"               --name=\"{APP_NAME}\" --version-file=\"assets/dist/version_info.txt\" \\")
    print(f"               --add-data \"assets;assets\" --add-data \"native;native\" \\")
    print(f"               {ENTRY_POINT}")
    
    print("\n2. ON MACOS:")
    print("   pip install py2app")
    print("   # Use the provided icon at assets/dist/shadowcypher.icns")
    
    print("\n[!] ADVANCED MASKING TIPS:")
    print("    - AVOID UPX: Do not use --upx-dir. Packers are a major red flag for AVs.")
    print("    - NUITKA: Use 'nuitka' instead of PyInstaller for better 'stealth'.")
    print("      nuitka --standalone --show-progress --windows-disable-console \\")
    print("             --windows-icon-from-ico=assets/dist/shadowcypher.ico \\")
    print("             --plugin-enable=tk-inter --plugin-enable=numpy shadowcypher/app.py")
    print("    - CODE SIGNING: The only way to truly stop 'SmartScreen' flags is to sign")
    print("      your binary with a certificate (e.g., Sectigo, DigiCert).")
    print("="*60)

if __name__ == "__main__":
    if not os.path.exists("assets/dist"):
        os.makedirs("assets/dist")
    create_windows_version_info()
    print_instructions()
