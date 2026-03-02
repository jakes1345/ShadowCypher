# Free & Open-Source API Alternatives for ShadowCypher

Replace every paid API with free/open-source equivalents.

## Quick Reference

| Paid Service | Free Alternative | Key? | Endpoint/Notes |
|--------------|-------------------|------|----------------|
| **Shodan** | **Shodan InternetDB** | NO | https://internetdb.shodan.io/{IP} - ports, CVEs, hostnames |
| **VirusTotal** | **MalwareBazaar** | Free at auth.abuse.ch | Hash lookup |
| **VirusTotal** | **URLhaus** | Same key | URL + hash lookup |
| **SecurityTrails** | **crt.sh** | NO | Already in use |
| **Censys** | **Subfinder/Amass** | NO | Run locally |
| **ip-api.com** | **reallyfreegeoip.org** | NO | No rate limits |
| **HIBP** | **LeakIX** | Free reg | leakix.net/search?scope=leak |
| **Dehashed** | **LeakIX** | Free reg | Breach search |
| **GreyNoise** | **GreyNoise Community** | Free | 50 searches/week |
| **Hunter.io** | **Reacher** | Self-host | Open source Rust |
| **IntelX** | **Ahmia + psbdmp** | NO | Already in use |

## Shodan InternetDB (NO KEY)
curl https://internetdb.shodan.io/8.8.8.8
Returns: ports, vulns (CVEs), hostnames, cpes, tags. Updated weekly.

## LeakIX (FREE KEY)
- Register at leakix.net
- GET https://leakix.net/search?scope=leak&q=email:user@domain
- GET https://leakix.net/search?scope=service&q=ip:1.2.3.4
- Rate limit: ~1 req/sec

## reallyfreegeoip.org (NO KEY)
curl https://api.reallyfreegeoip.org/json/8.8.8.8
No limits, no key.

## Netlas.io (FREE TIER)
- Register at netlas.io
- Internet scanner, DNS, WHOIS, SSL certs
- Python SDK: pip install netlas

## abuse.ch (ONE FREE KEY)
- auth.abuse.ch - one key for MalwareBazaar, URLhaus, ThreatFox
- Hash lookup, URL lookup, IOC feeds
