# ShadowCypher Private Repo + Self-Hosted Releases — Deployment Checklist

## Phase 1: GitHub (Immediate)

- [ ] **Make repository private**
  - Go to: `github.com/jakes1345/ShadowCypher/settings`
  - Danger Zone → "Make private" → Confirm
  - Time: 2 minutes

## Phase 2: Releases Server Setup (releases.shadowcypher.site)

- [ ] **Prepare server**
  - SSH into your releases server
  - Have sudo access or run as root
  
- [ ] **Run automated setup**
  ```bash
  curl -s https://raw.githubusercontent.com/jakes1345/ShadowCypher/main/.github/setup-releases-server.sh | sudo bash
  ```
  - Creates `/var/www/releases` directory structure
  - Sets up `deploy` user with SSH
  - Installs Nginx + SSL support
  - Time: 5 minutes

- [ ] **Generate deploy SSH key**
  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/releases_deploy_key -N ""
  cat ~/.ssh/releases_deploy_key.pub
  ```
  - Copy public key output

- [ ] **Add public key to releases server**
  ```bash
  # On releases server:
  echo "your_public_key_here" >> /home/deploy/.ssh/authorized_keys
  chmod 600 /home/deploy/.ssh/authorized_keys
  chown deploy:deploy /home/deploy/.ssh/authorized_keys
  ```

- [ ] **Set up SSL certificate**
  ```bash
  # On releases server:
  sudo certbot certonly --standalone \
    -d releases.shadowcypher.site \
    -m admin@shadowcypher.site
  sudo systemctl reload nginx
  ```
  - Time: 5 minutes

- [ ] **Test releases server**
  ```bash
  curl https://releases.shadowcypher.site/
  # Should return index.html
  ```

## Phase 3: GitHub Actions Setup

- [ ] **Add GitHub Actions secrets**
  - Go to: `github.com/jakes1345/ShadowCypher/settings/secrets/actions`
  
  Add 3 secrets:
  
  1. **`RELEASE_SERVER_HOST`**
     - Value: `releases.shadowcypher.site` (or IP)
  
  2. **`RELEASE_SERVER_USER`**
     - Value: `deploy`
  
  3. **`RELEASE_SERVER_SSH_KEY`**
     - Value: (Contents of `~/.ssh/releases_deploy_key`)
     - ⚠️ Make sure it includes `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`

- [ ] **Test workflow manually**
  ```bash
  # Create a test release on GitHub
  git tag v0.0.1
  git push origin v0.0.1
  # Go to Releases → Create Release → Publish
  ```
  - Attach a test file (e.g., test.txt)
  - Watch GitHub Actions: `Actions → Upload Releases to CDN`
  - Should upload to releases.shadowcypher.site
  - Time: 5 minutes

## Phase 4: Website Deployment

- [ ] **Deploy download page**
  ```bash
  ./‌.github/deploy-download-page.sh shadowcypher.site deploy
  ```
  - Uploads `download_page.html` to website
  - Time: 2 minutes

- [ ] **Create web route**
  - Website should serve at: `/download` or `/download.html`
  - Link from homepage navigation

- [ ] **Test download page**
  - Visit: `https://shadowcypher.site/download`
  - Should load version from `/api/latest`
  - Download buttons should work

## Phase 5: Verification

- [ ] **Check /api/latest endpoint**
  ```bash
  curl https://api.shadowcypher.site/api/latest
  # Should return JSON with version info
  ```

- [ ] **Verify releases server**
  - List releases: `https://releases.shadowcypher.site/latest/`
  - Should show all files

- [ ] **Test full download flow**
  1. Visit `shadowcypher.site/download`
  2. Click download button
  3. File should download from releases.shadowcypher.site
  4. Check SHA256SUMS match

- [ ] **Remove GitHub releases**
  - Delete old releases from GitHub
  - Or archive them (read-only)

## Phase 6: Cleanup

- [ ] **Remove GitHub links from docs**
  - Check README.md for GitHub references
  - Update to point to shadowcypher.site instead

- [ ] **Update installation instructions**
  - Change download links to website
  - Update build scripts if needed

- [ ] **Monitor first release**
  - Create v1.0.0 release
  - Verify GitHub Actions uploads correctly
  - Test download from website
  - Check server logs for any issues

## Rollback Plan

If something breaks:

1. **Releases stop working?**
   - SSH into releases.shadowcypher.site
   - Check Nginx: `sudo systemctl status nginx`
   - Check disk space: `df -h /var/www`
   - View logs: `sudo tail -f /var/log/nginx/error.log`

2. **GitHub Actions fails?**
   - Check secrets are set correctly
   - Verify SSH key format (must be PEM)
   - Test SSH manually: `ssh -i key deploy@releases.shadowcypher.site`

3. **Fallback:**
   - Keep GitHub releases active temporarily
   - Point `/api/latest` back to GitHub
   - Revert workflow changes

## Timeline

| Phase | Task | Time |
|-------|------|------|
| 1 | Make repo private | 2 min |
| 2 | Setup releases server | 15 min |
| 3 | GitHub Actions secrets | 3 min |
| 4 | Deploy website | 2 min |
| 5 | Test everything | 10 min |
| **Total** | | **~30 min** |

## Contacts & Docs

- **Releases Server Guide:** `.github/RELEASES_SETUP.md`
- **Setup Script:** `.github/setup-releases-server.sh`
- **Automated Deploy:** `.github/deploy-download-page.sh`
- **Download Page:** `shadowcypher/ui/download_page.html`
- **API Endpoint:** `shadowcypher/main.py` → `/api/latest`

---

**Status: Ready for deployment ✓**

All code changes pushed to main. Follow checklist to complete setup.
