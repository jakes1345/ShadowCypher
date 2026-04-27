# Landing page copy variants

Use these as A/B test material on the hero section of shadowcypher.site. Current hero says "Enterprise security, sovereign by design" — that's fine but generic. Better variants below, ranked by my read of conversion potential.

---

## Variant A — concrete and specific (recommended)

**Hero**: `See every device on your network — before something rogue does.`

**Subhead**: `ShadowCypher is an open-source security platform that continuously scans your home or office network, alerts you when anything weird happens, and lets you ask plain-English questions about what's going on. Built on the same tools security pros already trust.`

**CTAs**: `Install free` · `See pricing`

---

## Variant B — fear-based (high CTR, lower trust)

**Hero**: `Your network has 14 devices. Do you know what 3 of them are doing?`

**Subhead**: `Your router probably has known vulnerabilities. Your smart TV is calling unfamiliar servers. ShadowCypher gives you the full picture in 60 seconds — and tells you what to do about it.`

**CTAs**: `Run a free scan` · `See sample report`

---

## Variant C — benefit-led, friendly

**Hero**: `Network security that doesn't require a CISSP.`

**Subhead**: `Continuous monitoring, real-time threat alerts, and an AI assistant that answers questions like "what changed this week?" in plain English. Free for personal use, $9.99/mo for households and small teams.`

**CTAs**: `Get started free` · `How it works`

---

## Variant D — direct comparison

**Hero**: `CrowdStrike for $9.99/month.`

**Subhead**: `Open-source, self-hostable, and built on the security tools you already trust. Real continuous monitoring. Real alerts. Real AI. No million-dollar enterprise contract required.`

**CTAs**: `Try it free` · `Compare plans`

---

## Above-the-fold supporting elements (regardless of variant)

After hero, before deeper sections, add this strip:

```
Trusted by [counter] operators · Open source on GitHub · 14-day Pro trial, no card
```

(`[counter]` should pull a real number from your DB — once you have 50+ signups, this becomes social proof. Until then, leave it out.)

---

## Feature-section microcopy rewrites

Current dashboard text uses "tactical", "ghost-grade", "sovereign" heavily. For mainstream signups, lean on the boring/professional side:

| Current | Replace with |
|---|---|
| "Tactical Arsenal" | "Security toolkit" |
| "Ghost Protocol" | "Anonymity stack" |
| "Sovereign Tactical Suite" | "Network security platform" |
| "Total operational invisibility" | "Privacy-first browsing" |
| "Engage Arsenal" | "Browse tools" |
| "Guardian Shield" | "Protect my network" |

Keep the technical/tactical naming for the docs and the in-product UI (it's part of the brand identity), but on the marketing page lean clear over clever.

---

## Pricing-page additions to consider

1. **FAQ section** below the comparison table:
   - "Is the data really private?" (yes — self-hostable, no telemetry)
   - "What's the difference between trial and free?" (trial = full Pro for 14 days, then auto-downgrade unless you subscribe)
   - "Can I cancel anytime?" (yes — Stripe customer portal, one click)
   - "Do you offer annual plans?" (not yet — coming soon at 20% off monthly)
   - "Education / non-profit pricing?" (50% off Operator if you email)

2. **Logo strip** of "Used by" companies/communities (start with: GitHub, your university, etc. — even small ones build trust)

3. **Customer testimonial** (even one anonymous quote helps): `"Found 3 IoT devices I didn't know were on my network in 5 minutes." — early Pro user, security engineer at $FORTUNE_500`

---

## Email templates

### Welcome email (sent immediately after signup)

```
Subject: Welcome to ShadowCypher

Hey,

Thanks for signing up. Quick orientation:

• Your trial: 14 days of Guardian Pro free, no card needed
• Get started: install the agent → shadowcypher.site/agent
• Help: just hit reply, I read every email

What broke or felt confusing? Tell me — early feedback shapes the product.

— Jacob, ShadowCypher
github.com/jakes1345
```

### Trial-day-12 reminder

```
Subject: 2 days left on your Pro trial

Quick heads up: your Pro trial ends in 2 days.

What you'd lose if you don't subscribe:
• 24/7 monitoring (back to manual scans only)
• Email + push alerts (silent on incidents)
• AI assistant (locked)
• 90-day scan history (back to 7 days)

If Pro hasn't been useful enough to keep, I get it — would love to hear why so I can fix it.

If it has been useful: shadowcypher.site/pricing → $9.99/mo, cancel anytime.

— Jacob
```

### First incident email (sent 24h after first real alert)

```
Subject: We found something on your network last night

Hey,

Your agent flagged a [SEVERITY] incident at [TIMESTAMP]:
[INCIDENT_TITLE]

This is exactly what Pro is for. If the alert was useful, that's the value prop in action.

Open dashboard: shadowcypher.site/?nav=account

— Jacob
```
