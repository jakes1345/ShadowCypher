# Ghost Mode & Anonymity Reference

## Ghost Mode in ShadowCypher

Ghost Mode is ShadowCypher's privacy protocol that enables anonymous network operation.

### What Ghost Mode Does
- Routes all traffic through Tor hidden service
- Applies system-level IP anonymization
- Spoofs MAC address on network interfaces
- Disables WebRTC (IP leak vector in browsers)
- Kills identifiable telemetry processes
- Enables DNS-over-Tor (no DNS leaks)

### Ghost Mode Status
- Check from ShadowCypher desktop app: Guardian → Ghost Protocol tab
- Status levels: Disabled / Partial / Full
- Ask Shadow: "Are you in ghost mode?" or "Check my anonymity status"

## Tor Network

### How Tor Works
- Onion routing: traffic encrypted in three layers, routed through 3 relays
- **Guard/Entry node**: knows your real IP, not destination
- **Middle relay**: knows neither real IP nor destination
- **Exit node**: knows destination, not your real IP
- Hidden services (.onion): both parties anonymous; no exit node needed

### Tor Node Types
- Guard nodes: long-lived, stable, high-bandwidth; first hop
- Middle relays: general relays
- Exit nodes: final hop to clearnet; operator sees destination traffic
- Bridges: unlisted guards; circumvent censorship; types: obfs4, meek, Snowflake
- Hidden services: .onion v3 (56-char) — use ED25519 keys

### Tor Limitations
- **Speed**: 3-hop latency; not suitable for video streaming
- **Exit node MITM**: exit nodes see plaintext HTTP; use HTTPS everywhere
- **Timing correlation attack**: global passive adversary can correlate entry/exit traffic
- **JavaScript/browser fingerprinting**: Tor Browser minimizes; stay at default window size
- **Not a VPN**: doesn't encrypt all traffic; only SOCKS5 proxy by default
- **DNS leaks**: configure DNS through Tor or use a resolver only via Tor

### Tor Browser Hardening
- Keep at default window size (fingerprinting)
- Disable JavaScript for maximum security (breaks many sites)
- Never maximize window
- Don't install browser extensions
- Don't login to personal accounts over Tor
- Use Tor Browser, not just Tor SOCKS5 in another browser

## VPN + Tor Combinations

### VPN → Tor
- Your ISP sees VPN traffic (not Tor)
- VPN provider sees you're using Tor (not destinations)
- Tor entry guard sees VPN IP, not real IP
- **Risk**: VPN provider is trusted party; logs can deanonymize

### Tor → VPN
- Tor exit node connects to VPN server
- Destination sees VPN IP
- Use case: access Tor-blocked services; consistent exit IP
- **Risk**: VPN provider knows all your exit traffic; adds trust dependency

## MAC Address Spoofing

### Why Spoof MAC
- MAC addresses are broadcast on local network
- Visible to router, switches, WiFi APs
- Used for device tracking in managed networks
- Forensic evidence of presence on network

### How to Spoof (Linux)
```bash
# Bring interface down
ip link set eth0 down

# Set random/specific MAC
ip link set eth0 address 02:$(od -An -N5 -tx1 /dev/urandom | tr ' ' ':' | head -c14)

# Or use macchanger
macchanger -r eth0        # random
macchanger -p eth0        # restore permanent

# Bring back up
ip link set eth0 up
```

Note: MAC is only visible on local network segment; not routed over internet.
Modern Android/iOS randomize MAC per network by default.

## DNS Leak Prevention

DNS queries can reveal browsing destinations even through VPN/Tor:

```bash
# Check current DNS servers
cat /etc/resolv.conf
resolvectl status

# Test for leaks
# Use dnsleaktest.com or ipleak.net

# Force all DNS through VPN
# Set DNS to VPN provider's DNS in network config
# Or use encrypted DNS: DoH/DoT

# systemd-resolved DoH configuration
[Resolve]
DNS=1.1.1.1#cloudflare-dns.com 9.9.9.9#dns.quad9.net
DNSOverTLS=yes
```

## WebRTC Leak Prevention

WebRTC reveals local IPs via STUN requests:
- Affects browsers even behind VPN
- Disable in Firefox: `media.peerconnection.enabled = false` in about:config
- Chrome: install uBlock Origin (WebRTC control) or WebRTC Leak Prevent
- Test: browserleaks.com/webrtc

## Operational Security (OpSec)

### Compartmentalization
- Separate identities for separate activities
- Never mix real-identity accounts with anonymous ones
- Use separate devices or VMs for different trust levels
- Tails OS: amnesic live system — no persistence between sessions

### Metadata Removal
- Images: EXIF contains GPS, device model, timestamp → use `exiftool -all= file.jpg`
- Documents: Office metadata (author, company, revisions) → File → Properties → Remove
- PDF: `qpdf --linearize --empty input.pdf output.pdf`

### Communication
- Signal: E2E encrypted, sealed sender, disappearing messages
- Session: no phone number required, onion routing
- ProtonMail: E2E encrypted at rest; metadata still visible to Proton
- Briar: P2P, Tor-based, works without internet (WiFi/Bluetooth mesh)

## Anonymity vs. Privacy vs. Security

| Concept | Definition | Example |
|---------|-----------|---------|
| Privacy | Others can't see your data | Encrypted messages |
| Anonymity | Others can't identify you | Tor browsing |
| Pseudonymity | Known by a different name | Online alias |
| Security | System resists attack | 2FA, patching |

All three are needed for full protection — each alone is insufficient.
