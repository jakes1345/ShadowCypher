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
- **Python:** (3.12.x, 3.13.x, etc.)
- **GPU:** (NVIDIA, AMD, CPU, none)
- **Installation:** (pip, apt, Flatpak, manual)
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

- **Python 3.12+**
- **Go 1.24+** (for native relay component)
- **Git**
- **Virtual environment tool** (venv, Poetry, or similar)

### Clone & Install

```bash
# Clone repository
git clone https://github.com/shadowcypher/shadowcypher.git
cd shadowcypher

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Build native components
cd native && go build -o shadowcypher-relay ./cmd/relay && cd ..

# Verify installation
python -m shadowcypher --version
```

### Running in Development

```bash
# Run with debug logging
PYTHONUNBUFFERED=1 DEBUG=1 python -m shadowcypher

# Run tests
pytest tests/ -v --cov=shadowcypher

# Run linting
black shadowcypher/ tests/
isort shadowcypher/ tests/
flake8 shadowcypher/ tests/
mypy shadowcypher/
```

### Project Structure

```
shadowcypher/
├── shadowcypher/          # Main package
│   ├── ui/               # GTK interface
│   ├── ai_engine/        # Local LLM orchestration (Ollama)
│   ├── arsenal/          # Tool wrappers & modules
│   ├── core/             # Event bus, crypto, auth
│   └── guardian/         # Guardian module system
├── native/               # Go relay component
├── tests/                # Unit & integration tests
├── docs/                 # User & developer documentation
├── .github/              # CI/CD workflows
└── configs/              # Default configuration templates
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
- [ ] Unit tests pass: `pytest tests/ -v`
- [ ] Manual testing: (describe what you tested and on what OS)
- [ ] No new warnings from linting/type checking

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

### Python

**Style Guide:** PEP 8 with Black formatter

```bash
# Format code
black shadowcypher/ tests/

# Sort imports
isort shadowcypher/ tests/

# Check for issues
flake8 shadowcypher/ tests/
mypy shadowcypher/ --strict
```

**Key Conventions:**
- 4-space indentation
- Max line length: 100 characters
- Use type hints for all function signatures
- Use descriptive variable names (avoid single-letter vars except in loops)
- Use docstrings for classes and functions (Google style)
- Prefer list/dict comprehensions for clarity

**Example:**

```python
from typing import Optional, List
from shadowcypher.core.models import Threat

def analyze_threat(
    threat: Threat,
    confidence_threshold: float = 0.75,
) -> Optional[dict]:
    """
    Analyze a threat against known patterns.
    
    Args:
        threat: Threat object to analyze
        confidence_threshold: Minimum confidence score (0.0-1.0)
    
    Returns:
        Analysis results dict or None if confidence is too low
    
    Raises:
        ValueError: If confidence_threshold is not in range [0.0, 1.0]
    """
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be in range [0.0, 1.0]")
    
    results = [
        pattern.match(threat) 
        for pattern in known_patterns 
        if pattern.confidence >= confidence_threshold
    ]
    
    return {"matches": results} if results else None
```

### Go

**Style Guide:** Go conventions (gofmt, golint)

```bash
# Format code
go fmt ./...

# Lint
golangci-lint run ./...

# Test
go test ./... -v -cover
```

**Key Conventions:**
- Use interfaces for extensibility
- Error handling: explicit `if err != nil` checks
- Concurrency-safe with channels and sync primitives
- Document exported functions

### Configuration Files

- **YAML:** 2-space indentation, no tabs
- **JSON:** 2-space indentation, no trailing commas
- **Markdown:** Max line length 100, consistent heading levels

---

## Testing Requirements

### Unit Tests

All new functionality must have unit tests. Aim for 80%+ code coverage.

```bash
# Run tests with coverage
pytest tests/ -v --cov=shadowcypher --cov-report=html

# Test a specific module
pytest tests/test_identity.py -v

# Run with markers
pytest tests/ -v -m "not slow"
```

**Test Organization:**
- Mirror source structure: `shadowcypher/core/foo.py` → `tests/core/test_foo.py`
- Use descriptive test names: `test_autoscan_rejects_invalid_cidr_formats`
- Use fixtures for setup/teardown (see `tests/conftest.py`)

**Example Test:**

```python
import pytest
from shadowcypher.arsenal.autoscan import AutoScan

@pytest.fixture
def autoscan():
    """Provide an AutoScan instance for testing."""
    return AutoScan()

def test_autoscan_accepts_valid_cidr(autoscan):
    """AutoScan should accept valid CIDR notation."""
    result = autoscan.validate_target("192.168.1.0/24")
    assert result.is_valid is True

def test_autoscan_rejects_invalid_cidr(autoscan):
    """AutoScan should reject invalid CIDR notation."""
    result = autoscan.validate_target("999.999.999.999/32")
    assert result.is_valid is False
```

### Integration Tests

If your change affects module orchestration, threat feed integration, or the event bus, add integration tests in `tests/integration/`.

### Manual Testing Checklist

For UI changes:
- [ ] Test on target OS (Linux/macOS/WSL)
- [ ] Test with different themes (light/dark)
- [ ] Test accessibility (keyboard navigation, screen readers)
- [ ] Test with different window sizes
- [ ] Screenshot for PR if UI changes are significant

For modules/tools:
- [ ] Test with realistic targets (with permission)
- [ ] Test with edge cases (empty results, network timeout, malformed input)
- [ ] Verify output accuracy against expected behavior
- [ ] Check error handling and user feedback

---

## Documentation Expectations

### Code Documentation

Every public class, function, and module should have docstrings:

```python
def orchestrate_scan(
    target: str,
    modules: List[str],
    timeout_seconds: int = 300,
) -> ScanResult:
    """
    Orchestrate a security scan against a target using specified modules.
    
    This function coordinates parallel execution of multiple modules, 
    aggregates results, and deduplicates findings.
    
    Args:
        target: Target hostname, IP, or CIDR range
        modules: List of module names to run (e.g., ["nmap", "nikto"])
        timeout_seconds: Maximum time allowed for the entire scan (default: 300)
    
    Returns:
        ScanResult object with aggregated findings, timing info, and metadata
    
    Raises:
        ValueError: If target is invalid or modules list is empty
        TimeoutError: If scan exceeds timeout_seconds
        ModuleNotFoundError: If a module in the list is not available
    
    Example:
        >>> result = orchestrate_scan("192.168.1.1", ["nmap", "nikto"])
        >>> print(f"Found {len(result.findings)} issues")
    """
```

### Feature Documentation

For new features, update:

1. **README.md** — add to feature list if it's user-facing
2. **Module Library** — if it's a new module, add to `docs/modules/`
3. **User Guide** — workflow documentation in `docs/guides/`
4. **API Docs** — if it's a new API endpoint or orchestration function
5. **Threat Model** — if it introduces new attack surface or mitigations

### Blog Posts

Share knowledge with the community:
- Security findings or threat intelligence → `docs/blog/threats/`
- Tool tutorials and how-tos → `docs/blog/tutorials/`
- Architecture decisions → `docs/blog/engineering/`

**Format:**
```markdown
---
title: "How to Set Up Offline YARA Rules"
author: Your Name
date: 2026-07-05
tags: ["yara", "offline", "detection"]
---

# How to Set Up Offline YARA Rules

[Content...]
```

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
