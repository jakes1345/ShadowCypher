import sys
import os
from shadowcypher.core.forensics import registry
from shadowcypher.core.irc_bot import cmd_unmask

# Mock reply function
def mock_reply(text):
    print(f"[BOT_REPLY] {text}")

print("[*] Testing Unmask Command Dispatch...")

# 1. Register a dummy threat
target_nick = "Suspect_01"
registry.register_threat({
    "handle": target_nick,
    "hostmask": "192.168.1.50",
    "hw_mac": "DE:AD:BE:EF:CA:FE",
    "risk_level": "CRITICAL"
})

# 2. Simulate !unmask command
print(f"[*] Simulating: !unmask {target_nick}")
cmd_unmask(nick="Operator", target="#sha", args=target_nick, reply=mock_reply, admin=True)

print("[*] Bot Logic Test Complete.")
