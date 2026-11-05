<p align="center">
  <img src="icon-192.png" width="100" alt="ShadowCypher logo"/>
</p>

<h1 align="center">ShadowCypher</h1>
<h3 align="center">A sovereign personal security platform</h3>

<p align="center">
  <img src="https://img.shields.io/badge/desktop-Qt6%20C%2B%2B-41cd52?style=flat-square" alt="Qt6 C++"/>
  <img src="https://img.shields.io/badge/backend-Cloudflare%20Workers-f38020?style=flat-square" alt="Cloudflare Workers"/>
  <img src="https://img.shields.io/badge/license-MIT-10b981?style=flat-square" alt="MIT license"/>
</p>

<p align="center">
  <a href="https://shadowcypher.site">shadowcypher.site</a>
</p>

---

ShadowCypher is network monitoring, a live CVE threat feed, encrypted mail, chat and drive, and a local AI assistant in one platform. It is self-hostable and has no telemetry.

It started as shell scripts written to debug real network problems, because the commercial tools kept phoning home. Everything in here exists because it was needed.

## What's in this repo

| Part | What it is | Where |
|---|---|---|
| Desktop app | Qt6 C++ Widgets UI plus a C++ background daemon | [`shadowcypher-qt/`](shadowcypher-qt/) |
| Web app | Single-page HTML/JS, no build step | [`www/`](www/) |
| API | Cloudflare Worker in TypeScript | [`backend/api/`](backend/api/) |
| ShadowOS | Arch Linux live/installable ISO | [`shadowos/`](shadowos/) |
| Android | Capacitor app that ships a copy of the web app | [`android/`](android/) |
| Website and blog | `index.html`, the other root `.html` pages, `blog/` | repo root |

## Desktop app

The UI talks to a C++ daemon over local IPC. The daemon does the scans, incident tracking, CVE feed, Ghost mode and AI work, so the interface stays responsive. Ghost mode's kill-switch runs through a small root helper started with `pkexec`.

| Page | What it does |
|---|---|
| Dashboard | Daemon and system overview |
| Network | Network monitoring |
| Guardian | Network and device protection |
| Threat | CVE feed from NVD, plus a local package audit (`arch-audit` / `pacman`) |
| Vuln | Vulnerability scanning |
| OSINT | Lookups on a domain, IP or company |
| Counter-Intel | Detects when you are the target |
| Ghost | Privacy and anonymity controls, with a kill-switch |
| Arsenal | Live check of which security tools are installed on the machine |
| ShadowScript | Write and run missions in the ShadowScript language |
| AI | The AI assistant |
| Mail, Chat, Drive, Calendar | The ShadowCypher account services, from the desktop |

ShadowScript missions run on `shadowcypher-runtime`, a native Qt/C++ executable with no Python dependency. See [`shadowcypher-qt/core/README.md`](shadowcypher-qt/core/README.md) for the language and the module calls it supports.

## Web app and API

The web app and the desktop app use the same API, a Cloudflare Worker backed by:

| Need | Service |
|---|---|
| Accounts and database | Supabase (Auth and PostgreSQL), mirrored to Neon |
| Real-time chat | Cloudflare Durable Objects (WebSocket rooms) |
| File storage | Cloudflare R2 |
| Mail | Cloudflare Email Routing in, Resend out |
| Desktop updates | Cloudflare KV |

**Sign-in.** You sign up with a handle. The web app signs in against Supabase Auth, and API calls use a personal key (`sc_live_…`) as a bearer token. The desktop app signs in through your browser: it asks the API for a device code, you approve it at shadowcypher.site/device, and the app picks up the key.

**Split password.** On accounts that use the split-password scheme, your device stretches the password with Argon2id and sends only a derived login secret. Your OpenPGP identity key never leaves the device.

**Plans.** The hosted service has a free community plan and paid Guardian Pro and Operator plans, which raise the limits on agents, scan history, alerts and team features.

## ShadowOS

An Arch-based live and installable ISO with Hyprland, a hardened kernel, and pentest, dev and gaming tooling. `shadow-mode <normal|dev|pentest|privacy|ghost|undercover>` switches the firewall, DNS and autostart apps in one command.

```bash
cd shadowos
bash build.sh          # on an Arch host (needs archiso)
bash build-docker.sh   # on any other host
bash qemu-test.sh      # boot the result in QEMU
```

See [`shadowos/README.md`](shadowos/README.md) and [`shadowos/INSTALL.md`](shadowos/INSTALL.md).

## Build from source

**Desktop app.** You need CMake 3.16+, Ninja, a C++17 compiler, OpenSSL, and Qt 6.4 or newer (Core, Widgets, Network, Concurrent, WebSockets).

```bash
cmake -S shadowcypher-qt -B build -G Ninja -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

**API.** You need Node.js. Copy `.dev.vars.example` to `.dev.vars` and fill it in. Production secrets go in with `wrangler secret put` and are never committed.

```bash
cd backend/api
npm install
npm run dev          # local server on http://localhost:8787
npm run typecheck
npm test
```

**Web app.** There is no build step. Serve `www/` with any static file server.

## Self-hosting

See the guide at [shadowcypher.site/self-host](https://shadowcypher.site/self-host).

## Status of the Python code

ShadowCypher moved from Python and GTK to Qt6 C++, and the old Python app has been removed. The one piece left is the Guardian agent (`agent/`), which the site still installs with `agent/install.sh` until the C++ daemon ships as a download. New desktop work goes in `shadowcypher-qt/`.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report vulnerabilities as described in [SECURITY.md](SECURITY.md).

## Legal

ShadowCypher is built for authorized security testing, research and education. The offensive tools assume you have explicit written permission to test the target. Using them against systems you don't own or aren't authorized to test is illegal. The authors accept no liability for misuse.

Released under the [MIT License](LICENSE).
