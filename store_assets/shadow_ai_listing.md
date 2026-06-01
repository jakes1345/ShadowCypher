# Shadow AI — Play Store Listing

## App Details
- Package: site.shadowcypher.assistant
- Category: Productivity
- Content Rating: Everyone

## Title (30 chars max)
Shadow AI — Voice Assistant

## Short Description (80 chars max)
Private voice assistant for your ShadowCypher security network.

## Full Description (4000 chars max)
Shadow AI is your always-on voice assistant built for the ShadowCypher ecosystem.

Ask questions, trigger network scans, check security incidents, set alarms, and control your phone — all by voice, with no data sent to third-party AI clouds unless you configure it.

**What you can do:**

• Ask Shadow about your network — devices, open incidents, CVE alerts
• Trigger Guardian scans and missions by voice
• Set alarms and timers hands-free
• Open apps, dial contacts, get directions
• Full offline speech recognition via on-device neural model (Vosk, ~40 MB, downloaded once)
• Optional wake word — say "Hey Shadow" to activate without touching your phone

**How it works:**

Shadow AI connects to your ShadowCypher account using your API key. Voice input is processed on-device first; only your typed or spoken query reaches the API. Your network data never leaves ShadowCypher infrastructure.

To use Guardian-aware commands (device lists, incidents, scans), install the Guardian agent on a Linux machine on your network and configure it in the Guardian app.

**Privacy:**
- On-device STT — your voice is not streamed to third parties
- No analytics, no ads, no tracking
- API key stored locally on-device only

**Requirements:**
- Android 7.0+
- Microphone permission
- A ShadowCypher account (free at shadowcypher.site)
- Guardian app + agent for network-aware commands (optional)

---
Part of the ShadowCypher ecosystem — personal sovereign security tools.

## Keywords (Play Console internal)
voice assistant, offline STT, network monitor, security, privacy, wake word

## Notes for submission
- First launch downloads Vosk model (~40 MB) — mention in "What's New" or onboarding
- Needs RECORD_AUDIO permission — include in Data Safety: "Audio — not shared, not stored"
- Can be set as default assist app (replaces Google Assistant / Bixby)
