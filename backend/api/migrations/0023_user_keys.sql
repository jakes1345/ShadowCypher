-- Per-user OpenPGP identity keys for zero-access encryption.
-- Private keys arrive already locked by the client (password-derived key, and
-- separately the user's recovery phrase); the server never holds either secret.

create table if not exists user_keys (
  user_id               uuid primary key references auth.users(id) on delete cascade,
  handle                text not null unique,
  fingerprint           text not null,
  public_key            text not null,
  encrypted_private_key text not null,
  recovery_private_key  text,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

-- No policies: only the API (service role) may read or write; the anon key gets nothing.
alter table user_keys enable row level security;
