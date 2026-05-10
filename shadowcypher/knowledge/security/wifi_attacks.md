# WiFi Security & Attacks Reference

## WiFi Security Standards

| Standard | Encryption | Key Exchange | Vulnerability |
|----------|-----------|--------------|---------------|
| WEP | RC4 | Shared key | Completely broken; IV reuse, FMS attack |
| WPA | TKIP | PSK / 802.1X | TKIP deprecated; Michael MIC attack |
| WPA2-Personal | AES-CCMP | PSK | PMKID attack, KRACK (patched), weak passphrase |
| WPA2-Enterprise | AES-CCMP | 802.1X/EAP | Evil twin, EAP downgrade |
| WPA3-Personal | AES-CCMP | SAE (Dragonfly) | Dragonblood (side-channel; patched) |
| WPA3-Enterprise | AES-GCMP-256 | 192-bit suite | Current best practice |

## Common WiFi Attacks

### PMKID Attack (WPA2)
- No need to capture full 4-way handshake
- PMKID derived from PMK, AP MAC, client MAC, SSID
- Request RSN IE from AP (single packet), extract PMKID
- Offline dictionary/brute force: `hcxdumptool` → `hashcat -m 22000`
- Mitigation: long random passphrase (20+ chars)

### 4-Way Handshake Capture
- Passive: wait for client to connect
- Active: send deauth frames to force reconnect
- `airodump-ng`, `hcxdumptool`
- Offline crack: `hashcat -m 22000` (WPA2), dictionary + rules
- Mitigation: passphrase length and randomness

### Evil Twin / Rogue AP
- Clone legitimate SSID + BSSID; higher power wins clients
- Captive portal: harvest credentials
- SSLstrip: downgrade HTTPS (defeated by HSTS preloading)
- WPA2-Enterprise evil twin: capture EAP credentials
- Tools: `hostapd-wpe`, `airbase-ng`, WiFi Pineapple
- Mitigation: 802.1X certificate pinning, validate server cert in supplicant

### Deauthentication / Disassociation Attack
- 802.11 management frames unencrypted in WPA2
- Spoofed deauth frames disconnect clients
- Enables handshake capture or DoS
- `aireplay-ng -0 10 -a [BSSID] -c [Client MAC] wlan0mon`
- Mitigation: 802.11w (Management Frame Protection) — mandatory in WPA3

### KRACK (Key Reinstallation Attack)
- CVE-2017-13077 through 13088
- Replay nonce in 4-way handshake → reinstall already-in-use key → nonce reuse → decrypt/inject
- All WPA2 clients were affected; patched by OS updates
- Mitigation: apply OS patches; use WPA3

### WPS PIN Attack
- 8-digit PIN = 10^4 + 10^4 combinations (left/right half checked independently)
- `reaver`, `bully` online bruteforce
- Offline: Pixie Dust attack against Ralink/Broadcom chipsets (~seconds)
- Mitigation: disable WPS entirely

### Karma Attack
- Fake AP responds to all Probe Request frames (client broadcasting preferred networks)
- Clients auto-connect to attacker's AP thinking it's a known network
- Mitigated by modern OS behavior (no longer auto-probe SSIDs without matching)
- Hotspot 2.0/Passpoint: credential-based authentication prevents karma

## Wireless Reconnaissance

```bash
# Put interface in monitor mode
ip link set wlan0 down
iw wlan0 set monitor none
ip link set wlan0 up

# Or using airmon-ng
airmon-ng start wlan0

# Scan all channels
airodump-ng wlan0mon

# Target specific network
airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon

# Capture PMKID/handshake (modern)
hcxdumptool -i wlan0mon -o capture.pcapng --enable_status=1

# Convert for hashcat
hcxpcapngtool -o hash.hc22000 capture.pcapng
```

## Client-Side Probing Risks

Modern devices broadcast preferred network SSIDs in Probe Requests:
- Reveals SSIDs of previously connected networks
- MAC address randomization (iOS, Android 10+) mitigates tracking
- But SSIDs still visible until association

Check your probe history:
- Windows: `netsh wlan show profiles`
- Linux: `nmcli connection show`
- Android: Settings → WiFi → Saved Networks

## Securing Your WiFi

1. **WPA3 if available**; WPA2-AES minimum (disable TKIP)
2. **Passphrase**: 20+ random characters (not words)
3. **Disable WPS** completely
4. **Enable MFP** (802.11w / Management Frame Protection)
5. **Hidden SSID**: security theater — still detectable
6. **MAC filtering**: security theater — trivially spoofed
7. **Separate guest network**: isolate untrusted devices
8. **Monitor for rogue APs**: compare beacon frames on your channel
9. **VPN on public WiFi**: treat all public WiFi as hostile

## Signal Analysis

- RSSI (Received Signal Strength Indicator): dBm; -30 excellent, -70 good, -90 edge
- Channel overlap: 2.4 GHz use 1, 6, 11 (non-overlapping); 5 GHz has more channels
- Hidden AP detection: probe responses, association frames reveal hidden SSIDs
- 6 GHz (WiFi 6E): less interference, faster, shorter range
