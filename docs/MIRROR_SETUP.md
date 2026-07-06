# ShadowOS Mirror Network

## Becoming a Mirror

To host ShadowOS downloads:

1. **Storage:** 50+ GB available space
2. **Bandwidth:** Minimum 100 Mbps symmetrical
3. **Uptime:** 99.5% required
4. **Verification:** All files must pass SHA256/GPG verification

## Setup Instructions

```bash
# Create mirror directory
mkdir -p /var/www/shadowos/downloads
cd /var/www/shadowos/downloads

# Download latest release
wget https://dl.shadowcypher.site/shadowos-latest.iso
wget https://dl.shadowcypher.site/shadowos-latest.iso.sig
wget https://dl.shadowcypher.site/SHA256SUMS
wget https://dl.shadowcypher.site/SHA256SUMS.sig

# Verify integrity
gpg --recv-keys 0xABCD1234
gpg --verify SHA256SUMS.sig
sha256sum -c SHA256SUMS

# Setup rsync sync (hourly)
# Add to crontab:
# 0 * * * * rsync -av --delete dl.shadowcypher.site::/shadowos/downloads/ /var/www/shadowos/downloads/

# Configure web server (nginx example):
# location /shadowos/ {
#     alias /var/www/shadowos/;
#     autoindex on;
# }
```

## Mirror Registry

Add your mirror to [mirrors.json](.mirrors.json):

```bash
curl -X POST https://shadowcypher.site/api/mirrors/register \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://mirror.example.com/shadowos",
    "location": "Country/City",
    "bandwidth": "1 Gbps",
    "admin": "mirror-admin@example.com",
    "verify_token": "your-verification-token"
  }'
```

## Monitoring

All mirrors are monitored for:
- File integrity (SHA256 weekly)
- Availability (HTTP HEAD checks hourly)
- Response time (latency tracking)

Poor-performing mirrors may be delisted.
