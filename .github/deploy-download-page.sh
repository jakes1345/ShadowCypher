#!/bin/bash
# deploy-download-page.sh
# Deploy download page to shadowcypher.site
# Usage: ./deploy-download-page.sh <website_server> <deploy_user>

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <website_server> <deploy_user>"
    echo "Example: $0 shadowcypher.site deploy"
    exit 1
fi

WEBSITE_SERVER="$1"
DEPLOY_USER="$2"
DOWNLOAD_PAGE="shadowcypher/ui/download_page.html"
REMOTE_PATH="/var/www/shadowcypher/download.html"

echo "🚀 Deploying download page..."

if [ ! -f "$DOWNLOAD_PAGE" ]; then
    echo "❌ Error: $DOWNLOAD_PAGE not found"
    exit 1
fi

# SCP to website server
echo "Uploading to $WEBSITE_SERVER..."
scp "$DOWNLOAD_PAGE" "$DEPLOY_USER@$WEBSITE_SERVER:$REMOTE_PATH"

echo "✓ Download page deployed!"
echo ""
echo "Access at: https://shadowcypher.site/download.html"
echo "Or create symlink: ln -s /var/www/shadowcypher/download.html /var/www/shadowcypher/download"
