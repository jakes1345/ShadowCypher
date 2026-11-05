<p align="center">
  <img src="shadowcypher-qt/assets/icon-512.png" width="120" alt="ShadowCypher logo"/>
</p>

<h1 align="center">SHADOWCYPHER</h1>
<h3 align="center">A personal security platform you can run yourself</h3>

<p align="center">
  <img src="https://img.shields.io/badge/desktop-Qt6%20C%2B%2B-41cd52?style=flat-square" alt="Qt6 C++"/>
  <img src="https://img.shields.io/badge/API-Cloudflare%20Workers-f38020?style=flat-square" alt="Cloudflare Workers"/>
  <img src="https://img.shields.io/badge/AI-local%20(Ollama)-black?style=flat-square" alt="Local AI"/>
  <img src="https://img.shields.io/badge/license-MIT-10b981?style=flat-square" alt="MIT"/>
</p>

---

ShadowCypher watches your network, tracks the vulnerabilities that matter to your devices, and gives you encrypted mail, chat and file storage under your own handle, with no telemetry. It started as late-night scripts for real network problems, because the commercial tools kept phoning home.

## What's in this repo

| Part | Where | What it is |
|---|---|---|
| **Desktop app** | [`shadowcypher-qt/`](shadowcypher-qt) | Qt6 C++ app plus a background daemon. Network Guardian (devices, incidents), CVE feed, Ghost mode (Tor kill-switch), Shadow Mail, Drive, Calendar, local AI. Signs in through the browser. |
| **Web app** | [`www/`](www) | The site at [shadowcypher.site](https://shadowcypher.site): accounts, dashboard, encrypted chat and mail, drive. Single-page HTML/JS, no build step. |
| **API** | [`backend/api/`](backend/api) | Cloudflare Worker (TypeScript). Auth, incidents, scans, threat feed, mail, chat (Durable Objects), files (R2). |
| **Android** | [`android/`](android) | **Guardian**, the security app, and **Shadow AI**, an assistant you can set as the phone's default. |
| **ShadowOS** | [`shadowos/`](shadowos) | Arch Linux ISO (Hyprland) with the desktop app built in. |

## Desktop app

Needs CMake, a C++17 compiler, Qt 6 (`base`, `websockets`, `wayland` on Wayland) and OpenSSL.

```bash
cmake -S shadowcypher-qt -B build -G Ninja -DBUILD_TESTING=ON
cmake --build build && ctest --test-dir build --output-on-failure
./build/shadowcypher
```

`sudo cmake --install build` installs the app, the daemon, and the Ghost mode privacy helper with its polkit policy. Ghost mode needs that install, because the kill-switch runs through `pkexec`.

## API

```bash
cd backend/api
npm ci
npm run dev        # local Worker
npm run typecheck
npm test
```

Secrets go through `wrangler secret put`; see [`CLAUDE.md`](CLAUDE.md) for the list.

## ShadowOS

```bash
cd shadowos && sudo ./build.sh     # on Arch, with archiso
cd shadowos && ./build-docker.sh   # on any host with Docker
bash shadowos/qemu-test.sh         # boot the ISO in QEMU
```

See [`shadowos/README.md`](shadowos/README.md).

## Security

Report vulnerabilities as described in [`SECURITY.md`](SECURITY.md).

## License

[MIT](LICENSE)
