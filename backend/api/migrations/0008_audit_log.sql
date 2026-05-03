-- ShadowCypher Phase 4H — per-user audit log
-- Run AFTER 0001-0007. Idempotent.

create table if not exists public.audit_log (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  event_type  text not null,                   -- 'signin' | 'signout' | 'key_rotated' | 'key_revoked' | 'plan_changed' | 'account_deleted' | 'webhook_added' | 'team_created' | 'team_joined' | 'totp_enabled' | 'totp_disabled' | 'export_downloaded'
  ip          text,
  user_agent  text,
  metadata    jsonb default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

create index if not exists idx_audit_user on public.audit_log(user_id, created_at desc);

alter table public.audit_log enable row level security;

drop policy if exists "audit_select_own" on public.audit_log;

create policy "audit_select_own" on public.audit_log
  for select to authenticated using (auth.uid() = user_id);
