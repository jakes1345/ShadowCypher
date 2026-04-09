# Plan: Fix Native ShadowCypher GTK (One-Unity UI)

## TL;DR
Transform the current native GTK app into a robust, single-UI (no web) system by fixing buffer wiring, threading safety, and error handling across all pages (Overview, Network, System, Firewall, Logs, Tools), while addressing build-time warnings and UX polish. Deliver a stable, crash-free application with consistent data display and a clear, documented plan for future enhancements.

## Context
- Current state (as of plan discussion): native/GTK app loads Overview correctly but crashes when navigating to other pages due to miswired per-page text buffers and inconsistent async update paths.
- Key issues observed: segmentation faults on Firewall page, GTK assertion when updating text buffers, and unnecessary reuse of a shared buffer across pages.
- Objective: make all six pages functional, robust, and testable, with a clean extension path for future features.

## Work Objectives
- Core objective: Fix buffer wiring and threading so that each page (Network, System, Firewall, Logs, Tools) can display asynchronous command output without crashing.
- Concrete deliverables:
  - [ ] A per-page PageCtx structure and a unified update path for async command results.
  - [ ] Safe, race-free threading model for executing system commands and updating the GUI.
  - [ ] Resilient error handling and default content when commands fail or buffers are unavailable.
  - [ ] Fix GNUP truncation warnings in shadowcypher.c and address related buffer size issues.
  - [ ] Basic UX polish: consistent typography, minimal error messaging, and hardening of the UI against edge cases.
- Definition of Done: All pages render content without crashes; commands execute and render output; no buffer-null dereferences; build succeeds without warnings.
- Must Have:
  - [ ] Thread-safe command execution with per-page context.
  - [ ] All pages load at least minimal content without crash.
  - [ ] No buffer-null dereferences in GTK text buffers.
- Must NOT Have (Guardrails):
  - [ ] No global buffers shared across pages without synchronization.
  - [ ] No silent crashes or silent empty outputs without error messages.

## Verification Strategy (Agent-Executed QA)
- QA Scenarios (minimum 1 happy-path + 1 negative):
  - Scenario: Launch app and verify Overview loads and shows CPU/Memory/Disk/Public IP values.
    - Tool: GTK app, in-app checks via accessibility/GUI state or custom test harness.
    - Preconditions: Native binary built; data sources available.
    - Steps: Open app, read Overview labels, take a screenshot, ensure values parseable.
    - Expected Result: Overview displays non-empty, sensible values; no crash.
    - Evidence: .sisyphus/evidence/task-XX-overview.png
  - Scenario: Navigate to Network page and verify content area populates with a sample output (even minimal text).
    - Steps: Switch to Network tab, wait for update, check buffer text not empty.
    - Expected Result: Non-empty text buffer appears; app remains responsive.
    - Evidence: .sisyphus/evidence/task-XX-network.png
  - Scenario: Trigger a failing command (simulate permission-denied or nonexistent tool) and verify graceful handling.
    - Steps: Navigate to Firewall page and cause a command fail; ensure UI shows a meaningful error instead of crash.
    - Expected Result: Error content appears; no crash.
    - Evidence: .sisyphus/evidence/task-XX-firewall-error.txt

- The agent will also test buffer lifecycle by navigating away and back to pages to ensure buffers are properly allocated/freed.
- If any buffer is NULL, the plan requires a safe default message and reinitialization code path.

## Execution Strategy
### Wave 1 — Architectural stabilization (foundation)
- T1. Introduce a per-page PageCtx structure that encapsulates: buffer, widget, and a small state object for the page.
- T2. Refactor on_activate/on_stack_visible_child to allocate and store a PageCtx per page; ensure buffers are created before starting async tasks.
- T3. Centralize async command path: implement a common function run_command_for_page(ctx, cmd) that creates a thread, collects output, and updates via a page-specific callback.
- T4. Replace current OverviewIdle with per-page maintainers; ensure no page uses the OverviewIdle pattern for other pages.
- T5. Fix snprintf truncation warnings in shadowcypher.c by using safer string handling and dynamic allocation where needed.
- T6. Add abort/cancel support for long-running commands with a per-page cancel button and thread cleanup.

### Wave 2 — Robustness & error handling
- T7. Add robust error messaging: if a command fails, display a clearly labeled error message in the page buffer.
- T8. Implement timeouts and input sanitization for commands invoked by the UI.
- T9. Harden thread lifecycle: join/destroy threads on page destroy and app exit.
- T10. Improve memory management: ensure all allocated buffers are freed; avoid memory leaks.

### Wave 3 — UX polish & tests
- T11. Add simple, consistent styling touches to ensure readability across all pages.
- T12. Add a minimal test harness for the native UI to exercise the buffer flow without user interaction.
- T13. Documentation: update comments and add a short README with usage details for the native GTK UI.

## Plan Governance
- Plan Owner: [Your Name or Team]
- Stakeholders: Frontend/Desktop UI team, Core GNOME GTK developers, Security QA
- Decision Points: Naming of Plan, plan versioning, and whether to extend with new pages or deprecate old ones.

## Final Verification Wave
- After implementing Wave 1-3, run a full smoke test: open app, navigate through all 6 pages, verify at least static content is loaded without crash, capture logs, and verify buffers update with sample command outputs.
- Evidence will be stored under `.sisyphus/evidence/` with per-task slugs.

## Commit Strategy
- Commit atomic changes per task; include a brief rationale in commit messages. Do not squash all fixes into a single commit.

## Success Criteria
- All 6 pages render without crash; at least Overview shows live data.
- No buffer NULL dereferences; all per-page outputs display meaningful content.
- Warnings from build are resolved (snprintf buffer sizes).
- Commands time out gracefully when needed; aborts work without crashing the app.
