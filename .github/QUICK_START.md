# ShadowCypher Private Repo + Releases — Quick Start

**Status: Repo is now private ✓**

## Next: 3 Steps to Go Live

### Step 1: Releases Server Setup (15 min)

On your `releases.shadowcypher.site` server:

```bash
# Download and run automated setup
curl -s https://raw.githubusercontent.com/jakes1345/ShadowCypher/main/.github/setup-releases-server.sh | sudo bash

# This creates:
# - /var/www/releases directory structure
# - 'deploy' SSH user
# - Nginx config (HTTP, waiting for SSL)
```

**Then manually:**

```bash
# Generate SSH keypair for GitHub Actions
ssh-keygen -t ed25519 -f ~/.ssh/releases_deploy_key -N ""
cat ~/.ssh/releases_deploy_key.pub
# Copy public key output
```

```bash
# Add public key to releases server
ssh deploy@releases.shadowcypher.site
# Paste public key into ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
exit
```

```bash
# Set up SSL certificate
sudo certbot certonly --standalone \
  -d releases.shadowcypher.site \
  -m admin@shadowcypher.site
sudo systemctl reload nginx

# Test it
curl https://releases.shadowcypher.site/
# Should return index.html
```

### Step 2: GitHub Actions Secrets (5 min)

1. Go to: `github.com/jakes1345/ShadowCypher/settings/secrets/actions`
2. Add 3 secrets:

**Secret 1: `RELEASE_SERVER_HOST`**
- Value: `releases.shadowcypher.site`

**Secret 2: `RELEASE_SERVER_USER`**
- Value: `deploy`

**Secret 3: `RELEASE_SERVER_SSH_KEY`**
- Value: (contents of `~/.ssh/releases_deploy_key` — private key)
- Must include `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`

### Step 3: Test Full Pipeline (10 min)

```bash
# Create test release on GitHub
git tag v0.0.1-test
git push origin v0.0.1-test

# Go to: github.com/jakes1345/ShadowCypher/releases
# Create Release from tag v0.0.1-test
# Attach test file: test.txt (any content)
# Click "Publish release"
```

**Watch GitHub Actions:**
- Go to: `Actions → Upload Releases to CDN`
- Should see workflow running
- Should upload to `releases.shadowcypher.site/v0.0.1-test/`

**Verify:**
```bash
curl https://releases.shadowcypher.site/v0.0.1-test/
# Should list test.txt
```

---

## Current Code State

✅ **Already committed to main:**
- `/chat/vault/unlock` endpoint (2FA for messages)
- `download_page.html` (website download UI)
- `.github/setup-releases-server.sh` (automated server setup)
- `.github/upload-releases.yml` (CI/CD workflow)
- `.github/RELEASES_SETUP.md` (detailed setup guide)
- `.github/DEPLOYMENT_CHECKLIST.md` (step-by-step)

---

## What's Protected Now

### Encrypted Group Messages
- Server: encrypted blobs only (can't decrypt)
- Device locked: can't access app
- Device unlocked: need vault password
- Vault password: required even if device seized

### Website Downloads
- All files served from releases.shadowcypher.site
- No GitHub releases linked
- Version info from `/api/latest` endpoint

### Source Code
- Repo is private (no public clone)
- GitHub links removed from code
- Self-hosted releases only

---

## Rollback If Needed

If something breaks during setup:

```bash
# Revert last few commits
git reset --soft HEAD~3
git status  # Review what reverts

# Or just re-run setup script on server
sudo bash setup-releases-server.sh
```

---

## Timeline

| Step | Time | Status |
|------|------|--------|
| Repo private | ✅ Done | Complete |
| Releases server setup | ⏳ Your turn | 15 min |
| GitHub Actions secrets | ⏳ Your turn | 5 min |
| Test pipeline | ⏳ Your turn | 10 min |
| **Total** | | **30 min** |

---

## You're Now

🔐 Private repo + Self-hosted releases + 2FA message protection

Everything is in place. Just need to:
1. Run the server setup script
2. Add 3 GitHub secrets
3. Test with a v0.0.1-test release

Then you can cut v1.0.0 and it'll auto-upload to your server.

Good luck! 🚀
