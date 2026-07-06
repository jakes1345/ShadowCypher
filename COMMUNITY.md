# ShadowCypher Community

Welcome to the ShadowCypher community. We're building a personal security platform that respects operator autonomy and transparency. This document outlines how to engage, contribute, and connect with other users and developers.

---

## Community Values

### 1. **Operator-First**
We prioritize the needs and autonomy of individual operators. No feature is shipped that compromises the principle of "your machine, your rules."

### 2. **Transparency**
- Code is public and reviewable
- Design decisions are documented
- Security vulnerabilities are handled responsibly
- We discuss limitations honestly

### 3. **Non-Commercial**
- No telemetry or data collection
- No cloud backend requirement
- No paywalls or subscription models
- No corporate tracking

### 4. **Collaborative Security**
- We believe in shared threat intelligence, not gatekeeping
- Vulnerability reports are handled with professional care
- Community-contributed modules go through peer review

### 5. **Respect**
- No harassment, discrimination, or bad-faith engagement
- Disagree thoughtfully; attack ideas, not people
- Recognize contributors publicly
- Assume good intent

---

## Code of Conduct

All participants in the ShadowCypher community agree to:

- **Be respectful** of differing opinions, experience levels, and backgrounds
- **Be professional** in discussions about security, vulnerabilities, and tool usage
- **Avoid illegal or unethical activity** — ShadowCypher is for defensive security and authorized testing only
- **Report violations** to the maintainer at `conduct@shadowcypher.site` rather than escalating publicly
- **Assume good faith** when others ask questions or need help
- **Protect the community** by not sharing security vulnerabilities publicly before responsible disclosure

Violations may result in removal from community spaces.

---

## How to Join

### Start Contributing Code
1. Read [CONTRIBUTING.md](./CONTRIBUTING.md)
2. Fork the repository and set up your development environment
3. Pick an issue labeled `good-first-issue` or `help-wanted`
4. Submit a pull request

### Share Knowledge
- Contribute blog posts to the [docs/blog](./docs/blog/) directory
- Write module documentation
- Create threat models or use-case examples
- Answer questions in GitHub Discussions

### Test & Report Bugs
- Run the latest builds and report issues with clear reproduction steps
- Submit enhancement suggestions with realistic use cases
- Test on multiple platforms (Linux, macOS, Windows WSL)

