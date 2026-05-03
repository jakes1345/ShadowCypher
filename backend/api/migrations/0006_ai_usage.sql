-- ShadowCypher Phase 4F — AI usage tracking, BYOK, monthly quotas
-- Run AFTER 0001-0005. Idempotent.

alter table public.profiles
  add column if not exists ai_query_count integer not null default 0,
  add column if not exists ai_query_period_start timestamptz not null default now(),
  add column if not exists ai_provider text not null default 'platform',  -- 'platform' | 'byok' | 'ollama'
  add column if not exists ai_byok_key_encrypted text,                     -- encrypted user-supplied Anthropic key
  add column if not exists ai_byok_key_last4 text,                         -- last 4 chars for UI display
  add column if not exists ai_ollama_url text;                             -- optional self-hosted endpoint

create index if not exists idx_profiles_ai_period on public.profiles(ai_query_period_start);

-- Helper: reset a user's monthly usage if their period started >30 days ago.
-- Called inline by the Worker before each query — no cron needed.
