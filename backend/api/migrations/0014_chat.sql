-- Chat rooms and messages

create table if not exists chat_rooms (
  id          uuid primary key default gen_random_uuid(),
  name        text unique not null,          -- slug: 'global', 'team-<uuid>'
  display_name text not null,                -- shown in sidebar: '#global'
  room_type   text not null default 'global', -- 'global' | 'team'
  team_id     uuid,
  created_at  timestamptz not null default now()
);

create table if not exists chat_messages (
  id          uuid primary key default gen_random_uuid(),
  room_id     uuid not null references chat_rooms(id) on delete cascade,
  user_id     uuid not null,
  nick        text not null,
  content     text not null check (char_length(content) between 1 and 2000),
  created_at  timestamptz not null default now()
);

create index if not exists chat_messages_room_created
  on chat_messages(room_id, created_at desc);

create table if not exists chat_presence (
  user_id   uuid not null,
  room_id   uuid not null references chat_rooms(id) on delete cascade,
  nick      text not null,
  seen_at   timestamptz not null default now(),
  primary key (user_id, room_id)
);

-- Seed the global room
insert into chat_rooms (name, display_name, room_type)
values ('global', '#global', 'global')
on conflict (name) do nothing;

-- Enable Supabase Realtime on messages
alter publication supabase_realtime add table chat_messages;
