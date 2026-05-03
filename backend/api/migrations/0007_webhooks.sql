-- ShadowCypher Phase 4G — outbound webhooks (Slack/Discord/PagerDuty/custom)
-- Run AFTER 0001-0006. Idempotent.

create table if not exists public.webhooks (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  url             text not null,
  label           text,                                  -- "Slack #ops", "PagerDuty"
  events          text[] not null default array['incident.created']::text[],
  min_severity    text not null default 'warning',      -- 'info' | 'warning' | 'critical'
  signing_secret  text not null,                        -- random per-webhook secret for HMAC
  is_active       boolean not null default true,
  last_called_at  timestamptz,
  last_status     int,
  failure_count   int not null default 0,
  created_at      timestamptz not null default now()
);

create index if not exists idx_webhooks_user on public.webhooks(user_id) where is_active = true;

alter table public.webhooks enable row level security;

drop policy if exists "webhooks_select_own" on public.webhooks;
drop policy if exists "webhooks_update_own" on public.webhooks;

create policy "webhooks_select_own" on public.webhooks
  for select to authenticated using (auth.uid() = user_id);

create policy "webhooks_update_own" on public.webhooks
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
