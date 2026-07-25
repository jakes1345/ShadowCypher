-- ShadowCypher Neon Schema (backup/auth mirror)
-- Run this in your Neon project's SQL editor.

create table if not exists public.users (
  id            uuid primary key,
  email         text not null unique,
  password_hash text not null default '',
  created_at    timestamptz not null default now()
);

create table if not exists public.profiles (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null unique references public.users(id) on delete cascade,
  email      text not null,
  handle     text,
  plan       text not null default 'community',
  created_at timestamptz not null default now()
);

create table if not exists public.api_keys (
  id         uuid primary key default gen_random_uuid(),
  key        text not null unique,
  user_id    uuid not null references public.users(id) on delete cascade,
  revoked    boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_api_keys_key     on public.api_keys(key) where not revoked;
create index if not exists idx_api_keys_user_id on public.api_keys(user_id);
