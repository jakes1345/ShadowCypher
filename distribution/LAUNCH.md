# ShadowCypher Distribution Kit

This is the playbook for getting real users. Code is built; revenue requires distribution.

---

## Phase 1 — Pre-launch checklist (do first, takes ~1 hour)

Before any launch post, verify the site is bulletproof:

- [ ] All SQL migrations run (`0001` → `0002` → `0003` → `0004`) in Supabase
- [ ] Sign up + sign out + sign in works on production
- [ ] At least 1 real device shows in dashboard (run the agent on your machine)
- [ ] Stripe test-mode subscription completes end-to-end (`4242 4242 4242 4242`)
- [ ] Plan badge flips to `guardian_pro` after test payment
- [ ] Trial countdown badge shows for new accounts
- [ ] Email notification test sends a real email
- [ ] AI assistant returns a real answer to "What devices are on my network?"
- [ ] Mobile site is responsive (open `shadowcypher.site` on your phone)
- [ ] Site has 0 console errors in browser devtools
- [ ] Privacy policy + terms pages exist (Stripe asks for these before going live)

When all green: switch Stripe from Test → Live mode, generate new live Price IDs, update `STRIPE_PRICE_*` Worker secrets.

---

## Phase 2 — Hacker News launch (best ROI single shot)

### Submission settings
- **Title** (max 80 chars): `Show HN: ShadowCypher – open-source enterprise network security platform`
- **URL**: `https://shadowcypher.site`
- **Time to post**: Tuesday–Thursday, 8–10 AM ET (peak HN traffic)
- **NOT during**: Mondays (busy week start), Fridays-Sundays (low engagement)

### First comment (post immediately after submission)
> Hey HN — I built ShadowCypher because the network security tooling space splits cleanly into two camps: enterprise products that cost $50k+/year (CrowdStrike, SentinelOne) and a fragmented mess of CLI tools (nmap, wireshark, hydra, aircrack-ng) that require expert assembly.
>
> I wanted something in between: an open-source, self-hostable platform that uses the same real tools under the hood (no reinvented wheels) but ties them together with a unified dashboard, AI-assisted querying, and continuous monitoring agents.
>
> Tech stack: Cloudflare Workers (TypeScript) for the API, Supabase for auth + Postgres, vanilla HTML/CSS/JS for the dashboard (no React bloat), Python for the agent and 32+ tactical scripts. All free tiers — costs me $0/month to run.
>
> The CLI toolkit is open source and free forever. Paid tiers ($9.99 Guardian Pro / $49 Operator) unlock continuous monitoring, alerts, the AI assistant, and team features. Currently in test mode — happy to give Pro free to first 100 HN signups.
>
> Honest about what's not done: web push needs more polish, mobile app is a PWA (no native iOS/Android yet), and the AI assistant has a 200-word answer cap.
>
> Tear it apart — what would you want from a tool like this?

### Expected outcomes
- **Top 30 on HN**: 200–500 signups, 5–10 paid conversions
- **Front page**: 2000–10000 signups, 50–200 paid conversions
- **Day 1 traffic spike**: Cloudflare free tier (100k req/day) is enough; Workers free tier limit is the same. Supabase free DB has 500MB; you'll be fine.

### What kills HN posts
- Marketing language ("revolutionary", "game-changing", "next-gen") — HN smells it instantly
- Hype copy — be honest about what's broken
- Not responding to comments in the first 2 hours
- Pricing too aggressive (HN audience is allergic to anything that feels VC-funded)

---

## Phase 3 — Reddit (slower burn, sticky users)

Different subreddits, different tones. Post one per week max — over-posting gets you shadowbanned.

### r/selfhosted (650k members)
**Title**: `I built a self-hosted network monitor that alerts me when sketchy devices join my Wi-Fi`

**Body**:
> Spent the last few months building this because I got tired of paying CrowdStrike-tier prices for what's essentially nmap + a dashboard.
>
> ShadowCypher is open source (MIT-licensed), runs an agent on your home server, scans your LAN every 10 min, and pings you when something new shows up or starts behaving weird (ARP spoofing, port changes).
>
> All the heavy lifting is via real tools — nmap, ip neigh, scapy. The platform is just glue + UI + alerting.
>
> Free tier is plenty for a single home network. Pro (paid, $9.99/mo) adds continuous monitoring + email alerts + AI Q&A — but I'm comfortable saying the free tier is the actual product. Pro is just convenience.
>
> Code: github.com/jakes1345/ShadowCypher
> Site: shadowcypher.site

### r/HomeNetworking (1.2M)
**Title**: `Free tool I made to find unknown devices on your home network`

(Lead with the immediate utility, downplay the platform-ness)

### r/homelab (700k)
**Title**: `[Self-hosted] Built a tactical security dashboard for my homelab — open source`

(Emphasize the homelab angle, share screenshots of the dashboard)

### r/cybersecurity (700k)
**Title**: `Open-source platform combining nmap/aircrack/hydra into one dashboard with continuous monitoring`

(More technical, lead with the tool list, link the GitHub)

