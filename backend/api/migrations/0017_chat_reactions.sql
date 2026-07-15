-- Emoji reactions on chat messages
create table if not exists chat_reactions (
  message_id  uuid not null references chat_messages(id) on delete cascade,
  user_id     uuid not null,
  emoji       text not null check (char_length(emoji) between 1 and 8),
  created_at  timestamptz not null default now(),
  primary key (message_id, user_id, emoji)
);

create index if not exists chat_reactions_message
  on chat_reactions(message_id);
