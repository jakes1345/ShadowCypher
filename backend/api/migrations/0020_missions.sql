-- ShadowScript remote mission execution

create table if not exists missions (
  id              text primary key,                -- msn_<hex>
  agent_id        text not null,
  user_id         uuid not null,
  status          text not null default 'pending', -- pending | running | completed | failed
  script_content  text not null,
  label           text,
  created_at      timestamptz not null default now(),
  started_at      timestamptz,
  completed_at    timestamptz,
  result_output   text,
  exit_code       int
);

create index if not exists missions_agent_status
  on missions(agent_id, status, created_at asc);

create index if not exists missions_user_created
  on missions(user_id, created_at desc);