### Don't post to
- r/programming (too generic, gets buried)
- r/sysadmin (suspicious of new tools without real enterprise track record)
- r/Python (hostile to anything that's not a pure library)

---

## Phase 4 — Product Hunt (week 2–3 after HN)

PH works best when you already have ~50 users from HN/Reddit who can upvote on launch day.

### Launch checklist
- [ ] Set launch date for a Tuesday or Wednesday
- [ ] Announce on your Twitter/Mastodon 24h ahead, "Launching ShadowCypher tomorrow at 12:01 AM PT"
- [ ] Email your existing free users at 12:30 AM PT launch day asking for an upvote
- [ ] Post in HN Show HN comments: "We just launched on Product Hunt — would love your support: [link]"
- [ ] Reply to every PH comment within 30 min for the first 6 hours

### PH copy
**Tagline (max 60 chars)**: `Continuous network security for homes and small teams`

**Description** (240 chars):
> The CLI security tools you already trust (nmap, scapy, aircrack-ng) wrapped in a clean dashboard with continuous monitoring, alerts, and AI Q&A. Open-source core, $9.99/mo Pro for 24/7 monitoring. Self-hostable.

**Topics**: Productivity, Security, Open Source, Network

---

## Phase 5 — YouTube / TikTok (month 2+, compounds long-term)

Content ideas (record yourself doing these, edit to 30-60s for TikTok / 5-10 min for YouTube):

1. **"I scanned my home network and found 4 devices I didn't recognize"** — most viral angle
2. **"Your router is a security nightmare — here's how to audit it in 60 seconds"** — high CTR
3. **"Why I stopped using LastPass for everything and started running my own security tools"** — narrative
4. **"How my smart TV was talking to 7 servers in China"** — pure clickbait but legit story most people have
5. **"Building open-source CrowdStrike from scratch (Cloudflare Workers + Supabase)"** — dev audience

---

## Phase 6 — SEO landing pages (month 3+, compounds forever)

Each one targets a long-tail query that brings in 10–100 signups/month after ranking:

| URL | Target query | Word count |
|---|---|---|
| `/blog/find-unknown-devices-wifi` | "how to find unknown devices on my wifi" | 1500 |
| `/blog/router-security-audit-checklist` | "router security audit checklist" | 2000 |
| `/blog/arp-spoofing-detection-home` | "how to detect ARP spoofing at home" | 1200 |
| `/blog/best-self-hosted-security-tools-2026` | "best self-hosted security tools" | 2500 |
| `/blog/replace-crowdstrike-open-source` | "open source crowdstrike alternative" | 1800 |

Each post should:
1. Answer the question in the first 200 words (Google's AI snippets)
2. Have an actionable demo (screenshot of using ShadowCypher to do the thing)
3. End with a clear CTA: "Try it free — shadowcypher.site"

Use a tool like Ahrefs free trial or Ubersuggest to find more long-tails.

---

## Phase 7 — Cold outreach (highest revenue per hour)

Target small IT shops / MSPs who serve 10–50 small business clients each. Operator tier ($49/mo) per client = $5k MRR for 100 clients.

### Cold email template

Subject: `Open-source CrowdStrike for SMB clients`

> Hi [Name],
>
> Saw your team services [X] clients in the [vertical] space.
>
> I built ShadowCypher (shadowcypher.site) — open-source, self-hostable network security platform. Same real-tool foundation as CrowdStrike (nmap, scapy, etc.) but at $49/month per protected network.
>
> A few things you might find useful for SMB clients:
> - Continuous device discovery + alerts on rogue devices
> - Automated router/firewall hardening recommendations
> - AI-powered "what should I worry about?" assistant
> - Self-hostable so client data never leaves their environment
>
> Free tier is fully functional. Want a 30-min walkthrough?
>
> [Your name]
> github.com/jakes1345

Send 50/day for 2 weeks → expect 5–10 demos → 1–3 closes. $50–150 MRR per outreach campaign.

---

## Phase 8 — What NOT to do

- ❌ Don't pay for Google/FB ads on day 1. Burn rate is high, conversion is low until product is proven.
- ❌ Don't add hype features ("AI-powered", "blockchain-secured", "quantum-resistant") just to trend. HN/Reddit will brutally call you out.
- ❌ Don't gate the free tier too hard. Reddit communities will revolt.
- ❌ Don't bug existing users for upgrades more than once a month. Email fatigue kills retention.
- ❌ Don't over-promise on the AI assistant. Be honest: "answers based on your scan data, not magic."

---

## Metrics to track from day 1

| Metric | Tool | Goal Month 1 |
|---|---|---|
| Signups | Supabase user count | 500 |
| Active agents | `select count(distinct user_id) from agents where last_seen_at > now() - interval '7 days'` | 100 |
| Trial → paid conversion | Stripe | 5–10% |
| MRR | Stripe | $200–500 |
| GitHub stars | github.com/jakes1345/ShadowCypher | 200 |
| HN comment count on launch | hn.algolia.com | 50+ |

---

## Realistic 90-day projection

| Day | Milestone |
|---|---|
| 0 | Pre-launch checklist done, Stripe Live |
| 1 | HN launch — 1000 visitors, 100 signups |
| 7 | First Reddit post — 500 visitors, 50 signups |
| 14 | Second Reddit post + Product Hunt — 2000 visitors, 200 signups |
| 30 | First $100 MRR (10 paying users) |
| 45 | First YouTube video posted |
| 60 | First SEO blog post indexed |
| 90 | $500 MRR (50 paying users), 1000+ free signups, 300+ GitHub stars |

This is ambitious but achievable if all phases ship. Cut by half if you only do HN + Reddit.
