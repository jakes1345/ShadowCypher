# Webhook Integration Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add native payload formatting for Splunk, Datadog, and ConnectWise in the webhook delivery layer, plus Quick Setup template cards in the webhooks UI.

**Architecture:** Extend the existing URL-pattern detection in `deliverOne` and `deliverCveOne` (webhooks.ts) with three new cases. Add template cards above the "Add webhook" form in `index.html` that pre-fill the form fields on click.

**Tech Stack:** TypeScript Cloudflare Worker, vanilla HTML/JS (no build step).

---

## Files

| File | Action | Purpose |
|---|---|---|
| `backend/api/src/webhooks.ts` | Modify | Add Splunk/Datadog/ConnectWise payload formatting |
| `www/index.html` + `index.html` | Modify | Add template cards UI above webhook form |

---

## Task 1: Backend — Splunk/Datadog/ConnectWise payload formatting

**Files:**
- Modify: `backend/api/src/webhooks.ts` — `deliverOne` function (line ~177) and `deliverCveOne` function

### Incident delivery (`deliverOne`)

- [ ] **Step 1: Add the three new platform detections to `deliverOne`**

In `backend/api/src/webhooks.ts`, replace the existing `deliverOne` function body (the part that sets `body` and `contentType`) with the extended version below. The function signature and fetch call stay the same — only the if/else chain changes:

```typescript
async function deliverOne(wh: WebhookRow, incident: IncidentForWebhook): Promise<{ ok: boolean; status: number; reason?: string }> {
  const isSlack      = /hooks\.slack\.com\//.test(wh.url);
  const isDiscord    = /discord(?:app)?\.com\/api\/webhooks\//.test(wh.url);
  const isSplunk     = /\/services\/collector/.test(wh.url);
  const isDatadog    = /datadoghq\.com/.test(wh.url);
  const isConnectWise = /connectwise/i.test(wh.url);

  let body: string;
  let contentType = "application/json";

  if (isSlack) {
    body = JSON.stringify({
      text: `*[${incident.severity.toUpperCase()}]* ${incident.title}`,
      attachments: [{
        color: incident.severity === "critical" ? "#ff3b6b" : incident.severity === "warning" ? "#ffb84d" : "#7eb6ff",
        text: incident.detail || incident.category,
        footer: "ShadowCypher",
        ts: Math.floor(Date.now() / 1000),
      }],
    });
  } else if (isDiscord) {
    body = JSON.stringify({
      embeds: [{
        title: `[${incident.severity.toUpperCase()}] ${incident.title}`,
        description: incident.detail || incident.category,
        color: incident.severity === "critical" ? 0xff3b6b : incident.severity === "warning" ? 0xffb84d : 0x7eb6ff,
        footer: { text: "ShadowCypher" },
        timestamp: new Date().toISOString(),
      }],
    });
  } else if (isSplunk) {
    body = JSON.stringify({
      time: Date.now() / 1000,
      source: "shadowcypher",
      sourcetype: "security_alert",
      index: "main",
      event: {
        id: incident.id,
        severity: incident.severity,
        category: incident.category,
        title: incident.title,
        detail: incident.detail,
      },
    });
  } else if (isDatadog) {
    const alertType = incident.severity === "critical" ? "error" : incident.severity === "warning" ? "warning" : "info";
    body = JSON.stringify({
      title: `[${incident.severity.toUpperCase()}] ${incident.title}`,
      text: `%%% \n**Category:** ${incident.category}\n**Detail:** ${incident.detail || "—"}\n %%%`,
      alert_type: alertType,
      source_type_name: "ShadowCypher",
      tags: [`severity:${incident.severity}`, `category:${incident.category}`, "source:shadowcypher"],
    });
  } else if (isConnectWise) {
    const priority = incident.severity === "critical" ? "High" : incident.severity === "warning" ? "Medium" : "Low";
    body = JSON.stringify({
      summary: `[${incident.severity.toUpperCase()}] ${incident.title}`,
      initialDescription: `Severity: ${incident.severity.toUpperCase()}\nCategory: ${incident.category}\n\n${incident.detail || ""}`,
      board: { name: "ShadowCypher" },
      priority: { name: priority },
      status: { name: "New" },
    });
  } else {
    body = JSON.stringify({
      event: "incident.created",
      timestamp: new Date().toISOString(),
      incident: {
        id: incident.id,
        severity: incident.severity,
        category: incident.category,
        title: incident.title,
        detail: incident.detail,
      },
    });
  }

  const signature = await hmacSha256(wh.signing_secret, body);
  try {
    const resp = await fetch(wh.url, {
      method: "POST",
      headers: {
        "Content-Type": contentType,
        "User-Agent": "ShadowCypher-Webhook/1.0",
        "X-ShadowCypher-Signature": `sha256=${signature}`,
        "X-ShadowCypher-Event": "incident.created",
        "X-ShadowCypher-Delivery": incident.id,
      },
      body,
      signal: AbortSignal.timeout(8000),
    });
    const ok = resp.ok || resp.status === 204;
    dbUpdate(undefined as never, "webhooks", {} as never, {} as never).catch(() => null);
    return { ok, status: resp.status };
  } catch (e) {
    return { ok: false, status: 0, reason: e instanceof Error ? e.message : "unknown" };
  }
}
```

