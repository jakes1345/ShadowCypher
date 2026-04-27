-- ShadowCypher Billing — Phase 3 schema
-- Run after 0001_guardian.sql in Supabase SQL editor.
--
-- Creates a public.profiles table tied 1:1 to auth.users for non-auth-managed user fields.
-- Stripe billing fields live here so the Worker can update them via service-role on webhook events.
-- We mirror `plan` from user_metadata for fast read; profiles table is source of truth for billing.

create table if not exists public.profiles (
  user_id                  uuid primary key references auth.users(id) on delete cascade,
  email                    text,
  handle                   text,
  plan                     text not null default 'community',     -- 'community' | 'guardian_pro' | 'operator'
  stripe_customer_id       text unique,
  stripe_subscription_id   text unique,
  subscription_status      text,                                  -- 'active' | 'trialing' | 'past_due' | 'canceled' | 'incomplete'
  current_period_end       timestamptz,
  cancel_at_period_end     boolean not null default false,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);
create index if not exists idx_profiles_stripe_customer on public.profiles(stripe_customer_id);
create index if not exists idx_profiles_stripe_sub on public.profiles(stripe_subscription_id);
create index if not exists idx_profiles_plan on public.profiles(plan);

-- Auto-populate profiles row on user signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (user_id, email, handle)
  values (new.id, new.email, coalesce(new.raw_user_meta_data->>'handle', split_part(new.email, '@', 1)))
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Backfill existing users
insert into public.profiles (user_id, email, handle)
select id, email, coalesce(raw_user_meta_data->>'handle', split_part(email, '@', 1))
from auth.users
on conflict (user_id) do nothing;

-- ─── RLS ───────────────────────────────────────────────────────────────────
alter table public.profiles enable row level security;

create policy "profiles_select_own" on public.profiles
  for select to authenticated using (auth.uid() = user_id);

-- Users CAN update their own non-billing fields (handle), service-role handles plan changes
create policy "profiles_update_own_safe" on public.profiles
  for update to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
