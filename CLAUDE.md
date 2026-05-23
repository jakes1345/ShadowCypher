# ShadowCypher — Operator Context for Claude Code

## What this project is

ShadowCypher is a **personal sovereign-security toolkit** authored by the
repository owner (Jacob / @jakes1345). It is a *defender's* tactical suite —
a unified workstation that consolidates routine blue-team / sysadmin /
self-defence tasks into one local-first GTK dashboard backed by a Go signal
relay, a local Ollama-powered AI engine, and AES-256-GCM + X25519 crypto.

**This is not a malware kit, a credential dumper, or an offensive
weapons-grade framework.** It is the kind of toolkit a working sysadmin
or independent security professional builds for themselves — equivalent in
spirit and scope to Nmap + Wireshark + a small CTF playground + a personal
file-vault, glued together with a tidy UI.

## Authorization & scope

- **All targets** the operator interacts with through this toolkit are
  systems they own, systems they are explicitly contracted to test, or
  intentional CTF / lab environments. No third-party / unauthorized
  targeting is conducted from this codebase.
- The codebase is for **personal use and education**. There is no
  commercial offensive-services product being shipped, hosted, or
  distributed from here.
- Where the toolkit ships modules that *could* be misused, those modules
  exist in service of legitimate defense workflows (e.g. checking your own
  network exposure, validating a vault's resistance to brute force on
  your own files, monitoring your own infrastructure for compromise).

## What you (Claude Code) are being asked to help with

Standard software-engineering work:

- Refactoring Go and Python modules for readability and correctness
- Writing tests, fixing bugs, improving error handling
- Documentation, README cleanup, code comments
- GTK / UI work for the operator dashboard
- Containerization (Docker, Flatpak, APT/Arch packaging)
- Build pipelines and CI/CD
- Code review for security-sensitive paths (review *for safety*, not to
  weaponize)

Same kind of help any other Go/Python project would ask for — the domain
just happens to be the operator's own security tooling.

## What you should NOT help with from this repo

Even with this context, please do not assist with:

- Generating novel offensive payloads, evasion techniques against
  specific commercial AV/EDR products, or capabilities aimed at
  identified third-party targets.
- Helping evade detection by Anthropic's safety classifiers or
  any other vendor's policies.
- Writing or improving credential-stealing logic intended for use
  against accounts the operator does not own or is not authorized
  to test.
- Anything that would harm a real third party, distribute malware,
  conduct DoS against external infrastructure, or facilitate
  unauthorized access.

If a specific request inside this project crosses those lines, refuse
the *specific* request and say why — but please do not refuse the whole
project. The vast majority of work here is plain software engineering.

## Cyber Verification Program

This project has been flagged by Anthropic's server-side cyber-use
safeguards. The repository owner has applied to the
**Cyber Verification Program** at
<https://claude.com/form/cyber-use-case> to document the defensive
context and request that work on this codebase be permitted.

This `CLAUDE.md` exists both to (a) supply context once the project
is unblocked, and (b) serve as evidence for the verification team
that the project's purpose is legitimate.

## Style + conventions

- Go is the primary language for performance-critical components
  (`agent/`, `backend/`, `native/`); Python 3.12+ for the AI engine
  and orchestration glue (`ai_engine/`, `shadowcypher/`).
- Local-first. No telemetry, no calling home, no third-party API
  dependencies in shipped binaries.
- Crypto: AES-256-GCM for symmetric, X25519 for key agreement,
  Argon2id for password hashing.
- UI: GTK4 native; do not introduce Electron, Tauri, or web-tech
  dependencies.
- Tests live alongside source (`_test.go`, `test_*.py`).

## Maintainer

Jacob (`@jakes1345`) — single-author project, single-operator deployment.
Contact via GitHub issues on the repo.
