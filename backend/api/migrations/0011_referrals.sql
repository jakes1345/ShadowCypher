-- ShadowCypher Phase 4L — referral program
-- Run AFTER 0001-0010. Idempotent.
--
-- Each profile gets a short URL-safe referral code. New signups can attribute themselves
-- via /r/<code> on the marketing site. When a referee subscribes to a paid plan, the
-- referrer gets 30 days of Guardian Pro credit (we mark it; the actual application
-- happens by extending trial_ends_at — simplest possible model for v1).

alter table public.profiles
  add column if not exists referral_code  text unique,
  add column if not exists referred_by    uuid references auth.users(id) on delete set null,
  add column if not exists referral_credits_pending  int not null default 0;  -- days of credit owed but not yet applied

-- Generate codes for any existing rows that don't have one
do $$
declare
  r record;
  code text;
  alphabet text := 'abcdefghjkmnpqrstuvwxyz23456789';  -- no 0/o/1/i/l
begin
  for r in select user_id from public.profiles where referral_code is null loop
    code := '';
    for _ in 1..8 loop
      code := code || substr(alphabet, 1 + (floor(random() * length(alphabet)))::int, 1);
    end loop;
    update public.profiles set referral_code = code where user_id = r.user_id;
  end loop;
end $$;

create index if not exists idx_profiles_referral_code on public.profiles(referral_code);

-- Auto-issue a referral code on every future signup
create or replace function public.assign_referral_code()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  alphabet text := 'abcdefghjkmnpqrstuvwxyz23456789';
  i int;
  code text;
begin
  if NEW.referral_code is null then
    code := '';
    for i in 1..8 loop
      code := code || substr(alphabet, 1 + (floor(random() * length(alphabet)))::int, 1);
    end loop;
    NEW.referral_code := code;
  end if;
  return NEW;
end;
$$;

drop trigger if exists profiles_assign_referral_code on public.profiles;
create trigger profiles_assign_referral_code
  before insert on public.profiles
  for each row execute function public.assign_referral_code();

-- Track redemptions so we can audit who paid out what
create table if not exists public.referral_redemptions (
  id            uuid primary key default gen_random_uuid(),
  referrer_id   uuid not null references auth.users(id) on delete cascade,
  referee_id    uuid not null references auth.users(id) on delete cascade,
  credit_days   int  not null default 30,
  applied_at    timestamptz not null default now(),
  unique(referrer_id, referee_id)
);

create index if not exists idx_redemptions_referrer on public.referral_redemptions(referrer_id);
create index if not exists idx_redemptions_referee on public.referral_redemptions(referee_id);
