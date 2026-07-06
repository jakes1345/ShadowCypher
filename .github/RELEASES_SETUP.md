# Releases Server Setup

This document describes how to set up the `releases.shadowcypher.site` infrastructure for self-hosted downloads.

## GitHub Actions Secrets Required

Add these secrets to your GitHub repository settings (`Settings → Secrets and variables → Actions`):

### 1. `RELEASE_SERVER_HOST`
- **Type:** Repository Secret
- **Value:** IP or hostname of your releases server
- **Example:** `releases.shadowcypher.site` or `1.2.3.4`

### 2. `RELEASE_SERVER_USER`
- **Type:** Repository Secret
- **Value:** SSH username for releases server
- **Example:** `deploy` or `releases`

### 3. `RELEASE_SERVER_SSH_KEY`
- **Type:** Repository Secret
- **Value:** Private SSH key for authentication (PEM format)
- **How to generate:**
  ```bash
  ssh-keygen -t ed25519 -f releases_deploy_key -N ""
  # Use contents of releases_deploy_key (private key)
  # Add releases_deploy_key.pub to server's ~/.ssh/authorized_keys
  ```

## Server Setup

### Directory Structure
```bash
/var/www/releases/
├── latest/               # Symlink to current version
├── v1.0.0/
│   ├── shadowcypher-linux.tar.gz
│   ├── shadowcypher-guardian.apk
│   ├── shadowcypher-os.iso
│   └── SHA256SUMS
├── v1.0.1/
└── v1.1.0/
```

### Installation
```bash
# As root or with sudo:
mkdir -p /var/www/releases
chmod 755 /var/www/releases

# Create deploy user (if needed)
useradd -m -s /bin/bash deploy
chmod 700 /home/deploy/.ssh
echo "your_public_key_here" > /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
```

### Web Server Config (Nginx)
```nginx
server {
    listen 80;
    server_name releases.shadowcypher.site;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name releases.shadowcypher.site;

    # SSL certificate (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/releases.shadowcypher.site/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/releases.shadowcypher.site/privkey.pem;

    root /var/www/releases;
    index index.html;

    # Enable directory listing
    autoindex on;
    autoindex_format json;

    # Serve files with correct MIME types
    location ~* \.(apk|iso|tar\.gz|deb|rpm)$ {
        add_header Content-Disposition "attachment; filename=$request_filename";
    }

    # API endpoint for version info
    location = /api/latest {
        return 301 https://api.shadowcypher.site/api/latest;
    }

    # Serve SHA256SUMS
    location ~ /SHA256SUMS$ {
        add_header Content-Type text/plain;
    }

    # Cache headers
    location ~* \.(tar\.gz|apk|iso|deb|rpm)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Let's Encrypt SSL
```bash
sudo certbot certonly --standalone \
    -d releases.shadowcypher.site \
    -m admin@shadowcypher.site
```

## Workflow

1. **Create Release on GitHub**
   - Tag: `v1.0.0`
   - Attach artifacts: `.tar.gz`, `.apk`, `.iso`, `SHA256SUMS`

2. **Publish Release**
   - GitHub Actions workflow triggers
   - Downloads artifacts from GitHub
   - Uploads to `releases.shadowcypher.site/v1.0.0/`

3. **Update Latest Symlink**
   ```bash
   cd /var/www/releases
   ln -sfn v1.0.0 latest
   ```

4. **Verify**
   - Check: `https://releases.shadowcypher.site/v1.0.0/`
   - Download links should work
   - API returns correct version info

## Monitoring

### Check Storage Usage
```bash
du -sh /var/www/releases/*
```

### Verify Checksums
```bash
# On server
cd /var/www/releases/v1.0.0
sha256sum -c SHA256SUMS
```

### Monitor Disk Space
```bash
# Set alert if disk > 80%
df /var/www | awk '{print $5}' | grep -oE '[0-9]+'
```

## Troubleshooting

### SSH Key Issues
```bash
# Test connection
ssh -i /path/to/key deploy@releases.shadowcypher.site "ls -la"

# Check permissions on server
ls -la ~/.ssh/
# Should be 700 for .ssh, 600 for authorized_keys
```

### Upload Fails
```bash
# Check GitHub Actions logs
# Verify SSH key secret is correctly set (multi-line PEM format)
# Test manual SCP:
scp -i /path/to/key file.tar.gz deploy@releases.shadowcypher.site:/var/www/releases/v1.0.0/
```

### API Endpoint Returns Wrong Info
- Verify `shadowcypher/main.py` has correct `/api/latest` endpoint
- Check VERSION file exists and is readable
- Verify CORS headers allow `releases.shadowcypher.site`

## Security

- SSH keys should use Ed25519 (not RSA)
- Restrict deploy user to only SCP/SFTP (use `restricted-shell` or similar)
- Enable HTTPS only (redirect HTTP → HTTPS)
- Monitor access logs for suspicious activity
- Keep server patched and updated

## Backup

```bash
# Backup releases daily
sudo tar -czf /backup/releases-$(date +%Y%m%d).tar.gz /var/www/releases/
```
