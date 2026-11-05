# Native runtime

`shadowcypher-runtime` is the Qt6/C++ execution backend for ShadowScript, plus a native Guardian agent and a small MCP server. It builds and runs without Python. The desktop ShadowScript page starts this executable to run missions.

It doesn't yet do everything the old Python app did. The gaps are listed in each section below, and anything not ported fails with an explicit error rather than falling back to something else.

## Build and test

Requires C++17, CMake, and Qt 6.4 or newer (Core and Network; Qt Test for tests). Building the full desktop app also needs Widgets, Concurrent, WebSockets and OpenSSL. Build output can stay outside the checkout:

```sh
cmake -S shadowcypher-qt/core -B /tmp/shadowcypher-runtime -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/shadowcypher-runtime
ctest --test-dir /tmp/shadowcypher-runtime --output-on-failure
```

The full desktop CMake build also builds the runtime. `cmake --install` installs both executables, and the ShadowOS build stages them together. The desktop app looks for the runtime next to its own executable, then in a `core/` subdirectory, then on `PATH`, so running from a build directory works as is.

## ShadowScript

```sh
shadowcypher-runtime check mission.shadow
shadowcypher-runtime script mission.shadow
shadowcypher-runtime script mission.shadow --config-ini ~/.config/shadowcypher/config.ini
```

`check` validates syntax only. It does not check external tools or run a mission.

The language supports variables, target selection, conditionals, FOR/WHILE, BREAK/RETURN, MAP/FILTER/YIELD, relative LOAD, output, sleep and UNSAFE blocks. C++, Go and Rust blocks are compiled and run as separate processes, so they need `c++`, `go` or `cargo` installed. Rust blocks keep the `serde_json` Cargo dependency.

`!sys` and `!pipe` need UNSAFE and split their arguments without a shell. Pipelines, redirection and shell expansion don't happen implicitly. Native function calls also need UNSAFE. Compilation happens in a private temporary directory that is removed when the call finishes. Process timeouts, cancellation, output limits, loop limits and LOAD nesting limits apply. These controls are not an operating-system sandbox.

SCAN accepts up to 4096 TCP ports per call. AI calls go to the configured Ollama service and only analyse the text you pass in. There is no cloud fallback, RAG, team prompts or ShadowGuard here; those were part of the removed Python engine.

Implemented module calls:

- `network`: `arp_scan`, `port_scan`, `port_scan_tcp_connect`
- `recon`: `quick_scan`, `deep_recon`, `subdomain_enum`, `amass_enum`
- `osint`: `whois_lookup`, `subnet_info`, `email_mx_check`
- `host`: `lynis_audit`, `rkhunter_scan`
- `wireless`: `list_interfaces`, `scan_networks`, `scan_wifi`
- `forensics`: `generate_hashes`, `hash_file`, `extract_metadata`, `extract_strings`, `binwalk_scan`
- `vuln` and `web`: `nuclei_scan`

External tools (nmap, subfinder, amass, lynis, exiftool and so on) must be installed separately, and some of them use Python themselves. Other module calls and directives, including SWARM, fail with an error. Some missions in `shadowscript/missions/` use those, so not all of them run yet.

## Guardian agent preview

```sh
shadowcypher-runtime agent-once --config ~/.shadowcypher/config.json
shadowcypher-runtime agent-run --config ~/.shadowcypher/config.json --interval 600
```

The JSON config accepts `api_base`, `api_key`, `ollama_url` and `ollama_model`. Keep it readable by your user only. The desktop INI config uses `api_key`, `ollama/endpoint` and an optional `ollama/model` instead. `--interval` takes 10 to 86400 seconds.

The native agent registers the host, sends heartbeats and uploads the current neighbour table. On Linux it reads `ip -j neigh`; elsewhere it parses `arp -a`. It won't find hosts that aren't already in the neighbour table, and it doesn't fingerprint services. The router, DNS, firewall and hardening audits, incident detection, automatic updates, device login and service installation are still only in the Python agent (`agent/`).

The default state file is `~/.shadowcypher/native-agent-state.json`, separate from the Python agent's. Override it with `--state`. Only one native agent can use a state file at a time. Finished remote mission results are saved before they're sent and retried if sending fails. If the agent is interrupted while a mission is running, check the mission's state on the server.

Add `--missions` to let the agent claim remote missions and run them with the native ShadowScript engine. It never falls back to running a script as shell commands. Don't enable it for a queue that contains unported module calls.

## MCP preview

Point an MCP client at `shadowcypher-runtime mcp` over stdin/stdout. Use `--config` or `--config-ini` to pick the Ollama settings. Stdout carries JSON-RPC messages only; diagnostics go to stderr. Requests over 1 MiB are rejected.

There are three tools: `shadowcypher_network_scan` (reads the neighbour table), `shadowcypher_port_scan` and `shadowcypher_ai_query`. The intelligence, offensive and binary-analysis tool sets from the old Python MCP server haven't been ported.

`shadowcypher-runtime capabilities` prints the available modes and MCP tools as JSON.
