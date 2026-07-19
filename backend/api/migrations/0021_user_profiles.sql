-- Public user profiles (social links, bio, avatar)

create table if not exists user_profiles (
  user_id     uuid primary key references auth.users(id) on delete cascade,
  handle      text,
  bio         text,
  avatar_url  text,
  website     text,
  twitter     text,
  github      text,
  discord     text,
  location    text,
  is_public   boolean not null default true,
  updated_at  timestamptz not null default now()
);
