-- ShadowCypher Phase 4K — device authorization flow (RFC 8628 style)
-- Lets shadow-cli / agent authenticate without asking the user to paste an API key.
-- Run AFTER 0001-0009. Idempotent.

create table if not exists public.device_auth_codes (
  device_code      text primary key,
  user_code        text not null unique,
  user_id          uuid references auth.users(id) on delete cascade,
  status           text not null default 'pending',  -- 'pending' | 'authorized' | 'denied' | 'expired' | 'consumed'
  client_label     text,                              -- "shadow-agent on hostname"
  expires_at       timestamptz not null,
  created_at       timestamptz not null default now(),
  authorized_at    timestamptz,
  consumed_at      timestamptz
);

create index if not exists idx_device_codes_status on public.device_auth_codes(status, expires_at);
create index if not exists idx_device_codes_user on public.device_auth_codes(user_id) where user_id is not null;

-- No RLS — accessed only via service-role from the Worker.
