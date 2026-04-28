-- ShadowCypher Phase 4E — team / family accounts
-- Run AFTER 0001/0002/0003/0004. Idempotent — safe to re-run.

-- ─── teams ─────────────────────────────────────────────────────────────────
create table if not exists public.teams (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  owner_id      uuid not null references auth.users(id) on delete cascade,
  created_at    timestamptz not null default now()
);
create index if not exists idx_teams_owner on public.teams(owner_id);

-- ─── team_members ──────────────────────────────────────────────────────────
create table if not exists public.team_members (
  team_id       uuid not null references public.teams(id) on delete cascade,
  user_id       uuid references auth.users(id) on delete cascade,
  invited_email text,                                  -- nullable until accept
  role          text not null default 'member',       -- 'owner' | 'member'
  status        text not null default 'pending',      -- 'pending' | 'active'
  invited_at    timestamptz not null default now(),
  joined_at     timestamptz,
  primary key (team_id, coalesce(user_id, '00000000-0000-0000-0000-000000000000'::uuid), coalesce(invited_email, ''))
);
create index if not exists idx_team_members_user on public.team_members(user_id) where user_id is not null;
create index if not exists idx_team_members_email on public.team_members(invited_email) where invited_email is not null;

-- ─── RLS ───────────────────────────────────────────────────────────────────
alter table public.teams enable row level security;
alter table public.team_members enable row level security;

drop policy if exists "teams_select_member" on public.teams;
drop policy if exists "teams_update_owner"  on public.teams;
drop policy if exists "team_members_select_self_or_member" on public.team_members;

-- Read teams I own or am a member of
create policy "teams_select_member" on public.teams
  for select to authenticated
  using (
    auth.uid() = owner_id
    or exists (
      select 1 from public.team_members tm
      where tm.team_id = teams.id
        and tm.user_id = auth.uid()
        and tm.status = 'active'
    )
  );

-- Owner can rename their own team
create policy "teams_update_owner" on public.teams
  for update to authenticated
  using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

-- Members can read membership rows for teams they belong to (for the member list UI)
create policy "team_members_select_self_or_member" on public.team_members
  for select to authenticated
  using (
    user_id = auth.uid()
    or invited_email = (auth.jwt() ->> 'email')
    or exists (
      select 1 from public.teams t
      where t.id = team_members.team_id
        and (t.owner_id = auth.uid()
             or exists (
               select 1 from public.team_members tm2
               where tm2.team_id = t.id
                 and tm2.user_id = auth.uid()
                 and tm2.status = 'active'
             ))
    )
  );
