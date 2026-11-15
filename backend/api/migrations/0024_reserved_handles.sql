-- Reserved handles.
--
-- Every user's address is handle@shadowcypher.site and sign-up goes straight
-- from the browser to Supabase Auth, so the only place that can stop someone
-- registering "security" or "billing" is the database.
--
-- This rejects a new account, or a change of email or handle, that would take
-- a reserved name. Accounts that already exist are left alone, so the
-- operator's own account keeps working.
--
-- The list must match RESERVED_HANDLES in backend/api/src/reserved.ts.
-- Mail sent to a reserved address is delivered to the operator's inbox by the
-- Worker, so these names do not need accounts of their own.

create or replace function public.reject_reserved_handle()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  reserved constant text[] := array[
    'shadow', 'shadowcypher', 'admin', 'administrator', 'root', 'sysadmin', 'owner',
    'official', 'staff', 'team', 'system', 'moderator', 'mod',
    'security', 'privacy', 'legal', 'billing', 'hello',
    'support', 'help', 'abuse', 'postmaster', 'hostmaster', 'webmaster', 'info',
    'contact', 'sales', 'press', 'jobs', 'dmca', 'copyright', 'compliance',
    'trust', 'safety', 'accounts', 'account', 'payments', 'refunds',
    'noreply', 'no_reply', 'mailer_daemon', 'notifications', 'alerts',
    'guardian', 'api', 'www', 'mail', 'status', 'docs', 'blog', 'dev', 'ops'
  ];
  local_part  text := lower(split_part(coalesce(new.email, ''), '@', 1));
  mail_domain text := lower(split_part(coalesce(new.email, ''), '@', 2));
  meta_handle text := lower(coalesce(new.raw_user_meta_data->>'handle', ''));
begin
  -- An update that leaves both the email and the handle alone is never a claim on a name.
  if tg_op = 'UPDATE'
     and new.email is not distinct from old.email
     and (new.raw_user_meta_data->>'handle') is not distinct from (old.raw_user_meta_data->>'handle')
  then
    return new;
  end if;

  if (mail_domain = 'shadowcypher.site' and local_part = any(reserved))
     or meta_handle = any(reserved)
  then
    raise exception 'handle_reserved'
      using errcode = '23514',
            hint = 'This handle is reserved. Choose a different one.';
  end if;

  return new;
end;
$$;

drop trigger if exists reject_reserved_handle on auth.users;

create trigger reject_reserved_handle
  before insert or update of email, raw_user_meta_data on auth.users
  for each row execute function public.reject_reserved_handle();
