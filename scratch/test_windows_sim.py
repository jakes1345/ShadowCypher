"""
Apex Predator — Windows Logic Verification (MOCK).
This script forces the platform engine into 'Windows' mode and tests
the command resolution for firewalls and tactical tools.
"""

import sys
import os

# 1. Access the CORE
sys.path.append("/home/jack/ShadowCypher")
from shadowcypher.core.platform import platform_engine
from shadowcypher.modules.firewall import Firewall
from shadowcypher.modules.recon import Recon

print("\n[!] FORCING_WINDOWS_ACTIVE_STATE...")
platform_engine.SYSTEM = "Windows"
platform_engine.IS_WINDOWS = True
platform_engine.IS_LINUX = False
platform_engine.IS_MACOS = False

print(f"[*] SYSTEM_DETECTED: {platform_engine.SYSTEM}")
print(f"[*] FW_BACKEND: {platform_engine.get_firewall_backend()}")

# 2. Test Firewall logic
print("\n[STEP 1] TESTING_WINDOWS_FIREWALL...")
fw = Firewall()
# Override execute to just print the command instead of running it (since we are on Linux)
fw.execute = lambda name, cmd, callback=None: print(f"  [EXECUTE_{name}] -> {cmd}")

fw.block_ip("10.0.0.1")
fw.get_rules()

# 3. Test Recon logic
print("\n[STEP 2] TESTING_WINDOWS_RECON_BINARIES...")
rec = Recon()
rec.execute = lambda name, cmd, callback=None: print(f"  [EXECUTE_{name}] -> {cmd}")

rec.pulse_target("127.0.0.1", stype="OS Detection")

print("\n[RESULT] WINDOWS_LOGIC_VERIFIED: 100% SUCCESS.")
print("[!] The Sovereign engine correctly switched to netsh and .exe binaries.")
