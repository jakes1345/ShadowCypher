-- Read receipts for DM rooms (one row per user per room, upserted on read)
create table if not exists dm_read_receipts (
  room_id      text        not null,
  user_id      uuid        not null,
  nick         text        not null default '',
  last_read_at timestamptz not null default now(),
  primary key (room_id, user_id)
);

create index if not exists dm_read_receipts_room
  on dm_read_receipts(room_id);
