-- Add os_fingerprint column to devices table for CVE matching
-- Run in Supabase SQL editor

alter table public.devices
  add column if not exists os_fingerprint text;
