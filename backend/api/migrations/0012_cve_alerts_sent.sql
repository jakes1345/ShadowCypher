-- ShadowCypher — CVE alert deduplication table
-- Run after 0011. Idempotent.

create table if not exists public.cve_alerts_sent (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  device_id  uuid not null references public.devices(id) on delete cascade,
  cve_id     text not null,
  fired_at   timestamptz not null default now()
);

create unique index if not exists cve_alerts_sent_dedup
  on public.cve_alerts_sent(user_id, device_id, cve_id);

create index if not exists cve_alerts_sent_user_idx
  on public.cve_alerts_sent(user_id);

alter table public.cve_alerts_sent enable row level security;

create policy "cve_alerts_select_own" on public.cve_alerts_sent
  for select to authenticated using (auth.uid() = user_id);
