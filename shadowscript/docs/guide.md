# ── THE SHADOWSCRIPT BIBLE (v1.1-GAMMA) ──

ShadowScript is an Omni-Paradigm Programming Language designed for **Sovereign Tactical Operations.** It combines the memory safety of Python with the raw power of HolyC and the logic of Lisp.

## 1. TACTICAL DIRECTIVES

### `TARGET(addr)`
Locks the Mission Kernel onto a specific coordinate (IP/Domain).
```shadow
TARGET("GATEWAY_IP")
```

### `SWARM()`
Initializes a decentralized P2P peer-discovery loop via the Go Relay. Ensures your node is visible to the Citadel.

### `AI(intent)`
Triggers a **Neural Link** call to the Shadow-AI brain. Results are returned as an industrial-grade intelligence summary.
```shadow
VAR report = AI("Identify vulnerable services on current target")
```

### `UNSAFE { ... }`
Enters **Memory Sovereignty** mode. Allows for raw pointer manipulation and direct kernel syscalls in a HolyC-style block.

### `!syscall(args)`
Executes a native Linux/Windows/macOS system call via the Apex Platform Engine.

## 2. TYPES & REGISTERS
- **U64 / U32 / U8**: Fixed-width unsigned integers for memory strikes.
- **RAX - RIP**: Virtual registers for the internal shadow-stack.

## 3. MISSION EXAMPLES

## 4. GHOST-SIGNAL PROTOCOLS (Tier-5 Invisibility)

### Phantom-MAC (Hardware Masking)
Always run `scripts/phantom_mac.sh` before connecting. This randomizes your NIC identifier, making your device appear as a new, anonymous piece of hardware to the ISP_INFRASTRUCTURE gateway.

### DNS Blackout (Spectrum Isolation)
Run `scripts/dns_blackout.sh` to kill Port 53 clear-text leaks. All queries move through ShadowCypher's encrypted tunnel, invisible to ISP-level Deep Packet Inspection.

### Obfuscation & Chaff
The Shadow-Relay natively injects **Chaff** (random noise packets) and **Jitter** (timing variance) into your stream. This prevents traffic correlation attacks from identifying what you are doing.

## 5. PHYSICAL SPECTRUM SILENCE (Critical)

To be truly untraceable by State-level actors (CIA/NSA):
1.  **Device Correlation**: Disable all Bluetooth and Wi-Fi on your mobile devices within a 50ft radius of your tactical station. 
2.  **Faraday Isolation**: Keep mobile devices in a physical Faraday bag during high-stakes missions.
3.  **SON Disablement**: Ensure 'Self-Organizing Network' is **OFF** in the ISP_INFRASTRUCTURE (GATEWAY_IP) Advanced Settings to prevent the router from "steering" your device onto observable frequencies.

**THE CITADEL HAS NO DOORS. ONLY SHADOWS.**

## 🧬 2. DATA TYPES
We bypass the standard "integers" and "booleans" for HolyC-style native types:
- `U8`: 8-bit unsigned (perfect for shellcode/bytes).
- `U32`: 32-bit unsigned.
- `U64`: 64-bit unsigned (the standard for memory addresses).
- `VAR`: Auto-typed tactical variable.

## ⚔️ 3. TACTICAL KEYWORDS
- `TARGET("...")`: Sets the primary objective for the mission.
- `STRIKE(payload)`: Executes an offensive module against the target.
- `SWARM { ... }`: Synchronizes the task across all decentralized nodes.
- `AI("...")`: Synthesizes logic through the Shadow-AI brain.
- `UNSAFE { ... }`: Opens the gateway to raw memory manipulation.

## 🏴‍☠️ 4. OMNI-BLOCKS
ShadowScript understands other languages.
- **HolyC**: Use `U64` and `unsafe` to talk to the kernel.
- **Assembly**: Use `REG_RAX`, `REG_RSP` inside unsafe blocks.
- **Bash**: Use `!sys` for immediate system commands.

## 🚀 5. EXAMPLE MISSION
```shadow
# My First Independent Strike
TARGET("10.0.0.5")
U64 buffer = 0x7FFF1234
UNSAFE()
STRIKE(buffer, "overflow_v1")
AI("Check if target is still alive")
!sys("echo Mission Complete")
```

---
*Developed for the Shadows. Sovereign in the Light.*
