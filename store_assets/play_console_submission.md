# Play Console Submission Guide
## Two separate app listings — do NOT combine

---

## App 1: Guardian — Network Monitor
**Package:** `site.shadowcypher.app`
**AAB:** `releases/ShadowCypher-Guardian-v2.1-final.aab`
**Privacy policy URL:** `https://shadowcypher.site/privacy.html`

### Store listing
| Field | Value |
|---|---|
| App name | Guardian — Network Monitor |
| Short description | Monitor your network, devices & security incidents from anywhere. |
| Category | Tools |
| Tags | network monitor, security, home network, device tracker |

### Full description
Paste from: `store_assets/guardian_listing.md`

### Graphics
| Asset | File | Required size |
|---|---|---|
| App icon | `store_assets/icon_guardian_512.png` | 512×512 ✅ |
| Feature graphic | `store_assets/feature_guardian.png` | 1024×500 ✅ |
| Screenshots | `store_assets/screenshots/guardian_*.png` | min 2 ✅ (6 available) |

---

### Data Safety form — Guardian

**Does the app collect or share any of the required user data types?**
→ **Yes**

Go through each category:

| Category | Collected? | Shared? | Notes |
|---|---|---|---|
| Location (precise) | No | — | |
| Location (approximate) | No | — | |
| Personal info — Name | No | — | |
| Personal info — Email | No | — | App doesn't ask for email; auth is via API key only |
| Personal info — User IDs | No | — | |
| Financial info | No | — | |
| Health & fitness | No | — | |
| Messages | No | — | |
| Photos & videos | No | — | |
| Audio files | No | — | |
| Files & docs | No | — | |
| Calendar | No | — | |
| Contacts | No | — | |
| App activity — App interactions | No | — | |
| App activity — In-app search history | No | — | |
| App activity — Installed apps | No | — | |
| App activity — Other actions | No | — | |
| Web browsing history | No | — | |
| App info & performance — Crash logs | No | — | No crash SDK |
| App info & performance — Diagnostics | No | — | |
| Device or other identifiers | No | — | No ad ID, no fingerprint |

**The one thing declared:**
- **Other data types → Other:** API key (user-entered, stored locally on-device only via Android SharedPreferences). It is used solely to authenticate requests to the user's own ShadowCypher account. It is NOT collected by ShadowCypher the company — it stays on the device.

**Is the data encrypted in transit?** Yes (HTTPS/TLS 1.3)

**Can users request deletion?** Yes — delete account at shadowcypher.site/dashboard or email privacy@shadowcypher.site

---

### Content Rating — Guardian

In Play Console → Content Rating → fill out IARC questionnaire:

| Question | Answer |
|---|---|
| Violence | None |
| Sexual content | None |
| Profanity | None |
| Substances (drugs/alcohol) | None |
| User-generated content | No |
| Social features (chat, sharing) | No |
| Location sharing | No |
| Digital purchases | No |
| Unrestricted internet access | Yes (connects to user's own API) |

→ **Expected rating: Everyone**

---

---

## App 2: Shadow AI
**Package:** `site.shadowcypher.assistant`
**AAB:** `releases/ShadowCypher-ShadowAI-v1.4-final.aab`
**Privacy policy URL:** `https://shadowcypher.site/privacy.html`

### Store listing
| Field | Value |
|---|---|
| App name | Shadow AI — Voice Assistant |
| Short description | Offline voice assistant. Security-aware. No cloud. No listening. |
| Category | Tools |
| Tags | voice assistant, offline assistant, security assistant, no cloud |

### Full description
Paste from: `store_assets/shadow_ai_listing.md`

### Graphics
| Asset | File | Required size |
|---|---|---|
| App icon | `store_assets/icon_shadow_ai_512.png` | 512×512 ✅ |
| Feature graphic | `store_assets/feature_shadow.png` | 1024×500 ✅ |
| Screenshots | `store_assets/screenshots/shadow_*.png` | min 2 ✅ |

---

### Data Safety form — Shadow AI

| Category | Collected? | Shared? | Notes |
|---|---|---|---|
| Location | No | — | |
| Personal info | No | — | |
| Financial info | No | — | |
| Health & fitness | No | — | |
| Messages | No | — | |
| Photos & videos | No | — | |
| Audio files | **No** | — | Voice is processed 100% on-device via Vosk (offline model). No audio is recorded, stored, or transmitted. Ever. |
| Files & docs | No | — | |
| Calendar | No | — | |
| Contacts | No | — | |
| App activity | No | — | |
| Web browsing history | No | — | |
| Crash logs / diagnostics | No | — | |
| Device or other identifiers | No | — | |

**Microphone permission note for the form:**
When Play Console asks about microphone/audio permission: select "For app functionality" → "Voice or sound commands" → "Not shared with third parties" → "Users can see what's recorded: No (processed on-device only, never stored)"

**Is data encrypted in transit?** Yes (HTTPS — only for web search fallback and Guardian API calls)

**Can users request deletion?** Yes — no data is stored to delete. API key can be cleared from app settings.

---

### Content Rating — Shadow AI

| Question | Answer |
|---|---|
| Violence | None |
| Sexual content | None |
| Profanity | None |
| Substances | None |
| User-generated content | No |
| Social features | No |
| Location sharing | No |
| Digital purchases | No |
| Unrestricted internet access | Yes (web search fallback, user-initiated) |

→ **Expected rating: Everyone**

---

## CI Secrets to add (GitHub repo settings → Secrets)

Go to: `github.com/jakes1345/ShadowCypher/settings/secrets/actions`

| Secret name | Value |
|---|---|
| `KEYSTORE_B64` | Contents of `store_assets/keystore.b64` — paste the whole file |
| `KEYSTORE_PASS` | `ShadowCypher2026!` |
| `KEY_PASS` | `ShadowCypher2026!` |

## Keystore backup reminder

`android/shadowcypher_release.keystore` is in `.gitignore` — it does NOT get pushed.
**Back this file up externally RIGHT NOW** (USB drive, Google Drive, encrypted cloud) before you forget.
Losing it = can never update the Play Store apps. Google does not recover it.

Command to copy it:
```bash
cp android/shadowcypher_release.keystore ~/Desktop/shadowcypher_release.keystore.BACKUP
```

---

## Upload order

1. Go to play.google.com/console
2. Create app → Guardian (choose "App", "Free", "Android")
3. Fill store listing, upload icon + feature graphic + screenshots
4. Paste privacy policy URL
5. Fill Data Safety form (table above)
6. Fill Content Rating questionnaire
7. Create release → Production → upload `releases/ShadowCypher-Guardian-v2.1-final.aab`
8. Submit for review

Repeat steps 2–8 for Shadow AI.

Review typically takes 3–7 days for new apps.
