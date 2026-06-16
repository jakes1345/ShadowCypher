"""
Shadow AI training dataset builder.

Pulls real open-source cybersecurity datasets from HuggingFace,
voice-formats responses, merges with ShadowCypher-specific examples,
and outputs a JSONL ready for Unsloth/TRL fine-tuning.

Datasets used:
  - AlicanKiraz0/Cybersecurity-Dataset-Fenrir-v2.1  (99,870 rows, Apache-2.0)
  - trendmicro-ailab/Primus-Instruct               (expert-curated, MIT)

Usage:
  pip install datasets
  python build_dataset.py
  # Outputs: shadow_train.jsonl (~5-10K filtered rows)
"""

import json
import re
import random
from pathlib import Path

SYSTEM_PROMPT = (
    "You are Shadow, ShadowCypher's voice assistant. "
    "Answer in 1-3 sentences. No markdown, no bullet points — "
    "respond naturally as if speaking aloud. "
    "Reference Guardian security data when available."
)

def strip_markdown(text: str) -> str:
    """Convert markdown to plain spoken text."""
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\n{2,}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate_to_sentences(text: str, max_sentences: int = 3) -> str:
    """Keep first N sentences for voice-length responses."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return " ".join(sentences[:max_sentences]).strip()


def is_voice_safe(text: str) -> bool:
    """Reject responses that are inherently list/code-heavy."""
    if text.count("\n") > 4:
        return False
    if text.count("```") > 0:
        return False
    if len(text) < 20 or len(text) > 800:
        return False
    return True


def format_example(system: str, user: str, assistant: str) -> dict:
    return {
        "conversations": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


def load_fenrir(max_rows: int = 6000) -> list[dict]:
    """Pull Fenrir v2.1 — 99K cybersecurity SFT triples."""
    try:
        from datasets import load_dataset
        ds = load_dataset("AlicanKiraz0/Cybersecurity-Dataset-Fenrir-v2.1", split="train")  # nosec B615
        print(f"[Fenrir] Loaded {len(ds)} rows")
    except Exception as e:
        print(f"[Fenrir] Load failed: {e}. Run: pip install datasets")
        return []

    out = []
    for row in ds:
        user = (row.get("user") or row.get("instruction") or row.get("input") or "").strip()
        assistant = (row.get("assistant") or row.get("output") or row.get("response") or "").strip()

        if not user or not assistant:
            continue

        # Voice-format the response
        assistant = strip_markdown(assistant)
        assistant = truncate_to_sentences(assistant, max_sentences=3)

        if not is_voice_safe(assistant):
            continue

        out.append(format_example(SYSTEM_PROMPT, user, assistant))
        if len(out) >= max_rows:
            break

    print(f"[Fenrir] Kept {len(out)} voice-formatted rows")
    return out


def load_primus_instruct(max_rows: int = 2000) -> list[dict]:
    """Pull Primus-Instruct — Trend Micro expert-curated cybersecurity Q&A."""
    try:
        from datasets import load_dataset
        ds = load_dataset("trendmicro-ailab/Primus-Instruct", split="train")  # nosec B615
        print(f"[Primus] Loaded {len(ds)} rows")
    except Exception as e:
        print(f"[Primus] Load failed: {e}")
        return []

    out = []
    for row in ds:
        user = (row.get("instruction") or row.get("input") or row.get("prompt") or "").strip()
        assistant = (row.get("output") or row.get("response") or row.get("completion") or "").strip()

        if not user or not assistant:
            continue

        assistant = strip_markdown(assistant)
        assistant = truncate_to_sentences(assistant, max_sentences=3)

        if not is_voice_safe(assistant):
            continue

        out.append(format_example(SYSTEM_PROMPT, user, assistant))
        if len(out) >= max_rows:
            break

    print(f"[Primus] Kept {len(out)} voice-formatted rows")
    return out


def shadowcypher_specific() -> list[dict]:
    """
    ShadowCypher app-specific training examples.
    These teach Shadow its own context: Guardian, ShadowScript, plans, etc.
    Real data — no placeholders.
    """
    examples = [
        # Guardian / network monitoring
        ("How many devices are on my network?",
         "I can see your Guardian summary — check the dashboard for the exact device count, or ask me to pull a fresh network summary."),
        ("Is the Guardian agent online?",
         "Your Guardian agent status shows in the dashboard. If it's offline, check that the agent process is running and has outbound access to port 443."),
        ("Run a network scan.",
         "Starting a network scan now. Results will appear in your Guardian dashboard within a few minutes."),
        ("What devices did the last scan find?",
         "I'll pull the latest scan data from Guardian. The most recent scan shows your discovered devices — tap Devices in the app to see the full list."),
        ("Do I have any active incidents?",
         "Let me check your Guardian incidents. If there are active alerts, I'll tell you the severity and description right now."),
        ("What's my threat level?",
         "Your threat level is calculated from active incidents, CVE matches, and anomalous traffic detected by Guardian. Zero incidents means low threat."),
        ("Are any of my agents offline?",
         "Guardian reports agents as offline if they miss a heartbeat for 90 seconds. Check the Agents tab to see current online status."),
        ("When was my last network scan?",
         "I can see the last scan timestamp from your Guardian summary. Scans run automatically based on your agent's scan_interval setting, default every 5 minutes."),
        ("Show me my CVE alerts.",
         "Your CVE alerts are matched against discovered services on your network. I'll pull the count and most critical findings from Guardian now."),
        ("Acknowledge all incidents.",
         "I can't bulk-acknowledge from here, but you can mark incidents resolved in the Guardian dashboard under the Incidents tab."),

        # ShadowScript
        ("What ShadowScript commands can I use?",
         "ShadowScript supports net, sys, file, sec, and ghost commands. For example, net.scan runs a subnet sweep, sys.info shows OS details, and sec.log pulls recent auth events."),
        ("Run net.status on my desktop.",
         "Sending a net.status mission to your online agent now. Results will come back within 10 to 30 seconds depending on poll interval."),
        ("Check active connections on my server.",
         "I'll send net.connections via ShadowScript to your agent. This shows all active TCP and UDP connections currently established on that machine."),
        ("What's the difference between DSL and shell passthrough?",
         "DSL commands like net.scan map to safe predefined functions. Shell passthrough lets you run any shell command, but requires the Operator plan and every execution is audit-logged."),
        ("How do I send a ShadowScript mission?",
         "Open the Guardian app, go to Missions, tap the play button, pick your target agent, type your ShadowScript, and hit Submit. Results show up when the agent polls."),

        # Plans and account
        ("What plan am I on?",
         "Your current plan is visible in Account settings. Free gives you 5 scans per day, Pro is unlimited with CVE correlation, and Operator adds shell passthrough and webhooks."),
        ("Do I have Ghost Mode?",
         "Ghost Mode is available on the Pro and Operator plans. If you're on Free, you'd need to upgrade to access it."),
        ("How many AI queries do I have left this month?",
         "Your AI query usage is tracked monthly. Pro users get 50 queries, Operator gets 500. Check Account stats to see your current count."),
        ("What's included in the Operator plan?",
         "Operator includes everything in Pro plus ShadowScript shell passthrough, full API access, webhooks, custom threat rules, 3-year incident history, and dedicated support."),
        ("How do I upgrade my plan?",
         "Visit shadowcypher.site, go to Account, and tap Upgrade Plan. Plans are billed monthly and you can cancel anytime."),

        # Ghost Mode / anonymity
        ("Enable ghost mode.",
         "Ghost Mode is controlled from the ShadowCypher desktop app. Go to Guardian, then the Ghost Protocol tab to enable it."),
        ("Are you in ghost mode?",
         "Ghost mode status comes from your desktop Guardian agent. Check the Ghost Protocol tab in the desktop app for current Tor routing and MAC spoofing status."),
        ("What does ghost mode do?",
         "Ghost Mode routes all traffic through Tor, spoofs your MAC address, disables WebRTC to prevent IP leaks, and kills telemetry processes. It requires the Pro or Operator plan."),
        ("How do I check for DNS leaks?",
         "Use dnsleaktest.com or ipleak.net from a browser to verify your DNS queries aren't bypassing your Tor or VPN tunnel. Ghost Mode configures DNS over Tor automatically."),

        # Security knowledge (grounded in KB)
        ("What is a CVSS score?",
         "CVSS is the Common Vulnerability Scoring System, scored from 0 to 10. Scores above 9 are Critical, 7 to 9 are High, 4 to 7 are Medium, and below 4 are Low."),
        ("What's the difference between WPA2 and WPA3?",
         "WPA3 replaces the PSK handshake with SAE, which eliminates offline dictionary attacks possible against WPA2. WPA3 also mandates management frame protection against deauth attacks."),
        ("What is a PMKID attack?",
         "A PMKID attack lets you capture a single frame from the access point without waiting for a client to connect, then crack the WPA2 passphrase offline using hashcat."),
        ("What is AES-256-GCM?",
         "AES-256-GCM is authenticated encryption that simultaneously encrypts data and produces an integrity tag. It's the standard for secure symmetric encryption and is used in TLS 1.3 and WireGuard."),
        ("What is LockBit?",
         "LockBit is a ransomware-as-a-service operation. Affiliates gain access via RDP or phishing, move laterally with PsExec, steal data before encrypting, and extort victims with double extortion."),
        ("How does Tor work?",
         "Tor encrypts traffic in three layers and routes it through three relays: a guard node that knows your IP, a middle relay, and an exit node that knows only the destination."),
        ("What is MITRE ATT&CK?",
         "MITRE ATT&CK is a knowledge base of real attacker tactics and techniques. It covers 14 enterprise tactics from reconnaissance through impact, used for threat modeling and detection engineering."),
        ("What is pass-the-hash?",
         "Pass-the-hash lets an attacker authenticate using a stolen NTLM hash without knowing the plaintext password. It's detected in Windows Event ID 4648 and mitigated by disabling NTLM and using Kerberos."),
        ("What is a Golden Ticket attack?",
         "A Golden Ticket is a forged Kerberos TGT signed with the krbtgt account hash. An attacker with this can impersonate any user in the domain for the ticket lifetime, up to 10 years by default."),
        ("How do I respond to ransomware?",
         "Immediately isolate the infected host by disconnecting it from the network. Preserve memory and logs before wiping, rotate all credentials, identify the initial access vector, and restore from clean backups."),
        ("What is Cobalt Strike?",
         "Cobalt Strike is a commercial red team framework whose Beacon payload is widely abused by threat actors. It supports malleable C2 profiles that mimic legitimate traffic to evade detection."),
        ("What is a supply chain attack?",
         "A supply chain attack compromises software or hardware before it reaches the victim, like the SolarWinds SUNBURST malware inserted into a legitimate update, or the XZ Utils backdoor in 2024."),
        ("What ports should I block at my firewall?",
         "Block inbound RDP on 3389, SMB on 445, WinRM on 5985 and 5986, and Telnet on 23 unless explicitly needed. Allow only what's required and log everything denied."),
        ("What is ChaCha20-Poly1305?",
         "ChaCha20-Poly1305 is a stream cipher with an authentication tag, designed as a faster alternative to AES on devices without hardware AES acceleration. It's used in TLS 1.3, WireGuard, and Signal."),
        ("What is the CWE Top 25?",
         "The CWE Top 25 is MITRE's list of the most dangerous software weaknesses. Out-of-bounds write, cross-site scripting, and SQL injection consistently top the list each year."),
        ("What is OPSEC?",
         "Operational security means preventing adversaries from gathering intelligence about your activities. Key principles are compartmentalization, metadata removal, and never mixing real and anonymous identities."),

        # General assistant
        ("What time is it?",
         "I don't have direct access to your system clock, but your phone's status bar shows the current time."),
        ("What can you do?",
         "I can scan your network, check incidents and CVEs, look up CVE IDs, check IP reputation, run ShadowScript missions on your desktop, answer security questions, search the web, and check weather and currency rates."),
        ("Who made you?",
         "I'm Shadow, built by the ShadowCypher team. I run on your device with on-device knowledge and can connect to your Guardian security platform."),
        ("How do I set my API key?",
         "Tap the settings gear in the bottom left of the Shadow panel, enter your sc_live_ API key from shadowcypher.site, and tap Save and Connect."),
        ("What is ShadowCypher?",
         "ShadowCypher is a personal security platform. Guardian monitors your network from a desktop agent, and Shadow is the AI assistant that helps you understand and respond to what's found."),
    ]

    return [format_example(SYSTEM_PROMPT, u, a) for u, a in examples]


def main():
    out_path = Path(__file__).parent / "shadow_train.jsonl"

    print("Building Shadow AI training dataset...")
    fenrir = load_fenrir(max_rows=6000)
    primus = load_primus_instruct(max_rows=2000)
    app_specific = shadowcypher_specific()

    all_data = fenrir + primus + app_specific
    random.seed(42)
    random.shuffle(all_data)

    # Write JSONL
    with open(out_path, "w") as f:
        for ex in all_data:
            f.write(json.dumps(ex) + "\n")

    print(f"\nDataset written: {out_path}")
    print(f"  Total examples: {len(all_data)}")
    print(f"    Fenrir v2.1:    {len(fenrir)}")
    print(f"    Primus-Instruct: {len(primus)}")
    print(f"    ShadowCypher:   {len(app_specific)}")

    # Write eval split (last 5%)
    split = int(len(all_data) * 0.95)
    eval_path = Path(__file__).parent / "shadow_eval.jsonl"
    with open(eval_path, "w") as f:
        for ex in all_data[split:]:
            f.write(json.dumps(ex) + "\n")
    print(f"  Eval split:     {eval_path} ({len(all_data) - split} rows)")


if __name__ == "__main__":
    main()
