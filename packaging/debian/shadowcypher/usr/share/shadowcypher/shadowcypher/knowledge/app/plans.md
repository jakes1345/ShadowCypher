# ShadowCypher Plans Reference

## Available Plans

### Free
- Basic network monitoring
- 5 network scans per day
- 10 device tracking limit
- 30-day incident history
- Community support
- Guardian Android app
- Shadow voice assistant (basic)
- No ShadowScript missions

### Pro
- Unlimited network scans
- Unlimited device tracking
- 1-year incident history
- CVE correlation alerts
- Email incident notifications
- Priority support
- ShadowScript missions (DSL commands only)
- All Shadow voice features
- Ghost Mode

### Operator
- Everything in Pro
- ShadowScript shell passthrough
- API access (all endpoints)
- Webhook integrations
- Custom threat detection rules
- 3-year incident history
- Dedicated support channel
- Team access (up to 3 members, future)
- White-label reporting (future)

## Plan Features Matrix

| Feature | Free | Pro | Operator |
|---------|------|-----|----------|
| Network scan (per day) | 5 | Unlimited | Unlimited |
| Devices tracked | 10 | Unlimited | Unlimited |
| Incident history | 30 days | 1 year | 3 years |
| CVE correlation | Basic | Full | Full |
| Email alerts | No | Yes | Yes |
| Guardian Android app | Yes | Yes | Yes |
| Shadow voice assistant | Basic | Full | Full |
| Ghost Mode | No | Yes | Yes |
| ShadowScript missions | No | DSL only | Shell + DSL |
| API access | No | Read | Full |
| Webhooks | No | No | Yes |
| Support | Community | Priority | Dedicated |

## API Access by Plan

### Endpoints Available
| Endpoint | Free | Pro | Operator |
|----------|------|-----|---------|
| GET /v1/me | Yes | Yes | Yes |
| GET /v1/guardian/summary | Yes | Yes | Yes |
| POST /v1/scans | Limited | Yes | Yes |
| GET /v1/incidents | Yes | Yes | Yes |
| GET /v1/agents | Yes | Yes | Yes |
| POST /v1/agents/:id/missions | No | Yes | Yes |
| shell: missions | No | No | Yes |
| POST /v1/webhooks | No | No | Yes |

## Checking Your Plan

From Shadow voice assistant:
- "What plan am I on?"
- "Check my account"
- "Do I have Operator access?"

From Android Guardian app:
- Settings screen shows current plan

Via API:
```
GET /v1/me
Response: { email, effective_plan, in_trial, trial_ends_at }
```

## Upgrade

Visit shadowcypher.site → Account → Upgrade Plan
Plans are billed monthly; cancel anytime.
Trial: 14 days of Pro available on signup.