### Join the Security & Threat Intelligence Channels
- [GitHub Discussions](https://github.com/shadowcypher/shadowcypher/discussions) — public, async
- [Community Discord](#) — (link provided upon request to verified contributors)
- [Security Reports](#) — see `SECURITY.md` for responsible disclosure

---

## Discussion Forums & Channels

### GitHub Discussions
- **Announcements:** New releases, roadmap updates, breaking changes
- **Ideas & Features:** Propose new modules, threat detection methods, UI improvements
- **Q&A:** Troubleshooting, installation, configuration
- **Show & Tell:** Share your ShadowCypher setups, custom modules, automation scripts

### GitHub Issues
- Bug reports with reproduction steps
- Feature requests (search first to avoid duplicates)
- Security vulnerabilities: **DO NOT open public issues** — see `SECURITY.md`

### Discord (Verified Contributors)
- Real-time chat for active contributors
- Early access to beta builds
- Casual discussion about threat landscape and tooling
- Coordination on large pull requests

---

## Event Calendar

### Recurring
- **Monthly Office Hours:** First Monday of each month, 19:00 UTC
  - Live Q&A with maintainer
  - Module walkthroughs
  - Community announcements
  - Link: Shared in Discussions 48 hours prior

- **Quarterly Threat Briefing:** Mid-quarter (Jan, Apr, Jul, Oct)
  - Industry threat landscape summary
  - New attack patterns relevant to personal security
  - Open Q&A
  - Format: Async Markdown + optional live discussion thread

### Special Events
- **Hacktoberfest Participation:** September–October
  - Curated issues with `hacktoberfest` label
  - First-time contributor onboarding
- **Annual Security Review:** December
  - Full codebase security audit
  - Community feedback on threat model
  - Planning for next year

---

## Recognition & Contributor Badges

We recognize contributors in multiple ways:

### GitHub
- Maintainer "Reviewed by @username" on your PRs
- Listed in `CONTRIBUTORS.md` (organized by contribution type)
- Pinned as "Community Heroes" in Discussions if you reach major milestones

### Badges (for your profile)
```
<!-- Contributor Shield -->
![Contributor](https://img.shields.io/badge/ShadowCypher-Contributor-4B9BFF?logo=github)

<!-- Security Reporter -->
![Security Researcher](https://img.shields.io/badge/ShadowCypher-Security%20Researcher-FF6B6B?logo=shield)

<!-- Module Author -->
![Module Author](https://img.shields.io/badge/ShadowCypher-Module%20Author-00D4FF?logo=code)
```

### Public Recognition
- Mentioned in release notes (with your permission)
- Featured in "Community Spotlight" announcements
- Invited to co-author security blog posts on threats you've helped address

---

## Support Channels

### For Help & Questions
1. **Search existing issues/discussions** — your question may already be answered
2. **GitHub Discussions** — post in Q&A with:
   - Your environment (OS, Python version, GPU type)
   - Error messages or unexpected behavior
   - Steps to reproduce
3. **Community Discord** — faster real-time responses for verified members

### For Bug Reports
1. Read [CONTRIBUTING.md — Bug Reports](./CONTRIBUTING.md#bug-reports)
2. Search existing issues first
3. Create a new issue with:
   - Clear title (`[Bug] Describing the problem`)
   - Environment details
   - Minimal reproduction steps
   - Actual vs. expected behavior
   - Relevant logs from `~/.shadowcypher/logs/`

### For Security Vulnerabilities
**Do NOT use public issues.** See `SECURITY.md` for the responsible disclosure process.

### For Feature Requests
1. Post in Discussions under "Ideas & Features"
2. Include:
   - Use case — why you need this
   - Proposed behavior — what success looks like
   - Alternatives you've tried
3. If there's strong interest, it becomes an issue for future roadmapping

### For Licensing & Legal Questions
- Email: `legal@shadowcypher.site`

---

## Contributor Roles

### Module Author
You've developed a module (tool wrapper, analysis pipeline, or detection method) that's merged into the main repository.
- **Expectations:** Your module stays maintained and documented
- **Benefits:** Listed in module library, recognized in releases

### Security Researcher
You've reported, triaged, or fixed security vulnerabilities.
- **Expectations:** Responsible disclosure; contributions to threat docs
- **Benefits:** Early access to security updates, invited to threat briefings

### Documentation Contributor
You've written tutorials, threat models, use-case guides, or API documentation.
- **Expectations:** Content is accurate, follows style guide (see CONTRIBUTING.md)
- **Benefits:** Visible attribution, featured in docs

### Community Moderator
You actively help in Discussions, answer Q&A, and flag violations.
- **Expectations:** Fair, respectful, neutral moderation; no abuse of position
- **Benefits:** Badge, official status, invited to planning discussions

### Maintainer
Sole role: Jack (jakes1345@github). Responsible for final merge decisions, security policy, roadmap prioritization, and release management.

---

## FAQ

**Q: Can I use ShadowCypher for offensive security?**  
A: ShadowCypher is designed for authorized testing and defensive security on systems you own or have explicit written permission to test. Always follow applicable laws and organizational policies.

**Q: How do I report bugs privately before public disclosure?**  
A: See `SECURITY.md` if it's a security vulnerability. For non-security bugs, open a private discussion with the maintainer or email `support@shadowcypher.site`.

**Q: Can I build a commercial product on top of ShadowCypher?**  
A: Check `LICENSE` (Sovereign License). Generally: derivative works must remain open-source and non-commercial.

**Q: Is there a Slack/Teams/Matrix community?**  
A: Currently no — we're keeping infrastructure minimal. GitHub Discussions + Discord for verified contributors. If there's strong interest, we'll evaluate adding a public chat.

**Q: How long do you maintain older versions?**  
A: Only `main` branch is actively supported. Older releases receive security patches for 12 months after release; older patches are archived in `/releases/`.

**Q: Can I translate ShadowCypher into another language?**  
A: Yes. Please open a discussion first to coordinate with other translators, then follow the localization guide in `CONTRIBUTING.md`.

---

## Community Resources

- **Main Repository:** https://github.com/shadowcypher/shadowcypher
- **Discussions:** https://github.com/shadowcypher/shadowcypher/discussions
- **Issue Tracker:** https://github.com/shadowcypher/shadowcypher/issues
- **Blog:** https://shadowcypher.site/blog
- **Security Policy:** [SECURITY.md](./SECURITY.md)
- **Contributing Guide:** [CONTRIBUTING.md](./CONTRIBUTING.md)
- **License:** [LICENSE](./LICENSE) (Sovereign)

---

## Contact

- **General Inquiries:** `hello@shadowcypher.site`
- **Security Issues:** `security@shadowcypher.site` (encrypted, see SECURITY.md)
- **Code of Conduct Violations:** `conduct@shadowcypher.site`
- **Community & Collaboration:** `community@shadowcypher.site`

---

**Last Updated:** 2026-07-05  
**Community Champion:** Jack (Maintainer)
