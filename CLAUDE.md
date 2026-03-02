# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is ShadowCypher

A self-hosted network administration dashboard with a dark "Mr. Robot" aesthetic. It provides real-time monitoring, network tools, firewall management, an AI assistant, and pentesting utilities — all through a single-page web UI backed by an Express server.

## Commands

```bash
# Start the server (runs on http://localhost:3000)
npm start

# Run all tests (requires SHORTEST_ANTHROPIC_API_KEY in .env.local)
npm test

# Run a single test suite
npx shortest tests/auth.test.ts
npx shortest tests/dashboard.test.ts
npx shortest tests/network.test.ts
npx shortest tests/tools.test.ts
npx shortest tests/hacking.test.ts
npx shortest tests/intelligence.test.ts
npx shortest tests/ai-assistant.test.ts
npx shortest tests/diagnostic.test.ts
```

Tests use [Shortest](https://github.com/antiwork/shortest) — an AI-powered natural-language browser testing framework. Tests are `.ts` files containing plain English descriptions of UI interactions, not traditional assertions.

## Architecture

**Monolithic single-file server**: Everything lives in `server.js` (~1770 lines). There is no build step, no TypeScript compilation, no bundler. The server is plain Node.js + Express.

### Backend (`server.js`)

- **Express server** on port 3000 serving static files from `public/` and a large REST API
- **Session-based auth** with bcryptjs password hashing; users stored in `users.json`
- **WebSocket server** (via `ws`) for the real-time terminal feature
- **Router integration**: supports local machine, OpenWrt (via SSH), and pfSense modes — configured via `router_config.json`
- **AI assistant**: proxies chat to a configurable LLM provider (Groq by default) with function-calling for system operations; config in `ai_config.json`
- **Shell command execution**: many endpoints run system commands via `child_process.exec` — this is intentional for the admin tool's purpose
- **Systemd service**: `shadow-cypher.service` for production deployment

### Frontend (`public/`)

- **Single-page app**: `index.html` (~1030 lines) contains all page sections as `<section class="page">` elements, switched via JS
- **`app.js`** (~460 lines): client-side logic — auth flow, page navigation via `go()` function, API calls via `api()` helper
- **`style.css`** (~1400 lines): dark theme with CSS custom properties (vars like `--cyan`, `--purple`, `--green`)
- No framework — vanilla HTML/CSS/JS

### Key API route groups

| Prefix | Purpose |
|--------|---------|
| `/api/auth/*` | Login, logout, session status, password change |
| `/api/router/*` | Router config, status, port forwarding, firewall (multi-router support) |
| `/api/overview`, `/api/cpu-history`, `/api/mem-history` | Dashboard system metrics |
| `/api/devices`, `/api/wifi` | Network device scanning, WiFi management |
| `/api/firewall/*`, `/api/portforward` | Local iptables firewall & port forwarding |
| `/api/tools/*` | Ping, traceroute, DNS lookup, whois, nmap, curl, WoL |
| `/api/services`, `/api/docker/*` | Systemd services & Docker container management |
| `/api/ai/*` | AI assistant config and chat |
| `/api/hacking/*`, `/api/pentest` | Shadow mode, pentesting tools |
| `/api/intel/*` | Intelligence: packet sniffing, IDS alerts, WiFi recon, threat feeds |
| `/api/diagnostic` | System health checks |

### Auth model

- `requireAuth` middleware guards mutating endpoints
- Read-only endpoints (GET) are generally unprotected
- Default credentials: `admin` / `shadow`

### Data files (gitignored, created at runtime)

- `users.json` — user accounts
- `router_config.json` — router connection settings
- `ai_config.json` — AI provider/key config
- `activity.log` — request logging
