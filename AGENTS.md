## Learned User Preferences

- Run commands and tests yourself; keep iterating on ShadowOS/ShadowCypher until checks pass rather than stopping after one attempt.
- Prefer live QEMU with a visible window (`shadowos/boot-iso.sh --gui`) for manual login/desktop verification, not headless-only runs.
- Avoid full ISO rebuilds for routine fixes; use `shadowos/sync-to-live.sh` and `shadowos-apply-fixes.sh` on a running live VM, then re-login. Use `build-new-iso.sh` when stale image or profile drift makes sync unreliable.
- Installed ShadowOS must use the operator's own admin account via `shadowos-install`, not a shared default account beyond the live-demo `shadow/shadow` session.
- Surface clearly that `shadow/shadow` is live-ISO demo-only; installed disks get a user-chosen username, password, and wheel/sudo.
- Expect agents to diagnose root causes (e.g. old ISO vs profile fixes, SSH-before-login limits) instead of asking the user to retry blindly.
- Prefer real, working implementations over placeholders, mocks, samples, or stub/demo modules when building or reviewing features.
- End-to-end test modes and integrated features; disabled or half-wired capabilities break the overall ShadowOS experience.
- Target ShadowOS for security-conscious operators plus full gaming and dev support, with enterprise-grade polish beyond a minimal ShadowCypher shell.
- Normal networking must work in daily-driver modes (normal/dev/pentest/undercover); switching back from ghost/privacy must fully restore connectivity.
- Operator-private state (config, DB, logs, ghost/privacy) belongs per-user under XDG home paths; `/opt/shadowcypher` is shared app code only.
- Live desktop must present a full OS shell (welcome, Waybar, gaming/settings hubs), not ShadowCypher autostart as the sole session.

## Learned Workspace Facts

- Live ISO demo account must never use forced password expiry — SDDM cannot handle change-password prompts; keep non-expiring `shadow/shadow` and `shadowos-live-login-fix.service`.
- Threat-awareness education lives in separate `public_awareness/` module; do not fold it into core ShadowCypher tooling.

## Multi-agent coordination (Cursor + Claude Code)

Both tools edit the same repo. **No live API between them** — use the agent bridge:

```bash
export AGENT_BRIDGE_ID=cursor      # or claude-code, in each terminal
python3 scripts/agent-bridge.py status
python3 scripts/agent-bridge.py claim shadowos --task "what you are doing"
python3 scripts/agent-bridge.py handoff claude-code "done X; you take Y"
python3 scripts/agent-bridge.py release shadowos
```

**Default ownership** (claim before editing; handoff when switching):

| Agent | Primary areas |
|-------|----------------|
| **Cursor** | `shadowos`, `infra-release`, QEMU/sync/live fixes |
| **Claude Code (Sonnet)** | `shadowcypher-app`, `shadowcypher-modules`, `backend-go`, audits |

Always run `status` at session start. Do not edit paths another agent registered in the last 3h without reading handoffs. See `.agents/README.md`.

**Agent Hub (local API):** `./scripts/agent-hubctl.sh start` → `http://127.0.0.1:8765`
- Both Cursor and Claude Code auto-load briefing via SessionStart hooks
- Queue work: `./scripts/agent-hubctl.sh task claude-code "audit stealth modes"`
- Handoff: `./scripts/agent-hubctl.sh handoff cursor claude-code "ISO rebuild ready"`
- Dispatch uses native CLIs (`claude -p`, `agent -p`) on your existing subscriptions

**Tool stack:** Claude Code = Sonnet 4.6 for large sweeps/refactors; Cursor for boot-test-fix loops and terminal work.

- Canonical name is ShadowCypher; local checkouts may still use a `Pulse` folder path for the same monorepo (Python GTK dashboard `shadowcypher/`, Go relay/agent, Arch live ISO `shadowos/`).
- ShadowOS ships ShadowCypher at `/opt/shadowcypher` with Hyprland (Wayland), SDDM, and Waybar; profile source lives under `shadowos/profile/airootfs`.
- Live ISO sessions use demo login `shadow/shadow`; permanent installs use `shadowos-install` (archinstall) to create a wheel/sudo user and do not keep the demo account.
- `/etc/shadowos/live-iso` marks live sessions; SDDM theme uses `liveIso` for the demo-account banner on live media only.
- Day-to-day validation: `shadowos/test_iso.sh` (profile), `shadowos/redteam.sh` (QEMU/SSH), `shadowos/boot-iso.sh` (`--gui`, `--headless`, `--smoke`); dev app via `PYTHONPATH=. python3 -m shadowcypher.app` from repo root.
- Post-login desktop stack depends on `shadowcypher-autostart`, `shadowos-session-start`, Python deps on the image, and writable `/opt/shadowcypher` or logger fallback under `~/.local/state/shadowcypher`.
- Project is a local-first, defensive personal security toolkit (see `CLAUDE.md`); UI stays GTK native, not Electron/web shells.
- ShadowOS gaming stack should include Steam/Proton and Heroic as easily accessible defaults, not only manual post-install setup.
- Welcome guide and mode/onboarding documentation are required product deliverables for ShadowOS, not optional extras.
