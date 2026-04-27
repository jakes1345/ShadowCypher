-- ShadowCypher Phase 4A — trial period + tier limits
-- Run in Supabase SQL editor AFTER 0001 + 0002 idempotent migrations.

-- Add trial column
alter table public.profiles
  add column if not exists trial_ends_at timestamptz;

-- Backfill: any existing user without a trial date gets 14 days from now
update public.profiles
set trial_ends_at = now() + interval '14 days'
where trial_ends_at is null;

-- Update the new-user trigger to seed trial on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (user_id, email, handle, trial_ends_at)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'handle', split_part(new.email, '@', 1)),
    now() + interval '14 days'
  )
  on conflict (user_id) do nothing;
  return new;
end;
$$;
