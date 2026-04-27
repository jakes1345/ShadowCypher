-- ShadowCypher Guardian — Phase 2 schema (IDEMPOTENT — safe to re-run)
-- Run this in Supabase SQL editor. Drops conflicting policies first so re-runs don't error.

-- Make sure pgcrypto / uuid generation is available (Supabase enables this by default but be safe)
create extension if not exists pgcrypto;

-- ─── agents ────────────────────────────────────────────────────────────────
create table if not exists public.agents (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  hostname        text not null,
  os              text,
  agent_version   text,
  registered_at   timestamptz not null default now(),
  last_seen_at    timestamptz,
  created_at      timestamptz not null default now()
);
create index if not exists idx_agents_user on public.agents(user_id);
create index if not exists idx_agents_last_seen on public.agents(last_seen_at desc);

-- For idempotent upserts on (user_id, hostname)
create unique index if not exists uniq_agents_user_hostname on public.agents(user_id, hostname);

-- ─── devices ───────────────────────────────────────────────────────────────
create table if not exists public.devices (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  agent_id        uuid references public.agents(id) on delete set null,
  mac             text not null,
  ip              text,
  hostname        text,
  vendor          text,
  device_type     text,
  open_ports      jsonb default '[]'::jsonb,
  first_seen_at   timestamptz not null default now(),
  last_seen_at    timestamptz not null default now(),
  trusted         boolean not null default false,
  notes           text
);
-- Add unique constraint if not present (separate to make idempotent)
do $$ begin
  if not exists (
    select 1 from pg_constraint where conname = 'devices_user_mac_key'
  ) then
    alter table public.devices add constraint devices_user_mac_key unique (user_id, mac);
  end if;
end $$;
create index if not exists idx_devices_user on public.devices(user_id);
create index if not exists idx_devices_last_seen on public.devices(user_id, last_seen_at desc);

-- ─── scans ─────────────────────────────────────────────────────────────────
create table if not exists public.scans (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  agent_id        uuid references public.agents(id) on delete set null,
  scan_type       text not null,
  target          text,
  duration_ms     int,
  device_count    int,
  result          jsonb not null default '{}'::jsonb,
  started_at      timestamptz not null default now()
);
create index if not exists idx_scans_user on public.scans(user_id, started_at desc);

-- ─── incidents ─────────────────────────────────────────────────────────────
create table if not exists public.incidents (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  agent_id        uuid references public.agents(id) on delete set null,
  device_id       uuid references public.devices(id) on delete set null,
  severity        text not null,
  category        text not null,
  title           text not null,
  detail          text,
  data            jsonb default '{}'::jsonb,
  acknowledged    boolean not null default false,
  acknowledged_at timestamptz,
  created_at      timestamptz not null default now()
);
create index if not exists idx_incidents_user on public.incidents(user_id, created_at desc);
create index if not exists idx_incidents_open on public.incidents(user_id, acknowledged, created_at desc);

-- ─── Row-Level Security ────────────────────────────────────────────────────
alter table public.agents     enable row level security;
alter table public.devices    enable row level security;
alter table public.scans      enable row level security;
alter table public.incidents  enable row level security;

-- Drop existing policies if present, then recreate (idempotent)
drop policy if exists "agents_select_own"    on public.agents;
drop policy if exists "devices_select_own"   on public.devices;
drop policy if exists "scans_select_own"     on public.scans;
drop policy if exists "incidents_select_own" on public.incidents;
drop policy if exists "incidents_update_own" on public.incidents;
drop policy if exists "devices_update_own"   on public.devices;

create policy "agents_select_own"    on public.agents     for select to authenticated using (auth.uid() = user_id);
create policy "devices_select_own"   on public.devices    for select to authenticated using (auth.uid() = user_id);
create policy "scans_select_own"     on public.scans      for select to authenticated using (auth.uid() = user_id);
create policy "incidents_select_own" on public.incidents  for select to authenticated using (auth.uid() = user_id);

create policy "incidents_update_own" on public.incidents
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "devices_update_own" on public.devices
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
