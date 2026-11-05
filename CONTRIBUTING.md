# Contributing to ShadowCypher

Thank you for your interest in contributing to ShadowCypher. This document explains how to report bugs, suggest features, set up your development environment, and submit pull requests.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Bug Reports](#bug-reports)
3. [Feature Suggestions](#feature-suggestions)
4. [Development Setup](#development-setup)
5. [Pull Request Process](#pull-request-process)
6. [Coding Standards](#coding-standards)
7. [Testing Requirements](#testing-requirements)
8. [Documentation Expectations](#documentation-expectations)
9. [Commit Message Style](#commit-message-style)
10. [Questions & Help](#questions--help)

---

## Code of Conduct

By contributing, you agree to uphold our [Community Code of Conduct](./COMMUNITY.md#code-of-conduct). Violations may result in removal from the project.

---

## Bug Reports

### Before Submitting

1. **Check existing issues** — search for similar reports at https://github.com/shadowcypher/shadowcypher/issues
2. **Try the latest main branch** — the bug may already be fixed
3. **Isolate the problem** — reproduce it without custom modules or configurations if possible
4. **Collect logs** — run in debug mode and save output

### When Submitting

Create an issue with this template:

```
Title: [Bug] Brief description (e.g., "[Bug] AutoScan crashes on invalid CIDR input")

## Environment
- **OS:** (Linux distro, macOS version, Windows WSL version)
- **Qt version:** (from `qmake6 --version` or your package manager)
- **GPU:** (NVIDIA, AMD, CPU, none)
- **Installation:** (built from source, ShadowOS, Android app)
- **ShadowCypher Version:** (main branch or specific commit hash)

## Steps to Reproduce
1. First step
2. Second step
3. Exact action that triggers the bug

## Expected Behavior
What should happen?

## Actual Behavior
What actually happened? Include error message or screenshot.

## Relevant Logs
```
Paste from ~/.shadowcypher/logs/ or terminal output (truncate if >100 lines)
```

## Additional Context
- Custom modules involved? (list names)
- Recent configuration changes?
- Third-party tools modified? (Nmap, SQLmap versions, etc.)
```

### Security Vulnerabilities

**DO NOT open public bug reports for security issues.** See `SECURITY.md` for responsible disclosure.

---

## Feature Suggestions

### Before Suggesting

1. **Check existing ideas** — search Discussions at https://github.com/shadowcypher/shadowcypher/discussions?discussions_q=category%3AIdeas
2. **Confirm it aligns with ShadowCypher's scope** — single-user, local-first personal security tool, no cloud dependency
3. **Think through implications** — does it break existing workflows? Increase complexity? Create new dependencies?

### When Suggesting

Post in **Discussions** (not Issues) with:

```
Title: [Feature Idea] Descriptive title (e.g., "[Feature Idea] Offline YARA rule database")

## Problem
Why is this needed? What use case does it address?

## Proposed Solution
How should it work? What does success look like?

## Alternatives Considered
What else did you try? Why isn't it sufficient?

## Impact
- Affects which modules/workflows?
- Does it require new dependencies?
- Is it backward-compatible?
- What's the performance/storage cost?

## Acceptance Criteria
- [ ] Works offline
- [ ] Integrates with existing threat feed system
- [ ] Documented in threat library
```

---

## Development Setup

### Prerequisites

- **Desktop app:** CMake 3.16+, a C++17 compiler, Qt 6 (`qt6-base`, `qt6-websockets`; `qt6-wayland` on Wayland), OpenSSL, Ninja or make
- **API:** Node.js 20+ and npm
- **ShadowOS:** an Arch host with `archiso`, or Docker
- **Android:** Android Studio or the Android SDK with JDK 17

### Build & Test

```bash
git clone https://github.com/jakes1345/ShadowCypher.git
cd ShadowCypher

# Desktop app (Qt6 C++)
cmake -S shadowcypher-qt -B build -G Ninja -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build --output-on-failure
./build/shadowcypher

# API (Cloudflare Worker)
cd backend/api && npm ci && npm run typecheck && npm test
```

CI runs the desktop build and tests and the API typecheck and tests on every pull request. Both must pass before a PR can merge.

### Project Structure

```
ShadowCypher/
├── shadowcypher-qt/       # Desktop app (Qt6 C++): UI, background daemon, privacy helper
├── www/                   # Web app (single-page HTML/JS)
├── backend/api/           # API (Cloudflare Worker, TypeScript)
├── android/               # Android apps: Guardian and Shadow AI
├── shadowos/              # ShadowOS (Arch Linux ISO profile)
├── blog/                  # Blog posts
└── .github/               # CI/CD workflows
```

---

## Pull Request Process

### Before Creating a PR

1. **Create a branch** from `main` with a descriptive name:
   ```bash
   git checkout -b fix/autoscan-cidr-validation
   # or
   git checkout -b feat/offline-yara-rules
   ```

2. **Work on your changes** — commit frequently with clear messages (see [Commit Message Style](#commit-message-style))

3. **Add/update tests** — see [Testing Requirements](#testing-requirements)

4. **Update documentation** — see [Documentation Expectations](#documentation-expectations)

5. **Test locally** — run the full test suite and manual tests on your target OS

### Creating the PR

Push your branch and open a PR with this template:

```
Title: [Type] Short description (e.g., "[Fix] AutoScan CIDR validation")

## Summary
Briefly describe what this PR does. What problem does it solve?

## Changes
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Tests pass: `ctest --test-dir build` and/or `npm test` in `backend/api`
- [ ] Manual testing: (describe what you tested and on what OS)
- [ ] No new compiler warnings, and `npm run typecheck` is clean

## Checklist
- [ ] Code follows style guide (see Coding Standards)
- [ ] Tests added/updated (if behavior changed)
- [ ] Documentation updated (if new feature or API change)
- [ ] No breaking changes (or clearly documented in title)
- [ ] Commit messages follow convention (see Commit Message Style)

## Related Issues
Closes #123
```

### Review Process

1. Maintainer will review within 7 days
2. Changes may be requested — respond with commits rather than force-pushing
3. Once approved, PR will be merged by maintainer
4. Your contribution will be recognized in release notes

### Merge Criteria

- [ ] Tests pass (100% of CI checks green)
- [ ] Code review approved
- [ ] Documentation updated
- [ ] No unresolved discussions
- [ ] Commit history is clean (no "fix typo" commits)

---

## Coding Standards

### C++ (desktop app)

- C++17 and Qt 6. Keep the UI in `shadowcypher-qt/src/`, the background work in `daemon/`, and shared code in `core/`.
- Network calls go through `ApiClient`; never build request URLs or auth headers by hand.
- Anything that needs root goes through the privacy helper and `pkexec`. The app and the daemon run unprivileged.
- Fix new compiler warnings in code you touch.

### TypeScript (API)

- Keep `npm run typecheck` clean, and add a Vitest test next to the code you change.
- Look up auth users with `findAuthUserByEmail`; the auth API ignores an `email` filter.
- Secrets come from `wrangler secret put`, never from the repo.

### Web app

- `www/index.html` ships as-is, with no build step. `callApi()` returns parsed JSON, not a `Response`.

### No Python, no GTK

The project moved from Python + GTK to Qt6 C++. Don't add Python or GTK code, dependencies or CI jobs.

---

## Testing Requirements

- **Desktop:** add or extend tests in `shadowcypher-qt/core/tests/` for runtime logic, and run `ctest`. For UI changes, run the app and attach screenshots to the PR.
- **API:** `npm test` (Vitest) in `backend/api/`. Cover new routes, including error and auth-failure cases.
- **ShadowOS:** run `bash shadowos/validate.sh`. For changes to the image, build the ISO and boot it with `bash shadowos/qemu-test.sh`.

### Manual Testing Checklist

For UI changes:
- [ ] Test on Linux (X11 and Wayland if you can)
- [ ] Test with different window sizes
- [ ] Screenshot for PR if UI changes are significant

For network features:
- [ ] Test edge cases: empty results, network timeouts, malformed input
- [ ] Check error handling and what the user sees

---

## Documentation Expectations

- Document public classes and functions with a short comment on what they do and why.
- Update `README.md` for user-facing changes, and `CLAUDE.md` for new conventions or commands.
- Don't add internal planning docs to the repo.

---

## Commit Message Style

Use conventional commits for clarity and automatic changelog generation:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `style`

**Example:**

```
fix(arsenal/autoscan): validate CIDR format before launching scan

Previously, AutoScan would attempt to scan invalid CIDR ranges, 
causing cryptic errors from Nmap. Now we validate CIDR format 
and return a helpful error message.

Fixes #456
```

**Rules:**
- Subject: present tense, lowercase, no period, <50 chars
- Body: explain *why*, not *what* (the diff shows what)
- Footer: reference issues (e.g., `Fixes #123`, `Relates to #456`)
- No `Co-Authored-By` trailers (per project policy)

---

## Questions & Help

- **Coding questions:** Open a Discussion under "Q&A"
- **Setup trouble:** Reply in the "Development" category
- **Design feedback:** Post in "Ideas & Features" before you code
- **Real-time chat:** Join the community Discord (verified contributors)
- **Private help:** Email `community@shadowcypher.site`

---

## Recognition

Your contributions are recognized:
- Listed in `CONTRIBUTORS.md` (organized by contribution type)
- Mentioned in release notes (with your permission)
- Invited to community events and threat briefings
- Eligible for contributor badges (see `COMMUNITY.md`)

---

**Last Updated:** 2026-07-05  
**Maintained By:** Jack (Maintainer)
