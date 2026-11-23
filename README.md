<p align="center">
  <img src="www/icon-192.png" width="100" alt="ShadowCypher logo"/>
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

ShadowCypher puts network monitoring, a CVE feed, mail, chat, file storage and a local AI assistant in one place. You can self-host it, and it sends no telemetry. Syncing scan results to your account is off until you turn it on.

It started as shell scripts I wrote to debug real network problems, because the commercial tools kept phoning home. Most of what's here exists because I needed it.

## What's in this repo

| Part | What it is | Where |
|---|---|---|
| Desktop app | Qt6 C++ Widgets UI, a C++ background daemon and the ShadowScript runtime | [`shadowcypher-qt/`](shadowcypher-qt/) |
| Web app and website | Single-page HTML/JS app plus the site pages, no build step | [`www/`](www/) |
| Blog | Static HTML posts | [`blog/`](blog/) |
| API | Cloudflare Worker in TypeScript | [`backend/api/`](backend/api/) |
| ShadowOS | Arch Linux live ISO | [`shadowos/`](shadowos/) |
| Android | Native Kotlin/Compose app (dashboard, devices, incidents, CVEs, AI, missions) | [`android/`](android/) |
| Guardian agent | Python network agent, the last Python in the project | [`agent/`](agent/) |

## Desktop app

