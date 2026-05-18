# Tor Network Reference

## Tor Basics

Tor (The Onion Router) — free, open-source anonymity network.
Developed by the US Naval Research Laboratory; now maintained by the Tor Project (nonprofit).
Used by journalists, activists, privacy-conscious users, and law enforcement worldwide.

## How Onion Routing Works

1. Tor client downloads consensus (list of relays) from directory authorities
2. Builds a circuit: Client → Guard → Middle → Exit
3. Each layer encrypts with the relay's public key (3 layers = "onion")
4. Each relay decrypts one layer and forwards; no relay knows both source and destination
5. Exit relay communicates with destination in plaintext (unless HTTPS)

Circuit building: 1–3 seconds typically
Circuit lifetime: rotates every 10 minutes by default

## Tor Hidden Services (.onion)

### v3 Onion Addresses (current)
- 56 characters + `.onion`
- ED25519 public key derived; address is the key's hash
- 6 characters = checksum + version

### How Hidden Services Work
1. Service picks 6 "Introduction Points" from relay network
2. Publishes descriptor (IP list + pubkey) to distributed hash table
3. Client fetches descriptor, builds circuit to an Introduction Point
4. Client creates a "Rendezvous Point" — sends one-time secret
5. Service builds circuit to Rendezvous Point
6. Encrypted circuit established: neither knows the other's IP

### Notable .onion Sites
- SecureDrop instances (news organizations): whistleblower submissions
- DuckDuckGo: `duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion`
- Facebook: `facebookwkhpilnemxj7asber7cyber2stgkgq3xbwa5zghom3ap73oad.onion`
- Tor Project: `2gzyxa5ihm7nsggfxnu52rck2vv4rvmdlkiu3zzui5du4xyclen53wid.onion`

## Tor Traffic Analysis

### What Your ISP Sees
- You are connecting to Tor (guard node IP)
- Connection is encrypted
- Duration of Tor usage
- Amount of data transferred (approximate)

### What the Exit Node Sees
- Destination website/IP
- Unencrypted content (if HTTP)
- Your Tor circuit's exit IP (not your real IP)

### What the Destination Sees
- Tor exit node IP address
- Browser/HTTP headers (Tor Browser minimizes these)
- Cookies you send

## Tor Detection and Blocking

### Exit Node Lists
- Tor Project publishes exit node IP list
- Websites use this to block Tor users
- Cloudflare shows CAPTCHA to Tor exit IPs by default

### Bridge Transports (Censorship Circumvention)
| Transport | Method | Use Case |
|-----------|--------|----------|
| obfs4 | Obfuscates traffic shape | Most censored countries |
| meek-azure | Mimics HTTPS to Azure CDN | China, Iran |
| Snowflake | WebRTC via volunteer browsers | China, Russia |
| webtunnel | Mimics HTTPS website | Latest; hard to detect |

Get bridges: bridges.torproject.org or `GETBRIDGES` email to bridges@torproject.org

## Tor on Android

### Orbot (official Tor app)
- Routes all device traffic through Tor (VPN mode)
- App-specific Tor: only route selected apps
- Download: Google Play or Guardian Project F-Droid repo
- Tor Browser for Android: bundled Tor + hardened Firefox

### ShadowCypher + Tor Integration
Ghost Mode uses Tor via Orbot or system Tor daemon when available.
Check Ghost Mode status from the ShadowCypher Guardian dashboard.

## Common Tor Misconceptions

| Myth | Reality |
|------|---------|
| "Tor makes you completely anonymous" | Reduces anonymity to near zero but not perfect; behavior matters |
| "Only criminals use Tor" | Used by journalists, activists, corporations, military, privacy users |
| "Tor is slow" | Improved; usable for browsing, slow for video/large downloads |
| "VPN is better than Tor" | Different threat models; Tor: no single trusted party; VPN: trust provider |
| "Tor Browser has been hacked" | Specific vulnerabilities patched; keep updated; JS vulnerabilities are main risk |

## Operational Security with Tor

- Never login to real accounts on Tor
- Don't use Tor from home WiFi for sensitive activities (timing correlation)
- Keep Tor Browser at default window size
- Disable JavaScript for maximum anonymity (High/Safest security level)
- Use Tails OS for compartmentalized Tor sessions
- Don't torrent over Tor (reveals real IP, slows network)
- Clear cookies/history between sessions (Tor Browser does this by default)

## Running a Tor Relay

```bash
# Install
apt install tor

# torrc configuration for relay
Nickname MyRelay
RelayBandwidthRate 1 MBytes
RelayBandwidthBurst 2 MBytes
ContactInfo your@email.com
ExitPolicy reject *:*  # Middle relay only; no exit traffic
ORPort 9001

# Monitor relay
nyx  # Terminal Tor status monitor

# Check your relay on atlas.torproject.org
```

Running an exit node exposes you to DMCA and abuse complaints.
Middle relays: low risk, help the network significantly.
