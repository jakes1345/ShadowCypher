# Webhook Integration Templates — Design Spec

**Goal:** Splunk, Datadog, and ConnectWise get native payload formatting + UI setup cards in the webhooks section.

**Date:** 2026-05-08

---

## Architecture

Two parts: backend payload formatting (extend existing URL-pattern detection in `webhooks.ts`) and frontend template cards (extend existing webhooks UI section in `index.html`).

---

## Backend — Native Payload Formats

Each integration is detected by URL pattern in `deliverOne` and `deliverCveOne`. The existing Slack/Discord detection pattern is extended with three new cases.

### Splunk HEC
**Detection:** URL contains `/services/collector`
**Format:**
```json
{
  "time": 1234567890.123,
  "source": "shadowcypher",
  "sourcetype": "security_alert",
  "index": "main",
  "event": {
    "id": "...",
    "severity": "critical",
    "title": "...",
    "detail": "...",
    "category": "..."
  }
}
```
**Content-Type:** `application/json`
**Auth:** Splunk uses `Authorization: Splunk <HEC_TOKEN>` — the user pastes the full URL including the token as a query param (`?token=...`) OR we note in the UI that they should use the URL with token in header. Since our webhook system only stores URLs, the token goes in the URL: `https://splunk.company.com:8088/services/collector?token=xxx`. We extract it and set the header.

Actually simpler: Splunk HEC accepts the token as `Authorization: Splunk <token>` OR as a URL query param. Users paste `https://host:8088/services/collector` and put their token in the URL as `?token=xxx`. We send the payload — Splunk accepts both. No special handling needed beyond payload format.

### Datadog
**Detection:** URL contains `datadoghq.com`
**Format (Events API):**
```json
{
  "title": "[CRITICAL] New Device Detected on 192.168.1.1",
  "text": "%%% \n**Detail:** ...\n**Category:** ...\n %%%",
  "alert_type": "error",
  "source_type_name": "ShadowCypher",
  "tags": ["severity:critical", "source:shadowcypher", "category:new_device"]
}
```
**alert_type mapping:** `critical` → `"error"`, `warning` → `"warning"`, `info` → `"info"`

### ConnectWise Manage
**Detection:** URL contains `connectwise`
**Format (Service Ticket):**
```json
{
  "summary": "[CRITICAL] New Device Detected — 192.168.1.1",
  "initialDescription": "Severity: CRITICAL\nCategory: new_device\n\nDetail: ...",
  "board": { "name": "ShadowCypher" },
  "priority": { "name": "High" },
  "status": { "name": "New" }
}
```
**priority mapping:** `critical` → `"High"`, `warning` → `"Medium"`, `info` → `"Low"`

---

## Frontend — Template Cards

Location: webhooks section in `index.html`, above the "Add Webhook" form.

Three cards in a row:

```
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  🔴 Splunk   │  │  🟣 Datadog  │  │  🔵 ConnectWise  │
│              │  │              │  │                  │
│ HEC endpoint │  │ Events API   │  │ Service Tickets  │
│              │  │              │  │                  │
│ [Quick Add]  │  │ [Quick Add]  │  │  [Quick Add]     │
└──────────────┘  └──────────────┘  └──────────────────┘
```

Each "Quick Add" button pre-fills the webhook form:
- **URL field:** placeholder text showing the expected URL format
- **Label field:** pre-filled with service name (e.g. "Splunk SIEM")
- **Events:** all events checked
- **Min severity:** Critical for Splunk/ConnectWise, Warning for Datadog

---

## Modified Files

| File | Change |
|---|---|
| `backend/api/src/webhooks.ts` | Add Splunk/Datadog/ConnectWise detection + payload formatting in `deliverOne` and `deliverCveOne` |
| `index.html` + `www/index.html` | Add template cards UI to webhooks section |

---

## Out of Scope

- OAuth flows for Datadog/ConnectWise (users handle auth via URL/token)
- Webhook delivery retry logic (future phase)
- PagerDuty, OpsGenie (future phase)