The window talks to a C++ daemon over a local socket (`$XDG_RUNTIME_DIR/shadowcypher-daemon.sock`, owner-only). The daemon handles LAN discovery from the neighbour table, new-device incidents, the hardware watch described below, NVD lookups, the Counter-Intel checks and chat with a local Ollama model. Pages that wrap command-line tools (Network, OSINT, Vuln, the Threat page's package audit) start those tools themselves.

On Linux the daemon also watches what is plugged into the computer, because a "USB stick" or a charging cable can be a keyboard that types commands the moment it is connected. It raises an incident for:

- a keyboard, USB or Bluetooth, that this computer has not used before, and with higher severity one that is also a storage drive or a network adapter;
- a USB network adapter it has not used before, since traffic can be routed through one;
- a Flipper Zero, by the names its firmware gives it, and a Digispark board set up as a keyboard.

It reads what the kernel reports about each device (`/sys/bus/usb/devices`, `/proc/bus/input/devices`) and never reads keystrokes. It reports; it does not block, so the typing has already happened by the time the incident appears. A device that copies the IDs and names of a keyboard you already use is not noticed, and a Flipper Zero or other tool whose owner changed its defaults shows up only as a new keyboard. Whatever was plugged in the first time the daemon ran is taken as yours.

Ghost mode is the only part that needs root. Turning it on or off runs `shadowcypher-privacy-helper` through `pkexec`, which starts Tor and sets up an iptables kill-switch. The daemon only reports its status.

| Page | What it does |
|---|---|
| Dashboard | CPU, memory and network stats, plus a summary from the daemon |
| Guardian | Devices on the network and open incidents from the daemon, including the hardware watch's. Can upload the device list to your account if you enable sync in Settings |
| Network Ops | Host discovery (`arp-scan`, or `nmap -sn`), `nmap -sV` service scans and `tcpdump` capture |
| Threat Intel | Recent CVEs from NVD, and a local package audit with `arch-audit` (falls back to `pacman -Q`) |
| OSINT | `whois`, `dig`, theHarvester, subfinder, amass and Shodan lookups on a domain or IP |
| Vuln | Runs nikto, sqlmap, nmap NSE scripts and searchsploit |
| Counter-Intel | Checks for ARP spoofing, promiscuous interfaces, DNS leaks, rogue DHCP, TLS interception and traffic anomalies |
| Arsenal | Shows which of 24 security tools are installed, with an install hint for each missing one |
| AI Assistant | Chat with a local Ollama model through the daemon |
| ShadowScript | Write and run missions in the ShadowScript language |
| Chat, Shadow Mail, Shadow Drive, Calendar | Your ShadowCypher account services, from the desktop |
| Ghost Mode | Tor plus the kill-switch, with Tor, DNS and MAC status |
| CVE Feed | NVD search, recent CVEs, and an `nmap -sV` scan of a target matched against NVD |
| Settings | API key, Ollama endpoint, alerts and scan sync |

The CVE Feed page shows EPSS scores (from the FIRST.org API) and CISA KEV status (from the CISA catalog). The daemon fetches both when you load the feed and caches them for 12 hours. If a fetch fails, those columns stay empty.

ShadowScript missions run on `shadowcypher-runtime`, a native Qt/C++ executable with no Python dependency. Example missions and lessons are in [`shadowscript/`](shadowscript/). See [`shadowcypher-qt/core/README.md`](shadowcypher-qt/core/README.md) for the language and the module calls it supports.

## Web app and API

The web app and the desktop app use the same API, a Cloudflare Worker backed by:

| Need | Service |
|---|---|
| Accounts and database | Supabase (Auth and PostgreSQL), mirrored to Neon |
| Real-time chat | Cloudflare Durable Objects (WebSocket rooms) |
| File storage | Cloudflare R2 |
| Mail | Cloudflare Email Routing in, Resend out |
| Desktop updates | Cloudflare KV |

**Sign-in.** You sign up with a handle, and your address becomes `handle@shadowcypher.site`. The web app signs in against Supabase Auth, and API calls use a personal key (`sc_live_…`) as a bearer token. The desktop app signs in through your browser: it asks the API for a device code, you approve it at shadowcypher.site/device, and the app picks up the key. You can also paste a key.

**Split password.** New accounts created on the web app use a split-password scheme when the browser supports it. Your device stretches the password with Argon2id and sends only a derived login secret to Supabase. The other half unlocks your OpenPGP identity key. The server stores that key only in locked form, and it is only unlocked on your device. Older accounts are moved to the split password the next time they sign in on the web app, and get an identity key then. The desktop and Android apps never see your password: they sign in through the browser.

**What is encrypted.** Chat messages are encrypted in the browser with AES-GCM while the chat vault is unlocked. The key is derived from your password at sign-in, or from a passphrase you type into the vault dialog, and it's kept in memory only. Others in a room can read those messages only if they use the same passphrase. For accounts with an identity key, mail bodies are stored encrypted to that key (zero-access): the server encrypts each message as it arrives and keeps only the ciphertext, and your browser opens it with your unlocked key. Mail from outside ShadowCypher still arrives in the clear over SMTP, so the server sees it once on the way in. Subject, sender and recipient are not encrypted. Drive files uploaded from the web app are encrypted to your key in the browser before upload, so the server only ever holds ciphertext. The desktop app can't open encrypted mail or files yet; it points you to the web app.

**Plans.** The hosted service has a free community plan and paid Guardian Pro and Operator plans, which raise the limits on agents, scan history, alerts and team features.

## ShadowOS

Still in development. An Arch-based live ISO with Hyprland, `linux-hardened`, nftables, AppArmor, Tor and dnscrypt-proxy, with the ShadowCypher desktop app built in. `shadow-mode <normal|privacy|ghost|dev|gaming>` switches the firewall, Tor routing and a few services in one command.

```bash
cd shadowos
sudo bash build.sh     # on an Arch host (needs archiso, cmake and Qt6)
bash build-docker.sh   # on any other host with Docker
bash qemu-test.sh      # boot the newest ISO in out/ with QEMU
```

See [`shadowos/README.md`](shadowos/README.md) and [`shadowos/INSTALL.md`](shadowos/INSTALL.md).

## Build from source

**Desktop app.** You need CMake 3.16+, Ninja, a C++17 compiler, OpenSSL, and Qt 6.4 or newer (Core, Widgets, Network, Concurrent, WebSockets, and Test for the tests).

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

ShadowCypher moved from Python and GTK to Qt6 C++, and the old Python app has been removed. The one piece left is the Guardian agent (`agent/`), which the site still installs with `agent/install.sh`. The runtime has a native agent mode (`shadowcypher-runtime agent-run`), but it doesn't cover everything the Python agent does yet. New desktop work goes in `shadowcypher-qt/`.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report vulnerabilities as described in [SECURITY.md](SECURITY.md).

## Legal

ShadowCypher is built for authorized security testing, research and education. The offensive tools assume you have explicit written permission to test the target. Using them against systems you don't own or aren't authorized to test is illegal. The authors accept no liability for misuse.

Released under the [MIT License](LICENSE).
