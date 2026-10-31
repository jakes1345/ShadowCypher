# Native runtime

`shadowcypher-runtime` is the Qt6/C++ execution backend. It builds and runs without
Python. The desktop ShadowScript page uses this executable directly; it does not
need the Python IPC daemon to execute missions.

This is an incremental migration. Other desktop pages still use the Python daemon,
and the native agent and MCP server do not yet replace every feature of their
Python counterparts. Keep existing installations until the required features are
available here. No Python fallback is performed by this runtime.

## Build and test

Requires C++17, CMake, and Qt 6.4 or newer (Core and Network; Qt Test for tests).
Building the full desktop additionally requires Widgets, Concurrent, WebSockets,
and OpenSSL. Build artifacts can stay outside the checkout:

```sh
cmake -S shadowcypher-qt/core -B /tmp/shadowcypher-runtime -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/shadowcypher-runtime
ctest --test-dir /tmp/shadowcypher-runtime --output-on-failure
```

The full desktop CMake build also builds the runtime. `cmake --install` installs
both executables; ShadowOS stages them together. To run from a build directory,
keep the runtime in its `core/` subdirectory next to the desktop executable.

## ShadowScript

```sh
shadowcypher-runtime check mission.shadow
shadowcypher-runtime script mission.shadow
shadowcypher-runtime script mission.shadow --config-ini ~/.config/shadowcypher/config.ini
```

`check` validates syntax only. It does not check external tools or run a mission.
Supported language constructs include variables, target selection, conditionals,
FOR/WHILE, BREAK/RETURN, MAP/FILTER/YIELD, relative LOAD, output, sleep, and UNSAFE
blocks. C++, Go, and Rust blocks execute in separate processes; they require their
respective compilers. Rust blocks retain the `serde_json` Cargo dependency.

`!sys` and `!pipe` require UNSAFE and split arguments without shell interpretation.
Pipelines, redirection, and shell expansion are not implicit. Native function calls
also require UNSAFE. Compilation occurs in a private temporary directory, removed
when the call finishes. Process timeouts, cancellation, output limits, loop limits,
and LOAD nesting limits apply. These controls are not an operating-system sandbox.

SCAN supports up to 4096 TCP ports per call. AI uses the configured Ollama service;
it does not include the Python engine's cloud fallback, RAG, team prompts, or
ShadowGuard implementation. Its analysis is limited to explicitly supplied text.

Implemented module calls:

- `network`: `arp_scan`, `port_scan`, `port_scan_tcp_connect`
- `recon`: `quick_scan`, `deep_recon`, `subdomain_enum`, `amass_enum`
- `osint`: `whois_lookup`, `subnet_info`, `email_mx_check`
- `host`: `lynis_audit`, `rkhunter_scan`
- `wireless`: `list_interfaces`, `scan_networks`, `scan_wifi`
- `forensics`: `generate_hashes`, `hash_file`, `extract_metadata`, `extract_strings`, `binwalk_scan`
- `vuln` and `web`: `nuclei_scan`

External tools must be installed separately. Some third-party tools may themselves
use Python. Unported module calls and directives, including SWARM, fail explicitly.
Bundled missions that use those operations are not yet fully runnable here.

## Guardian agent preview

```sh
shadowcypher-runtime agent-once --config ~/.shadowcypher/config.json
shadowcypher-runtime agent-run --config ~/.shadowcypher/config.json --interval 600
```

Configuration accepts `api_base`, `api_key`, `ollama_url`, and `ollama_model`.
Protect the configuration with owner-only permissions. Desktop INI configuration
uses `api_key`, `ollama/endpoint`, and optional `ollama/model` instead.

The native agent registers the host, sends heartbeats, and uploads the current
neighbor table. Linux uses `ip -j neigh`; other platforms use `arp -a`. This does
not discover hosts absent from the neighbor table or fingerprint their services.
Router/DNS/firewall/hardening audits, incident detection, automatic updates, device
login, and service installation remain in the Python agent.

The default state file is `~/.shadowcypher/native-agent-state.json`, separate from
the Python agent. Override it with `--state`. Only one native agent may use a state
file at a time. Completed remote mission results are saved before submission and
retried after a transmission failure. An interruption during mission execution
still requires checking the server-side mission state.

Add `--missions` to allow the agent to claim remote work and execute it with the
native ShadowScript engine. This does not fall back to executing scripts as shell
commands. Do not enable it for queues containing unported module calls.

## MCP preview

Configure an MCP client to run `shadowcypher-runtime mcp` over standard input/output.
Use `--config` or `--config-ini` to select Ollama settings. Standard output contains
JSON-RPC messages only; diagnostics go to standard error.

The current tool set is `shadowcypher_network_scan` (neighbor-table discovery),
`shadowcypher_port_scan`, and `shadowcypher_ai_query`. The intelligence, offensive,
and unified binary-analysis MCP tool sets remain in Python.

`shadowcypher-runtime capabilities` reports the available modes and MCP tools.
