#!/usr/bin/env bash
# ShadowCypher Self-Host Setup
# Deploys the ShadowCypher stack to your own Cloudflare account.
#
# Requirements:
#   - Node.js 18+
#   - A Cloudflare account with your domain added
#   - A Supabase project (supabase.com)
#   - A Neon project (neon.tech) — used as auth/API key mirror
#   - A Resend account (resend.com) — outbound email

set -euo pipefail

# ─── Colors ──────────────────────────────────────────────────────────────────

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()    { echo -e "${CYAN}→${RESET} $*"; }
success() { echo -e "${GREEN}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}!${RESET} $*"; }
die()     { echo -e "${RED}✗${RESET} $*" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$REPO_ROOT/backend/api"
SELF_TOML="$API_DIR/wrangler.self.toml"
TEMPLATE_TOML="$API_DIR/wrangler.template.toml"

# ─── Banner ──────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}ShadowCypher Self-Host Setup${RESET}"
echo "───────────────────────────────────────────────"
echo ""
echo "This script will:"
echo "  1. Create your Cloudflare KV namespace and R2 bucket"
echo "  2. Generate a config file for your domain"
echo "  3. Set all secrets in your Cloudflare account"
echo "  4. Deploy the API Worker"
echo "  5. Tell you what manual steps remain"
echo ""
echo "Before you start, you need accounts at:"
echo "  cloudflare.com  •  supabase.com  •  neon.tech  •  resend.com"
echo ""
read -rp "Ready? Press Enter to continue or Ctrl+C to abort."
echo ""

# ─── Prerequisites ────────────────────────────────────────────────────────────

info "Checking prerequisites..."

check_node_version() {
  local version
  version=$(node --version 2>/dev/null | grep -oP '\d+' | head -1)
  [[ -n "$version" && "$version" -ge 18 ]]
}

command -v node &>/dev/null || die "Node.js not found. Install Node.js 18+ from nodejs.org"
check_node_version || die "Node.js 18+ required. Current: $(node --version)"
command -v npm &>/dev/null || die "npm not found. Install Node.js 18+ from nodejs.org"
success "Node.js $(node --version)"

if ! command -v wrangler &>/dev/null; then
  info "Installing Wrangler CLI..."
  npm install -g wrangler
fi
success "Wrangler $(wrangler --version 2>/dev/null | head -1)"

# ─── Cloudflare login ────────────────────────────────────────────────────────

echo ""
info "Checking Cloudflare login..."
if ! wrangler whoami &>/dev/null 2>&1; then
  warn "Not logged in to Cloudflare. Opening browser..."
  wrangler login
fi
CF_ACCOUNT=$(wrangler whoami 2>/dev/null | grep -oP '(?<=Account Name: ).*' | head -1 || echo "your account")
success "Logged in as: $CF_ACCOUNT"

# ─── Configuration ───────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Configuration${RESET}"
echo "───────────────────────────────────────────────"
echo "Your domain must already be added to Cloudflare and have its"
echo "nameservers pointed to Cloudflare."
echo ""

prompt_required() {
  local var_name="$1" prompt_text="$2" secret="${3:-false}"
  local value=""
  while [[ -z "$value" ]]; do
    if [[ "$secret" == "true" ]]; then
      read -rsp "${prompt_text}: " value; echo
    else
      read -rp "${prompt_text}: " value
    fi
    [[ -z "$value" ]] && warn "This field is required."
  done
  printf -v "$var_name" '%s' "$value"
}

prompt_required DOMAIN            "Your domain (e.g. myapp.com)"
prompt_required SUPABASE_URL      "Supabase project URL (https://xxx.supabase.co)"
prompt_required SUPABASE_KEY      "Supabase service role key" true
prompt_required SUPABASE_WEBHOOK  "Supabase webhook secret (any random string, min 16 chars)" true
prompt_required NEON_DB_URL       "Neon database URL (postgresql://user:pass@host/db)" true
prompt_required RESEND_KEY        "Resend API key (re_...)" true

# Derive slugified name from domain (dots → dashes)
DOMAIN_SLUG="${DOMAIN//./-}"
WORKER_NAME="shadowcypher-api-${DOMAIN_SLUG}"
R2_BUCKET="shadowcypher-files-${DOMAIN_SLUG}"

echo ""
echo -e "${BOLD}Summary${RESET}"
echo "  Domain:       $DOMAIN"
echo "  Worker name:  $WORKER_NAME"
echo "  R2 bucket:    $R2_BUCKET"
echo ""
read -rp "Proceed? (y/N) " CONFIRM
[[ "${CONFIRM,,}" == "y" ]] || { echo "Aborted."; exit 0; }

# ─── Create Cloudflare resources ─────────────────────────────────────────────

echo ""
info "Creating KV namespace (SHADOW_OTA)..."
KV_OUTPUT=$(wrangler kv namespace create SHADOW_OTA 2>&1) || die "KV creation failed:\n$KV_OUTPUT"
KV_ID=$(echo "$KV_OUTPUT" | grep -oP '(?<=id = ")[^"]+' | head -1)
if [[ -z "$KV_ID" ]]; then
  # Alternate format in newer wrangler versions
  KV_ID=$(echo "$KV_OUTPUT" | grep -oP '"id"\s*:\s*"\K[^"]+' | head -1)
fi
if [[ -z "$KV_ID" ]]; then
  warn "Could not auto-detect KV ID from wrangler output."
  echo "$KV_OUTPUT"
  prompt_required KV_ID "Paste the KV namespace ID from the output above"
fi
success "KV namespace ID: $KV_ID"

info "Creating KV preview namespace..."
KV_PREV_OUTPUT=$(wrangler kv namespace create SHADOW_OTA --preview 2>&1) || die "KV preview creation failed"
KV_PREVIEW_ID=$(echo "$KV_PREV_OUTPUT" | grep -oP '(?<=id = ")[^"]+' | head -1)
if [[ -z "$KV_PREVIEW_ID" ]]; then
  KV_PREVIEW_ID=$(echo "$KV_PREV_OUTPUT" | grep -oP '"id"\s*:\s*"\K[^"]+' | head -1)
fi
[[ -z "$KV_PREVIEW_ID" ]] && KV_PREVIEW_ID="$KV_ID"  # fallback: reuse prod ID
success "KV preview ID: $KV_PREVIEW_ID"

info "Creating R2 bucket ($R2_BUCKET)..."
wrangler r2 bucket create "$R2_BUCKET" 2>&1 || warn "R2 bucket may already exist — continuing."
success "R2 bucket ready."

# ─── Generate wrangler config ─────────────────────────────────────────────────

info "Generating $SELF_TOML..."
[[ -f "$TEMPLATE_TOML" ]] || die "Template not found at $TEMPLATE_TOML"

sed \
  -e "s|__WORKER_NAME__|${WORKER_NAME}|g" \
  -e "s|__DOMAIN__|${DOMAIN}|g" \
  -e "s|__KV_ID__|${KV_ID}|g" \
  -e "s|__KV_PREVIEW_ID__|${KV_PREVIEW_ID}|g" \
  -e "s|__R2_BUCKET__|${R2_BUCKET}|g" \
  "$TEMPLATE_TOML" > "$SELF_TOML"

success "Config written to backend/api/wrangler.self.toml"

# ─── Install dependencies ─────────────────────────────────────────────────────

info "Installing API dependencies..."
(cd "$API_DIR" && npm ci --silent)
success "Dependencies installed."

# ─── Set secrets ─────────────────────────────────────────────────────────────

info "Setting Cloudflare secrets..."

set_secret() {
  local name="$1" value="$2"
  echo "$value" | wrangler secret put "$name" --config "$SELF_TOML" 2>/dev/null \
    && success "Secret: $name" \
    || die "Failed to set secret: $name"
}

set_secret SUPABASE_URL             "$SUPABASE_URL"
set_secret SUPABASE_SERVICE_ROLE_KEY "$SUPABASE_KEY"
set_secret SUPABASE_WEBHOOK_SECRET  "$SUPABASE_WEBHOOK"
set_secret NEON_DATABASE_URL        "$NEON_DB_URL"
set_secret RESEND_API_KEY           "$RESEND_KEY"

# ─── Deploy ───────────────────────────────────────────────────────────────────

echo ""
info "Deploying Worker to Cloudflare..."
(cd "$API_DIR" && wrangler deploy --config wrangler.self.toml)
success "Worker deployed!"

# ─── Patch frontend API URL ───────────────────────────────────────────────────

FRONTEND="$REPO_ROOT/www/index.html"
if [[ -f "$FRONTEND" ]]; then
  info "Patching frontend API URL..."
  sed -i "s|'https://api\.shadowcypher\.site'|'https://api.${DOMAIN}'|g" "$FRONTEND"
  success "Frontend updated to use api.${DOMAIN}"
fi

# ─── Next steps ───────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${GREEN}Deployment complete!${RESET}"
echo ""
echo -e "${BOLD}Manual steps remaining:${RESET}"
echo ""
echo -e "${BOLD}1. Supabase — run the schema SQL${RESET}"
echo "   Open your Supabase project → SQL Editor → New query"
echo "   Paste the contents of: backend/api/schema.sql"
echo "   Run it."
echo ""
echo -e "${BOLD}2. Neon — run the schema SQL${RESET}"
echo "   Open your Neon project → SQL Editor"
echo "   Paste the contents of: backend/api/schema.neon.sql"
echo "   Run it."
echo ""
echo -e "${BOLD}3. Supabase — configure Auth${RESET}"
echo "   Authentication → Settings → Site URL: https://${DOMAIN}"
echo "   Authentication → Settings → Redirect URLs: https://${DOMAIN}/**"
echo "   Authentication → Email → disable email confirmation (or configure SMTP)"
echo ""
echo -e "${BOLD}4. Supabase — set up the webhook${RESET}"
echo "   Database → Webhooks → Create new webhook"
echo "     Name:    new-user-sync"
echo "     Table:   auth.users"
echo "     Events:  INSERT"
echo "     URL:     https://api.${DOMAIN}/v1/internal/supabase-event"
echo "     Header:  x-supabase-event-secret: <your SUPABASE_WEBHOOK_SECRET>"
echo ""
echo -e "${BOLD}5. Cloudflare — set up Email Routing${RESET}"
echo "   Dashboard → Email → Email Routing → Enable on ${DOMAIN}"
echo "   Add MX records as instructed by Cloudflare"
echo "   Add catch-all rule: *@${DOMAIN} → Send to Worker → ${WORKER_NAME}"
echo ""
echo -e "${BOLD}6. Host the frontend${RESET}"
echo "   Upload www/index.html to Cloudflare Pages, or serve it statically."
echo "   Point your domain's root A/CNAME record to the hosting."
echo ""
echo "   Quick option: Cloudflare Pages → Create project → Direct upload → www/"
echo ""
echo -e "${CYAN}Your API endpoint:${RESET} https://api.${DOMAIN}"
echo ""
