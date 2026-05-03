-- ShadowCypher Phase 4I — annual subscription support
-- Run AFTER 0001-0008. Idempotent.

-- Track billing interval so the dashboard can show "renews in X months"
-- and the webhook can map annual price IDs to the same plan tier.
alter table public.profiles
  add column if not exists billing_interval text not null default 'month';   -- 'month' | 'year'
