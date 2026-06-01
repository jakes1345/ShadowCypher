-- ShadowCypher — Neon schema (Supabase-free)
-- users + api_keys replace Supabase auth.users + user_metadata

create extension if not exists pgcrypto;

-- ─── users (replaces Supabase auth.users) ──────────────────────────────────
create table if not exists public.users (
  id              uuid primary key default gen_random_uuid(),
  email           text unique not null,
  password_hash   text not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- ─── api_keys ───────────────────────────────────────────────────────────────
create table if not exists public.api_keys (
  key             text primary key,  -- sc_live_<48 hex>
  user_id         uuid not null references public.users(id) on delete cascade,
  created_at      timestamptz not null default now(),
  revoked         boolean not null default false
);
create index if not exists idx_api_keys_user on public.api_keys(user_id);

-- ─── profiles ───────────────────────────────────────────────────────────────
create table if not exists public.profiles (
  user_id                  uuid primary key references public.users(id) on delete cascade,
  email                    text,
  handle                   text,
  plan                     text not null default 'community',
  trial_ends_at            timestamptz,
  stripe_customer_id       text unique,
  stripe_subscription_id   text unique,
  subscription_status      text,
  current_period_end       timestamptz,
  cancel_at_period_end     boolean not null default false,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);
create index if not exists idx_profiles_plan on public.profiles(plan);

-- ─── agents ─────────────────────────────────────────────────────────────────
create table if not exists public.agents (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.users(id) on delete cascade,
  hostname        text not null,
  os              text,
  agent_version   text,
  registered_at   timestamptz not null default now(),
  last_seen_at    timestamptz,
  created_at      timestamptz not null default now()
);
create unique index if not exists uniq_agents_user_hostname on public.agents(user_id, hostname);
create index if not exists idx_agents_user on public.agents(user_id);

-- ─── devices ────────────────────────────────────────────────────────────────
create table if not exists public.devices (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.users(id) on delete cascade,
  agent_id        uuid references public.agents(id) on delete set null,
  mac             text not null,
  ip              text,
  hostname        text,
  vendor          text,
  device_type     text,
  os_fingerprint  text,
  open_ports      jsonb default '[]'::jsonb,
  first_seen_at   timestamptz not null default now(),
  last_seen_at    timestamptz not null default now(),
  trusted         boolean not null default false,
  notes           text,
  constraint devices_user_mac_key unique (user_id, mac)
);
create index if not exists idx_devices_user on public.devices(user_id);
create index if not exists idx_devices_last_seen on public.devices(user_id, last_seen_at desc);

-- ─── scans ──────────────────────────────────────────────────────────────────
create table if not exists public.scans (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.users(id) on delete cascade,
  agent_id        uuid references public.agents(id) on delete set null,
  scan_type       text not null,
  target          text,
  duration_ms     int,
  device_count    int,
  result          jsonb not null default '{}'::jsonb,
  started_at      timestamptz not null default now()
);
create index if not exists idx_scans_user on public.scans(user_id, started_at desc);

-- ─── incidents ──────────────────────────────────────────────────────────────
create table if not exists public.incidents (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.users(id) on delete cascade,
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

-- ─── notification_prefs ─────────────────────────────────────────────────────
create table if not exists public.notification_prefs (
  user_id         uuid primary key references public.users(id) on delete cascade,
  email_incidents boolean not null default true,
  email_cves      boolean not null default true,
  webhook_url     text,
  updated_at      timestamptz not null default now()
);

-- ─── teams ──────────────────────────────────────────────────────────────────
create table if not exists public.teams (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,
  owner_id        uuid not null references public.users(id) on delete cascade,
  created_at      timestamptz not null default now()
);

create table if not exists public.team_members (
  team_id         uuid not null references public.teams(id) on delete cascade,
  user_id         uuid not null references public.users(id) on delete cascade,
  role            text not null default 'member',
  invited_by      uuid references public.users(id),
  joined_at       timestamptz not null default now(),
  primary key (team_id, user_id)
);

create table if not exists public.team_invites (
  id              uuid primary key default gen_random_uuid(),
  team_id         uuid not null references public.teams(id) on delete cascade,
  email           text not null,
  invited_by      uuid not null references public.users(id),
  token           text unique not null default encode(gen_random_bytes(24), 'hex'),
  expires_at      timestamptz not null default now() + interval '7 days',
  created_at      timestamptz not null default now()
);

-- ─── ai_usage ───────────────────────────────────────────────────────────────
create table if not exists public.ai_usage (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.users(id) on delete cascade,
  model           text,
  input_tokens    int default 0,
  output_tokens   int default 0,
  created_at      timestamptz not null default now()
);
create index if not exists idx_ai_usage_user on public.ai_usage(user_id, created_at desc);

-- ─── webhooks ───────────────────────────────────────────────────────────────
create table if not exists public.webhooks (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.users(id) on delete cascade,
  url             text not null,
  secret          text not null default encode(gen_random_bytes(24), 'hex'),
  events          jsonb not null default '["incident","scan"]'::jsonb,
  enabled         boolean not null default true,
  created_at      timestamptz not null default now()
);
create index if not exists idx_webhooks_user on public.webhooks(user_id);

-- ─── audit_log ──────────────────────────────────────────────────────────────
create table if not exists public.audit_log (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references public.users(id) on delete set null,
  action          text not null,
  resource        text,
  ip              text,
  ua              text,
  meta            jsonb default '{}'::jsonb,
  created_at      timestamptz not null default now()
);
create index if not exists idx_audit_user on public.audit_log(user_id, created_at desc);

-- ─── device_auth_codes ──────────────────────────────────────────────────────
create table if not exists public.device_auth_codes (
  device_code     text primary key,
  user_code       text unique not null,
  user_id         uuid references public.users(id) on delete cascade,
  client_id       text not null,
  authorized      boolean not null default false,
  expires_at      timestamptz not null,
  created_at      timestamptz not null default now()
);

-- ─── referral_redemptions ───────────────────────────────────────────────────
create table if not exists public.referral_redemptions (
  id              uuid primary key default gen_random_uuid(),
  referrer_id     uuid not null references public.users(id) on delete cascade,
  referee_id      uuid not null references public.users(id) on delete cascade,
  code            text not null,
  redeemed_at     timestamptz not null default now(),
  unique(referee_id)
);

-- ─── cve_alerts_sent ────────────────────────────────────────────────────────
create table if not exists public.cve_alerts_sent (
  user_id         uuid not null references public.users(id) on delete cascade,
  cve_id          text not null,
  sent_at         timestamptz not null default now(),
  primary key (user_id, cve_id)
);

-- ─── chat ───────────────────────────────────────────────────────────────────
create table if not exists public.chat_rooms (
  id              text primary key,
  name            text not null,
  created_at      timestamptz not null default now()
);
insert into public.chat_rooms (id, name) values ('global', 'Global') on conflict do nothing;

create table if not exists public.chat_messages (
  id              uuid primary key default gen_random_uuid(),
  room_id         text not null references public.chat_rooms(id) on delete cascade,
  user_id         uuid not null references public.users(id) on delete cascade,
  handle          text not null,
  body            text not null,
  created_at      timestamptz not null default now()
);
create index if not exists idx_chat_messages_room on public.chat_messages(room_id, created_at desc);

create table if not exists public.chat_presence (
  user_id         uuid not null references public.users(id) on delete cascade,
  room_id         text not null references public.chat_rooms(id) on delete cascade,
  handle          text not null,
  last_seen_at    timestamptz not null default now(),
  primary key (user_id, room_id)
);
