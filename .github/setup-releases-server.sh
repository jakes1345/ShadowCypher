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
DOMAIN="releases.shadowcypher.site"
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"

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

# ─── Install packages ──────────────────────────────────────────────────────
echo -e "${BLUE}Installing Nginx + certbot...${NC}"
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx > /dev/null 2>&1

# ─── Bootstrap: HTTP-only config until cert exists ─────────────────────────
echo -e "${BLUE}Configuring Nginx (HTTP bootstrap)...${NC}"
cat > /etc/nginx/sites-available/"$DOMAIN" << NGINXEOF
server {
    listen 80;
    server_name $DOMAIN;
    root $RELEASES_DIR;
    index index.html;
    autoindex on;

    # Used by certbot ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/"$DOMAIN" /etc/nginx/sites-enabled/"$DOMAIN"
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable nginx
systemctl reload nginx || systemctl restart nginx
echo "✓ Nginx running (HTTP)"

# ─── Obtain SSL cert ────────────────────────────────────────────────────────
if [ -f "$CERT_DIR/fullchain.pem" ]; then
    echo "✓ SSL cert already exists, skipping certbot"
else
    echo -e "${BLUE}Obtaining SSL certificate...${NC}"
    certbot --nginx \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email admin@shadowcypher.site \
        --redirect
    echo "✓ SSL cert obtained"
fi

# ─── Write full SSL config ─────────────────────────────────────────────────
echo -e "${BLUE}Writing SSL Nginx config...${NC}"
cat > /etc/nginx/sites-available/"$DOMAIN" << NGINXEOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    root $RELEASES_DIR;
    index index.html;

    autoindex on;
    autoindex_format json;

    location ~* \.(apk|iso|tar\.gz|deb|rpm)$ {
        add_header Content-Disposition "attachment; filename=\$request_filename";
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location = /api/latest {
        return 301 https://api.shadowcypher.site/api/latest;
    }

    location ~ /SHA256SUMS\$ {
        add_header Content-Type text/plain;
    }

    error_page 404 /404.html;
    error_page 403 /403.html;
}
NGINXEOF

nginx -t
systemctl reload nginx
echo "✓ Nginx running (HTTPS)"

# ─── Permissions ────────────────────────────────────────────────────────────
echo -e "${BLUE}Setting permissions...${NC}"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$RELEASES_DIR"
chmod 755 "$RELEASES_DIR"

# ─── Create index page ──────────────────────────────────────────────────────
cat > "$RELEASES_DIR/index.html" << 'HTMLEOF'
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
HTMLEOF

chown "$DEPLOY_USER:$DEPLOY_USER" "$RELEASES_DIR/index.html"
chmod 644 "$RELEASES_DIR/index.html"

# ─── Generate deploy SSH keypair ────────────────────────────────────────────
if [ ! -f "$DEPLOY_HOME/.ssh/id_ed25519" ]; then
    echo -e "${BLUE}Generating deploy SSH keypair...${NC}"
    sudo -u "$DEPLOY_USER" ssh-keygen -t ed25519 -f "$DEPLOY_HOME/.ssh/id_ed25519" -N ""
    sudo -u "$DEPLOY_USER" cp "$DEPLOY_HOME/.ssh/id_ed25519.pub" "$DEPLOY_HOME/.ssh/authorized_keys"
    chmod 600 "$DEPLOY_HOME/.ssh/authorized_keys"
    echo "✓ SSH keypair generated"
fi

echo ""
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "══════════════════════════════════════════════════════"
echo "  Add these 3 secrets to GitHub:"
echo "  Settings → Secrets → Actions → New repository secret"
echo ""
echo "  RELEASE_SERVER_HOST  = $(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
echo "  RELEASE_SERVER_USER  = $DEPLOY_USER"
echo "  RELEASE_SERVER_SSH_KEY = (paste the key below)"
echo ""
echo "── PRIVATE KEY (copy everything including the dashes) ──"
cat "$DEPLOY_HOME/.ssh/id_ed25519"
echo "══════════════════════════════════════════════════════"
echo ""
echo "Test: curl https://$DOMAIN/"
