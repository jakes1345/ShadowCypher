#!/bin/bash
# setup-releases-server.sh
# Automated setup for releases.shadowcypher.site server
# Run as: sudo bash setup-releases-server.sh

set -e

echo "🔧 Setting up ShadowCypher Releases Server..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
RELEASES_DIR="/var/www/releases"
DEPLOY_USER="deploy"
DEPLOY_HOME="/home/$DEPLOY_USER"

# ─── Create directories ───────────────────────────────────────────────────
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p "$RELEASES_DIR"/{latest,v1.0.0}
chmod 755 "$RELEASES_DIR"

# ─── Create deploy user ────────────────────────────────────────────────────
echo -e "${BLUE}Setting up deploy user...${NC}"
if ! id "$DEPLOY_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$DEPLOY_USER"
    echo "Created user: $DEPLOY_USER"
else
    echo "User $DEPLOY_USER already exists"
fi

# SSH setup
mkdir -p "$DEPLOY_HOME/.ssh"
chmod 700 "$DEPLOY_HOME/.ssh"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_HOME/.ssh"

# ─── Install Nginx ─────────────────────────────────────────────────────────
echo -e "${BLUE}Installing Nginx...${NC}"
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx > /dev/null 2>&1

# ─── Create Nginx config ───────────────────────────────────────────────────
echo -e "${BLUE}Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/releases.shadowcypher.site << 'EOF'
server {
    listen 80;
    server_name releases.shadowcypher.site;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name releases.shadowcypher.site;

    ssl_certificate /etc/letsencrypt/live/releases.shadowcypher.site/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/releases.shadowcypher.site/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    root /var/www/releases;
    index index.html;

    autoindex on;
    autoindex_format json;

    location ~* \.(apk|iso|tar\.gz|deb|rpm)$ {
        add_header Content-Disposition "attachment; filename=$request_filename";
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location = /api/latest {
        return 301 https://api.shadowcypher.site/api/latest;
    }

    location ~ /SHA256SUMS$ {
        add_header Content-Type text/plain;
    }

    error_page 404 /404.html;
    error_page 403 /403.html;
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/releases.shadowcypher.site \
       /etc/nginx/sites-enabled/releases.shadowcypher.site
rm -f /etc/nginx/sites-enabled/default

# Test config
nginx -t > /dev/null 2>&1 && echo "✓ Nginx config valid"

# Reload Nginx (without SSL cert yet)
systemctl reload nginx || systemctl restart nginx

# ─── Permissions ────────────────────────────────────────────────────────────
echo -e "${BLUE}Setting permissions...${NC}"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$RELEASES_DIR"
chmod 755 "$RELEASES_DIR"
chmod 755 "$RELEASES_DIR"/*

# ─── Create index page ──────────────────────────────────────────────────────
cat > "$RELEASES_DIR/index.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>ShadowCypher Releases</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: monospace; background: #0a0e27; color: #e2e8f0; padding: 40px; }
        h1 { color: #00f2ff; }
        a { color: #0088ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .info { background: rgba(0, 242, 255, 0.1); padding: 20px; border-radius: 4px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>ShadowCypher Releases</h1>
    <p>Browse releases: <a href="/latest/">/latest/</a> | <a href="/api/latest">Version Info</a></p>
    <div class="info">
        <strong>✓ Releases server is online</strong>
        <p>Download latest: <a href="https://api.shadowcypher.site/api/latest">shadowcypher.site/download</a></p>
    </div>
</body>
</html>
EOF

chown "$DEPLOY_USER:$DEPLOY_USER" "$RELEASES_DIR/index.html"
chmod 644 "$RELEASES_DIR/index.html"

echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Add public SSH key to: $DEPLOY_HOME/.ssh/authorized_keys"
echo "2. Set up SSL certificate: sudo certbot certonly --standalone -d releases.shadowcypher.site"
echo "3. Reload Nginx: sudo systemctl reload nginx"
echo "4. Test: curl https://releases.shadowcypher.site/"
