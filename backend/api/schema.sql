-- ShadowCypher Database Schema
-- Run this in the Supabase SQL editor for your project.
-- The Cloudflare Worker uses the service_role key (bypasses RLS).

-- ─── Core user profile ──────────────────────────────────────────────────────

create table if not exists public.profiles (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null unique references auth.users(id) on delete cascade,
  handle          text unique,
  plan            text not null default 'community',
  trial_ends_at   timestamptz,
  subscription_status text default 'inactive',
  current_period_end  timestamptz,
  stripe_customer_id  text,
  api_key         text unique,
  created_at      timestamptz not null default now()
);

create table if not exists public.user_profiles (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null unique references auth.users(id) on delete cascade,
  display_name text,
  bio          text,
  avatar_url   text,
  settings     jsonb not null default '{}',
  created_at   timestamptz not null default now()
);

-- Auto-create profile row when Supabase Auth creates a user
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (user_id, handle, api_key)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'handle', split_part(new.email, '@', 1)),
    coalesce(new.raw_user_meta_data->>'api_key', 'sc_live_' || encode(gen_random_bytes(24), 'hex'))
  )
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ─── Guardian agent tables ───────────────────────────────────────────────────

create table if not exists public.agents (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  hostname      text not null,
  os            text,
  agent_version text,
  last_seen_at  timestamptz default now(),
  created_at    timestamptz not null default now(),
  unique(user_id, hostname)
);

create table if not exists public.devices (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  agent_id      uuid references public.agents(id) on delete set null,
  mac           text not null,
  ip            text,
  hostname      text,
  vendor        text,
  device_type   text,
  open_ports    integer[],
  os_fingerprint text,
  last_seen_at  timestamptz default now(),
  created_at    timestamptz not null default now(),
  unique(user_id, mac)
);

create table if not exists public.scans (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  agent_id    uuid references public.agents(id) on delete set null,
  scan_type   text not null,
  target      text,
  duration_ms integer,
  result      jsonb,
  devices     jsonb,
  started_at  timestamptz,
  created_at  timestamptz not null default now()
);

create table if not exists public.incidents (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  agent_id     uuid references public.agents(id) on delete set null,
  device_id    uuid references public.devices(id) on delete set null,
  severity     text not null default 'info',
  category     text not null,
  title        text not null,
  detail       text,
  data         jsonb,
  acknowledged boolean not null default false,
  acked_at     timestamptz,
  created_at   timestamptz not null default now()
);

create table if not exists public.missions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  agent_id     uuid references public.agents(id) on delete cascade,
  type         text not null,
  payload      jsonb,
  status       text not null default 'pending',
  result       jsonb,
  created_at   timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists public.cve_alerts_sent (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  cve_id     text not null,
  sent_at    timestamptz not null default now(),
  unique(user_id, cve_id)
);

-- ─── Device auth (Guardian install pairing) ──────────────────────────────────

create table if not exists public.device_auth_codes (
  id          uuid primary key default gen_random_uuid(),
  device_code text not null unique,
  user_code   text not null unique,
  user_id     uuid references auth.users(id) on delete cascade,
  authorized  boolean not null default false,
  expires_at  timestamptz not null,
  created_at  timestamptz not null default now()
);

-- ─── Shadow Mail ─────────────────────────────────────────────────────────────

create table if not exists public.mail_messages (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  from_address text,
  to_address   text,
  subject      text,
  body_text    text,
  body_html    text,
  headers      jsonb,
  read         boolean not null default false,
  created_at   timestamptz not null default now()
);

-- ─── Notifications & webhooks ────────────────────────────────────────────────

create table if not exists public.notification_prefs (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null unique references auth.users(id) on delete cascade,
  email_incidents     boolean not null default true,
  email_cve_alerts    boolean not null default true,
  webhook_incidents   boolean not null default false,
  webhook_cve_alerts  boolean not null default false,
  created_at          timestamptz not null default now()
);

create table if not exists public.webhooks (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  url        text not null,
  secret     text,
  events     text[] not null default '{}',
  active     boolean not null default true,
  created_at timestamptz not null default now()
);

-- ─── Audit log ───────────────────────────────────────────────────────────────

create table if not exists public.audit_log (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid references auth.users(id) on delete set null,
  action        text not null,
  resource_type text,
  resource_id   text,
  ip            text,
  metadata      jsonb,
  created_at    timestamptz not null default now()
);

-- ─── Teams ───────────────────────────────────────────────────────────────────

create table if not exists public.teams (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  owner_id   uuid not null references auth.users(id) on delete cascade,
  plan       text not null default 'community',
  created_at timestamptz not null default now()
);

create table if not exists public.team_members (
  id         uuid primary key default gen_random_uuid(),
  team_id    uuid not null references public.teams(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  role       text not null default 'member',
  created_at timestamptz not null default now(),
  unique(team_id, user_id)
);

-- ─── Referrals ───────────────────────────────────────────────────────────────

create table if not exists public.referral_redemptions (
  id          uuid primary key default gen_random_uuid(),
  referrer_id uuid not null references auth.users(id) on delete cascade,
  referred_id uuid not null references auth.users(id) on delete cascade,
  created_at  timestamptz not null default now(),
  unique(referred_id)
);

-- ─── Row-level security (Worker bypasses via service_role key) ───────────────

alter table public.profiles              enable row level security;
alter table public.user_profiles         enable row level security;
alter table public.agents                enable row level security;
alter table public.devices               enable row level security;
alter table public.scans                 enable row level security;
alter table public.incidents             enable row level security;
alter table public.missions              enable row level security;
alter table public.cve_alerts_sent       enable row level security;
alter table public.device_auth_codes     enable row level security;
alter table public.mail_messages         enable row level security;
alter table public.notification_prefs    enable row level security;
alter table public.webhooks              enable row level security;
alter table public.audit_log             enable row level security;
alter table public.teams                 enable row level security;
alter table public.team_members          enable row level security;
alter table public.referral_redemptions  enable row level security;

-- ─── Indexes ─────────────────────────────────────────────────────────────────

create index if not exists idx_agents_user_id     on public.agents(user_id);
create index if not exists idx_devices_user_id    on public.devices(user_id);
create index if not exists idx_scans_user_id      on public.scans(user_id);
create index if not exists idx_incidents_user_id  on public.incidents(user_id);
create index if not exists idx_mail_user_id       on public.mail_messages(user_id);
create index if not exists idx_audit_user_id      on public.audit_log(user_id);
create index if not exists idx_profiles_api_key   on public.profiles(api_key);

-- Calendar events
create table if not exists public.calendar_events (
  id          uuid        primary key default gen_random_uuid(),
  user_id     uuid        not null references auth.users(id) on delete cascade,
  title       text        not null check (char_length(title) <= 200),
  description text        check (char_length(description) <= 2000),
  start_at    timestamptz not null,
  end_at      timestamptz not null check (end_at >= start_at),
  all_day     boolean     not null default false,
  color       text        not null default '#b44aff',
  location    text        check (char_length(location) <= 500),
  created_at  timestamptz not null default now()
);
alter table public.calendar_events enable row level security;
create policy "owner" on public.calendar_events using (user_id = auth.uid());
create index if not exists idx_cal_user_range on public.calendar_events (user_id, start_at, end_at);
