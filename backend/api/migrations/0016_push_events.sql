-- Push notification per-event controls
-- Apply to Supabase via SQL Editor or migrations runner before deploying the
-- corresponding Worker update.

ALTER TABLE notification_prefs
  ADD COLUMN IF NOT EXISTS mail_push_enabled    boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS mention_push_enabled boolean NOT NULL DEFAULT true;