### CVE delivery (`deliverCveOne`)

- [ ] **Step 2: Add the same three platform detections to `deliverCveOne`**

In the `deliverCveOne` function (around line 300 in the updated file), find where `isSlack` and `isDiscord` are detected and the body is built. Replace that entire if/else chain with:

```typescript
  const isSlack      = /hooks\.slack\.com\//.test(wh.url);
  const isDiscord    = /discord(?:app)?\.com\/api\/webhooks\//.test(wh.url);
  const isSplunk     = /\/services\/collector/.test(wh.url);
  const isDatadog    = /datadoghq\.com/.test(wh.url);
  const isConnectWise = /connectwise/i.test(wh.url);

  const title = `[${payload.severity}] ${payload.cve_id} affects ${payload.device_name}`;
  const text = `${payload.description}\nDevice: ${payload.device_ip} | Matched on: ${payload.matched_on.join(", ")}\n${payload.cve_url}`;
  const color = payload.severity === "CRITICAL" ? "#ff3b6b" : "#ffb84d";

  let body: string;
  if (isSlack) {
    body = JSON.stringify({
      text: `*${title}*`,
      attachments: [{ color, text, footer: "ShadowCypher CVE Alert", ts: Math.floor(Date.now() / 1000) }],
    });
  } else if (isDiscord) {
    body = JSON.stringify({
      embeds: [{
        title,
        description: text,
        color: payload.severity === "CRITICAL" ? 0xff3b6b : 0xffb84d,
        footer: { text: "ShadowCypher CVE Alert" },
        timestamp: new Date().toISOString(),
      }],
    });
  } else if (isSplunk) {
    body = JSON.stringify({
      time: Date.now() / 1000,
      source: "shadowcypher",
      sourcetype: "cve_alert",
      index: "main",
      event: {
        cve_id: payload.cve_id,
        severity: payload.severity,
        cvss: payload.cvss,
        description: payload.description,
        device_ip: payload.device_ip,
        device_name: payload.device_name,
        matched_on: payload.matched_on,
        cve_url: payload.cve_url,
      },
    });
  } else if (isDatadog) {
    const alertType = payload.severity === "CRITICAL" ? "error" : "warning";
    body = JSON.stringify({
      title,
      text: `%%% \n${text}\n %%%`,
      alert_type: alertType,
      source_type_name: "ShadowCypher",
      tags: [`severity:${payload.severity.toLowerCase()}`, `cve:${payload.cve_id}`, "source:shadowcypher"],
    });
  } else if (isConnectWise) {
    const priority = payload.severity === "CRITICAL" ? "High" : "Medium";
    body = JSON.stringify({
      summary: title,
      initialDescription: text,
      board: { name: "ShadowCypher" },
      priority: { name: priority },
      status: { name: "New" },
    });
  } else {
    const canonical = JSON.stringify({ event: "cve.matched", fired_at: new Date().toISOString(), data: payload });
    const signature = await hmacSha256(wh.signing_secret, canonical);
    try {
      const resp = await fetch(wh.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "User-Agent": "ShadowCypher-Webhook/1.0",
          "X-ShadowCypher-Signature": `sha256=${signature}`,
          "X-ShadowCypher-Event": "cve.matched",
        },
        body: canonical,
        signal: AbortSignal.timeout(8000),
      });
      return { ok: resp.ok || resp.status === 204, status: resp.status };
    } catch {
      return { ok: false, status: 0 };
    }
  }

  try {
    const resp = await fetch(wh.url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "User-Agent": "ShadowCypher-Webhook/1.0" },
      body,
      signal: AbortSignal.timeout(8000),
    });
    return { ok: resp.ok || resp.status === 204, status: resp.status };
  } catch {
    return { ok: false, status: 0 };
  }
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/jack/ShadowCypher/backend/api
node_modules/.bin/tsc --noEmit 2>&1
```
Expected: no output (clean).

- [ ] **Step 4: Deploy**

```bash
node_modules/.bin/wrangler deploy 2>&1 | tail -5
```
Expected: `Deployed shadowcypher-api triggers` with no errors.

- [ ] **Step 5: Commit**

```bash
cd /home/jack/ShadowCypher
git add backend/api/src/webhooks.ts
git commit -m "feat(webhooks): native Splunk/Datadog/ConnectWise payload formatting"
```

---

## Task 2: Frontend — Template cards UI

**Files:**
- Modify: `www/index.html` (line ~499) and `index.html` (same line — files are identical)

