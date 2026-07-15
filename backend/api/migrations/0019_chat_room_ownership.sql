-- Room ownership + topic so users can self-serve create/manage rooms
alter table chat_rooms
  add column if not exists created_by uuid,
  add column if not exists topic      text default null;
