-- ShadowCypher Phase 4B — notification preferences
-- Run AFTER 0001/0002/0003 idempotent migrations.

create table if not exists public.notification_prefs (
  user_id           uuid primary key references auth.users(id) on delete cascade,
  email_enabled     boolean not null default true,
  email_severity    text not null default 'warning',  -- 'info' | 'warning' | 'critical'
  push_enabled      boolean not null default false,
  push_subscription jsonb,                            -- web push subscription object
  updated_at        timestamptz not null default now()
);

alter table public.notification_prefs enable row level security;

drop policy if exists "notif_prefs_select_own" on public.notification_prefs;
drop policy if exists "notif_prefs_update_own" on public.notification_prefs;

create policy "notif_prefs_select_own" on public.notification_prefs
  for select to authenticated using (auth.uid() = user_id);

create policy "notif_prefs_update_own" on public.notification_prefs
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