The existing webhooks section HTML is at line ~497–516 of both files. It looks like:
```html
<div style="margin-bottom: 40px;">
    <h3 class="mono" ...>// Webhooks <span ...>(Pro)</span></h3>
    <p style="...">Forward incident events to Slack, Discord, PagerDuty, or any HTTPS URL...</p>
    <div id="webhooks-list" style="margin-bottom:14px;"></div>
    <details ...>
        <summary ...>+ Add webhook</summary>
        ...
    </details>
</div>
```

- [ ] **Step 1: Add the `fillWebhookTemplate` JS function**

In `www/index.html`, find the `createWebhook` function (around line 1540). Just before it, add:

```javascript
        function fillWebhookTemplate(urlPlaceholder, label, severity) {
            const urlEl = document.getElementById('wh-url');
            const labelEl = document.getElementById('wh-label');
            const severityEl = document.getElementById('wh-severity');
            if (urlEl) urlEl.placeholder = urlPlaceholder;
            if (labelEl && !labelEl.value) labelEl.value = label;
            if (severityEl) severityEl.value = severity;
            // Open the details panel so the form is visible
            const details = urlEl?.closest('details');
            if (details) details.open = true;
            if (urlEl) urlEl.focus();
        }
```

- [ ] **Step 2: Add the template cards HTML**

In `www/index.html`, find the existing `<p>` description tag in the webhooks section:
```html
<p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 14px;">Forward incident events to Slack, Discord, PagerDuty, or any HTTPS URL. HMAC-SHA256 signed via per-webhook secret.</p>
```

Replace it with the description plus the three template cards:

```html
<p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 14px;">Forward incident events to Slack, Discord, PagerDuty, or any HTTPS URL. HMAC-SHA256 signed via per-webhook secret.</p>
<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:14px;">
    <button onclick="fillWebhookTemplate('https://your-splunk:8088/services/collector?token=YOUR_HEC_TOKEN','Splunk SIEM','critical')" style="background:rgba(255,128,0,0.08); border:1px solid rgba(255,128,0,0.25); color:#ff8000; padding:10px 8px; border-radius:6px; cursor:pointer; font-size:0.7rem; text-align:left;">
        <div style="font-weight:600; margin-bottom:4px;">⬛ Splunk</div>
        <div style="color:var(--text-secondary); font-size:0.65rem;">HEC endpoint · critical+</div>
    </button>
    <button onclick="fillWebhookTemplate('https://http-intake.logs.datadoghq.com/api/v2/logs?dd-api-key=YOUR_DD_API_KEY','Datadog SIEM','warning')" style="background:rgba(99,0,210,0.08); border:1px solid rgba(99,0,210,0.25); color:#7c3aed; padding:10px 8px; border-radius:6px; cursor:pointer; font-size:0.7rem; text-align:left;">
        <div style="font-weight:600; margin-bottom:4px;">🟣 Datadog</div>
        <div style="color:var(--text-secondary); font-size:0.65rem;">Events API · warning+</div>
    </button>
    <button onclick="fillWebhookTemplate('https://your-company.connectwise.com/v4_6_release/apis/3.0/service/tickets','ConnectWise Manage','critical')" style="background:rgba(0,122,255,0.08); border:1px solid rgba(0,122,255,0.25); color:#007aff; padding:10px 8px; border-radius:6px; cursor:pointer; font-size:0.7rem; text-align:left;">
        <div style="font-weight:600; margin-bottom:4px;">🔵 ConnectWise</div>
        <div style="color:var(--text-secondary); font-size:0.65rem;">Service tickets · critical+</div>
    </button>
</div>
```

- [ ] **Step 3: Apply the identical changes to root `index.html`**

Since `www/index.html` and `index.html` are identical files (confirmed earlier), apply Steps 1 and 2 to `/home/jack/ShadowCypher/index.html` as well — same line numbers, same content.

- [ ] **Step 4: Verify both files updated consistently**

```bash
diff /home/jack/ShadowCypher/index.html /home/jack/ShadowCypher/www/index.html
```
Expected: no output (files identical).

- [ ] **Step 5: Commit**

```bash
cd /home/jack/ShadowCypher
git add www/index.html index.html
git commit -m "feat(ui): add Splunk/Datadog/ConnectWise webhook quick-setup template cards"
```

---

## Self-Review

**Spec coverage:**
- ✅ Splunk HEC payload (`sourcetype: "security_alert"`, `index`, `event`) → Task 1 `deliverOne` + `deliverCveOne`
- ✅ Datadog payload (`alert_type`, `tags`, `source_type_name`) → Task 1
- ✅ ConnectWise payload (`summary`, `board`, `priority`, `status`) → Task 1
- ✅ Severity mapping for each platform → Task 1 (critical/warning/info → platform-specific values)
- ✅ HMAC signing still applied → existing fetch call unchanged for all three new platforms
- ✅ CVE alerts also get native formatting → Task 1 Step 2 (`deliverCveOne`)
- ✅ Template cards in webhooks UI → Task 2
- ✅ Pre-fill URL placeholder + label + severity → `fillWebhookTemplate()` in Task 2
- ✅ Both `index.html` and `www/index.html` updated → Task 2 Step 3
