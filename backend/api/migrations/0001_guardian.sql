-- ShadowCypher Guardian — Phase 2 schema
-- Run this in Supabase SQL editor (Dashboard → SQL → New query → Run)
--
-- Creates 4 tables for the Guardian agent flow:
--   agents       — registered agent installs (one row per machine running shadowcypher-agent)
--   devices      — discovered devices on a user's networks (one row per MAC seen)
--   scans        — historical scan runs (one row per /v1/scans POST)
--   incidents    — security alerts the agent raised (ARP spoof, new device, port change…)
--
-- All tables use Row-Level Security so the anon-key client can only read its own rows.
-- The Worker uses the service_role key and bypasses RLS to write on behalf of users.

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

-- ─── devices ───────────────────────────────────────────────────────────────
create table if not exists public.devices (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  agent_id        uuid references public.agents(id) on delete set null,
  mac             text not null,
  ip              text,
  hostname        text,
  vendor          text,
  device_type     text,                                    -- 'router' | 'phone' | 'iot' | 'pc' | 'unknown'
  open_ports      jsonb default '[]'::jsonb,
  first_seen_at   timestamptz not null default now(),
  last_seen_at    timestamptz not null default now(),
  trusted         boolean not null default false,
  notes           text,
  unique(user_id, mac)
);
create index if not exists idx_devices_user on public.devices(user_id);
create index if not exists idx_devices_last_seen on public.devices(user_id, last_seen_at desc);

-- ─── scans ─────────────────────────────────────────────────────────────────
create table if not exists public.scans (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  agent_id        uuid references public.agents(id) on delete set null,
  scan_type       text not null,                          -- 'network' | 'port' | 'router' | 'arp' | 'audit'
  target          text,                                    -- subnet, ip, etc.
  duration_ms     int,
  device_count    int,
  result          jsonb not null default '{}'::jsonb,     -- raw scan output
  started_at      timestamptz not null default now()
);
create index if not exists idx_scans_user on public.scans(user_id, started_at desc);

-- ─── incidents ─────────────────────────────────────────────────────────────
create table if not exists public.incidents (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  agent_id        uuid references public.agents(id) on delete set null,
  device_id       uuid references public.devices(id) on delete set null,
  severity        text not null,                          -- 'info' | 'warning' | 'critical'
  category        text not null,                          -- 'new_device' | 'arp_spoof' | 'port_change' | 'router_exposure' | 'audit_failure'
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

-- Anon-key (browser) sessions: read-only, own rows only
create policy "agents_select_own"    on public.agents     for select to authenticated using (auth.uid() = user_id);
create policy "devices_select_own"   on public.devices    for select to authenticated using (auth.uid() = user_id);
create policy "scans_select_own"     on public.scans      for select to authenticated using (auth.uid() = user_id);
create policy "incidents_select_own" on public.incidents  for select to authenticated using (auth.uid() = user_id);

-- Authenticated users can ack their own incidents directly
create policy "incidents_update_own" on public.incidents
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Authenticated users can mark their own devices trusted/untrusted from the dashboard
create policy "devices_update_own" on public.devices
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- The service_role key bypasses RLS entirely (for the Worker to write on behalf of agents).
-- No INSERT policies needed for client — clients only read.
